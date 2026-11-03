"""In-memory Google HTTP double shared by Drive acceptance tests and the opt-in browser app."""
import copy, json, re, threading
from email import policy
from email.parser import BytesParser
import httpx, jwt
from app.services.managed_tools import drive
from app.services.managed_tools.google_auth import TOKEN_URL

FOLDER_ID = "fixture-folder-123"
OAUTH = {"type": "authorized_user", "client_id": "fixture.apps.googleusercontent.com", "client_secret": "fixture-client-secret", "refresh_token": "fixture-refresh-token"}
TOKEN = "fixture-drive-access-token"


class DriveProvider:
    def __init__(self, account=None):
        self.account, self.calls, self.files, self.uploads = account, [], {}, 0
        self.shared, self.can_write, self.folder_valid = True, True, True
        self.write_mode, self.lookup_mode, self.read_mode, self.token_mode = "ok", "ok", "ok", "ok"
        self.entered, self.release = threading.Event(), threading.Event()

    def add(self, fid="fixture-text-123", folder=FOLDER_ID, mime="text/plain", content=b"Synthetic text", **extra):
        metadata = {"id": fid, "name": "example.txt", "mimeType": mime, "parents": [folder], "trashed": False,
            "size": str(len(content)), "md5Checksum": drive.md5(content), "appProperties": {}, "webViewLink": "https://drive.google.com/file/d/" + fid + "/view", **extra}
        if self.shared: metadata["driveId"] = "fixture-shared-drive-123"
        self.files[fid] = {"metadata": metadata, "content": content}
        return metadata

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, copy.deepcopy(kwargs)))
        if url == TOKEN_URL:
            if self.token_mode == "timeout": raise httpx.ReadTimeout("fixture-client-secret")
            if self.token_mode == "reject": return httpx.Response(400, json={"error": "fixture-client-secret"})
            if self.token_mode == "malformed": return httpx.Response(200, json={"access_token": {"secret": "must not leak"}})
            data = kwargs["data"]
            if data["grant_type"] == "refresh_token":
                assert {field: data[field] for field in ("client_id", "client_secret", "refresh_token")} == {field: OAUTH[field] for field in ("client_id", "client_secret", "refresh_token")}
                assert "scope" not in data
            else:
                assert self.account is not None
                claims = jwt.decode(data["assertion"], self.account["public_key"], algorithms=["RS256"], audience=TOKEN_URL)
                assert claims["scope"] == drive.SCOPE and claims["iss"] == self.account["client_email"] and "sub" not in claims
            return httpx.Response(200, json={"access_token": TOKEN})
        assert kwargs["headers"]["Authorization"] == "Bearer " + TOKEN
        params = kwargs.get("params", {})
        if url == drive.UPLOAD:
            assert method == "POST" and params["uploadType"] == "multipart" and params["supportsAllDrives"] == "true"
            if self.write_mode == "reject": return httpx.Response(403, json={"error": TOKEN})
            if self.write_mode == "crash_before": raise KeyboardInterrupt()
            message = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + kwargs["headers"]["Content-Type"].encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + kwargs["content"])
            parts = list(message.iter_parts()); assert len(parts) == 2
            metadata = json.loads(parts[0].get_payload(decode=True)); content = parts[1].get_payload(decode=True)
            assert metadata["mimeType"] == parts[1].get_content_type() == "text/plain"
            self.uploads += 1
            file = self.add(f"fixture-created-{self.uploads:04d}", folder=metadata["parents"][0], content=content, **{k: v for k, v in metadata.items() if k != "parents"})
            if self.write_mode == "block": self.entered.set(); self.release.wait(5)
            if self.write_mode == "crash_after": raise KeyboardInterrupt()
            if self.write_mode == "timeout": raise httpx.ReadTimeout(TOKEN)
            if self.write_mode == "server": return httpx.Response(503, json={"error": TOKEN})
            if self.write_mode == "malformed": return httpx.Response(200, json={})
            if self.write_mode == "wrong_checksum": return httpx.Response(200, json={**file, "md5Checksum": "0" * 32})
            return httpx.Response(200, json=file)
        if url == drive.API:
            assert method == "GET" and params["supportsAllDrives"] == params["includeItemsFromAllDrives"] == "true"
            folder = re.match(r"^'([A-Za-z0-9_-]+)' in parents and trashed = false", params["q"]).group(1)
            marker = re.search(r"value='([0-9a-f]{64})'", params["q"])
            files = [entry["metadata"] for entry in self.files.values() if folder in entry["metadata"]["parents"] and not entry["metadata"]["trashed"]]
            if marker: files = [file for file in files if file["appProperties"].get("studio_operation") == marker.group(1)]
            if self.lookup_mode == "missing": files = []
            if self.lookup_mode == "duplicate": files = files * 2
            data = {"files": files[:params["pageSize"]], "incompleteSearch": self.lookup_mode == "incomplete"}
            if self.lookup_mode == "next_page": data["nextPageToken"] = "fixture-next-page"
            if self.lookup_mode == "outside" and self.files: data["files"] = [{**next(iter(self.files.values()))["metadata"], "parents": ["another-folder-123"]}]
            return httpx.Response(200, json=data)
        assert url.startswith(drive.API + "/") and method == "GET"
        path = url[len(drive.API) + 1:]; fid = path.split("/")[0]
        if fid.startswith("fixture-folder-"):
            result = {"id": fid, "mimeType": drive.FOLDER if self.folder_valid else "text/plain", "trashed": False, "capabilities": {"canAddChildren": self.can_write}}
            if self.shared: result["driveId"] = "fixture-shared-drive-123"
            return httpx.Response(200, json=result)
        if fid not in self.files: return httpx.Response(404, json={"error": TOKEN})
        entry = self.files[fid]
        if params.get("alt") == "media" or path.endswith("/export"):
            if path.endswith("/export"): assert params == {"mimeType": "text/plain"} and entry["metadata"]["mimeType"] == drive.DOC
            if self.read_mode == "oversized": return httpx.Response(200, content=b"x" * (drive.MAX_TEXT + 1))
            if self.read_mode == "invalid_utf8": return httpx.Response(200, content=b"\xff")
            return httpx.Response(200, content=entry["content"])
        return httpx.Response(200, content=json.dumps(entry["metadata"]).encode(), headers={"Content-Type": "application/json"})
