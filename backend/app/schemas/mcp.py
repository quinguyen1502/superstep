from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class McpServerIn(BaseModel):
    adapter: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    name: str
    transport: str = "http"          # fixed after creation
    scope: str = "user"              # fixed after creation
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    secrets: Optional[Dict[str, Optional[str]]] = None  # null value = keep the stored one
