"""Static JSON HTTP operations; configuration owns targets/auth, never runtime tool arguments."""
import json, math, re
from urllib.parse import unquote, urlsplit
import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from ...core import config
from ...core.errors import AppError
from .base import ToolFailure, request, redact_values

MAX_RESPONSE = 256 * 1024
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
SCALARS = {"string", "integer", "number", "boolean", "null"}
EXAMPLE = json.dumps([{"name": "create_record", "description": "Create a record in the configured API",
    "method": "POST", "path": "/records", "input_schema": {"type": "object", "additionalProperties": False,
    "required": ["text"], "properties": {"text": {"type": "string", "maxLength": 4000}}}}], indent=2)


def invalid(field): raise AppError("MCP_CONFIG_INVALID", field=field)


def bounded(value, depth=0, schema=False):
    if depth > 16: raise ValueError("JSON nesting")
    if isinstance(value, dict):
        for key, item in value.items():
            if schema and key in ("$ref", "$dynamicRef", "$recursiveRef"): raise ValueError("Schema references are unsupported")
            bounded(item, depth + 1, schema)
    elif isinstance(value, list):
        for item in value: bounded(item, depth + 1, schema)
    elif isinstance(value, float) and not math.isfinite(value): raise ValueError("Non-finite JSON")


class HttpApiTools:
    id = "http_api"
    settings_limit = 65536
    secret_fields = ("headers",)
    settings_schema = {"type": "object", "properties": {"base_url": {"type": "string"},
        "tools_json": {"type": "string", "format": "json", "default": EXAMPLE}}}

    @staticmethod
    def definitions(settings): return json.loads(settings["tools_json"])

    @staticmethod
    def headers(secrets):
        try:
            if set(secrets) - {"headers"}: raise ValueError()
            headers = json.loads(secrets.get("headers") or "{}")
            if not isinstance(headers, dict) or len(headers) > 20: raise ValueError()
            seen = set()
            for name, value in headers.items():
                lower = name.lower()
                if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,100}", name) or lower in seen: raise ValueError()
                if lower in {"host", "connection", "content-length", "content-type", "transfer-encoding", "idempotency-key", "accept-encoding", "cookie", "upgrade", "te", "trailer", "keep-alive", "expect"} or lower.startswith(("proxy-", "x-studio-")):
                    raise ValueError()
                if not isinstance(value, str) or not 1 <= len(value) <= 8000 or any(ord(c) < 32 or ord(c) > 126 for c in value): raise ValueError()
                seen.add(lower)
            return headers
        except (ValueError, TypeError, AttributeError, RecursionError): invalid("secrets.headers")

    def validate(self, uid, settings, secrets):
        if set(settings) != {"base_url", "tools_json"}: invalid("settings")
        try:
            base = settings["base_url"]
            if not isinstance(base, str) or not 1 <= len(base) <= 2000 or any(ord(c) < 33 for c in base): raise ValueError()
            url = urlsplit(base)
            if url.scheme not in ({"https", "http"} if config.mcp_allow_private() else {"https"}) or not url.hostname or url.username is not None or url.password is not None or url.query or url.fragment or "\\" in base:
                raise ValueError()
            if url.port is not None and not 1 <= url.port <= 65535: raise ValueError()
        except (ValueError, TypeError): invalid("settings.base_url")
        try:
            raw = settings["tools_json"]
            if not isinstance(raw, str) or len(raw.encode()) > 32768: raise ValueError()
            definitions = self.definitions(settings); bounded(definitions, schema=True)
            if not isinstance(definitions, list) or not 1 <= len(definitions) <= 20: raise ValueError()
            names = set()
            for tool in definitions:
                if not isinstance(tool, dict) or set(tool) - {"name", "description", "method", "path", "input_schema", "response_schema", "success_statuses"}: raise ValueError()
                name, path, method = tool["name"], tool["path"], tool["method"]
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name) or name in names: raise ValueError()
                names.add(name)
                if method not in METHODS: raise ValueError()
                if not isinstance(path, str) or len(path) > 1000 or not path.startswith("/") or path.startswith("//") or any(c in path for c in "?#\\{}") or any(ord(c) < 33 for c in path): raise ValueError()
                decoded = unquote(path)
                if any(part in (".", "..") for part in decoded.split("/")) or any(c in decoded for c in "?#\\") or any(ord(c) < 32 for c in decoded): raise ValueError()
                if not isinstance(tool.get("description", ""), str) or len(tool.get("description", "")) > 1000: raise ValueError()
                schema = tool["input_schema"]
                if not isinstance(schema, dict) or schema.get("type") != "object" or schema.get("additionalProperties") is not False: raise ValueError()
                Draft202012Validator.check_schema(schema)
                if method == "GET":
                    for prop in schema.get("properties", {}).values():
                        types = prop.get("type")
                        if not (set(types) if isinstance(types, list) else {types}) <= SCALARS: raise ValueError()
                if "response_schema" in tool: Draft202012Validator.check_schema(tool["response_schema"])
                statuses = tool.get("success_statuses", [200, 201, 204])
                if not isinstance(statuses, list) or not statuses or any(type(code) is not int or not 200 <= code < 300 or code == 202 for code in statuses): raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, SchemaError): invalid("settings.tools_json")
        self.headers(secrets)

    def authorize(self, uid, settings, allow_org=True): pass  # Existing MCP ownership/org policy gates this connection.

    def tools(self, settings):
        return [{"name": item["name"], "description": item.get("description", ""), "input_schema": item["input_schema"]}
                for item in self.definitions(settings)]

    @staticmethod
    def redact(value, headers):
        sensitive = set(headers.values())
        for name, secret in headers.items():
            if name.lower() == "authorization": sensitive.add(secret.split(" ", 1)[-1])
        return redact_values(value, sensitive)

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        definition = next(item for item in self.definitions(settings) if item["name"] == tool)
        headers = self.headers(secrets)
        payload = {"params": args} if definition["method"] == "GET" else {"json": args}
        if definition["method"] == "GET" and any(isinstance(value, (dict, list)) for value in args.values()):
            raise AppError("MCP_ARGUMENT_INVALID", name="arguments", type="scalar query parameters")
        try:
            response = request(definition["method"], settings["base_url"].rstrip("/") + definition["path"],
                headers={**headers, "Idempotency-Key": key, "Accept": "application/json"}, max_bytes=MAX_RESPONSE, **payload)
        except httpx.HTTPError: raise ToolFailure("unknown") from None
        if response.status_code == 202 or response.status_code == 408 or response.status_code >= 500: raise ToolFailure("unknown")
        if response.status_code not in definition.get("success_statuses", [200, 201, 204]):
            raise ToolFailure("unknown" if 200 <= response.status_code < 300 else "failed")
        try:
            if len(response.content) > MAX_RESPONSE: raise ValueError()
            data = response.json() if response.content else None
            bounded(data)
            if "response_schema" in definition: Draft202012Validator(definition["response_schema"]).validate(data)
        except (ValueError, TypeError, RecursionError, ValidationError): raise ToolFailure("unknown") from None
        return {"outcome": "confirmed", "operation_id": key, "http_status": response.status_code, "data": self.redact(data, headers)}

    def reconcile(self, uid, settings, secrets, tool, key, allow_org=True):
        return None  # No universal read-only lookup contract; never repeat an uncertain request.
