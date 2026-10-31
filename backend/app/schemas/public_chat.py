"""Models of the public Chat API v1 (TASK-0215, REQ-0082, DEC-0078): the published chat page's HTTP routes.

They document `/api/public/v1/chat/{slug}/...` in OpenAPI and in the public spec (docs/api/openapi.public.json). The
payloads are built by `services.public_chat_service` and `services.chat_attachment_service`; tests check that real
responses validate against these models. The v1 contract is additive only: new optional fields, never a removed one.
"""
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from .envelope import Envelope

Access = Literal["studio", "anonymous", "signed_in"]
StepsMode = Literal["none", "labels", "full"]


class Open(BaseModel):
    model_config = ConfigDict(extra="allow")  # v1 is additive: clients must ignore fields they do not know


class AttachmentLimits(Open):
    enabled: bool
    kinds: list[str] = Field(..., description="Allowed kinds: `document`, `image`.")
    max_files: int
    max_mb: float


class ChatPage(Open):
    """The published chat page: what a client shows before the first message."""
    slug: str = Field(..., examples=["support"])
    title: str = Field(..., examples=["Support"])
    intro: str = Field("", description="Markdown shown above the first message.")
    suggestions: list[str] = Field(default_factory=list, description="Up to 4 suggested first messages.")
    access: Access
    steps_mode: StepsMode = Field(..., description="What a visitor sees of the run's steps.")
    signed_in: bool = Field(..., description="Whether the caller is a signed-in studio user.")
    embed_origins: list[str] = Field(default_factory=list, description="Sites that may embed the page in an iframe.")
    logo: Optional[str] = Field(None, description="Hash of the logo; fetch it from `.../logo?v=<hash>`.")
    attachments: AttachmentLimits


class ChatSession(Open):
    id: str = Field(..., examples=["c7d1e0a9b2"])
    workflow_id: str
    channel: str
    title: str
    last_run_id: Optional[str] = None
    created: float = Field(..., description="Unix time (seconds).")
    updated: float = Field(..., description="Unix time (seconds).")
    visitor_token: Optional[str] = Field(None, description="Set once for a new anonymous visitor that sent `X-Chat-Visitor: new`: keep "
                                                            "it and send it back in `X-Chat-Visitor`.")


class ChatSessionList(Open):
    sessions: list[ChatSession]
    visitor_token: Optional[str] = None


class ChatAttachment(Open):
    id: str
    name: str
    kind: str
    mime: str
    size: int = Field(..., description="Bytes.")
    visitor_token: Optional[str] = None


class ChatRating(Open):
    value: Literal["up", "down"]
    comment: str = ""
    updated: float
    visitor_token: Optional[str] = None


class ChatTurn(Open):
    id: str
    role: Literal["user", "assistant"]
    text: str
    status: Optional[str] = Field(None, description="Answer status, e.g. `ok`, `error`, `waiting`, `cancelled`.")
    run_id: Optional[str] = None
    node: Optional[str] = Field(None, description="Set on a Human node's question: the node to answer.")
    answered_by: Optional[str] = None
    code: Optional[str] = Field(None, description="Error code of a failed answer.")
    created: float
    attachments: list[ChatAttachment] = Field(default_factory=list)
    rating: Optional[ChatRating] = None
    run_exists: Optional[bool] = None
    steps: Optional[list[dict[str, Any]]] = Field(None, description="The run's steps in `steps_mode`, on the run's first answer.")


class ChatSessionView(ChatSession):
    """One chat with its turns in the page's steps mode."""
    steps_mode: StepsMode
    turns: list[ChatTurn]


class ChatTurns(Open):
    """The turns after `after` (incremental history): poll with the id of the last turn you have."""
    turns: list[ChatTurn]
    visitor_token: Optional[str] = None


class Ok(Open):
    ok: bool = True
    visitor_token: Optional[str] = None


class ChatPageEnvelope(Envelope[ChatPage]): """Success envelope: the chat page."""
class ChatSessionEnvelope(Envelope[ChatSession]): """Success envelope: a new chat."""
class ChatSessionListEnvelope(Envelope[ChatSessionList]): """Success envelope: the caller's chats."""
class ChatSessionViewEnvelope(Envelope[ChatSessionView]): """Success envelope: one chat with its turns."""
class ChatTurnsEnvelope(Envelope[ChatTurns]): """Success envelope: newer turns."""
class ChatAttachmentEnvelope(Envelope[ChatAttachment]): """Success envelope: an uploaded file."""
class ChatRatingEnvelope(Envelope[ChatRating]): """Success envelope: the rating."""
class OkEnvelope(Envelope[Ok]): """Success envelope: done."""
