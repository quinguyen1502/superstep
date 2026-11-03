"""Owner-bound managed tool execution with durable intent, safe replay and read-only reconciliation."""
import hashlib, json, time
from jsonschema import Draft202012Validator
from ..core.errors import AppError
from ..models import McpOperation
from .managed_tools import adapters
from .managed_tools.base import ToolFailure


def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class ManagedToolService:
    def __init__(self, operations, channels, quota=None):
        self.operations, self.adapters = operations, adapters(channels, quota)

    def adapter(self, name):
        if name not in self.adapters: raise AppError("MCP_CONFIG_INVALID", field="adapter")
        return self.adapters[name]

    def validate(self, uid, name, settings, secrets):
        if not isinstance(settings, dict): raise AppError("MCP_CONFIG_INVALID", field="settings")
        self.adapter(name).validate(uid, settings, secrets)

    def tools(self, row): return self.adapter(row.adapter).tools(json.loads(row.settings or "{}"))

    @staticmethod
    def configuration(row): return digest({"adapter": row.adapter, "settings": json.loads(row.settings or "{}")})

    @staticmethod
    def public(operation):
        return {"operation_id": operation.id, "key": operation.key, "tool": operation.tool, "outcome": operation.status,
                "result": json.loads(operation.result) if operation.result else None, "created": operation.created, "updated": operation.updated}

    @staticmethod
    def _unknown(operation): raise AppError("MANAGED_OUTCOME_UNKNOWN", operation=operation.id)

    def call(self, uid, row, tool, args, secrets, key, dry_run=False, allow_org=True):
        adapter, settings = self.adapter(row.adapter), json.loads(row.settings or "{}")
        adapter.authorize(uid, settings, allow_org)
        definitions = {item["name"]: item for item in adapter.tools(settings)}
        if tool not in definitions: raise AppError("MCP_TOOL_NOT_FOUND", tool=tool)
        schema = definitions[tool]["input_schema"]
        if not Draft202012Validator(schema).is_valid(args): raise AppError("MCP_ARGUMENT_INVALID", name="arguments", type="tool schema")
        try: encoded = json.dumps(args, allow_nan=False, ensure_ascii=False).encode("utf-8")
        except (ValueError, TypeError, UnicodeError): raise AppError("MCP_ARGUMENT_INVALID", name="arguments", type="UTF-8 JSON") from None
        if len(encoded) > 128 * 1024: raise AppError("MCP_ARGUMENT_INVALID", name="arguments", type="bounded JSON")
        if dry_run: return {"outcome": "dry_run", "tool": tool}  # no tokens, outbound requests or intent records
        if not isinstance(key, str) or not 1 <= len(key) <= 200: raise AppError("MANAGED_OPERATION_KEY_REQUIRED")
        now, configuration = time.time(), self.configuration(row)
        operation = McpOperation(id=digest([uid, row.id, key]), owner=uid, server_id=row.id, key=key, tool=tool,
            fingerprint=digest({"configuration": configuration, "tool": tool, "args": args}), configuration=configuration,
            status="pending", result=None, created=now, updated=now)
        stored, created = self.operations.reserve(operation)
        if stored.fingerprint != operation.fingerprint: raise AppError("MANAGED_OPERATION_CONFLICT")
        if stored.status == "confirmed": return json.loads(stored.result)
        if stored.status == "failed": raise AppError("MCP_TOOL_FAILED", reason="The external service rejected this operation")
        if not created: return self.reconcile(uid, row, stored.id, secrets, allow_org)
        try: result = adapter.execute(uid, settings, secrets, tool, args, key, allow_org)
        except ToolFailure as error:
            self.operations.finish(stored.id, error.outcome, None, time.time())
            if error.outcome == "unknown": self._unknown(stored)
            raise AppError("MCP_TOOL_FAILED", reason="The external service rejected this operation") from None
        except AppError:
            # Local authorization/target validation failures happen before an outbound write.
            self.operations.finish(stored.id, "failed", None, time.time()); raise
        except Exception:
            self.operations.finish(stored.id, "unknown", None, time.time()); self._unknown(stored)
        self.operations.finish(stored.id, "confirmed", json.dumps(result), time.time())
        return result

    def reconcile(self, uid, row, operation_id, secrets, allow_org=True):
        stored = self.operations.get(operation_id)
        if stored is None or stored.owner != uid or stored.server_id != row.id: raise AppError("MCP_SERVER_NOT_FOUND")
        if stored.configuration != self.configuration(row): raise AppError("MANAGED_OPERATION_CONFLICT")
        adapter, settings = self.adapter(row.adapter), json.loads(row.settings or "{}")
        adapter.authorize(uid, settings, allow_org)
        if stored.status == "confirmed": return json.loads(stored.result)
        if stored.status == "failed": raise AppError("MCP_TOOL_FAILED", reason="The external service rejected this operation")
        try: result = adapter.reconcile(uid, settings, secrets, stored.tool, stored.key, allow_org)
        except (ToolFailure, AppError): result = None
        if result is None: self._unknown(stored)
        self.operations.finish(stored.id, "confirmed", json.dumps(result), time.time())
        return result
