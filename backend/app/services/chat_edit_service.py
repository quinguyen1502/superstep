"""Non-destructive chat revisions. Publication and execution admission are separate, durable steps."""
import hashlib, json, re, tempfile, time, uuid
from ..core.errors import AppError
from ..core import config
from ..engine import agents, handoffs
from ..models import ChatAttachment, ChatEdit, ChatSession, ChatTurn
from .chat_attachment_service import MB
from .chat_session_service import TITLE_MAX, last_handoff

BUSY = ("queued", "running", "waiting", "paused")


class ChatEditService:
    def __init__(self, chat): self.chat = chat

    def result(self, intent, mode):
        branch = self.chat.sessions.get(intent.branch_id)
        if branch is None: raise AppError("CHAT_EDIT_GONE")
        run = self.chat.runs.get(intent.run_id) if intent.claimed else None
        return {"session": self.chat.view(branch, mode), "operation_id": intent.operation_id, "run_id": intent.run_id,
                "message": intent.message, "attachment_ids": json.loads(intent.attachments),
                "state": "prepared" if not intent.claimed else "finished" if run and run.status not in BUSY else "started"}

    def prepare(self, source, trigger, body, validate, mode, *, app_key_id=None, action="edit"):
        op, target, message, tip = (body.get(k) for k in ("operation_id", "turn_id", "message", "expected_last_turn_id"))
        if action not in ("edit", "regenerate") or not isinstance(op, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", op) or (action == "edit" and not isinstance(message, str)):
            raise AppError("CHAT_EDIT_INVALID")
        # Keep existing edit fingerprints valid; action is part of every regeneration fingerprint.
        payload = [target, message, tip] if action == "edit" else [action, target, tip, None]
        fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
        existing = self.chat.sessions.edit(source.id, op)
        if existing is not None:
            if existing.body_hash != fingerprint: raise AppError("CHAT_EDIT_CONFLICT")
            return self.result(existing, mode)
        turns = self.chat.sessions.turns(source.id)
        run = self.chat.runs.get(source.last_run_id) if source.last_run_id else None
        roots = {x.run_id for x in turns if x.role == "user" and x.run_id}
        settled = {x.run_id for x in turns if x.role == "assistant" and x.status not in BUSY}
        if (run and run.status in BUSY) or not turns or turns[-1].role != "assistant" or turns[-1].status in BUSY or roots - settled or self.chat.sessions.has_active_runs(source.id, BUSY):
            raise AppError("CHAT_EDIT_BUSY")
        if turns[-1].id != tip: raise AppError("CHAT_EDIT_STALE")
        index = next((i for i, x in enumerate(turns) if x.id == target), None)
        if index is None: raise AppError("CHAT_TURN_NOT_FOUND")
        chosen = turns[index]
        lineage = chosen.id
        if action == "regenerate":
            if index != len(turns) - 1 or chosen.inherited or chosen.role != "assistant" or not chosen.run_id:
                raise AppError("CHAT_REGENERATE_INVALID")
            index = next((i for i, x in enumerate(turns) if x.role == "user" and x.run_id == chosen.run_id and not x.inherited), None)
            if index is None: raise AppError("CHAT_REGENERATE_INVALID")
            chosen = turns[index]
            message = chosen.text
        if chosen.inherited or chosen.role != "user" or not chosen.run_id or any(x.role == "user" and x.run_id == chosen.run_id for x in turns[:index]):
            raise AppError("CHAT_EDIT_INVALID")
        now = time.time()
        branch = ChatSession(id=uuid.uuid4().hex, workflow_id=source.workflow_id, trigger_id=source.trigger_id,
                             channel=source.channel, owner=source.owner, visitor=source.visitor, external_user=source.external_user,
                             app_key_id=app_key_id or source.app_key_id, title=message.strip()[:TITLE_MAX], created=now, updated=now,
                             source_session_id=source.id, source_turn_id=lineage, source_action=action, revision=0)
        prefix = []
        for i, old in enumerate(turns[:index]):
            prefix.append(ChatTurn(id=f"{i:08x}-{uuid.uuid4().hex}", session_id=branch.id, run_id=old.run_id,
                                   role=old.role, text=old.text, status=old.status, node=old.node, answered_by=old.answered_by,
                                   code=old.code, created=old.created, inherited=True))
        for old in reversed(turns[:index]):
            if old.role == "assistant" and old.run_id:
                r = self.chat.runs.get(old.run_id)
                if r is None and handoffs.continues(self.chat._graph(self.chat.workflows.get(source.workflow_id))):
                    raise AppError("CHAT_EDIT_CONTEXT_UNAVAILABLE")
                # A removed hand-off target resets routing to the entry. Use the latest retained run's actual
                # start input rather than scanning back to an older hand-off that may no longer apply.
                agent = last_handoff(json.loads(r.events or "[]")) if r and r.status == "ok" else None
                branch.active_agent = agent or (json.loads(r.input or "{}").get(agents.START_INPUT) if r else None)
                break
        keep = False
        try:
            turn_map = {old.id: new.id for old, new in zip(turns[:index], prefix)}
            ids = list(dict.fromkeys(aid for old in turns[:index + 1] for aid in self.chat._ids(old)))
            files = self.copy_files(source, branch, ids, turn_map)
            for old, new in zip(turns[:index], prefix):
                new.attachments = json.dumps([files[aid] for aid in self.chat._ids(old)])
            root_files = [files[aid] for aid in self.chat._ids(chosen)]
            prep = self.chat.prepare(branch, trigger, message, root_files, turns=prefix)
            validate(prep)  # Validate the ordinary run plan before publishing any branch.
            intent = ChatEdit(id=uuid.uuid4().hex, source_session_id=source.id, operation_id=op, branch_id=branch.id,
                              run_id=uuid.uuid4().hex, body_hash=fingerprint, message=prep["text"],
                              attachments=json.dumps(root_files), claimed=False, created=now)
            published = self.chat.sessions.publish_edit(source, branch, prefix, intent)
            if published is None: raise AppError("CHAT_EDIT_STALE")
            if published.body_hash != fingerprint: raise AppError("CHAT_EDIT_CONFLICT")
            keep = published.branch_id == branch.id
            return self.result(published, mode)
        finally:
            if not keep:
                refs = self.chat.files.refs_of_sessions([branch.id]) if self.chat.files else []
                self.chat.sessions.delete(branch.id)
                if self.chat.files: self.chat.files.drop(refs)

    def copy_files(self, source, branch, ids, turn_map):
        if not ids: return {}
        if config.demo_mode(): raise AppError("CHAT_ATTACHMENT_DEMO")
        if self.chat.attachments is None or self.chat.files is None: raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
        rows = self.chat.attachments.meta(ids)
        if len(rows) != len(ids) or any(row.session_id != source.id for row in rows): raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
        copied = {}
        for old in rows:
            if old.size > config.chat_attachment_max_mb() * MB:
                raise AppError("CHAT_ATTACHMENT_TOO_LARGE", max_mb=config.chat_attachment_max_mb())
            row = ChatAttachment(id=uuid.uuid4().hex, session_id=branch.id, turn_id=turn_map.get(old.turn_id),
                                 name=old.name, kind=old.kind, mime=old.mime, size=old.size, text=old.text,
                                 text_cut=old.text_cut, created=time.time())
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as spool:
                total = 0
                for chunk in self.chat.files.open(old):
                    total += len(chunk)
                    if total > old.size: raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
                    spool.write(chunk)
                if total != old.size: raise AppError("CHAT_ATTACHMENT_NOT_FOUND")
                spool.seek(0); self.chat.files.add(row, source.workflow_id, spool)
            copied[old.id] = row.id
        return copied

    def claim(self, branch, operation, message, attachment_ids):
        edit = self.chat.sessions.branch_edit(branch.id)
        if edit is None or operation != edit.operation_id or message != edit.message or (attachment_ids or []) != json.loads(edit.attachments):
            raise AppError("CHAT_EDIT_INVALID")
        claimed = self.chat.sessions.claim_edit(branch.id, operation)
        if claimed is None: raise AppError("CHAT_EDIT_STARTED", session_id=branch.id, run_id=edit.run_id)
        return claimed
