from typing import Any, Optional
from pydantic import BaseModel, Field


class TokenIn(BaseModel):
    name: str = Field("API token", max_length=80)


class ScheduleIn(BaseModel):  # TASK-0046
    name: str = Field("Schedule", max_length=80)
    cron: str = Field(..., max_length=120)
    timezone: str = Field("UTC", max_length=64)
    input: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SchedulePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    cron: Optional[str] = Field(None, max_length=120)
    timezone: Optional[str] = Field(None, max_length=64)
    input: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class SchedulePreview(BaseModel):
    cron: str = Field(..., max_length=120)
    timezone: str = Field("UTC", max_length=64)


class ChatTriggerIn(BaseModel):  # TASK-0074
    name: str = Field("", max_length=80)
    channel_id: str = Field(..., max_length=64)
    place: str = Field("dm", max_length=64)
    command: str = Field(..., max_length=40)
    input_field: str = Field(..., max_length=120)
    reply_field: str = Field(..., max_length=120)
    enabled: bool = True


class ChatTriggerPatch(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    channel_id: Optional[str] = Field(None, max_length=64)
    place: Optional[str] = Field(None, max_length=64)
    command: Optional[str] = Field(None, max_length=40)
    input_field: Optional[str] = Field(None, max_length=120)
    reply_field: Optional[str] = Field(None, max_length=120)
    enabled: Optional[bool] = None


class McpSettingsIn(BaseModel):
    enabled: bool
