"""Exact-target human decisions. Model/page text never grants browser authority."""
import time
import json
from .job_queue import enqueue_resume

from ..core import config
from ..engine.browser_worker import BrowserWorkerError
from ..models import BrowserIntent

EFFECTS={'click','fill'}
HUMAN_CHANNELS={'studio','slack','telegram','teams','email','whatsapp'}


class BrowserApprovalOutcome(Exception):
    def __init__(self,outcome):self.outcome=outcome;super().__init__('Browser approval '+outcome)


class BrowserApprovalService:
    def __init__(self,intents,waits,users,sessions,enqueue=None,active=None):
        self.intents,self.waits,self.users,self.sessions=intents,waits,users,sessions
        self.enqueue,self.active=enqueue,active

    @staticmethod
    def summary(intent):
        return {'intent_id':intent.command_id,'origin':intent.origin,'role':intent.role,'text':intent.text,'expires':intent.expires}

    def prepare(self,scope,node,group,cid,operation,arguments,force=False):
        row,ticket=scope.ticket(group,cid,operation,arguments)
        intent=self.intents.get(cid)
        try:scope._current(row)
        except Exception as error:
            self.sessions.close(row,'lost')
            if getattr(error,'fenced',False):raise
            return {'state':'session_lost'}
        if intent is None and operation not in EFFECTS and not force:return {'state':'allowed'}
        if ticket.status=='confirmed' and scope.resuming:return {'state':'allowed'}
        if intent is not None:
            if intent.status in {'pending','approved'} and (intent.expires<=time.time() or intent.status=='approved' and not self.valid_decision(intent)):
                self.intents.transition(cid,['pending','approved'],'expired');self.sessions.repo.skip(cid)
                return {'state':'expired',**self.summary(intent)}
            if intent.status in {'rejected','expired','stale'}:
                self.sessions.repo.skip(cid);return {'state':intent.status,**self.summary(intent)}
            if intent.status in {'dispatching','unknown','lost'}:
                self.intents.transition(cid,['dispatching'],'unknown')
                self.sessions.repo.finish(cid,'unknown')
                self.sessions.close(row,'unknown');return {'state':'unknown',**self.summary(intent)}
            if intent.status not in {'approved','pending'}:return {'state':'stale' if intent.status=='stale_observation' else 'session_lost',**self.summary(intent)}
            return {'state':'allowed' if intent.status=='approved' else 'waiting',**self.summary(intent)}
        worker=None
        try:
            scope._current(row);worker=scope._worker(row)
            deadline=time.monotonic()+65
            while time.monotonic()<deadline:
                scope._current(self.sessions.repo.get(row.id))
                head=self.sessions.repo.head(row.id)
                if head is None:raise BrowserWorkerError()
                if head.id==cid:break
                if head.status=='approval_required':
                    prior=self.intents.get(head.id)
                    if prior is None or prior.status=='pending':return {'state':'deferred'}
                time.sleep(.02)
            else:raise BrowserWorkerError('expired')
            row=self.sessions.repo.get(row.id)
            command=worker.command(operation,arguments,row.wire_sequence,cid)
            target=worker.inspect(command)
            health=worker.health()
            expiry=min(row.expires,time.time()+max(0,health['idle_remaining_ms'])/1000,time.time()+300)
            if expiry<=time.time():raise BrowserWorkerError('expired')
            intent=self.intents.reserve(BrowserIntent(command_id=cid,node_id=node,status='pending',target_hash=target.target_hash,
                page_generation=target.page_generation,origin=target.origin,role=target.role,text=target.text,
                created=time.time(),expires=expiry))
            self.sessions.repo.hold(cid)
            return {'state':'waiting',**self.summary(intent)}
        except BrowserWorkerError as error:
            if error.status in {'stale_observation','policy_denied'}:
                self.sessions.repo.skip(cid);return {'state':'stale' if error.status=='stale_observation' else 'policy_denied'}
            if worker is not None:worker.close()
            self.sessions.close(self.sessions.repo.get(row.id),'lost')
            return {'state':'session_lost'}

    def record(self,wait,actor,response,channel):
        """Called only after the existing authenticated owner/reviewer/channel CAS accepted the answer."""
        if not wait.browser_intent_id:return False
        intent=self.intents.get(wait.browser_intent_id)
        if intent is None or intent.node_id!=wait.node_id:return False
        command=self.sessions.repo.command(intent.command_id)
        row=self.sessions.repo.get(command.session_id) if command else None
        if row is None or row.run_id!=wait.run_id or row.status not in {'ready','renewing'} or not config.browser_runtime_enabled():
            self.intents.transition(intent.command_id,['pending'],'expired');return False
        if channel not in HUMAN_CHANNELS and channel not in {'auto','deadline'}:return False
        current=self.waits.wait_of(wait.id)
        if channel not in {'auto','deadline'} and (current is None or current.status!='closed' or current.outcome!='answered'):
            return False
        user=self.users.get_by_id(actor) if actor else None
        if (channel not in HUMAN_CHANNELS or user is None or not user.active or
            actor!=wait.owner and actor not in self.waits.wait_approvers(wait.id)):
            self.intents.transition(intent.command_id,['pending'],'expired')
            return False
        approved=isinstance(response,str) and response.strip().lower()=='approved'
        return self.intents.decide(intent.command_id,'approved' if approved else 'rejected',actor,channel)

    def direct_decision(self,rid,node,actor,response):
        wait=self.waits.latest_wait_for_node(rid,node)
        if wait is None or wait.status!='closed' or wait.outcome!='answered':return False
        return self.record(wait,actor,response,'studio')

    def valid_decision(self,intent):
        user=self.users.get_by_id(intent.decided_by) if intent.decided_by else None
        return bool(user and user.active and intent.decided_channel in HUMAN_CHANNELS and intent.decided_at is not None and intent.created<=intent.decided_at<intent.expires)

    def ready(self,cid,operation):
        intent=self.intents.get(cid)
        if intent is None:return operation not in EFFECTS
        if intent.status!='approved' or intent.consumed_at is not None or intent.expires<=time.time() or not self.valid_decision(intent):return False
        return True

    def consume(self,scope,row,ticket,worker,command):
        intent=self.intents.get(ticket.id)
        if intent is None:
            if command.operation in EFFECTS:raise BrowserApprovalOutcome('waiting')
            return None
        if intent.expires<=time.time():
            self.intents.transition(ticket.id,['pending','approved'],'expired');raise BrowserApprovalOutcome('expired')
        if intent.status!='approved':raise BrowserApprovalOutcome('waiting')
        if not self.valid_decision(intent):
            self.intents.transition(ticket.id,['approved'],'expired');raise BrowserApprovalOutcome('expired')
        try:target=worker.inspect(command)
        except BrowserWorkerError as error:
            if error.status=='stale_observation':
                self.intents.transition(ticket.id,['approved'],'stale');raise BrowserApprovalOutcome('stale') from None
            raise
        if target.generation!=command.generation or (target.target_hash,target.page_generation,target.origin)!=(intent.target_hash,intent.page_generation,intent.origin):
            self.intents.transition(ticket.id,['approved'],'stale');raise BrowserApprovalOutcome('stale')
        if not self.intents.transition(ticket.id,['approved'],'dispatching',consumed_at=time.time()):raise BrowserApprovalOutcome('unknown')
        if command.operation in EFFECTS:
            result=worker.approve(command,target=target,expires_at_ms=int(intent.expires*1000))
            if result.get('status')!='approved':
                outcome='expired' if result.get('status')=='expired' else 'stale'
                self.intents.transition(ticket.id,['dispatching'],outcome);raise BrowserApprovalOutcome(outcome)
        return intent

    def outcome(self,cid,status):
        if self.intents.get(cid) is not None:self.intents.transition(cid,['dispatching','pending','approved'] if status in {'lost','expired'} else ['dispatching'],status)

    def recover_decisions(self,now=None):
        """Repair accepted-decision/queue crash windows, including multiple waits in one wave.

        Only an unconsumed verified decision can grant. Dispatching/unknown outcomes
        are stopped, never converted into another browser attempt.
        """
        if self.enqueue is None or self.sessions.runs is None:return 0
        now=time.time() if now is None else now;count=0
        for intent in self.intents.resume_candidates(now):
            command=self.sessions.repo.command(intent.command_id)
            session=self.sessions.repo.get(command.session_id) if command else None
            run=self.sessions.runs.get(session.run_id) if session else None
            if run is None or run.status!='waiting' or self.active and self.active(run.id):continue
            checkpoint=json.loads(run.checkpoint or '{}')
            awaiting=checkpoint.get('browser_intent')==intent.command_id or any(wait.get('browser_intent')==intent.command_id for wait in checkpoint.get('waits') or [])
            wait=self.waits.latest_wait_for_node(run.id,intent.node_id)
            if not awaiting or wait is None or wait.status!='closed' or wait.browser_intent_id!=intent.command_id:continue
            if not self.intents.claim_resume(intent.command_id,intent.status,now):continue
            approved=intent.status=='approved' and intent.consumed_at is None and intent.expires>now and self.valid_decision(intent)
            if intent.status=='dispatching':
                self.intents.transition(intent.command_id,['dispatching'],'unknown');self.sessions.close(session,'unknown')
            elif intent.status=='pending' or intent.status=='approved' and not approved:
                self.intents.transition(intent.command_id,['pending','approved'],'expired')
            enqueue_resume(self.sessions.runs,self.enqueue,{'kind':'resume','run_id':run.id,'owner':run.owner,'workflow_id':run.workflow_id,
                'node':intent.node_id,'response':'approved' if approved else 'rejected',
                'by':{'channel':'browser_recovery','user_id':intent.decided_by}})
            count+=1
        return count
