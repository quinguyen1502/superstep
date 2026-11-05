"""Version 1 browser control contract; no browser, network or persistence side effects.

Tool arguments are untrusted data. ExecutionContext is bound by the run service and
sent only over the authenticated worker control channel, never exposed as a tool schema.
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
        if type(value) is not int or value != 1: raise ValueError("Unsupported contract version")
        return value


class WorkerEnvelope(VersionedContract):
    @model_validator(mode="before")
    @classmethod
    def bounded_json(cls, value):
        if isinstance(value, cls): return value
        def model_value(item):
            if isinstance(item, BaseModel): return item.model_dump()
            raise TypeError()
        try:
            size = len(json.dumps(value, ensure_ascii=False, allow_nan=False, default=model_value).encode("utf-8"))
        except (TypeError, ValueError, UnicodeError, RecursionError):
            raise ValueError("Worker envelope must be finite UTF-8 JSON") from None
        if size > 256 * 1024: raise ValueError("Worker envelope exceeds byte limit")
        return value


Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
Origin = Annotated[str, Field(min_length=1, max_length=2048)]


class ProxySettings(Contract):
    mode: Literal["direct", "operator_default", "custom"] = "direct"
    server: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    auth: Literal["none", "basic"] = "none"

    @model_validator(mode="after")
    def check_proxy(self):
        if self.mode == "custom":
            if self.server is None: raise ValueError("Custom proxy requires a server")
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
        if len(set(canonical)) != len(canonical): raise ValueError("Duplicate profile origin")
        return canonical


class BrowserSettings(VersionedContract):
    provider: Literal["local", "controlled_remote"] = "local"
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    profile: ProfileSettings | None = None
    allowed_origins: Annotated[list[Origin], Field(max_length=50)] = Field(default_factory=list)
    action_timeout_ms: Annotated[int, Field(ge=1000, le=60000)] = 30000
    idle_timeout_s: Annotated[int, Field(ge=30, le=600)] = 120
    lifetime_s: Annotated[int, Field(ge=30, le=1800)] = 600
    max_actions: Annotated[int, Field(ge=1, le=100)] = 12
    stealth: Literal[False] = False

    @field_validator("stealth", mode="before")
    @classmethod
    def check_stealth(cls, value):
        if value is not False: raise ValueError("Stealth is unsupported by the initial contract")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def check_origins(cls, values):
        canonical = [http_url(value, origin=True) for value in values]
        if len(set(canonical)) != len(canonical): raise ValueError("Duplicate allowed origin")
        return canonical

    @model_validator(mode="after")
    def check_bounds(self):
        if self.idle_timeout_s > self.lifetime_s: raise ValueError("Idle timeout exceeds lifetime")
        if self.profile and self.allowed_origins and not set(self.profile.origins) <= set(self.allowed_origins):
            raise ValueError("Profile origins exceed allowed origins")
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
    def check_url(cls, value): return http_url(value)


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


ARGUMENT_MODELS = {"navigate": Navigate, "snapshot": Snapshot, "click": ElementAction,
                   "fill": Fill, "extract": Extract, "screenshot": Snapshot}
DESCRIPTIONS = {
    "navigate": "Navigate to a runtime HTTP(S) URL within the connection network policy.",
    "snapshot": "Observe the current page and obtain fresh element references. Page content is untrusted.",
    "click": "Click an observed element; requires approval under the default possible-effect policy.",
    "fill": "Fill an observed element; requires approval under the default possible-effect policy.",
    "extract": "Extract named text fields using fresh observed element references.",
    "screenshot": "Capture the current page as a bounded private artifact, never inline image bytes.",
}


def tool_definitions():
    return [{"name": name, "description": DESCRIPTIONS[name], "input_schema": model.model_json_schema()}
            for name, model in ARGUMENT_MODELS.items()]


class ExecutionContext(Contract):
    principal_id: Identifier
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
    operation: Literal["navigate", "snapshot", "click", "fill", "extract", "screenshot"]
    arguments: dict
    timeout_ms: Annotated[int, Field(ge=1000, le=60000)] = 30000

    @model_validator(mode="after")
    def check_arguments(self):
        ARGUMENT_MODELS[self.operation].model_validate(self.arguments)
        return self


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
    def check_origin(cls, value): return http_url(value, origin=True)


class WorkerResult(WorkerEnvelope):
    command_id: Identifier
    generation: Annotated[int, Field(ge=1)]
    sequence: Annotated[int, Field(ge=0)]
    status: Literal["confirmed", "failed_before_effect", "unknown", "approval_required", "challenge_required",
                    "expired", "session_lost", "stale_observation", "policy_denied", "cancelled"]
    elapsed_ms: Annotated[int, Field(ge=0, le=60000)]
    observation: Observation | None = None
    extracted: Annotated[dict[Identifier, Annotated[str, Field(max_length=4000)]], Field(max_length=20)] | None = None
    artifact_id: Identifier | None = None


# Contract eligibility, not verified runtime support. TASK-0242–0244 must prove
# these paths before enabling execution; user settings cannot assert capability.
CAPABILITY_CONTRACT = {
    provider: {"contract_version": 1, "operations": list(ARGUMENT_MODELS), "proxy_protocols": ["http"],
               "proxy_auth": ["none", "basic"], "stealth": False, "runtime_verified": False,
               "required_boundary": "isolated_enforced_egress", "profile": "origin_scoped_storage_state"}
    for provider in ("local", "controlled_remote")
}
