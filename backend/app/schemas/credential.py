from typing import Any, Dict, Optional
from pydantic import BaseModel


class CredentialIn(BaseModel):
    name: str
    provider: str
    api_key: str = ""                          # optional for local providers (Ollama, LM Studio, ...)
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None   # provider-specific extra headers (OpenRouter: HTTP-Referer, X-Title)
    settings: Optional[Dict[str, Any]] = None  # provider settings that are not secret (SMTP host, port, ...; )


class ProviderProbeIn(BaseModel):
    """Unsaved connection settings for 'Test connection' / model list before the credential is created."""
    api_key: str = ""
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None
    credential_id: Optional[str] = None  # editing: test with this saved credential's key when none is typed


class CredentialUpdate(BaseModel):
    """Edit in place. The provider is fixed; `api_key` omitted/empty keeps the stored secret,
    `clear_key` removes it (providers where a key is optional)."""
    name: str
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    api_key: Optional[str] = None
    clear_key: bool = False
    settings: Optional[Dict[str, Any]] = None


class EmbeddingTestIn(BaseModel):
    model: Optional[str] = None
