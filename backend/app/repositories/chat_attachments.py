from typing import Optional
from sqlalchemy import delete, func, or_, select, update
from ..models import ChatAttachment, ChatSession
from ..models.database import Database

META = (ChatAttachment.id, ChatAttachment.session_id, ChatAttachment.turn_id, ChatAttachment.name, ChatAttachment.kind,
        ChatAttachment.mime, ChatAttachment.size, ChatAttachment.text, ChatAttachment.text_cut, ChatAttachment.created,
        ChatAttachment.storage, ChatAttachment.key, ChatAttachment.location)
Ref = tuple  # (storage, key, location) of a file's bytes outside the database (TASK-0191, TASK-0203)
REF = (ChatAttachment.storage, ChatAttachment.key, ChatAttachment.location)


class ChatAttachmentRepository:
    """The files of chat messages (TASK-0174, DEC-0072). Reads without `data` unless the bytes are asked for."""
    def __init__(self, db: Database): self.db = db

    def add(self, row: ChatAttachment) -> ChatAttachment:
        with self.db.session() as s: s.add(row); s.commit(); s.refresh(row); return row

    def get(self, aid: str) -> Optional[ChatAttachment]:
        """One file's metadata and where its bytes are (not the bytes)."""
        with self.db.session() as s: return s.execute(select(*META).where(ChatAttachment.id == aid)).first()

    # ---- the `db` backend's bytes (storage/db.py, TASK-0191) ----
    def data_of(self, aid: str) -> Optional[bytes]:
        with self.db.session() as s: return s.scalar(select(ChatAttachment.data).where(ChatAttachment.id == aid, ChatAttachment.storage == "db"))

    def set_data(self, aid: str, data: bytes) -> int:
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(ChatAttachment.id == aid, ChatAttachment.storage == "db").values(data=data)).rowcount
            s.commit(); return n

    def keys(self, storage: str) -> list[tuple[str, float]]:
        """(key, created) of the files kept in `storage`: the attachment id for db, the object key otherwise."""
        col = ChatAttachment.id if storage == "db" else ChatAttachment.key
        with self.db.session() as s:
            return [(k, c) for k, c in s.execute(select(col, ChatAttachment.created).where(ChatAttachment.storage == storage))]

    def located(self, storage: str) -> list[tuple[str, Optional[str]]]:
        """(key, location) of the files kept in `storage` (archive export, TASK-0203)."""
        with self.db.session() as s:
            return [tuple(r) for r in s.execute(select(ChatAttachment.key, ChatAttachment.location).where(ChatAttachment.storage == storage))]

    def known(self, storage: str, keys: list[str], location: Optional[str] = None) -> set[str]:
        """The keys among `keys` that a row of `storage` at `location` points at (the orphan sweep). A row without a
        location counts as everywhere, so a sweep never removes a file a row may still need."""
        if not keys: return set()
        where = [ChatAttachment.storage == storage, ChatAttachment.key.in_(keys)]
        if location is not None: where.append(or_(ChatAttachment.location.is_(None), ChatAttachment.location == location))
        with self.db.session() as s:
            return set(s.scalars(select(ChatAttachment.key).where(*where)))

    def backfill_locations(self, storage: str, location: str) -> int:
        """Rows of `storage` written before locations were recorded get `location` (TASK-0203)."""
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(ChatAttachment.storage == storage, ChatAttachment.location.is_(None))
                          .values(location=location)).rowcount
            s.commit(); return n

    def relocate(self, storage: str, key: str, location: str) -> int:
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(ChatAttachment.storage == storage, ChatAttachment.key == key)
                          .values(location=location)).rowcount
            s.commit(); return n

    def refs_of_sessions(self, sids: list[str]) -> list[Ref]:
        if not sids: return []
        with self.db.session() as s:
            return [tuple(r) for r in s.execute(select(*REF).where(
                ChatAttachment.session_id.in_(sids), ChatAttachment.storage != "db", ChatAttachment.key.is_not(None)))]

    def storages(self) -> list[str]:
        """The backends that rows point at."""
        with self.db.session() as s: return list(s.scalars(select(ChatAttachment.storage).distinct()))

    def meta(self, ids: list[str]) -> list:
        """Files without their bytes, in the order of `ids` (missing ones left out)."""
        if not ids: return []
        with self.db.session() as s:
            rows = {r.id: r for r in s.execute(select(*META).where(ChatAttachment.id.in_(ids)))}
        return [rows[i] for i in ids if i in rows]

    def unsent_count(self, sid: str) -> int:
        with self.db.session() as s:
            return s.scalar(select(func.count()).select_from(ChatAttachment).where(ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))) or 0

    def link(self, ids: list[str], sid: str, tid: str) -> int:
        """Gives unsent files of session `sid` to turn `tid`; the number linked."""
        if not ids: return 0
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(ChatAttachment.id.in_(ids), ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))
                          .values(turn_id=tid)).rowcount
            s.commit(); return n

    def delete_row(self, aid: str) -> int:
        with self.db.session() as s:
            n = s.execute(delete(ChatAttachment).where(ChatAttachment.id == aid)).rowcount; s.commit(); return n

    def delete_unsent(self, aid: str, sid: str) -> Optional[Ref]:
        """Deletes an unsent file; (storage, key) of its bytes, or None when there was no such file."""
        where = (ChatAttachment.id == aid, ChatAttachment.session_id == sid, ChatAttachment.turn_id.is_(None))
        with self.db.session() as s:
            ref = s.execute(select(*REF).where(*where)).first()
            if ref is None: return None
            s.execute(delete(ChatAttachment).where(*where)); s.commit(); return tuple(ref)

    def delete_stale(self, before: float) -> list[Ref]:
        """Unsent files uploaded before `before` (never sent with a message); (storage, key) of each."""
        where = (ChatAttachment.turn_id.is_(None), ChatAttachment.created < before)
        with self.db.session() as s:
            refs = [tuple(r) for r in s.execute(select(*REF).where(*where))]
            s.execute(delete(ChatAttachment).where(*where)); s.commit(); return refs

    # ---- moving files between backends (TASK-0194) ----
    def not_on(self, storage: str, limit: int, skip: tuple = (), location: str = "") -> list:
        """Up to `limit` files kept elsewhere than `storage` at `location` (another backend, or the same backend at an
        older folder or bucket/prefix, TASK-0203), oldest first, with their session's workflow (for the key)."""
        elsewhere = ChatAttachment.storage != storage
        if location: elsewhere = or_(elsewhere, ChatAttachment.location != location)
        q = (select(ChatAttachment.id, ChatAttachment.session_id, ChatAttachment.mime, ChatAttachment.size, ChatAttachment.storage,
                    ChatAttachment.key, ChatAttachment.location, ChatSession.workflow_id)
             .outerjoin(ChatSession, ChatSession.id == ChatAttachment.session_id)
             .where(elsewhere).order_by(ChatAttachment.created, ChatAttachment.id).limit(limit))
        if skip: q = q.where(ChatAttachment.id.not_in(list(skip)))
        with self.db.session() as s: return list(s.execute(q))

    def count_not_on(self, storage: str, location: str = "") -> int:
        elsewhere = ChatAttachment.storage != storage
        if location: elsewhere = or_(elsewhere, ChatAttachment.location != location)
        with self.db.session() as s: return s.scalar(select(func.count()).select_from(ChatAttachment).where(elsewhere)) or 0

    def switch(self, aid: str, frm: str, to: str, key: Optional[str], data: bytes, frm_location: Optional[str] = None,
               location: Optional[str] = None) -> int:
        """Points a file at its copy on `to` at `location` (only while it is still on `frm` at `frm_location`); `data`
        is the bytes for db, else b''."""
        where = [ChatAttachment.id == aid, ChatAttachment.storage == frm]
        where.append(ChatAttachment.location.is_(None) if frm_location is None else ChatAttachment.location == frm_location)
        with self.db.session() as s:
            n = s.execute(update(ChatAttachment).where(*where).values(storage=to, key=key, data=data, location=location)).rowcount
            s.commit(); return n

    def by_storage(self) -> dict:
        """{storage: {"files", "bytes"}} over every file."""
        with self.db.session() as s:
            return {k: {"files": n, "bytes": int(b or 0)} for k, n, b in s.execute(
                select(ChatAttachment.storage, func.count(), func.sum(ChatAttachment.size)).group_by(ChatAttachment.storage))}

    def count(self) -> int:
        with self.db.session() as s: return s.scalar(select(func.count()).select_from(ChatAttachment)) or 0
