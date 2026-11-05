"""Single-use exact-target decisions; all authorisation stays in the service."""
import time
from sqlalchemy import select,update,case,or_
from ..models import Run, ApprovalWait
from sqlalchemy.exc import IntegrityError
from ..models.browser_session import BrowserSession,BrowserCommand,BrowserIntent


class BrowserIntentRepository:
    def __init__(self,db):self.db=db

    def get(self,cid):
        with self.db.session() as s:return s.get(BrowserIntent,cid)

    def reserve(self,row):
        try:
            with self.db.session() as s:s.add(row);s.commit();return row
        except IntegrityError:
            existing=self.get(row.command_id)
            if existing is None:raise
            return existing

    def transition(self,cid,expected,status,**values):
        with self.db.session() as s:
            n=s.execute(update(BrowserIntent).where(BrowserIntent.command_id==cid,BrowserIntent.status.in_(expected))
                        .values(status=status,**values)).rowcount
            s.commit();return n==1

    def decide(self,cid,outcome,actor,channel):
        now=time.time()
        with self.db.session() as s:
            n=s.execute(update(BrowserIntent).where(BrowserIntent.command_id==cid,BrowserIntent.status=='pending',BrowserIntent.expires>now)
                .values(status=outcome,decided_by=actor,decided_channel=channel,decided_at=now,resume_after=now+5)).rowcount
            s.commit();return n==1

    def latest_for_node(self,rid,node):
        with self.db.session() as s:
            return s.scalar(select(BrowserIntent).join(BrowserCommand,BrowserCommand.id==BrowserIntent.command_id)
                .join(BrowserSession,BrowserSession.id==BrowserCommand.session_id)
                .where(BrowserSession.run_id==rid,BrowserIntent.node_id==node).order_by(BrowserIntent.created.desc()).limit(1))

    def close_session(self,sid):
        with self.db.session() as s:
            ids=select(BrowserCommand.id).where(BrowserCommand.session_id==sid)
            s.execute(update(BrowserIntent).where(BrowserIntent.command_id.in_(ids),BrowserIntent.status.in_(['pending','approved','dispatching']))
                .values(status=case((BrowserIntent.status=='dispatching','unknown'),else_='lost')))
            s.commit()

    def resume_candidates(self,now):
        with self.db.session() as s:
            return list(s.scalars(select(BrowserIntent).join(BrowserCommand,BrowserCommand.id==BrowserIntent.command_id)
                .join(BrowserSession,BrowserSession.id==BrowserCommand.session_id).join(Run,Run.id==BrowserSession.run_id)
                .join(ApprovalWait,ApprovalWait.browser_intent_id==BrowserIntent.command_id)
                .where(Run.status=='waiting',ApprovalWait.status=='closed',or_(BrowserIntent.resume_after.is_(None),BrowserIntent.resume_after<=now))
                .order_by(BrowserIntent.created).limit(100)))

    def claim_resume(self,cid,status,now):
        with self.db.session() as s:
            n=s.execute(update(BrowserIntent).where(BrowserIntent.command_id==cid,BrowserIntent.status==status,
                or_(BrowserIntent.resume_after.is_(None),BrowserIntent.resume_after<=now)).values(resume_after=now+30)).rowcount
            s.commit();return n==1
