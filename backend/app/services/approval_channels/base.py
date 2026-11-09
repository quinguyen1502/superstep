"""ApprovalChannel adapter interface.

An adapter knows one messaging platform: how to post an approval request with two buttons, how to authenticate and
parse the platform's callback, and how to edit the original message afterwards. Business rules (tokens, identity
mapping, authorization, audit, resuming the run) live in ApprovalService, so a new channel (WhatsApp, Teams, e-mail)
is one more subclass registered in `ADAPTERS`. WhatsApp has buttons like Slack and Telegram; e-mail and Teams are link
channels (`link_based`, ).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any, Optional
import httpx
from ...core.errors import AppError


@dataclass
class ApprovalMessage:
    """What an approval request says, channel-neutral (plain text; adapters format it)."""
    title: str
    lines: list[str]
    link: Optional[str]
    approve_token: str
    reject_token: str
    approve_label: str = "Approve"   # button / link texts in the owner's language
    reject_label: str = "Reject"
    open_label: str = "Open in Superstep"


@dataclass
class Callback:
    """A button press, parsed from the platform's callback."""
    token: str
    external_user: str
    context: dict = field(default_factory=dict)  # what acknowledge() needs (response_url, callback_query_id, ...)


@dataclass
class IncomingMessage:
    """A message to the bot, parsed from the platform's callback: chat triggers match its first word."""
    team: str      # workspace (Slack team id); "" on platforms without workspaces
    place: str     # "dm" (a direct message to the bot) or the channel / chat id
    sender: str    # platform user id
    text: str      # without the bot mention
    key: str       # the platform's id of this delivery (Slack event_id, Telegram update_id): retries carry the same one
    ref: dict = field(default_factory=dict)  # where replies go (reply() / reply_private())
    event: dict = field(default_factory=dict)  # bounded, untrusted event metadata; never studio authority


class ApprovalChannel:
    kind: str = ""
    label: str = ""                         # display name in messages ("Slack")
    fields: tuple[str, ...] = ()            # secret settings the owner enters (all encrypted)
    optional: tuple[str, ...] = ()          # of those, the ones that may be empty (adapter fills a default)
    patterns: dict[str, str] = {}           # field -> regex it must match
    identity_pattern: str = r".+"           # shape of a platform user id
    hint_field: str = ""                    # which secret the masked hint shows
    per_team: bool = False                  # identities are per workspace (Slack user ids belong to one workspace)
    shared_callback: bool = False           # one callback URL for every connection, routed by route_key() (Slack)
    transport: Optional[httpx.BaseTransport] = None  # tests plug in httpx.MockTransport
    # a link channel (e-mail, Teams) has no buttons that call us back. Its message links to the studio's
    # /approve page, where the signed-in studio user decides, so there is no chat identity to verify.
    link_based: bool = False
    target_required: bool = True            # False: the connection itself is the destination (a Teams webhook)
    # : chat triggers start runs from messages to the bot.
    chat: bool = False                      # the platform can start runs from messages (Slack, Telegram)
    events_only: bool = False               # inbound source, unavailable for approval delivery/identity linking
    chat_scopes: tuple[str, ...] = ()       # OAuth scopes messages need (Slack); describe() reports the granted ones
    events_path: Optional[str] = None       # a separate URL that receives messages (Slack Events API); None: the callback URL
    place_pattern: str = r".+"              # a chat a trigger may listen in (besides "dm"): Slack channel id, Telegram chat id

    # ---- configuration ----
    def prepare(self, values: dict) -> dict:
        """Validate the owner's settings; returns the dict to encrypt. Raises CHANNEL_CONFIG_INVALID {field}."""
        out = {}
        for f in self.fields:
            v = values.get(f); v = v.strip() if isinstance(v, str) else v
            if not v:
                if f in self.optional: continue
                raise AppError("CHANNEL_CONFIG_INVALID", field=f)
            if not isinstance(v, str) or (f in self.patterns and not re.fullmatch(self.patterns[f], v)): raise AppError("CHANNEL_CONFIG_INVALID", field=f)
            out[f] = v
        return out

    def valid_identity(self, external_id: str) -> bool: return bool(re.fullmatch(self.identity_pattern, external_id))

    def describe(self, secrets: dict) -> dict:
        """Check the credentials with the platform and name the account behind them: {"name", "team_id"}, plus
        "scopes" (granted, sorted) on platforms with OAuth scopes. Raises CHANNEL_API_FAILED when the platform refuses them."""
        return {"name": None, "team_id": None}

    def route_key(self, body: bytes) -> Optional[str]:
        """The account (team_id) an unauthenticated callback claims to come from, for the shared callback URL."""
        return None

    def challenge(self, secrets: dict, query: dict) -> Optional[str]:
        """Answer a platform's GET verification of the callback URL (WhatsApp); None: not supported."""
        return None

    def register(self, secrets: dict, callback_url: str) -> dict:
        """Point the platform at our callback URL when its API allows it. Default: manual setup, nothing to do."""
        return {"registered": False, "manual": True}

    # ---- the four operations ----
    def send_request(self, secrets: dict, target: str, msg: ApprovalMessage) -> dict:
        """Post the request with Approve/Reject buttons. Returns the message reference used by update()."""
        raise NotImplementedError

    def verify(self, secrets: dict, headers: dict, body: bytes) -> None:
        """Authenticate a callback (signature / secret header). Raises CHANNEL_SIGNATURE_INVALID."""
        raise NotImplementedError

    def handle_callback(self, body: bytes) -> Optional[Callback]:
        """Parse a verified callback into a button press; None for events that are not one (ignored)."""
        raise NotImplementedError

    def acknowledge(self, secrets: dict, cb: Callback, text: str, accepted: bool) -> None:
        """Tell the person who pressed the button what happened (only them when refused)."""

    def update(self, secrets: dict, ref: dict, text: str) -> None:
        """Replace the original message (buttons removed) with the outcome."""
        raise NotImplementedError

    def send_dm(self, secrets: dict, external_id: str, text: str) -> None:
        """Send a private message to one platform user (the identity verification code)."""
        raise NotImplementedError

    # ---- chat triggers: only platforms with `chat` ----
    def handle_message(self, body: bytes) -> Optional[IncomingMessage]:
        """Parse a message to the bot; None for anything else (bots, edits, joins, files, button presses)."""
        return None

    def event_challenge(self, body: bytes) -> Optional[str]:
        """The value to echo when the platform checks the events URL (Slack url_verification); None otherwise."""
        return None

    def reply(self, secrets: dict, ref: dict, text: str) -> None:
        """Answer in the message's thread, for everyone in the chat."""
        raise NotImplementedError

    def reply_private(self, secrets: dict, ref: dict, sender: str, text: str) -> None:
        """Answer the sender only (refusals)."""
        raise NotImplementedError

    # ---- HTTP helper ----
    def call(self, method: str, url: str, **kw) -> Any:
        try:
            with httpx.Client(timeout=10, transport=self.transport) as c: r = c.request(method, url, **kw)
            data = r.json()
        except (httpx.HTTPError, ValueError) as e: raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=type(e).__name__)
        return r, data
