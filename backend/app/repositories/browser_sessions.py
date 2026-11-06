"""CAS scheduling shared by SQLite/Postgres workers; no cached observations or effects replay."""
import time
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from ..models.browser_session import BrowserSession, BrowserCommand, BrowserCapacity


class BrowserSessionRepository:
    def __init__(self, db, max_active=16): self.db, self.max_active = db, max_active

    def get(self, sid):
        with self.db.session() as s: return s.get(BrowserSession, sid)

    def command(self, cid):
        with self.db.session() as s: return s.get(BrowserCommand, cid)

    def reserve_session(self, row):
        try:
            with self.db.session() as s:
                existing=s.get(BrowserSession,row.id)
                if existing is not None:return existing
                # A short shared-row write lock makes global capacity atomic across processes.
                if s.execute(update(BrowserCapacity).where(BrowserCapacity.id=='global').values(epoch=BrowserCapacity.epoch+1)).rowcount!=1:
                    s.rollback();return None
                existing=s.get(BrowserSession,row.id)
                if existing is not None:s.rollback();return existing
                count=s.scalar(select(func.count()).select_from(BrowserSession).where(
                    BrowserSession.status.in_(['new','starting','ready','renewing'])|BrowserSession.cleanup_pending.is_(True)))
                if count>=self.max_active:s.rollback();return None
                s.add(row);s.commit();return row
        except IntegrityError:
            existing = self.get(row.id)
            if existing is None: raise
            return existing

    def reserve(self, sid, commands):
        """Reserve an entire model-ordered batch atomically BEFORE slots are dispatched.

        Commands are (id, body_hash), with no URL/form/secret values persisted here.
        A model checkpoint retry may reuse its tickets, never replay their results.
        """
        for _ in range(20):
            try:
                with self.db.session() as s:
                    row = s.get(BrowserSession, sid)
                    if row is None or row.status not in {'new','starting','ready'}: return None
                    existing = [s.get(BrowserCommand, cid) for cid, _ in commands]
                    if any(existing):
                        if not all(item and item.session_id == sid and item.body_hash == digest for item, (_, digest) in zip(existing, commands)):
                            return None
                        return existing
                    position = row.next_order
                    if position + len(commands) > 300: return None
                    n = s.execute(update(BrowserSession).where(BrowserSession.id == sid, BrowserSession.next_order == position,
                        BrowserSession.status.in_(['new','starting','ready','renewing'])).values(next_order=position+len(commands))).rowcount
                    if n != 1: s.rollback();continue
                    result = [BrowserCommand(id=cid,session_id=sid,position=position+i,body_hash=digest,status='pending')
                              for i,(cid,digest) in enumerate(commands)]
                    s.add_all(result);s.commit();return result
            except IntegrityError: continue
        return None

    def transition(self, sid, expected, status, **values):
        with self.db.session() as s:
            n=s.execute(update(BrowserSession).where(BrowserSession.id==sid,BrowserSession.status.in_(expected))
                        .values(status=status,**values)).rowcount
            s.commit();return n==1

    def claim_command(self, cid):
        with self.db.session() as s:
            command=s.get(BrowserCommand,cid)
            if command is None: return None
            # A write CAS on the session serialises the claim, not a thread mutex.
            n=s.execute(update(BrowserSession).where(BrowserSession.id==command.session_id,
                BrowserSession.status=='ready',BrowserSession.executing_order==command.position)
                .values(touched=time.time())).rowcount
            if n!=1:s.rollback();return None
            authority=s.get(BrowserSession,command.session_id)
            n=s.execute(update(BrowserCommand).where(BrowserCommand.id==cid,BrowserCommand.status=='pending')
                        .values(status='executing',started=time.time(),wire_sequence=authority.wire_sequence,generation=authority.generation)).rowcount
            if n!=1:s.rollback();return None
            s.commit();return self.get(command.session_id)

    def finish(self, cid, status, consumed=True):
        with self.db.session() as s:
            command=s.get(BrowserCommand,cid)
            if command is None:return False
            n=s.execute(update(BrowserCommand).where(BrowserCommand.id==cid,BrowserCommand.status=='executing')
                        .values(status=status,ended=time.time())).rowcount
            if n!=1:s.rollback();return False
            # approval_required holds the head; it cannot be overtaken by another slot.
            if status!='approval_required':
                s.execute(update(BrowserSession).where(BrowserSession.id==command.session_id,
                    BrowserSession.executing_order==command.position).values(executing_order=command.position+1,
                    wire_sequence=BrowserSession.wire_sequence+int(consumed),touched=time.time()))
            self._advance_skipped(s,command.session_id)
            s.commit();return True

    def list_active(self, *, run_id=None, connection_id=None):
        with self.db.session() as s:
            q=select(BrowserSession).where((BrowserSession.status.in_(['new','starting','ready','renewing']))|BrowserSession.cleanup_pending.is_(True))
            if run_id is not None:q=q.where(BrowserSession.run_id==run_id)
            if connection_id is not None:q=q.where(BrowserSession.connection_id==connection_id)
            return list(s.scalars(q))

    def head(self,sid):
        with self.db.session() as s:
            row=s.get(BrowserSession,sid)
            if row is None:return None
            return s.scalar(select(BrowserCommand).where(BrowserCommand.session_id==sid,BrowserCommand.position==row.executing_order))

    def for_run(self,rid):
        with self.db.session() as s:return list(s.scalars(select(BrowserSession).where(BrowserSession.run_id==rid)))

    def for_owner(self,owner):
        with self.db.session() as s:return list(s.scalars(select(BrowserSession).where(BrowserSession.owner==owner)))

    def for_user(self,uid):
        with self.db.session() as s:return list(s.scalars(select(BrowserSession).where(
            (BrowserSession.owner==uid)|(BrowserSession.principal_id=='user:'+uid))))

    @staticmethod
    def _advance_skipped(s,sid):
        for _ in range(300):
            row=s.get(BrowserSession,sid)
            if row is None:return
            command=s.scalar(select(BrowserCommand).where(BrowserCommand.session_id==sid,BrowserCommand.position==row.executing_order))
            if command is None or command.status!='skipped':return
            n=s.execute(update(BrowserSession).where(BrowserSession.id==sid,BrowserSession.executing_order==row.executing_order)
                        .values(executing_order=row.executing_order+1)).rowcount
            if n!=1:return
            s.refresh(row)

    def skip(self,cid):
        with self.db.session() as s:
            command=s.get(BrowserCommand,cid)
            if command is None:return
            n=s.execute(update(BrowserCommand).where(BrowserCommand.id==cid,BrowserCommand.status.in_(['pending','approval_required'])).values(status='skipped',ended=time.time())).rowcount
            if n:self._advance_skipped(s,command.session_id)
            s.commit()

    def hold(self,cid):
        with self.db.session() as s:
            n=s.execute(update(BrowserCommand).where(BrowserCommand.id==cid,BrowserCommand.status=='pending').values(status='approval_required')).rowcount
            s.commit();return n==1

    def release(self,cid):
        with self.db.session() as s:
            n=s.execute(update(BrowserCommand).where(BrowserCommand.id==cid,BrowserCommand.status=='approval_required').values(status='pending')).rowcount
            s.commit();return n==1


    def claim_for_run(self, sid, *, run_id, lease, principal_id, conversation_id, configuration):
        """Move a live conversation-scoped session onto a later chat-turn run/lease."""
        with self.db.session() as s:
            n = s.execute(update(BrowserSession).where(
                BrowserSession.id == sid,
                BrowserSession.status.in_(['new', 'starting', 'ready', 'renewing']),
                BrowserSession.principal_id == principal_id,
                BrowserSession.conversation_id == conversation_id,
                BrowserSession.configuration == configuration,
            ).values(run_id=run_id, lease_generation=lease, touched=time.time())).rowcount
            s.commit()
            return n == 1

    def for_conversation(self, conversation_id):
        with self.db.session() as s:
            return list(s.scalars(select(BrowserSession).where(
                BrowserSession.conversation_id == conversation_id,
                (BrowserSession.status.in_(['new', 'starting', 'ready', 'renewing'])) | BrowserSession.cleanup_pending.is_(True))))
