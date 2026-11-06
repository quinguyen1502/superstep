"""Trusted run scope over durable session/ticket metadata. No model-supplied authority."""
import hashlib
import json
import threading
import time

from pydantic import ValidationError
from ..core import config, crypto
from ..core.errors import AppError
from ..engine.browser_contract import ARGUMENT_MODELS, BrowserSettings, ExecutionContext, WorkerResult
from ..engine.browser_worker import LocalBrowserWorker, BrowserWorkerError
from ..engine.browser_remote import RemoteBrowserWorker, approved_transport
from ..models.browser_session import BrowserSession
from .browser_profile_service import BrowserProfileService, browser_configuration


def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


class BrowserSessionService:
    def __init__(self, repo, mcp, runtime, *, local_options=None, controllers=(), approved_proxies=(), operator_default=None, runs=None):
        self.repo,self.mcp,self.runtime,self.runs=repo,mcp,runtime,runs
        self.local_options,self.controllers=local_options or {},controllers
        self.approved_proxies,self.operator_default=approved_proxies,operator_default

    def bind(self, owner, principal, run_id, lease, *, guard=None, cancelled=lambda:False, org_allowed=True, conversation_id=None):
        lost=False
        for row in self.repo.for_run(run_id):
            if row.lease_generation!=lease:
                self.close(row,'lost');lost=True
        scope=BrowserRunScope(self,owner,principal,run_id,lease,guard,cancelled,org_allowed,conversation_id)
        scope.lost=lost
        return scope

    @staticmethod
    def context(row):
        return ExecutionContext(principal_id=row.principal_id,conversation_id=row.conversation_id,run_id=row.run_id,group_id=row.group_id,
            connection_id=row.connection_id,configuration=row.configuration,lease_generation=row.lease_generation)

    def _cleanup(self,row):
        context=self.context(row)
        try:
            if not row.worker_id: cleaned=True
            elif row.provider=='browserless':
                secrets=json.loads(crypto.decrypt(row.control_secret))
                worker=RemoteBrowserWorker(context,BrowserSettings(provider='browserless'),approved_transport(secrets,self.controllers))
                worker.session_id=row.worker_id;cleaned=worker.close()
            else:
                import re
                if not re.fullmatch(r'[a-f0-9]{32}',row.worker_id): return False
                worker=LocalBrowserWorker(context,BrowserSettings.model_construct(provider='local',allowed_origins=['https://example.com']),**self.local_options)
                worker.session_id=row.worker_id
                worker.worker,worker.gateway,worker.volume=(f'ss-browser-{row.worker_id}-{part}' for part in ('worker','gateway','socket'))
                cleaned=worker.close()
        except (BrowserWorkerError,ValueError,TypeError,ValidationError): cleaned=False
        self.repo.transition(row.id,['new','starting','ready','closed','lost','revoked','expired','unknown'],
                             row.status if row.status not in {'new','starting','ready'} else 'closed',cleanup_pending=not cleaned,control_secret=None if cleaned else row.control_secret)
        return cleaned

    def close(self, row, status='closed'):
        if row is None:return True
        if row.status not in {'new','starting','ready'} and not row.cleanup_pending:return True
        self.repo.transition(row.id,['new','starting','ready'],status,cleanup_pending=bool(row.worker_id))
        return self._cleanup(self.repo.get(row.id))

    def close_run(self, rid, lease=None):
        for row in self.repo.list_active(run_id=rid):
            if lease is not None and row.lease_generation!=lease: continue
            # Conversation-scoped pages survive chat-turn run ends until idle/max/revoke (DEC-0085).
            if row.conversation_id: continue
            self.close(row)

    def close_owner(self, owner):
        for row in self.repo.for_user(owner):self.close(row,'revoked')

    def revoke(self, connection_id):
        for row in self.repo.list_active(connection_id=connection_id): self.close(row,'revoked')

    def sweep(self):
        for row in self.repo.list_active():
            if not config.browser_runtime_enabled() or row.cleanup_pending or row.expires<=time.time() or row.status=='starting' and row.touched+30<=time.time():
                self.close(row,'expired');continue
            connection=self.mcp.repo.get(row.connection_id)
            run=self.runs.get(row.run_id) if self.runs is not None else None
            if connection is None or browser_configuration(connection)!=row.configuration:
                self.close(row,'revoked');continue
            # Cross-turn conversation pages outlive a terminal chat run until idle/max/revoke.
            if row.conversation_id: continue
            if run is not None and (run.status not in {'running','waiting','paused','queued'} or (run.lease_gen or 1)!=row.lease_generation):
                self.close(row,'revoked');continue
            if row.status=='ready' and row.worker_id:
                try:
                    context=self.context(row);settings=BrowserSettings.model_validate(json.loads(connection.settings or '{}'))
                    if row.provider=='browserless':
                        RemoteBrowserWorker.attach(context,settings,row.worker_id,approved_transport(self.mcp._stored(connection),self.controllers))
                    else:LocalBrowserWorker.attach(context,settings,row.worker_id,**self.local_options)
                except (BrowserWorkerError,ValueError,TypeError):self.close(row,'expired')


class BrowserRunScope:
    def __init__(self, service, owner, principal, rid, lease, guard, cancelled, org, conversation_id=None):
        self.service,self.owner,self.principal,self.rid,self.lease=service,owner,principal,rid,lease
        self.guard,self.cancelled,self.org,self.conversation_id=guard,cancelled,org,conversation_id

    def is_browser(self,sid):
        row=self.service.mcp.repo.get(sid)
        return row is not None and row.transport=='managed' and row.adapter=='browser'

    def _guard(self):
        if self.cancelled(): raise BrowserWorkerError('cancelled')
        if self.guard: self.guard()
        if not config.browser_runtime_enabled(): raise BrowserWorkerError('expired')

    def _connection(self,sid):
        self._guard()
        row=self.service.mcp._visible(sid,self.owner)
        if row.adapter!='browser' or row.transport!='managed': raise BrowserWorkerError('unsupported')
        if row.scope=='org' and (not self.org or not self.service.mcp.org_allowed(self.principal[5:] if self.principal.startswith('user:') else self.owner)): raise AppError('ORG_RESOURCE_NOT_ALLOWED',kind='MCP server')
        return row

    def prepare(self,group,batch,calls):
        """calls=[{index,server_id,tool,arguments}]. Called once, in model order before Send."""
        if getattr(self,'lost',False):raise BrowserWorkerError('session_lost')
        tickets={};groups={}
        for call in calls:
            if not self.is_browser(call['server_id']):continue
            try:ARGUMENT_MODELS[call['tool']].model_validate(call['arguments'])
            except (KeyError,ValidationError,ValueError,TypeError):continue
            groups.setdefault(call['server_id'],[]).append(call)
        for sid,items in groups.items():
            connection=self._connection(sid)
            gid='group:'+digest(group)[:48]
            scope_key=self.conversation_id or self.rid
            context=ExecutionContext(principal_id=self.principal,conversation_id=self.conversation_id,run_id=self.rid,group_id=gid,connection_id=sid,
                                     configuration=browser_configuration(connection),lease_generation=self.lease)
            settings,_=BrowserProfileService.prepare(connection,context)
            identity=digest([self.principal,scope_key,gid,sid])[:32]
            now=time.time()
            row=self.service.repo.reserve_session(BrowserSession(id=identity,owner=self.owner,principal_id=self.principal,
                conversation_id=self.conversation_id,run_id=self.rid,group_id=gid,connection_id=sid,configuration=context.configuration,lease_generation=self.lease,
                provider=settings.provider,status='new',created=now,expires=now+settings.lifetime_s,touched=now))
            if row is None:raise BrowserWorkerError('expired')
            if self.conversation_id and (row.run_id,row.lease_generation)!=(self.rid,self.lease):
                if not self.service.repo.claim_for_run(row.id,run_id=self.rid,lease=self.lease,principal_id=self.principal,
                        conversation_id=self.conversation_id,configuration=context.configuration):
                    self.service.close(row,'lost');raise BrowserWorkerError('session_lost')
                row=self.service.repo.get(row.id)
            if self.service.context(row)!=context:
                self.service.close(row,'lost');raise BrowserWorkerError('session_lost')
            pairs=[(digest([identity,batch,item['index']])[:32],digest([item['tool'],item['arguments']])) for item in items]
            reserved=self.service.repo.reserve(identity,pairs)
            if reserved is None:raise BrowserWorkerError('session_lost')
            for item,ticket in zip(items,reserved):tickets[item['index']]=ticket.id
        return tickets

    def _current(self,row):
        if row is None or row.expires<=time.time() or row.status not in {'new','starting','ready'}:raise BrowserWorkerError('session_lost')
        connection=self._connection(row.connection_id)
        if row.lease_generation!=self.lease or row.principal_id!=self.principal or row.run_id!=self.rid:
            raise BrowserWorkerError('session_lost')
        if (row.conversation_id or None)!=(self.conversation_id or None):
            raise BrowserWorkerError('session_lost')
        return connection,*BrowserProfileService.prepare(connection,self.service.context(row))

    def _worker(self,row):
        connection,settings,seed=self._current(row)
        secrets=self.service.mcp._stored(connection);context=self.service.context(row)
        remote=settings.provider=='browserless'
        transport=approved_transport(secrets,self.service.controllers) if remote else None
        if row.status=='new' and self.service.repo.transition(row.id,['new'],'starting'):
            worker=RemoteBrowserWorker(context,settings,transport) if remote else LocalBrowserWorker(context,settings,**self.service.local_options)
            cleanup=crypto.encrypt(json.dumps({k:secrets[k] for k in ['browserless_token']})) if remote else None
            if not self.service.repo.transition(row.id,['starting'],'starting',worker_id=worker.session_id,control_secret=cleanup,cleanup_pending=True):raise BrowserWorkerError()
            try:
                self._current(self.service.repo.get(row.id))
                worker.start(secrets=secrets,profile_seed=seed,**({} if remote else {'approved_proxies':self.service.approved_proxies,'operator_default':self.service.operator_default}))
                if not self.service.repo.transition(row.id,['starting'],'ready',cleanup_pending=False):worker.close();raise BrowserWorkerError()
                return worker
            except BaseException:
                self.service.close(self.service.repo.get(row.id),'lost');raise
        deadline=time.monotonic()+20
        while row.status in {'new','starting'} and time.monotonic()<deadline:
            self._guard();time.sleep(.02);row=self.service.repo.get(row.id)
        if row.status!='ready' or not row.worker_id:raise BrowserWorkerError()
        return RemoteBrowserWorker.attach(context,settings,row.worker_id,transport) if remote else LocalBrowserWorker.attach(context,settings,row.worker_id,**self.service.local_options)

    def skip(self,group,ticket_id):
        ticket=self.service.repo.command(ticket_id)
        row=self.service.repo.get(ticket.session_id) if ticket is not None else None
        if row is None or row.group_id!='group:'+digest(group)[:48] or (row.principal_id,row.run_id)!=(self.principal,self.rid):
            raise BrowserWorkerError('policy_denied')
        self.service.repo.skip(ticket_id)

    def call(self,group,ticket_id,operation,arguments):
        ticket=self.service.repo.command(ticket_id)
        if ticket is None:raise AppError('MCP_ARGUMENT_INVALID',name='arguments',type='browser contract')
        row=self.service.repo.get(ticket.session_id)
        if row is None or row.group_id!='group:'+digest(group)[:48] or (row.principal_id,row.run_id,row.lease_generation)!=(self.principal,self.rid,self.lease):raise BrowserWorkerError('policy_denied')
        if ticket.body_hash!=digest([operation,arguments]):raise BrowserWorkerError('policy_denied')
        worker=None;claimed=None
        try:
            self._current(row);worker=self._worker(row)
            deadline=time.monotonic()+65
            while time.monotonic()<deadline:
                self._current(self.service.repo.get(row.id))
                current=self.service.repo.command(ticket_id)
                if current.status!='pending':raise BrowserWorkerError('session_lost')
                claimed=self.service.repo.claim_command(ticket_id)
                if claimed is not None:break
                blocker=self.service.repo.head(row.id)
                if blocker is not None and blocker.status=='approval_required':
                    return WorkerResult(command_id=ticket_id,generation=1,sequence=self.service.repo.get(row.id).wire_sequence,status='approval_required',elapsed_ms=0).model_dump()
                head=self.service.repo.get(row.id)
                if head.status!='ready':raise BrowserWorkerError('session_lost')
                time.sleep(.02)
            else:raise BrowserWorkerError('expired')
            command=worker.command(operation,arguments,claimed.wire_sequence,ticket_id)
            stop=threading.Event()
            def watch():
                while not stop.wait(.1):
                    try:self._current(self.service.repo.get(row.id))
                    except Exception:worker.close();return
            watcher=threading.Thread(target=watch,daemon=True);watcher.start()
            try:
                self._current(self.service.repo.get(row.id))
                result=self.service.runtime.execute(self.owner,worker,command)
                self._current(self.service.repo.get(row.id))
            finally:stop.set()
            self.service.repo.finish(ticket_id,result.status,consumed=result.status!='approval_required')
            if result.status in {'unknown','expired','session_lost','cancelled'}:self.service.close(self.service.repo.get(row.id),'lost')
            return result.model_dump()
        except Exception as error:
            pending=self.service.repo.command(ticket_id)
            uncertain=pending is not None and pending.status=='executing' and operation in {'click','fill'}
            if pending is not None and pending.status=='executing':self.service.repo.finish(ticket_id,'unknown' if uncertain else 'session_lost')
            if worker is not None:worker.close()
            self.service.close(self.service.repo.get(row.id),'lost')
            if getattr(error,'fenced',False):raise
            return WorkerResult(command_id=ticket_id,generation=1,sequence=claimed.wire_sequence if claimed is not None else row.wire_sequence,
                status='unknown' if uncertain else 'session_lost',elapsed_ms=0).model_dump()
