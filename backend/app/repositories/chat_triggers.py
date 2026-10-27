import time
from typing import Optional
from sqlalchemy import delete, select, update
from ..models import ChatLogo, WorkflowChatTrigger
from ..models.database import Database


WEB = "web"  # channel_id and place of a workflow's web chat trigger (TASK-0084)


class ChatTriggerRepository:
    def __init__(self, db: Database): self.db = db

    def add(self, t: WorkflowChatTrigger) -> WorkflowChatTrigger:
        with self.db.session() as s: s.add(t); s.commit(); s.refresh(t); return t

    def get(self, tid: str) -> Optional[WorkflowChatTrigger]:
        with self.db.session() as s: return s.get(WorkflowChatTrigger, tid)

    def list_for_workflow(self, wid: str) -> list[WorkflowChatTrigger]:
        with self.db.session() as s:
            return list(s.scalars(select(WorkflowChatTrigger).where(WorkflowChatTrigger.workflow_id == wid, WorkflowChatTrigger.channel_id != WEB)
                                  .order_by(WorkflowChatTrigger.created)))  # Slack / Telegram triggers; the web chat has its own settings

    def web(self, wid: str) -> Optional[WorkflowChatTrigger]:
        """The workflow's web chat (at most one)."""
        with self.db.session() as s:
            return s.scalar(select(WorkflowChatTrigger).where(WorkflowChatTrigger.workflow_id == wid, WorkflowChatTrigger.channel_id == WEB))

    def webs(self) -> list[WorkflowChatTrigger]:
        with self.db.session() as s: return list(s.scalars(select(WorkflowChatTrigger).where(WorkflowChatTrigger.channel_id == WEB)))

    def count_for_workflow(self, wid: str) -> int:
        return len(self.list_for_workflow(wid))

    def find(self, channel_id: str, place: str, command: str) -> Optional[WorkflowChatTrigger]:
        """The trigger that answers this command in this place (unique, uq_workflow_chat_triggers_command)."""
        with self.db.session() as s:
            return s.scalar(select(WorkflowChatTrigger).where(WorkflowChatTrigger.channel_id == channel_id, WorkflowChatTrigger.place == place,
                                                              WorkflowChatTrigger.command == command))

    def set_fields(self, tid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(WorkflowChatTrigger).where(WorkflowChatTrigger.id == tid).values(**values)); s.commit()

    def stop_for_channel(self, cid: str, note: str) -> int:
        with self.db.session() as s:
            n = s.execute(update(WorkflowChatTrigger).where(WorkflowChatTrigger.channel_id == cid).values(enabled=False, note=note)).rowcount
            s.commit(); return n or 0

    def delete(self, tid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(ChatLogo).where(ChatLogo.trigger_id == tid)); s.execute(delete(WorkflowChatTrigger).where(WorkflowChatTrigger.id == tid)); s.commit()

    def delete_for_workflow(self, wid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(ChatLogo).where(ChatLogo.trigger_id.in_(select(WorkflowChatTrigger.id).where(WorkflowChatTrigger.workflow_id == wid))))
            s.execute(delete(WorkflowChatTrigger).where(WorkflowChatTrigger.workflow_id == wid)); s.commit()

    # ---- a web chat's logo (TASK-0145) ----
    def logo(self, tid: str) -> Optional[ChatLogo]:
        with self.db.session() as s: return s.get(ChatLogo, tid)

    def set_logo(self, tid: str, mime: Optional[str], data: Optional[bytes]) -> None:
        """Replaces the logo, or removes it when `data` is None."""
        with self.db.session() as s:
            s.execute(delete(ChatLogo).where(ChatLogo.trigger_id == tid))
            if data is not None: s.add(ChatLogo(trigger_id=tid, mime=mime, data=data, created=time.time()))
            s.commit()
