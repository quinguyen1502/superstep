"""Google Drive tools scoped to one folder. Creation recovery only reads marker/checksum data."""
import hashlib, json, re, uuid
from urllib.parse import quote, urlsplit
import httpx
from ...core.errors import AppError
from .base import ToolFailure, request, redact_values
from .google_auth import credential, access_token

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER = "application/vnd.google-apps.folder"
DOC = "application/vnd.google-apps.document"
MAX_TEXT = 65536
ID = r"[A-Za-z0-9_-]{10,200}"
FIELDS = "id,name,mimeType,parents,trashed,driveId,size,modifiedTime,webViewLink,appProperties,md5Checksum"
FILE_ID = {"type": "string", "pattern": "^" + ID + "$"}


def sha(value): return hashlib.sha256(value).hexdigest()
def md5(value): return hashlib.md5(value, usedforsecurity=False).hexdigest()  # Drive blob integrity, not authorisation
def escaped(value): return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveTools:
    id = "google_drive"
    secret_fields = ("google_credentials",)
    settings_schema = {"type": "object", "properties": {"folder_id": {"type": "string"}}}

    def validate(self, uid, settings, secrets):
        if set(settings) != {"folder_id"} or not isinstance(settings.get("folder_id"), str) or not re.fullmatch(ID, settings["folder_id"]):
            raise AppError("MCP_CONFIG_INVALID", field="settings.folder_id")
        if set(secrets) != {"google_credentials"}: raise AppError("MCP_CONFIG_INVALID", field="secrets.google_credentials")
        credential(secrets["google_credentials"])

    def authorize(self, uid, settings, allow_org=True): pass  # Existing MCP owner/org policy gates this connection.

    def tools(self, settings):
        def tool(name, description, properties, required=()):
            return {"name": name, "description": description, "input_schema": {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}}
        return [
            tool("list_files", "List/search non-trashed direct children of the configured folder; no recursive traversal.", {
                "name_contains": {"type": "string", "maxLength": 200, "pattern": r"^[^\x00-\x1f]*$"},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100}, "page_token": {"type": "string", "maxLength": 4096}}),
            tool("get_file", "Inspect metadata of a direct child of the configured folder.", {"file_id": FILE_ID}, ("file_id",)),
            tool("read_text_file", "Read up to 64 KiB UTF-8 text, or export a Google Doc as plain text. Never follows shortcuts.", {"file_id": FILE_ID}, ("file_id",)),
            tool("create_text_file", "Create a plain-text file only in the configured folder. Service-account creation requires a Shared Drive. Unknown outcomes only reconcile read-only.", {
                "name": {"type": "string", "minLength": 1, "maxLength": 200, "pattern": r"^[^\x00-\x1f]+$"},
                "content": {"type": "string", "maxLength": MAX_TEXT}}, ("name", "content")),
        ]

    @staticmethod
    def _raw(method, url, token, outcome="failed", **kwargs):
        headers = {"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
        try: response = request(method, url, headers=headers, max_bytes=MAX_TEXT, **kwargs)
        except httpx.HTTPError: raise ToolFailure(outcome) from None
        if len(response.content) > MAX_TEXT: raise ToolFailure(outcome)
        if response.status_code == 202 or not 200 <= response.status_code < 300:
            raise ToolFailure(outcome if response.status_code in (202, 408) or response.status_code >= 500 else "failed")
        return response

    def _json(self, method, url, token, outcome="failed", **kwargs):
        response = self._raw(method, url, token, outcome, **kwargs)
        try:
            data = response.json()
            if not isinstance(data, dict): raise ValueError()
            return data
        except (ValueError, TypeError, RecursionError): raise ToolFailure(outcome) from None

    def _folder(self, settings, token):
        folder = self._json("GET", API + "/" + settings["folder_id"], token, params={"supportsAllDrives": "true",
            "fields": "id,mimeType,trashed,driveId,capabilities(canAddChildren)"})
        if folder.get("id") != settings["folder_id"] or folder.get("mimeType") != FOLDER or folder.get("trashed") is not False:
            raise ToolFailure()
        if folder.get("driveId") is not None and (not isinstance(folder["driveId"], str) or not re.fullmatch(ID, folder["driveId"])): raise ToolFailure()
        return folder

    @staticmethod
    def _checked(file, settings, folder, expected=None, outcome="failed"):
        try:
            if not isinstance(file, dict) or not isinstance(file.get("id"), str) or not re.fullmatch(ID, file["id"]) or (expected is not None and file["id"] != expected): raise ValueError()
            if not isinstance(file.get("name"), str) or not 1 <= len(file["name"]) <= 4096 or not isinstance(file.get("mimeType"), str) or not 1 <= len(file["mimeType"]) <= 200: raise ValueError()
            file["name"].encode("utf-8"); file["mimeType"].encode("utf-8")
            if file.get("trashed") is not False or not isinstance(file.get("parents"), list) or settings["folder_id"] not in file["parents"] or file.get("driveId") != folder.get("driveId"): raise ValueError()
            if "size" in file and (not isinstance(file["size"], str) or not re.fullmatch(r"\d{1,24}", file["size"])): raise ValueError()
            if "modifiedTime" in file and (not isinstance(file["modifiedTime"], str) or len(file["modifiedTime"]) > 100): raise ValueError()
            if "modifiedTime" in file: file["modifiedTime"].encode("utf-8")
            if "webViewLink" in file:
                file["webViewLink"].encode("utf-8")
                link = urlsplit(file["webViewLink"])
                if len(file["webViewLink"]) > 2000 or link.scheme != "https" or link.hostname not in {"drive.google.com", "docs.google.com"} or link.username is not None or link.password is not None or link.port not in (None, 443): raise ValueError()
            return file
        except (ValueError, TypeError, KeyError, AttributeError): raise ToolFailure(outcome) from None

    @staticmethod
    def _metadata(file): return {field: file[field] for field in ("id", "name", "mimeType", "size", "modifiedTime", "webViewLink") if field in file}

    def _file(self, settings, folder, token, fid):
        file = self._json("GET", API + "/" + quote(fid, safe=""), token, params={"supportsAllDrives": "true", "fields": FIELDS})
        return self._checked(file, settings, folder, fid)

    def _list(self, settings, folder, token, query, page_size, page_token=None, outcome="failed"):
        params = {"q": query, "pageSize": page_size, "spaces": "drive", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true",
            "fields": "nextPageToken,incompleteSearch,files(" + FIELDS + ")", "corpora": "drive" if folder.get("driveId") else "user"}
        if folder.get("driveId"): params["driveId"] = folder["driveId"]
        if page_token: params["pageToken"] = page_token
        data = self._json("GET", API, token, outcome, params=params)
        data.setdefault("files", [])
        if data.get("error") or not isinstance(data["files"], list) or len(data["files"]) > page_size or ("incompleteSearch" in data and data["incompleteSearch"] is not False): raise ToolFailure(outcome)
        next_page = data.get("nextPageToken")
        if next_page is not None and (not isinstance(next_page, str) or len(next_page) > 4096): raise ToolFailure(outcome)
        if next_page is not None:
            try: next_page.encode("utf-8")
            except UnicodeError: raise ToolFailure(outcome) from None
        for file in data["files"]: self._checked(file, settings, folder, outcome=outcome)
        return data

    @staticmethod
    def _query(settings): return f"'{settings['folder_id']}' in parents and trashed = false"

    def _receipt(self, file, settings, folder, key, expected_sha=None, expected_md5=None):
        self._checked(file, settings, folder, outcome="unknown")
        props = file.get("appProperties")
        if not isinstance(props, dict) or props.get("studio_operation") != sha(key.encode()) or file["mimeType"] != "text/plain": raise ToolFailure("unknown")
        content_sha = props.get("studio_sha256")
        if not isinstance(content_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha) or (expected_sha is not None and content_sha != expected_sha): raise ToolFailure("unknown")
        if expected_md5 is not None and file.get("md5Checksum") != expected_md5: raise ToolFailure("unknown")
        return {"outcome": "confirmed", "operation_id": key, "file": self._metadata(file)}

    def _find(self, settings, folder, token, key, expected_sha=None):
        query = self._query(settings) + " and appProperties has { key='studio_operation' and value='" + sha(key.encode()) + "' }"
        data = self._list(settings, folder, token, query, 2, outcome="unknown")
        if data.get("nextPageToken") or len(data["files"]) > 1: raise ToolFailure("unknown")
        if not data["files"]: return None
        file = data["files"][0]
        self._receipt(file, settings, folder, key, expected_sha)
        content = self._raw("GET", API + "/" + file["id"], token, "unknown", params={"alt": "media", "supportsAllDrives": "true"}).content
        if len(content) > MAX_TEXT or file.get("size") != str(len(content)): raise ToolFailure("unknown")
        result = self._receipt(file, settings, folder, key, sha(content), md5(content))
        result["reconciled"] = True
        return result

    @staticmethod
    def _safe(result, secrets, token):
        account = json.loads(secrets["google_credentials"])
        return redact_values(result, [token, *(account.get(field) for field in ("private_key", "client_secret", "refresh_token"))])

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        content = None
        if tool == "create_text_file":
            try:
                content = args["content"].encode("utf-8")
                if len(content) > MAX_TEXT or not args["name"].strip(): raise ValueError()
            except (UnicodeError, ValueError): raise AppError("MCP_ARGUMENT_INVALID", name="content/name", type="64 KiB UTF-8 text and nonblank name") from None
        token = access_token(secrets["google_credentials"], SCOPE, request, refresh=True)
        folder = self._folder(settings, token)
        if tool == "list_files":
            query = self._query(settings)
            if args.get("name_contains"): query += " and name contains '" + escaped(args["name_contains"]) + "'"
            data = self._list(settings, folder, token, query, args.get("page_size", 25), args.get("page_token"))
            result = {"files": [self._metadata(file) for file in data["files"]], "next_page_token": data.get("nextPageToken")}
        elif tool in ("get_file", "read_text_file"):
            file = self._file(settings, folder, token, args["file_id"])
            result = {"file": self._metadata(file)}
            if tool == "read_text_file":
                if file["mimeType"] == DOC:
                    response = self._raw("GET", API + "/" + file["id"] + "/export", token, params={"mimeType": "text/plain"})
                elif file["mimeType"].startswith("text/") or file["mimeType"] in {"application/json", "application/xml"}:
                    if int(file.get("size", "0")) > MAX_TEXT: raise AppError("MCP_ARGUMENT_INVALID", name="file_id", type="text no larger than 64 KiB")
                    response = self._raw("GET", API + "/" + file["id"], token, params={"alt": "media", "supportsAllDrives": "true"})
                else: raise AppError("MCP_ARGUMENT_INVALID", name="file_id", type="direct text file or Google Doc (no shortcut)")
                try:
                    if len(response.content) > MAX_TEXT: raise ValueError()
                    result["content"] = response.content.decode("utf-8"); result["encoding"] = "utf-8"
                except (UnicodeError, ValueError): raise ToolFailure() from None
        else:
            account = json.loads(secrets["google_credentials"])
            if account.get("type") == "service_account" and not folder.get("driveId"):
                raise AppError("MCP_CONFIG_INVALID", field="settings.folder_id (service-account writes require Shared Drive)")
            if not isinstance(folder.get("capabilities"), dict) or folder["capabilities"].get("canAddChildren") is not True: raise ToolFailure()
            existing = self._find(settings, folder, token, key, sha(content))
            if existing is not None: return self._safe(existing, secrets, token)
            metadata = {"name": args["name"], "mimeType": "text/plain", "parents": [settings["folder_id"]],
                "appProperties": {"studio_operation": sha(key.encode()), "studio_sha256": sha(content)}}
            boundary = "studio-" + uuid.uuid4().hex
            body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode() + json.dumps(metadata, ensure_ascii=False).encode()
                + f"\r\n--{boundary}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n".encode() + content + f"\r\n--{boundary}--\r\n".encode())
            file = self._json("POST", UPLOAD, token, "unknown", headers={"Content-Type": "multipart/related; boundary=" + boundary}, content=body,
                params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": FIELDS})
            result = self._receipt(file, settings, folder, key, sha(content), md5(content))
            if file.get("size") != str(len(content)): raise ToolFailure("unknown")
        return self._safe(result, secrets, token)

    def reconcile(self, uid, settings, secrets, tool, key, allow_org=True):
        if tool != "create_text_file": return None
        token = access_token(secrets["google_credentials"], SCOPE, request, refresh=True)
        result = self._find(settings, self._folder(settings, token), token, key)
        return self._safe(result, secrets, token) if result is not None else None
