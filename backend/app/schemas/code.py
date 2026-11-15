"""Code mode DTOs."""
from typing import Optional
from pydantic import BaseModel, Field


class CodeTest(BaseModel):
    source: str = Field(max_length=64 * 1024)
    state: dict = Field(default_factory=dict)
    node: Optional[str] = Field(default=None, max_length=64)
    timeout: Optional[float] = Field(default=None, gt=0, le=3600)
    language: str = Field(default="python", max_length=32)
