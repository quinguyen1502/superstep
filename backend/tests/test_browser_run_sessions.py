"""Durable ordering starts before dispatch and works across independent database connections."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import time
import uuid

from app.models.database import Database
from app.models import User
from app.models.browser_session import BrowserSession
from app.repositories.browser_sessions import BrowserSessionRepository


def run_ordered_command(url, cid, delay):
    time.sleep(delay)
    db=Database(url);repo=BrowserSessionRepository(db)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        row=repo.claim_command(cid)
        if row is not None:
            time.sleep(.03)
            repo.finish(cid,'confirmed')
            return row.executing_order
        time.sleep(.01)
    raise AssertionError('Command never acquired its declared position')


def prepare(tmp_path, database=None):
    db=database or Database('sqlite:///'+str(tmp_path/'browser-sessions.db'));db.migrate()
    with db.session() as s:
        s.add(User(id='owner',email='browser-owner@example.test',password='fixture',created=time.time()));s.commit()
    now=time.time();repo=BrowserSessionRepository(db)
    row=repo.reserve_session(BrowserSession(id=uuid.uuid4().hex,owner='owner',principal_id='user:owner',run_id='run',group_id='agent',
        connection_id='connection',configuration='a'*64,lease_generation=1,provider='local',status='ready',created=now,expires=now+600,touched=now))
    return db,repo,row


def test_model_batch_is_ordered_before_multi_process_dispatch(tmp_path):
    db,repo,row=prepare(tmp_path)
    commands=[(uuid.uuid4().hex, str(i)*64) for i in range(4)]
    reserved=repo.reserve(row.id,commands)
    assert [item.position for item in reserved]==[0,1,2,3]
    assert [item.id for item in repo.reserve(row.id,commands)]==[item.id for item in reserved]
    assert repo.reserve(row.id,[(commands[0][0],'changed')]) is None
    # Later model calls deliberately reach the DB first, in other processes.
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks=[pool.submit(run_ordered_command,db.url,cid,(3-i)*.1) for i,(cid,_) in enumerate(commands)]
        assert [task.result(15) for task in tasks]==[0,1,2,3]
    assert repo.get(row.id).executing_order==4 and repo.get(row.id).wire_sequence==4
    # Repeating a confirmed ticket cannot replay either a read result or a website effect.
    assert repo.claim_command(commands[0][0]) is None


def test_approval_holds_head_and_closed_session_refuses_new_tickets(tmp_path):
    db,repo,row=prepare(tmp_path)
    commands=[(uuid.uuid4().hex,'a'*64),(uuid.uuid4().hex,'b'*64)]
    repo.reserve(row.id,commands)
    assert repo.claim_command(commands[1][0]) is None
    assert repo.claim_command(commands[0][0]) is not None
    assert repo.finish(commands[0][0],'approval_required',consumed=False)
    assert repo.get(row.id).wire_sequence==0 and repo.claim_command(commands[1][0]) is None
    assert repo.transition(row.id,['ready'],'revoked')
    assert repo.reserve(row.id,[(uuid.uuid4().hex,'c'*64)]) is None
    assert repo.claim_command(commands[1][0]) is None


def scoped_service(tmp_path,monkeypatch):
    from app.models import McpServer
    from app.repositories import McpServerRepository
    from app.services.mcp_service import McpService
    from app.services.browser_session_service import BrowserSessionService
    from app.services.browser_runtime_service import BrowserRuntimeService
    from app.engine.browser_worker import LocalBrowserWorker, BrowserWorkerError
    from app.engine.browser_contract import WorkerResult
    db,repo,_=prepare(tmp_path)
    monkeypatch.setenv('STUDIO_ENABLE_BROWSER','1')
    monkeypatch.setenv('STUDIO_ENABLE_BROWSER_RUNTIME','1')
    mcp=McpService(McpServerRepository(db))
    mcp.repo.save(McpServer(id='browser',owner='owner',scope='user',transport='managed',adapter='browser',name='Browser',settings='{"allowed_origins":["https://example.com"]}',created=time.time()))
    calls=[];workers={}
    class Worker(LocalBrowserWorker):
        def start(self,**kwargs):self.started=True;workers[self.session_id]=self;return self
        @classmethod
        def attach(cls,context,settings,worker_id,**kwargs):
            worker=workers.get(worker_id)
            if worker is None or worker.closed:raise BrowserWorkerError()
            # Conversation pages may move to a later chat-turn run/lease.
            if worker.context!=context:
                same=(worker.context.principal_id==context.principal_id and worker.context.connection_id==context.connection_id
                      and worker.context.group_id==context.group_id
                      and (worker.context.conversation_id or None)==(context.conversation_id or None))
                if not same:raise BrowserWorkerError()
                worker.context=context
            return worker
        def call(self,command):
            calls.append(command)
            time.sleep(.02)
            return WorkerResult(command_id=command.command_id,generation=1,sequence=command.sequence,status='confirmed',elapsed_ms=20)
        def inspect(self,command):
            from app.engine.browser_contract import WorkerTarget
            return WorkerTarget(generation=self.generation,page_generation=1,target_hash=getattr(self,'target_hash','a'*64),origin='https://example.test',role='button',text='Fixture')
        def health(self):return {'status':'ready','generation':self.generation,'idle_remaining_ms':120000,'lifetime_remaining_ms':600000}
        def approve(self,command,target=None,expires_at_ms=None):return {'status':'approved'}
        def renew(self,context):self.context=context;self.generation+=1;return {'status':'ready','generation':self.generation}
        def close(self):
            self.closed=True
            if self.session_id in workers:workers[self.session_id].closed=True
            return True
    monkeypatch.setattr('app.services.browser_session_service.LocalBrowserWorker',Worker)
    service=BrowserSessionService(repo,mcp,BrowserRuntimeService(None))
    from app.repositories import ApprovalRepository,UserRepository
    from app.repositories.browser_intents import BrowserIntentRepository
    from app.services.browser_approval_service import BrowserApprovalService
    service.approvals=BrowserApprovalService(BrowserIntentRepository(db),ApprovalRepository(db),UserRepository(db),service)
    return service,calls,workers


def test_run_scope_keeps_page_across_rounds_and_orders_threads(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    scope=service.bind('owner','user:owner','run-one',1)
    batch=[{'index':i,'server_id':'browser','tool':'navigate','arguments':{'url':f'https://example.com/{i}'}} for i in range(2)]
    tickets=scope.prepare('agent','round-one',batch)
    def invoke(i):
        if i==0:time.sleep(.05)
        return scope.call('agent',tickets[i],'navigate',batch[i]['arguments'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(invoke,[1,0]))
    assert all(result['status']=='confirmed' for result in results)
    assert [call.arguments['url'] for call in calls]==['https://example.com/0','https://example.com/1']
    later=scope.prepare('agent','round-two',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])
    assert scope.call('agent',later[0],'snapshot',{})['status']=='confirmed'
    assert len(workers)==1 and [call.sequence for call in calls]==[0,1,2]
    # Foreign scope cannot take control or close the owner's page.
    foreign=service.bind('owner','visitor:other','run-one',1)
    import pytest
    from app.engine.browser_worker import BrowserWorkerError
    with pytest.raises(BrowserWorkerError):foreign.call('agent',later[0],'snapshot',{})
    assert not next(iter(workers.values())).closed
    service.close_run('run-one');assert next(iter(workers.values())).closed


def test_cross_turn_conversation_reattaches_live_page(tmp_path,monkeypatch):
    """Same conversation/principal/connection keeps the worker across chat-turn run ends."""
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    first=service.bind('owner','user:owner','run-one',1,conversation_id='chat-session-1')
    ticket=first.prepare('agent','turn-1',[{'index':0,'server_id':'browser','tool':'navigate','arguments':{'url':'https://example.com/a'}}])[0]
    assert first.call('agent',ticket,'navigate',{'url':'https://example.com/a'})['status']=='confirmed'
    worker_id=next(iter(workers))
    # First chat turn ends successfully: conversation session must survive close_run.
    service.close_run('run-one',1)
    assert not workers[worker_id].closed
    second=service.bind('owner','user:owner','run-two',2,conversation_id='chat-session-1')
    later=second.prepare('agent','turn-2',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])
    assert second.call('agent',later[0],'snapshot',{})['status']=='confirmed'
    assert len(workers)==1 and list(workers)==[worker_id]
    # A different conversation cannot reattach the same page.
    import pytest
    from app.engine.browser_worker import BrowserWorkerError
    other=service.bind('owner','user:owner','run-three',1,conversation_id='chat-session-other')
    with pytest.raises(BrowserWorkerError):
        other.call('agent',later[0],'snapshot',{})


def test_updated_connection_and_cancel_deny_late_commands(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    cancel=[False]
    scope=service.bind('owner','user:owner','run-one',1,cancelled=lambda:cancel[0])
    ticket=scope.prepare('agent','round-one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    assert scope.call('agent',ticket,'snapshot',{})['status']=='confirmed'
    next_ticket=scope.prepare('agent','round-two',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    row=service.mcp.repo.get('browser');row.settings='{"allowed_origins":["https://example.com"],"max_actions":2}';service.mcp.repo.save(row)
    assert scope.call('agent',next_ticket,'snapshot',{})['status']=='session_lost'
    assert len(calls)==1 and next(iter(workers.values())).closed


def test_capacity_and_no_replay_after_lost_page(tmp_path,monkeypatch):
    from app.engine.browser_worker import BrowserWorkerError
    import pytest
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    service.repo.max_active=2  # one row was seeded by the repo fixture
    scope=service.bind('owner','user:owner','run-one',1)
    ticket=scope.prepare('agent','one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    assert scope.call('agent',ticket,'snapshot',{})['status']=='confirmed'
    with pytest.raises(BrowserWorkerError):scope.prepare('other-agent','one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])
    next(iter(workers.values())).closed=True
    second=scope.prepare('agent','two',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    assert scope.call('agent',second,'snapshot',{})['status']=='session_lost'
    assert len(workers)==1 and len(calls)==1


def test_real_agent_run_binds_browser_and_cleans_terminal_page(tmp_path,monkeypatch):
    import asyncio
    from app.engine import agents
    from app.engine.ports import Ports
    from app.repositories import RunRepository,WorkflowRepository,NodeResultRepository
    from app.services.run_service import RunService,RunPlan
    from tests.test_agent_node import wf,call
    from app.engine.browser_contract import tool_definitions
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    definitions={item['name']:item['input_schema'] for item in tool_definitions()}
    tools=[{'name':name,'description':name,'source':'mcp','server_id':'browser','tool':name,'parameters':definitions[name]} for name in ['navigate','snapshot']]
    generic=[]
    tools.append({'name':'generic','description':'generic','source':'mcp','server_id':'ordinary','tool':'echo','parameters':{'type':'object','properties':{}}})
    responses=iter([('',[call('navigate',{'url':'https://example.com/first'},'one'),call('snapshot',{},'two'),call('generic',{},'three')]),
                    ('',[call('snapshot',{},'four')]),('Done',[])])
    models=[]
    def fake(messages,*args,**kwargs):models.append(messages);return next(responses)
    monkeypatch.setattr(agents,'call_agent',fake)
    monkeypatch.setenv('STUDIO_AGENT_PARALLEL_TOOLS','4')
    ports=Ports(mcp_call=lambda *args:generic.append(args) or 'generic-result')
    runs=RunRepository(service.repo.db)
    runner=RunService(WorkflowRepository(service.repo.db),runs,browser=service,ledger=NodeResultRepository(service.repo.db))
    events=[]
    async def send(event):events.append(event);return True
    async def listen():await asyncio.Event().wait()
    plan=RunPlan(None,wf(tools=tools,steps_field='steps'),{'message':'fixture'},run_id='agent-browser-run',ports=ports)
    assert asyncio.run(runner.execute(plan,send,listen,'owner'))=='ok'
    assert [command.operation for command in calls]==['navigate','snapshot','snapshot']
    assert [command.sequence for command in calls]==[0,1,2] and len(workers)==1 and generic
    assert next(iter(workers.values())).closed
    assert all('_browser_ticket' not in str(message.get('tool_calls')) for messages in models for message in messages)
    assert runs.get('agent-browser-run').status=='ok'


def test_browser_tool_bypasses_node_ledger_and_rejected_head_is_skipped(tmp_path,monkeypatch):
    from app.engine.effects import Effects
    from app.engine.ports import Ports
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    scope=service.bind('owner','user:owner','run-one',1)
    batch=[{'index':i,'server_id':'browser','tool':'snapshot','arguments':{}} for i in range(2)]
    tickets=scope.prepare('agent','one',batch)
    scope.skip('agent',tickets[0])
    assert scope.call('agent',tickets[1],'snapshot',{})['status']=='confirmed' and calls[0].sequence==0
    class Ledger:
        def get(self,*args):raise AssertionError('A browser observation was read from the generic ledger')
        def put(self,*args):raise AssertionError('A browser observation was stored in the generic ledger')
    node={'id':'mcp','type':'mcp','data':{'server_id':'browser'}}
    ports=Ports(browser=scope)
    effect=Effects('run-one',ledger=Ledger())
    assert effect.wrap(node,lambda state:{'fresh':True},cache=lambda state:ports.cache_mcp(node,state))({})=={'fresh':True}


def test_fence_change_and_disable_refuse_late_dispatch(tmp_path,monkeypatch):
    import pytest
    from app.engine.browser_worker import BrowserWorkerError
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    scope=service.bind('owner','user:owner','run-one',1)
    ticket=scope.prepare('agent','one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    assert scope.call('agent',ticket,'snapshot',{})['status']=='confirmed'
    replacement=service.bind('owner','user:owner','run-one',2)
    with pytest.raises(BrowserWorkerError):replacement.prepare('agent','two',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])
    assert len(calls)==1 and next(iter(workers.values())).closed
    monkeypatch.delenv('STUDIO_ENABLE_BROWSER_RUNTIME')
    with pytest.raises(BrowserWorkerError):scope.prepare('different-agent','three',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])


def test_connection_crud_revokes_and_pending_cleanup_survives_user_purge(tmp_path,monkeypatch):
    from app.repositories.user_data import UserDataRepository
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    scope=service.bind('owner','user:owner','run-one',1)
    ticket=scope.prepare('agent','one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    scope.call('agent',ticket,'snapshot',{})
    row=service.repo.get(service.repo.command(ticket).session_id)
    service.mcp.browser_lifecycle=lambda:service
    root=next(iter(workers.values()));cls=type(root);close=cls.close
    monkeypatch.setattr(cls,'close',lambda self:False)  # daemon outage: cleanup is not verified
    service.mcp.update('browser','owner','Changed',settings={'allowed_origins':['https://example.com'],'max_actions':3})
    assert service.repo.get(row.id).status=='revoked' and service.repo.get(row.id).cleanup_pending
    UserDataRepository(service.repo.db).purge('owner',runs=True)
    assert service.repo.get(row.id).cleanup_pending and service.mcp.repo.get('browser') is None
    monkeypatch.setattr(cls,'close',close)
    service.sweep()
    assert not service.repo.get(row.id).cleanup_pending and root.closed


def test_cancel_during_possible_effect_is_unknown_and_not_retried(tmp_path,monkeypatch):
    from app.engine.browser_contract import WorkerResult
    import json as _json
    service,calls,workers=scoped_service(tmp_path,monkeypatch)
    row=service.mcp.repo.get('browser');s=_json.loads(row.settings or '{}');s['require_mutating_approval']=True
    row.settings=_json.dumps(s);service.mcp.repo.save(row)
    cancelled=[False];scope=service.bind('owner','user:owner','run-one',1,cancelled=lambda:cancelled[0])
    first=scope.prepare('agent','one',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    scope.call('agent',first,'snapshot',{})
    root=next(iter(workers.values()))
    def act(command):
        calls.append(command);cancelled[0]=True
        return WorkerResult(command_id=command.command_id,generation=1,sequence=command.sequence,status='confirmed',elapsed_ms=0)
    monkeypatch.setattr(root,'call',act)
    args={'observation_id':'observation','element_id':'element'}
    ticket=scope.prepare('agent','two',[{'index':0,'server_id':'browser','tool':'click','arguments':args}])[0]
    info=scope.action('fixture-slot','agent',ticket,'click',args)
    from app.models import ApprovalWait
    wait=ApprovalWait(id=uuid.uuid4().hex,run_id='run-one',node_id='fixture-slot',owner='owner',status='closed',outcome='answered',created=time.time(),browser_intent_id=ticket)
    service.approvals.waits.add_wait(wait,[])
    assert service.approvals.record(wait,'owner','approved','studio')
    assert scope.call('agent',ticket,'click',args)['status']=='unknown'
    assert service.repo.command(ticket).status=='unknown' and root.closed and len(calls)==2


def test_principal_comes_from_chat_actor_not_resource_owner(tmp_path,monkeypatch):
    from app.models import ChatSession,ChatTurn,Run
    from app.repositories import RunRepository,WorkflowRepository
    from app.services.run_service import RunService,RunPlan
    db,repo,row=prepare(tmp_path)
    runner=RunService(WorkflowRepository(db),RunRepository(db))
    plan=RunPlan(None,{}, {},source='chat')
    with db.session() as s:
        for name,owner,visitor,external in [('studio','owner',None,None),('visitor',None,'anonymous',None),('app',None,None,'external-user')]:
            s.add(ChatSession(id=name,workflow_id='workflow',trigger_id='trigger',owner=owner,visitor=visitor,external_user=external,app_key_id='app-key' if external else None,created=time.time(),updated=time.time()))
            s.add(ChatTurn(id='turn-'+name,session_id=name,run_id='run-'+name,role='user',text='fixture',created=time.time()))
            s.add(Run(id='run-'+name,owner='resource-owner',source='chat',workflow_id='workflow'))
        s.add(Run(id='child',owner='resource-owner',source='tool',parent_run_id='run-visitor'))
        s.commit()
    assert runner.browser_principal('run-studio',plan,'resource-owner')=='user:owner'
    visitor=runner.browser_principal('run-visitor',plan,'resource-owner')
    assert visitor.startswith('visitor:') and runner.browser_principal('child',plan,'resource-owner')==visitor
    assert runner.browser_principal('run-app',plan,'resource-owner').startswith('app:')
    assert runner.browser_principal('missing-chat',plan,'resource-owner').startswith('chat:')


# Optional disposable PostgreSQL repeats the real multi-process claim/CAS proof.
import pytest
from tests.test_db_postgres import fresh_pg, URL


@pytest.mark.skipif(not URL.startswith('postgresql'),reason='requires disposable TEST_DATABASE_URL')
def test_postgres_model_batch_is_ordered_across_processes(tmp_path,fresh_pg):
    db,repo,row=prepare(tmp_path,fresh_pg)
    commands=[(uuid.uuid4().hex,str(i)*64) for i in range(4)]
    assert [item.position for item in repo.reserve(row.id,commands)]==[0,1,2,3]
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks=[pool.submit(run_ordered_command,db.url,cid,(3-i)*.1) for i,(cid,_) in enumerate(commands)]
        assert [task.result(20) for task in tasks]==[0,1,2,3]
    assert repo.get(row.id).wire_sequence==4
