"""Chat attachments (TASK-0174, REQ-0077, DEC-0072): files a person attaches to a chat message.

A file is uploaded before the message is sent, one per request, and belongs to the session until the message takes it
(`turn_id`). Its kind is read from the bytes, never from the name or the browser: PDF, PNG, JPEG, WebP, or UTF-8 text
named .txt, .md or .csv. A document's text is extracted once (engine/documents.py) and capped. Files are only ever
served as downloads (the router adds `attachment` and `nosniff`).

Who may touch a file: the session's owner (a visitor of the published page, or the studio user of a studio chat), and
the builder from the Visitors list. Anything else, and a guessed id, is CHAT_ATTACHMENT_NOT_FOUND.
"""
from __future__ import annotations
import os, time, uuid
from typing import TYPE_CHECKING, Optional
from ..core import config
from ..core import permissions as P
from ..core.errors import AppError
from ..engine import documents
from ..models import ChatAttachment, ChatSession
from ..repositories import ChatAttachmentRepository

if TYPE_CHECKING:
    from .chat_session_service import ChatSessionService
    from .public_chat_service import PublicChatService, Visitor

KINDS = ("document", "image")
DEFAULTS = {"enabled": False, "kinds": list(KINDS), "max_files": 5, "max_mb": 10, "field": "files"}
TEXT_MAX = 50_000  # characters of a document's text that reach the workflow
UNSENT_TTL = 3600  # an upload never sent with a message is swept after an hour
MB = 1024 * 1024
# (signature, MIME, kind, file name endings that must match)
SIGNATURES = ((b"%PDF-", "application/pdf", "document", (".pdf",)),
              (b"\x89PNG\r\n\x1a\n", "image/png", "image", (".png",)),
              (b"\xff\xd8\xff", "image/jpeg", "image", (".jpg", ".jpeg")))
TEXT_TYPES = {".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv"}


def settings_of(st: dict) -> dict:
    """A chat's attachment settings, with the defaults and under the operator's ceilings."""
    a = {**DEFAULTS, **((st or {}).get("attachments") or {})}
    a["max_mb"] = min(int(a["max_mb"]), config.chat_attachment_max_mb())
    a["max_files"] = min(int(a["max_files"]), config.chat_attachment_max_files())
    return a


def sniff(name: str, data: bytes) -> Optional[tuple[str, str]]:
    """(kind, MIME) read from the bytes, or None. The name's ending must agree with what the bytes are."""
    ext = os.path.splitext(name.lower())[1]
    for sig, mime, kind, exts in SIGNATURES:
        if data.startswith(sig): return (kind, mime) if ext in exts else None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return ("image", "image/webp") if ext == ".webp" else None
    if ext in TEXT_TYPES and b"\x00" not in data:
        try: data.decode("utf-8-sig")
        except UnicodeDecodeError: return None
        return "document", TEXT_TYPES[ext]
    return None


def text_of(name: str, data: bytes) -> tuple[str, bool]:
    """A document's text, capped, and whether it was cut. A PDF without a text layer, or one that cannot be read
    (encrypted), has empty text: there is no OCR."""
    try: text = documents.extract(name, data)
    except documents.DocumentError: text = ""
    return (text[:TEXT_MAX], True) if len(text) > TEXT_MAX else (text, False)


def public(a) -> dict:
    """What the page and the API show of a file (never its bytes or text)."""
    return {"id": a.id, "name": a.name, "kind": a.kind, "mime": a.mime, "size": a.size}


class ChatAttachmentService:
    def __init__(self, repo: ChatAttachmentRepository, chat: "ChatSessionService", pub: Optional["PublicChatService"] = None):
        self.repo, self.chat, self.pub = repo, chat, pub

    # ---- the published page (the visitor's own session) ----
    async def public_upload(self, slug: str, sid: str, token, user, ip: str, name: str, data: bytes) -> tuple[dict, "Visitor"]:
        t, st = self.pub.published(slug); v = self.pub.visitor(slug, st, token, user)
        s = self.pub.own(t, sid, v)
        self._allowed(settings_of(st))
        await self.pub.check_message(t, st, v, ip, daily=False)  # an upload counts as a message for the rate limits
        return self.store(s, st, name, data), v

    def public_file(self, slug: str, sid: str, aid: str, token, user) -> tuple[ChatAttachment, "Visitor"]:
        t, st = self.pub.published(slug); v = self.pub.visitor(slug, st, token, user)
        return self.file(self.pub.own(t, sid, v), aid), v

    def public_delete(self, slug: str, sid: str, aid: str, token, user) -> tuple[dict, "Visitor"]:
        t, st = self.pub.published(slug); v = self.pub.visitor(slug, st, token, user)
        return self.remove(self.pub.own(t, sid, v), aid), v

    # ---- the studio Chat tab (the user's own session) ----
    def upload_owned(self, sid: str, uid: str, name: str, data: bytes) -> dict:
        s, t = self.chat._own(sid, uid, P.RUN)
        return self.store(s, self.chat.settings_json(t), name, data)

    def file_owned(self, sid: str, aid: str, uid: str) -> ChatAttachment:
        s, _t = self.chat._own(sid, uid); return self.file(s, aid)

    def delete_owned(self, sid: str, aid: str, uid: str) -> dict:
        s, _t = self.chat._own(sid, uid, P.RUN); return self.remove(s, aid)

    def visitor_file(self, wid: str, sid: str, aid: str, uid: str) -> ChatAttachment:
        """The builder downloads a visitor's file from the Visitors list (run right)."""
        self.chat._workflow(wid, uid, P.RUN); s = self.chat.sessions.get(sid)
        if s is None or s.workflow_id != wid or s.channel not in ("web", "embed"): raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
        return self.file(s, aid)

    # ---- the rules ----
    @staticmethod
    def _allowed(a: dict) -> None:
        if config.demo_mode(): raise AppError("CHAT_ATTACHMENT_DEMO")
        if not a["enabled"]: raise AppError("CHAT_ATTACHMENTS_OFF")

    def store(self, s: ChatSession, st: dict, name, data: bytes) -> dict:
        """Checks and keeps one unsent file of session `s`, under the chat's settings `st`."""
        a = settings_of(st); self._allowed(a)
        if len(data) > a["max_mb"] * MB: raise AppError("CHAT_ATTACHMENT_TOO_LARGE", max_mb=a["max_mb"])
        if self.repo.unsent_count(s.id) >= a["max_files"]: raise AppError("CHAT_ATTACHMENT_TOO_MANY", max=a["max_files"])
        name = os.path.basename(str(name or "").replace("\\", "/")).strip()[:200]
        found = sniff(name, data) if name and data else None
        if found is None or found[0] not in a["kinds"]: raise AppError("CHAT_ATTACHMENT_TYPE", allowed=self.allowed_names(a))
        kind, mime = found
        text, cut = text_of(name, data) if kind == "document" else (None, False)
        row = self.repo.add(ChatAttachment(id=uuid.uuid4().hex, session_id=s.id, turn_id=None, name=name, kind=kind, mime=mime, size=len(data),
                                           data=data, text=text, text_cut=cut, created=time.time()))
        return public(row)

    @staticmethod
    def allowed_names(a: dict) -> str:
        names = {"document": ".pdf, .txt, .md, .csv", "image": ".png, .jpg, .webp"}
        return ", ".join(names[k] for k in KINDS if k in a["kinds"])

    def file(self, s: ChatSession, aid) -> ChatAttachment:
        row = self.repo.get(aid) if isinstance(aid, str) else None
        if row is None or row.session_id != s.id: raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
        return row

    def remove(self, s: ChatSession, aid) -> dict:
        """Removes a file that was not sent yet; a sent file stays with its turn."""
        if not isinstance(aid, str) or not self.repo.delete_unsent(aid, s.id): raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
        return {"ok": True}
