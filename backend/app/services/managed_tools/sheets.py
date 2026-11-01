import json, re, time
from urllib.parse import quote
import httpx, jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.exceptions import UnsupportedAlgorithm
from ...core.errors import AppError
from .base import ToolFailure, request

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/spreadsheets"
API = "https://sheets.googleapis.com/v4/spreadsheets"


class SheetsTools:
    id = "google_sheets"
    fields = ("spreadsheet_id", "sheet_name", "data_columns")
    secret_fields = ("service_account",)
    settings_schema = {"type": "object", "properties": {"spreadsheet_id": {"type": "string"}, "sheet_name": {"type": "string", "default": "Expenses"}, "data_columns": {"type": "integer", "default": 6}}}

    def validate(self, uid, settings, secrets):
        if set(settings) != set(self.fields): raise AppError("MCP_CONFIG_INVALID", field="settings")
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", str(settings.get("spreadsheet_id", ""))):
            raise AppError("MCP_CONFIG_INVALID", field="settings.spreadsheet_id")
        name, count = settings.get("sheet_name"), settings.get("data_columns")
        if not isinstance(name, str) or not name.strip() or len(name) > 100 or any(ord(c) < 32 for c in name):
            raise AppError("MCP_CONFIG_INVALID", field="settings.sheet_name")
        if type(count) is not int or not 1 <= count <= 25: raise AppError("MCP_CONFIG_INVALID", field="settings.data_columns")
        try:
            if set(secrets) != {"service_account"}: raise ValueError()
            account = json.loads(secrets["service_account"])
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.iam\.gserviceaccount\.com", account["client_email"]): raise ValueError()
            private = load_pem_private_key(account["private_key"].encode(), password=None)
            if not isinstance(private, RSAPrivateKey) or private.key_size < 2048: raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError, RecursionError, UnsupportedAlgorithm):
            raise AppError("MCP_CONFIG_INVALID", field="secrets.service_account") from None

    def authorize(self, uid, settings, allow_org=True): pass  # MCP owner/org policy gates the encrypted service account.

    def tools(self, settings):
        count = settings["data_columns"]
        return [{"name": "append_row", "description": "Append one RAW row to the configured sheet, with an extra operation-id column for reconciliation. Never blindly retries an uncertain write.",
            "input_schema": {"type": "object", "additionalProperties": False, "required": ["values"], "properties": {
                "values": {"type": "array", "minItems": count, "maxItems": count,
                           "items": {"type": ["string", "number", "boolean"], "maxLength": 4000}}}}}]

    @staticmethod
    def _range(settings, columns):
        return "'" + settings["sheet_name"].replace("'", "''") + "'!" + columns

    def _token(self, secrets):
        try:
            account = json.loads(secrets["service_account"]); now = int(time.time())
            assertion = jwt.encode({"iss": account["client_email"], "scope": SCOPE, "aud": TOKEN_URL, "iat": now, "exp": now + 3600},
                                   account["private_key"], algorithm="RS256")
            response = request("POST", TOKEN_URL, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
            if response.status_code != 200: raise ValueError()
            token = response.json()["access_token"]
            if not isinstance(token, str) or not token: raise ValueError()
            return token
        except (httpx.HTTPError, ValueError, KeyError, TypeError, jwt.PyJWTError): raise ToolFailure() from None

    @staticmethod
    def _url(settings, area): return f"{API}/{settings['spreadsheet_id']}/values/{quote(area, safe='')}"

    def _find(self, settings, token, key):
        column = chr(ord("A") + settings["data_columns"])
        area = self._range(settings, f"{column}1:{column}100000")
        try:
            response = request("GET", self._url(settings, area), headers={"Authorization": f"Bearer {token}"}, params={"valueRenderOption": "UNFORMATTED_VALUE"})
            if response.status_code != 200: raise ValueError()
            rows = response.json().get("values", [])
            if not isinstance(rows, list): raise ValueError()
            matches = [index + 1 for index, row in enumerate(rows) if isinstance(row, list) and row and row[0] == key]
            if len(matches) > 1: raise ValueError()
            if not matches:
                if len(rows) >= 100000: raise ValueError()  # bounded reconciliation window; do not append past it blindly
                return None
            number = matches[0]
            return {"outcome": "confirmed", "operation_id": key, "spreadsheet_id": settings["spreadsheet_id"],
                    "updated_range": self._range(settings, f"A{number}:{column}{number}"), "reconciled": True}
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError): raise ToolFailure("unknown") from None

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        token = self._token(secrets)
        # Recovery can find a prior successful append even when its local result was never recorded.
        existing = self._find(settings, token, key)
        if existing is not None: return existing
        column = chr(ord("A") + settings["data_columns"])
        area = self._range(settings, f"A:{column}")
        try:
            response = request("POST", self._url(settings, area) + ":append", headers={"Authorization": f"Bearer {token}"},
                               params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                               json={"majorDimension": "ROWS", "values": [[*args["values"], key]]})
        except httpx.HTTPError: raise ToolFailure("unknown") from None
        if response.status_code == 408 or response.status_code >= 500: raise ToolFailure("unknown")
        if not 200 <= response.status_code < 300: raise ToolFailure()
        try:
            updates = response.json()["updates"]
            if updates.get("updatedRows") != 1 or not isinstance(updates.get("updatedRange"), str): raise ValueError()
            return {"outcome": "confirmed", "operation_id": key, "spreadsheet_id": settings["spreadsheet_id"], "updated_range": updates["updatedRange"]}
        except (ValueError, KeyError, TypeError, AttributeError): raise ToolFailure("unknown") from None

    def reconcile(self, uid, settings, secrets, tool, key, allow_org=True):
        return self._find(settings, self._token(secrets), key)
