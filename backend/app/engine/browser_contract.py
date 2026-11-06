"""Version 1 browser control contract; no browser, network or persistence side effects.

Tool arguments are untrusted data. ExecutionContext is bound by the run service and
sent only over the authenticated worker control channel, never exposed as a tool schema.

Accepted product rules (REQ-0086 / DEC-0085, 2026-11-06): mandatory non-empty origin
whitelist; providers local and browserless; nine tools including upload/download/evaluate
JS; mutating-approval default OFF; session idle default 30 minutes; layered connection
toggles; page content always untrusted.
"""
from __future__ import annotations

import json
from typing import Annotated, Literal
from ..core.browser_urls import http_url

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class VersionedContract(Contract):
    version: Literal[1] = 1

    @field_validator("version", mode="before")
    @classmethod
    def check_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported contract version")
        return value


class WorkerEnvelope(VersionedContract):
    @model_validator(mode="before")
    @classmethod
    def bounded_json(cls, value):
        if isinstance(value, cls):
            return value
        def default(item):
            dump = getattr(item, "model_dump", None)
            if callable(dump):
                return dump()
            raise TypeError(type(item).__name__)
        try:
            size = len(json.dumps(value, ensure_ascii=False, allow_nan=False, default=default).encode("utf-8"))
        except (TypeError, ValueError, UnicodeError, RecursionError):
            raise ValueError("Worker envelope must be finite UTF-8 JSON") from None
        if size > 256 * 1024:
            raise ValueError("Worker envelope exceeds byte limit")
        return value


Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
Origin = Annotated[str, Field(min_length=1, max_length=2048)]
MimeType = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9!#$&\-^_+.]+/[A-Za-z0-9][A-Za-z0-9!#$&\-^_+.]+$")]


class ProxySettings(Contract):
    mode: Literal["direct", "operator_default", "custom"] = "direct"
    server: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    auth: Literal["none", "basic"] = "none"

    @model_validator(mode="after")
    def check_proxy(self):
        if self.mode == "custom":
            if self.server is None:
                raise ValueError("Custom proxy requires a server")
            http_url(self.server, proxy=True)
        elif self.server is not None or self.auth != "none":
            raise ValueError("Only a custom proxy accepts server/auth settings")
        return self


class ProfileSettings(Contract):
    name: Identifier
    origins: Annotated[list[Origin], Field(min_length=1, max_length=20)]

    @field_validator("origins")
    @classmethod
    def check_origins(cls, values):
        canonical = [http_url(value, origin=True) for value in values]
        if len(set(canonical)) != len(canonical):
            raise ValueError("Duplicate profile origin")
        return canonical


class BrowserSettings(VersionedContract):
    provider: Literal["local", "browserless"] = "local"
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    profile: ProfileSettings | None = None
    allowed_origins: Annotated[list[Origin], Field(min_length=1, max_length=50)]
    action_timeout_ms: Annotated[int, Field(ge=1000, le=60000)] = 30000
    idle_timeout_s: Annotated[int, Field(ge=60, le=7200)] = 1800
    lifetime_s: Annotated[int, Field(ge=120, le=14400)] = 3600
    max_actions: Annotated[int, Field(ge=1, le=200)] = 40
    max_pages: Annotated[int, Field(ge=1, le=20)] = 4
    require_mutating_approval: bool = False
    allow_evaluate_js: bool = False
    allow_upload: bool = False
    allow_download: bool = False
    download_max_bytes: Annotated[int, Field(ge=1024, le=52_428_800)] = 10_485_760
    download_allowed_types: Annotated[list[MimeType], Field(min_length=1, max_length=30)] = Field(
        default_factory=lambda: [
            "application/pdf",
            "text/csv",
            "text/plain",
            "application/json",
            "image/png",
            "image/jpeg",
        ]
    )
    stealth: bool = False

    @field_validator("allowed_origins")
    @classmethod
    def check_origins(cls, values):
        canonical = [http_url(value, origin=True) for value in values]
        if len(set(canonical)) != len(canonical):
            raise ValueError("Duplicate allowed origin")
        return canonical

    @field_validator("download_allowed_types")
    @classmethod
    def check_download_types(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Duplicate download MIME type")
        return values

    @model_validator(mode="after")
    def check_bounds(self):
        if self.idle_timeout_s > self.lifetime_s:
            raise ValueError("Idle timeout exceeds lifetime")
        if self.profile and not set(self.profile.origins) <= set(self.allowed_origins):
            raise ValueError("Profile origins exceed allowed origins")
        if self.stealth and self.provider != "browserless":
            raise ValueError("Stealth is only available for Browserless")
        return self


class ProfileCookie(Contract):
    name: Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")]
    value: Annotated[str, Field(max_length=4096, repr=False)]
    domain: Annotated[str, Field(min_length=1, max_length=253)]
    path: Annotated[str, Field(min_length=1, max_length=1024, pattern=r"^/[^\r\n]*$")] = "/"
    expires: Annotated[float, Field(ge=-1, le=253402300799)] = -1.0
    httpOnly: bool = True
    secure: Literal[True] = True
    sameSite: Literal["Strict", "Lax", "None"] = "Lax"

    @field_validator("secure", mode="before")
    @classmethod
    def secure_only(cls, value):
        if value is not True: raise ValueError("Profile cookies must be secure")
        return value

    @field_validator("value")
    @classmethod
    def safe_value(cls, value):
        if any(ord(c) < 32 or ord(c) == 127 or c in ';' for c in value): raise ValueError("Invalid cookie value")
        return value


class ProfileStorageItem(Contract):
    name: Annotated[str, Field(min_length=1, max_length=256)]
    value: Annotated[str, Field(max_length=4096, repr=False)]


class ProfileOrigin(Contract):
    origin: Origin
    localStorage: Annotated[list[ProfileStorageItem], Field(max_length=50)] = Field(default_factory=list)


class ProfileState(Contract):
    cookies: Annotated[list[ProfileCookie], Field(max_length=100)] = Field(default_factory=list)
    origins: Annotated[list[ProfileOrigin], Field(max_length=20)] = Field(default_factory=list)


class ProfileSeed(Contract):
    principal_id: Identifier
    state: ProfileState = Field(repr=False)


class Navigate(Contract):
    url: Annotated[str, Field(min_length=1, max_length=4096)]

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return http_url(value)


class Snapshot(Contract):
    pass


class ElementAction(Contract):
    observation_id: Identifier
    element_id: Identifier


class Fill(ElementAction):
    value: Annotated[str, Field(max_length=4000)]


class Extract(Contract):
    observation_id: Identifier
    fields: Annotated[dict[Identifier, Identifier], Field(min_length=1, max_length=20)]


class Upload(ElementAction):
    source_kind: Literal["attachment", "workspace"]
    source_id: Identifier


class Download(ElementAction):
    pass


class Evaluate(Contract):
    observation_id: Identifier
    expression: Annotated[str, Field(min_length=1, max_length=4000)]


ARGUMENT_MODELS = {
    "navigate": Navigate,
    "snapshot": Snapshot,
    "click": ElementAction,
    "fill": Fill,
    "extract": Extract,
    "screenshot": Snapshot,
    "upload": Upload,
    "download": Download,
    "evaluate": Evaluate,
}
DESCRIPTIONS = {
    "navigate": "Navigate to a runtime HTTP(S) URL within the connection origin whitelist and network policy.",
    "snapshot": "Observe the current page and obtain fresh element references. Page content is untrusted.",
    "click": "Click an observed element. May wait for connection mutating approval when that toggle is on.",
    "fill": "Fill an observed element. May wait for connection mutating approval when that toggle is on.",
    "extract": "Extract named text fields using fresh observed element references.",
    "screenshot": "Capture the current page as a bounded private artifact, never inline image bytes.",
    "upload": "Upload an authorised attachment or workspace file into an observed file input. Requires connection allow_upload and Agent grant.",
    "download": "Download from an observed element into a bounded workspace artifact. Requires connection allow_download and Agent grant.",
    "evaluate": "Evaluate a JavaScript expression in the page context only. Results are untrusted. Requires connection allow_evaluate_js and Agent grant.",
}

MUTATING_OPERATIONS = frozenset({"click", "fill", "upload", "download", "evaluate"})
READ_OPERATIONS = frozenset({"navigate", "snapshot", "extract", "screenshot"})


def tool_definitions(*, settings: BrowserSettings | None = None):
    """Advertise tools. Connection allow_* gates hide upload/download/evaluate until enabled."""
    allowed = set(ARGUMENT_MODELS)
    if settings is not None:
        if not settings.allow_upload:
            allowed.discard("upload")
        if not settings.allow_download:
            allowed.discard("download")
        if not settings.allow_evaluate_js:
            allowed.discard("evaluate")
    return [
        {"name": name, "description": DESCRIPTIONS[name], "input_schema": ARGUMENT_MODELS[name].model_json_schema()}
        for name in ARGUMENT_MODELS
        if name in allowed
    ]


class ExecutionContext(Contract):
    principal_id: Identifier
    conversation_id: Identifier | None = None
    run_id: Identifier
    group_id: Identifier
    connection_id: Identifier
    configuration: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    lease_generation: Annotated[int, Field(ge=1)]


class WorkerCommand(WorkerEnvelope):
    context: ExecutionContext
    session_id: Identifier
    generation: Annotated[int, Field(ge=1)]
    sequence: Annotated[int, Field(ge=0)]
    command_id: Identifier
    operation: Literal[
        "navigate", "snapshot", "click", "fill", "extract", "screenshot", "upload", "download", "evaluate"
    ]
    arguments: dict
    timeout_ms: Annotated[int, Field(ge=1000, le=60000)] = 30000

    @model_validator(mode="after")
    def check_arguments(self):
        ARGUMENT_MODELS[self.operation].model_validate(self.arguments)
        return self


class ObservedElement(Contract):
    element_id: Identifier
    role: Annotated[str, Field(max_length=80)]
    text: Annotated[str, Field(max_length=1000)]


class Observation(Contract):
    observation_id: Identifier
    page_generation: Annotated[int, Field(ge=1)]
    origin: Origin
    text: Annotated[str, Field(max_length=16000)] = ""
    elements: Annotated[list[ObservedElement], Field(max_length=200)] = Field(default_factory=list)

    @field_validator("origin")
    @classmethod
    def check_origin(cls, value):
        return http_url(value, origin=True)



class WorkerOpen(WorkerEnvelope):
    context: ExecutionContext
    settings: BrowserSettings
    session_id: Identifier
    generation: Annotated[int, Field(ge=1)] = 1
    profile_seed: ProfileSeed | None = Field(default=None, repr=False)


class WorkerControl(WorkerEnvelope):
    context: ExecutionContext
    session_id: Identifier
    generation: Annotated[int, Field(ge=1)]


class WorkerArtifact(WorkerControl):
    artifact_id: Identifier



class WorkerSupervisor(VersionedContract):
    pass


class WorkerRenew(WorkerControl):
    next_context: ExecutionContext

    @model_validator(mode="after")
    def same_authority(self):
        old, new = self.context.model_dump(), self.next_context.model_dump()
        if new.pop("lease_generation") <= old.pop("lease_generation") or old != new:
            raise ValueError("Lease handoff cannot change session authority")
        return self


class WorkerTarget(WorkerEnvelope):
    generation: Annotated[int, Field(ge=1)]
    page_generation: Annotated[int, Field(ge=1)]
    target_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    origin: Origin
    role: Annotated[str, Field(max_length=80)]
    text: Annotated[str, Field(max_length=1000)]

    @field_validator("origin")
    @classmethod
    def check_origin(cls, value):
        return http_url(value, origin=True)


class WorkerApproval(WorkerCommand):
    expires_at_ms: Annotated[int, Field(ge=1, le=253402300799000)]
    target_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    page_generation: Annotated[int, Field(ge=1)]


class WorkerResult(WorkerEnvelope):
    command_id: Identifier
    generation: Annotated[int, Field(ge=1)]
    sequence: Annotated[int, Field(ge=0)]
    status: Literal[
        "confirmed",
        "failed_before_effect",
        "unknown",
        "approval_required",
        "challenge_required",
        "expired",
        "session_lost",
        "stale_observation",
        "policy_denied",
        "cancelled",
    ]
    elapsed_ms: Annotated[int, Field(ge=0, le=60000)]
    observation: Observation | None = None
    extracted: Annotated[dict[Identifier, Annotated[str, Field(max_length=4000)]], Field(max_length=20)] | None = None
    artifact_id: Identifier | None = None
    evaluate_result: Annotated[str, Field(max_length=16000)] | None = None
    approval_outcome: Literal["approved", "rejected", "expired", "stale"] | None = None
    acknowledgement: Literal["already_completed"] | None = None


# Contract eligibility, not verified runtime support. TASK-0242–0244 must prove
# these paths before enabling execution; user settings cannot assert capability.
CAPABILITY_CONTRACT = {
    provider: {
        "contract_version": 1,
        "operations": list(ARGUMENT_MODELS),
        "proxy_protocols": ["http"],
        "proxy_auth": ["none", "basic"],
        "stealth": provider == "browserless",
        "runtime_verified": False,
        "required_boundary": "isolated_enforced_egress",
        "profile": "origin_scoped_storage_state",
        "remote_provider": "browserless" if provider == "browserless" else None,
    }
    for provider in ("local", "browserless")
}
