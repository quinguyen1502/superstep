"""Web chat (TASK-0084): the workflow's Chat settings. Unset fields keep their value."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatSettingsIn(BaseModel):
    enabled: Optional[bool] = None
    access: Optional[str | list[str]] = None  # legacy string or public modes (DEC-0077)
    slug: Optional[str] = None            # the page address: 3-64 of a-z, 0-9 and -, unique
    input_field: Optional[str] = None
    reply_field: Optional[str] = None
    messages_field: Optional[str] = None  # a list field that gets the history, or "" for none
    max_turns: Optional[int] = None
    steps: Optional[str] = None           # none | labels | full: what a visitor sees (builders always see full)
    retention_days: Optional[int] = None
    title: Optional[str] = None           # the public page (DEC-0067): its title, intro (Markdown) and up to 4 suggested messages
    intro: Optional[str] = None
    suggestions: Optional[List[str]] = None
    daily_limit: Optional[int] = None     # visitor messages per day (UTC), 0 = no cap
    embed_origins: Optional[List[str]] = None  # sites that may embed the page (https://host[:port])
    logo: Optional[str] = None            # a data: URL (PNG, JPEG or WebP, 256 KB) sets the logo, "" removes it, its hash keeps it
    attachments: Optional[dict] = None    # {enabled, kinds, max_files, max_mb, field} (REQ-0077, DEC-0072); off by default


class ChatAppKeyIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    origins: list[str] = Field(default_factory=list, max_length=10)


class ChatRatingIn(BaseModel):
    """A thumbs up or down on one finished answer (DEC-0070). `comment` is only kept with a thumbs down."""
    value: str
    comment: Optional[str] = None


class ChatEditIn(BaseModel):
    turn_id: str = Field(min_length=1, max_length=200)
    message: str = Field(max_length=4000)
    operation_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,128}$")
    expected_last_turn_id: str = Field(min_length=1, max_length=200)
