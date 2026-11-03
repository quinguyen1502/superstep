"""Fixed Google token endpoints and shared local credential checks; no delegated user or supplied token URL."""
import json, re, time
import httpx, jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.exceptions import UnsupportedAlgorithm
from ...core.errors import AppError
from .base import ToolFailure

TOKEN_URL = "https://oauth2.googleapis.com/token"


def service_account(value, field="secrets.service_account"):
    try:
        account = json.loads(value)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.iam\.gserviceaccount\.com", account["client_email"]): raise ValueError()
        private = load_pem_private_key(account["private_key"].encode(), password=None)
        if not isinstance(private, RSAPrivateKey) or private.key_size < 2048: raise ValueError()
        return account
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError, UnsupportedAlgorithm):
        raise AppError("MCP_CONFIG_INVALID", field=field) from None


def credential(value):
    try:
        account = json.loads(value)
        if account.get("type") == "service_account": return service_account(value, "secrets.google_credentials")
        if account.get("type") != "authorized_user": raise ValueError()
        for field in ("client_id", "client_secret", "refresh_token"):
            item = account[field]
            if not isinstance(item, str) or not 1 <= len(item) <= 8192 or any(ord(c) < 33 or ord(c) > 126 for c in item): raise ValueError()
        return account
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
        raise AppError("MCP_CONFIG_INVALID", field="secrets.google_credentials") from None


def access_token(value, scope, send, refresh=False):
    try:
        account = json.loads(value)
        if refresh and account.get("type") == "authorized_user":
            data = {"grant_type": "refresh_token", **{field: account[field] for field in ("client_id", "client_secret", "refresh_token")}}
        else:
            now = int(time.time())
            assertion = jwt.encode({"iss": account["client_email"], "scope": scope, "aud": TOKEN_URL, "iat": now, "exp": now + 3600}, account["private_key"], algorithm="RS256")
            data = {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
        response = send("POST", TOKEN_URL, data=data, max_bytes=16384)
        if response.status_code != 200: raise ValueError()
        token = response.json()["access_token"]
        if not isinstance(token, str) or not 1 <= len(token) <= 8192 or any(ord(c) < 33 or ord(c) > 126 for c in token): raise ValueError()
        return token
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, RecursionError, jwt.PyJWTError): raise ToolFailure() from None
