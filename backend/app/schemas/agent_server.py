"""Request bodies of the LangGraph Agent Server API subset (`/api/lg`). Unknown fields are accepted and ignored, as
clients send options this subset does not use (config, checkpoint, interrupt_before, …)."""
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class _Body(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AssistantSearch(_Body):
    graph_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[dict] = None
    limit: int = Field(10, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class ThreadCreate(_Body):
    thread_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[dict] = None
    if_exists: str = "raise"


class ThreadSearch(_Body):
    metadata: Optional[dict] = None
    status: Optional[str] = None
    limit: int = Field(10, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class RunCreate(_Body):
    assistant_id: str = Field(..., max_length=100)
    input: Optional[Any] = None
    command: Optional[dict] = None
    metadata: Optional[dict] = None
    stream_mode: Union[str, list[str], None] = None

    def modes(self) -> list[str]:
        """The requested stream modes; LangGraph's default is `values`."""
        m = self.stream_mode or "values"
        return [m] if isinstance(m, str) else list(m)
