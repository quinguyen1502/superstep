"""Personal data of one user, for account deletion / anonymisation. Org-scope resources are kept."""
from ..models.browser_session import BrowserSession, BrowserCommand, BrowserIntent
from sqlalchemy import delete, select, update
from ..models import (ApprovalChannel, ChannelIdentity, Credential, KbChunk, KbDocument, KnowledgeBase, McpServer, Notification, Run, WorkflowTemplate,
                      TeamMember, User, WorkflowShare, WorkflowToken, BrowserArtifact)
from ..models.database import Database
from ..models.run_usage import RunUsage
from ..models.usage_budget import UsageBudget
from ..models.dataset import Dataset
from ..models.dataset_access import DatasetApiToken
from .datasets import delete_dataset_definitions
from .usage_budgets import delete_budget_rows


class UserDataRepository:
    def __init__(self, db: Database): self.db = db

    def purge(self, uid: str, *, runs: bool) -> None:
        """Remove personal resources (secrets included), memberships and shares; with `runs`, also the runs they started."""
        with self.db.session() as s:
            browser_ids=select(BrowserSession.id).where(((BrowserSession.owner==uid)|(BrowserSession.principal_id=='user:'+uid)),BrowserSession.cleanup_pending.is_(False))
            personal_browser_ids=select(BrowserSession.id).where((BrowserSession.owner==uid)|(BrowserSession.principal_id=='user:'+uid))
            s.execute(delete(BrowserIntent).where(BrowserIntent.command_id.in_(select(BrowserCommand.id).where(BrowserCommand.session_id.in_(personal_browser_ids)))))
            s.execute(delete(BrowserCommand).where(BrowserCommand.session_id.in_(browser_ids)))
            s.execute(delete(BrowserSession).where(BrowserSession.id.in_(browser_ids)))
            kbs = list(s.scalars(select(KnowledgeBase.id).where(KnowledgeBase.owner == uid)))
            if kbs:
                s.execute(delete(KbChunk).where(KbChunk.kb_id.in_(kbs))); s.execute(delete(KbDocument).where(KbDocument.kb_id.in_(kbs)))
                s.execute(delete(KnowledgeBase).where(KnowledgeBase.id.in_(kbs)))
            s.execute(delete(Credential).where(Credential.owner == uid))
            s.execute(delete(BrowserArtifact).where(BrowserArtifact.owner == uid))
            s.execute(delete(McpServer).where(McpServer.owner == uid, McpServer.scope == "user"))
            s.execute(delete(ApprovalChannel).where(ApprovalChannel.owner == uid, ApprovalChannel.scope == "user"))
            s.execute(delete(ChannelIdentity).where(ChannelIdentity.user_id == uid))
            s.execute(delete(WorkflowToken).where(WorkflowToken.owner == uid))
            s.execute(delete(DatasetApiToken).where(DatasetApiToken.issuer_id == uid))
            delete_dataset_definitions(s, Dataset.owner_id == uid)
            delete_budget_rows(s, UsageBudget.user_id == uid)
            s.execute(update(UsageBudget).where(UsageBudget.created_by == uid).values(created_by=None))
            s.execute(delete(Notification).where(Notification.user_id == uid))
            s.execute(delete(WorkflowShare).where(WorkflowShare.user_id == uid))
            s.execute(delete(TeamMember).where(TeamMember.user_id == uid))
            s.execute(delete(WorkflowTemplate).where(WorkflowTemplate.owner == uid, WorkflowTemplate.scope == "user"))
            if runs:
                s.execute(delete(RunUsage).where(RunUsage.run_id.in_(select(Run.id).where(Run.owner == uid))))
                s.execute(delete(Run).where(Run.owner == uid))
            s.commit()

    def anonymise(self, uid: str) -> None:
        with self.db.session() as s:
            s.execute(update(User).where(User.id == uid).values(email=f"deleted-{uid}@deleted.invalid", password=None, active=False,
                                                                role="viewer", lang=None))
            s.commit()

    def delete_user(self, uid: str) -> None:
        with self.db.session() as s: s.execute(delete(User).where(User.id == uid)); s.commit()
