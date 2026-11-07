"""Verified human intent, current target and live session are all necessary to execute an effect."""
import asyncio
import json
import time
import uuid
import pytest

from app.engine import agents
from app.engine.browser_contract import tool_definitions
from app.models import ApprovalWait
from app.repositories import ApprovalRepository,UserRepository,WorkflowRepository,RunRepository,NodeResultRepository
from app.services.approval_service import ApprovalService
from app.services.channel_service import ChannelService
from app.services.run_service import RunService
from tests.test_agent_node import wf,call
from tests.test_browser_run_sessions import scoped_service



def enable_mutating_approval(service, connection_id='browser'):
    """Accepted DEC-0085: mutating approval default OFF; tests that expect waits opt in."""
    row=service.mcp.repo.get(connection_id)
    settings=json.loads(row.settings or '{}')
    settings.setdefault('allowed_origins',['https://example.com'])
    settings['require_mutating_approval']=True
    row.settings=json.dumps(settings)
    service.mcp.repo.save(row)


def runner_for(service):
    db=service.repo.db;waits=ApprovalRepository(db);users=UserRepository(db);runs=RunRepository(db);workflows=WorkflowRepository(db)
    approvals=ApprovalService(waits,users,workflows,runs,ChannelService(waits,users,{}),background=False,browser=lambda:service.approvals)
    service.runs=runs
    runner=RunService(workflows,runs,mcp=service.mcp,browser=service,approvals=approvals,ledger=NodeResultRepository(db))
    service.approvals.active=lambda rid:runner.bus.owner(rid) is not None
    return runner


def flow_for(operations):
    schemas={item['name']:item['input_schema'] for item in tool_definitions()}
    return wf(tools=[{'name':name,'description':name,'source':'mcp','server_id':'browser','tool':name,'parameters':schemas[name]}
                     for name in operations],steps_field='steps')


def execute(runner,plan):
    events=[]
    async def send(event):events.append(event);return True
    async def listen():await asyncio.Event().wait()
    return asyncio.run(runner.execute(plan,send,listen,'owner')),events


def responses(monkeypatch,items):
    iterator=iter(items)
    monkeypatch.setattr(agents,'call_agent',lambda *args,**kwargs:next(iterator))


def test_default_mutating_approval_off_runs_click_immediately(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    monkeypatch.setenv('STUDIO_AGENT_PARALLEL_TOOLS','4')
    args={'observation_id':'observed','element_id':'button'}
    responses(monkeypatch,[('',[call('navigate',{'url':'https://example.test/form'},'a'),
        call('click',args,'b'),call('snapshot',{},'c')]),('Done',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['navigate','click','snapshot']),'input':{'message':'fixture'}});plan.run_id='default-off'
    status,events=execute(runner,plan)
    assert status=='ok' and [command.operation for command in calls]==['navigate','click','snapshot']
    assert runner.approvals.repo.latest_wait('default-off') is None


def test_mutating_approval_on_click_waits_and_only_real_owner_decision_grants_once(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    monkeypatch.setenv('STUDIO_AGENT_PARALLEL_TOOLS','4')
    args={'observation_id':'observed','element_id':'button'}
    responses(monkeypatch,[('',[call('navigate',{'url':'https://example.test/form?secret=must-not-trace'},'a'),
        call('click',args,'b'),call('snapshot',{},'c')]),('Done',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['navigate','click','snapshot']),'input':{'message':'fixture'}});plan.run_id='approval-run'
    status,events=execute(runner,plan)
    assert status=='waiting' and [command.operation for command in calls]==['navigate']
    wait=runner.approvals.repo.latest_wait('approval-run')
    assert wait.browser_intent_id and 'secret=must-not-trace' not in wait.prompt
    intent=service.approvals.intents.get(wait.browser_intent_id);assert intent.status=='pending'
    # Supplying the word in an engine state cannot change the durable human decision.
    assert not service.approvals.ready(intent.command_id,'click')
    from app.services.browser_session_service import BrowserRunScope
    original=BrowserRunScope.call
    def reordered(self,*args,**kwargs):
        if self.resuming and args[2]=='click':time.sleep(.1)
        return original(self,*args,**kwargs)
    monkeypatch.setattr(BrowserRunScope,'call',reordered)
    resumed=runner.plan_resume('owner','approval-run','approved',node=wait.node_id)
    assert service.approvals.intents.get(intent.command_id).status=='approved'
    status,events=execute(runner,resumed)
    assert status=='ok' and [command.operation for command in calls]==['navigate','click','snapshot'], [(event.get('type'),event.get('node'),event.get('agent')) for event in events]
    assert service.approvals.intents.get(intent.command_id).status=='confirmed'
    assert next(iter(workers.values())).closed
    final=next(event['state'] for event in events if event['type']=='run_finished')
    assert 'must-not-trace' not in json.dumps(final['steps']) and [step['tool'] for step in final['steps']]==['navigate','click','snapshot']


@pytest.mark.parametrize('decision,outcome',[('rejected','rejected'),('I changed my mind','rejected'),('approved','expired')])
def test_reject_or_expired_approval_does_not_click(tmp_path,monkeypatch,decision,outcome):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})]),('Not done',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['click']),'input':{'message':'fixture'}});plan.run_id='reject-run'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait('reject-run')
    if outcome=='expired':
        from app.models import BrowserIntent
        with service.repo.db.session() as s:s.get(BrowserIntent,wait.browser_intent_id).expires=time.time()-1;s.commit()
    resumed=runner.plan_resume('owner','reject-run',decision,node=wait.node_id)
    assert execute(runner,resumed)[0]=='ok' and calls==[]
    assert service.approvals.intents.get(wait.browser_intent_id).status==outcome


def test_changed_target_requires_new_observation_and_new_decision(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})]),('Target changed',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['click']),'input':{'message':'fixture'}});plan.run_id='changed-run'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait('changed-run')
    resumed=runner.plan_resume('owner','changed-run','approved',node=wait.node_id)
    next(iter(workers.values())).target_hash='b'*64
    assert execute(runner,resumed)[0]=='ok' and calls==[]
    assert service.approvals.intents.get(wait.browser_intent_id).status=='stale'


def test_real_waiting_resume_hands_off_fence_without_reopening_page(tmp_path,monkeypatch):
    from app.models import Run
    from app.engine.browser_worker import BrowserWorkerError
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('navigate',{'url':'https://example.test/form'},'a')]),
        ('',[call('click',{'observation_id':'o','element_id':'e'},'b')]),('Done',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['navigate','click']),'input':{'message':'fixture'}});plan.run_id='queued-approval'
    runner.runs.add(Run(id=plan.run_id,owner='owner',status='queued',source='api',workflow_id='adhoc',started=time.time()))
    plan.fence=runner.runs.claim(plan.run_id,('queued',));plan.checkpointing=True
    assert execute(runner,plan)[0]=='waiting'
    root=next(iter(workers.values()));old_context=root.context
    wait=runner.approvals.repo.latest_wait(plan.run_id)
    resumed=runner.plan_resume('owner',plan.run_id,'approved',node=wait.node_id)
    resumed.fence=runner.runs.claim(plan.run_id,('waiting',));resumed.checkpointing=True
    service.sweep()  # maintenance can run between the queue claim and page handoff
    assert not root.closed
    assert resumed.fence==2 and execute(runner,resumed)[0]=='ok'
    assert len(workers)==1 and [command.operation for command in calls]==['navigate','click']
    assert calls[-1].context.lease_generation==3 and calls[-1].generation==2
    assert old_context!=calls[-1].context


def test_unknown_ack_is_not_retried_on_resume_or_fork(tmp_path,monkeypatch):
    from app.engine.browser_worker import BrowserWorkerError
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service)
    scope=service.bind('owner','user:owner','run-one',1)
    args={'observation_id':'o','element_id':'e'}
    cid=scope.prepare('agent','one',[{'index':0,'server_id':'browser','tool':'click','arguments':args}])[0]
    assert scope.action('slot','agent',cid,'click',args)['state']=='waiting'
    wait=service.approvals.waits.add_wait(ApprovalWait(id=uuid.uuid4().hex,run_id='run-one',node_id='slot',owner='owner',status='closed',outcome='answered',created=time.time(),browser_intent_id=cid),[])
    assert service.approvals.record(wait,'owner','approved','studio')
    root=next(iter(workers.values()))
    def lost_ack(command):calls.append(command);raise BrowserWorkerError()
    monkeypatch.setattr(root,'call',lost_ack)
    assert scope.call('agent',cid,'click',args)['status']=='unknown' and len(calls)==1
    assert service.approvals.intents.get(cid).status=='unknown'
    for candidate in [service.bind('owner','user:owner','run-one',2),service.bind('owner','user:owner','forked',1,forked_from='run-one')]:
        with pytest.raises(BrowserWorkerError):candidate.prepare('agent','again',[{'index':0,'server_id':'browser','tool':'click','arguments':args}])
    assert len(workers)==1 and len(calls)==1


def test_ai_review_and_unverified_chat_cannot_grant_a_browser_intent(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    runner.approvals._policy=lambda *args:(_ for _ in ()).throw(AssertionError('AI policy must not classify browser actions'))
    responses(monkeypatch,[('',[call('fill',{'observation_id':'o','element_id':'e','value':'synthetic-secret-value'})])])
    plan=runner.plan('owner',{'workflow':flow_for(['fill']),'input':{'message':'fixture'}});plan.run_id='human-only'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait(plan.run_id)
    assert wait.browser_intent_id and not runner.approvals.answers_itself(None,plan.workflow,{'node':wait.node_id,'browser_intent':wait.browser_intent_id})
    assert 'synthetic-secret-value' not in wait.prompt
    assert not service.approvals.record(wait,'owner','approved','chat')
    assert calls==[] and service.approvals.intents.get(wait.browser_intent_id).status=='pending'


from tests.test_browser_connections import c,api,user,H
from tests.test_approval_channels import until


def test_authenticated_inbox_reviewer_grants_but_stranger_does_not(c,tmp_path,monkeypatch):
    from app.api.deps import browser_session_service,run_service
    service,calls,workers=scoped_service(tmp_path,monkeypatch)  # installs a synthetic worker, never Docker/network
    owner,reviewer,stranger=user(c),user(c),user(c)
    connection=c.post('/api/mcp/servers',headers=H(owner['token']),json={'name':'Browser approval fixture '+uuid.uuid4().hex[:6],
        'transport':'managed','adapter':'browser','settings':{'allowed_origins':['https://example.com'],'require_mutating_approval':True}}).json()['data']
    flow=flow_for(['click'])
    agent=next(node for node in flow['nodes'] if node['type']=='agent')
    agent['data']['tools'][0]['server_id']=connection['id']
    agent['data']['approval']={'approvers':[reviewer['email']]}
    flow['name']='Browser approval '+uuid.uuid4().hex[:6]
    for node in flow['nodes']:node['position']={'x':0,'y':0}
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})]),('Done',[])])
    created=c.post('/api/workflows',headers=H(owner['token']),json=flow)
    assert created.status_code==200,created.text
    wid=created.json()['data']['id']
    with c.websocket_connect('/ws/run?token='+owner['token']) as socket:
        socket.send_json({'workflow_id':wid,'input':{'message':'fixture'}})
        events=[]
        while not events or events[-1]['type']!='run_summary':events.append(socket.receive_json())
    rid=events[0]['run_id'];assert events[-1]['status']=='waiting' and calls==[]
    denied=c.post('/api/approvals/inbox/'+rid,headers=H(stranger['token']),json={'response':'approved'})
    assert denied.status_code==404 and calls==[]
    request=next(item for item in c.get('/api/approvals/inbox',headers=H(reviewer['token'])).json()['data'] if item['run_id']==rid)
    accepted=c.post('/api/approvals/inbox/'+rid,headers=H(reviewer['token']),json={'response':'approved','node':request['node']})
    assert accepted.status_code==200,accepted.text
    done=until(lambda:(row:=run_service().runs.get(rid)) is not None and row.status=='ok' and row)
    assert len(calls)==1 and calls[0].operation=='click'
    assert calls[0].context.lease_generation==2 and calls[0].generation==2  # UI generation 0 -> first queued claim 1
    receipt=browser_session_service().approvals.intents.get(calls[0].command_id)
    assert receipt.status=='confirmed' and receipt.decided_by==reviewer['id']
    assert c.post('/api/approvals/inbox/'+rid,headers=H(reviewer['token']),json={'response':'approved','node':request['node']}).status_code==404
    assert len(calls)==1


@pytest.mark.parametrize('receipt,wave',[('approved',False),('approved',True),('missing',False),('unknown',False),('expired',False)])
def test_durable_decision_repairs_lost_enqueue_without_repeating_uncertain_effects(tmp_path,monkeypatch,receipt,wave):
    from app.models import BrowserIntent,Run
    from app.services.run_worker import RunWorker
    from app.services.job_queue import InMemoryJobQueue
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})]),('Done',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['click']),'input':{'message':'fixture'}});plan.run_id='lost-enqueue'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait(plan.run_id)
    assert runner.approvals.repo.close_wait(plan.run_id,'answered',wait.id)
    if receipt!='missing':assert service.approvals.record(wait,'owner','approved','studio')
    with service.repo.db.session() as s:
        intent=s.get(BrowserIntent,wait.browser_intent_id)
        if receipt=='unknown':intent.status='unknown';intent.consumed_at=time.time()
        if receipt=='expired':intent.expires=time.time()-1
        if wave:
            row=s.get(Run,plan.run_id);cp=json.loads(row.checkpoint)
            cp.pop('browser_intent',None);cp['waits']=[{'browser_intent':intent.command_id,'node':wait.node_id}]
            row.checkpoint=json.dumps(cp)
        s.commit()
    jobs=[];service.approvals.enqueue=jobs.append
    due=time.time()+6
    runner.bus.start(plan.run_id,'owner')
    assert service.approvals.recover_decisions(due)==0
    runner.bus.finish(plan.run_id)
    assert service.approvals.recover_decisions(due)==1
    assert service.approvals.recover_decisions(due)==0 and len(jobs)==1
    assert json.loads(runner.runs.get(plan.run_id).resume_job)==jobs[0]
    assert jobs[0]['response']==('approved' if receipt=='approved' else 'rejected')
    if not wave:
        assert asyncio.run(RunWorker(InMemoryJobQueue(),lambda:runner).resume_job(runner,jobs[0]))=='ok'
        assert len(calls)==(1 if receipt=='approved' else 0)
        assert asyncio.run(RunWorker(InMemoryJobQueue(),lambda:runner).resume_job(runner,jobs[0])) is None
        assert len(calls)==(1 if receipt=='approved' else 0)


def test_browser_deadline_is_bounded_and_can_only_reject(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})])])
    flow=flow_for(['click'])
    agent=next(node for node in flow['nodes'] if node['type']=='agent')
    agent['data']['deadline']={'after':'1h','on_timeout':'approve'}
    plan=runner.plan('owner',{'workflow':flow,'input':{'message':'fixture'}});plan.run_id='browser-deadline'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait(plan.run_id);intent=service.approvals.intents.get(wait.browser_intent_id)
    assert wait.due_at<=intent.expires+.02 and json.loads(wait.deadline)['on_timeout']=='reject'
    assert runner.approvals._timeout(wait,wait.due_at+1)==1
    assert service.approvals.intents.get(intent.command_id).status=='expired'
    assert calls==[] and not service.approvals.ready(intent.command_id,'click')


def test_two_resuming_binders_share_one_fence_handoff(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service)
    scope=service.bind('owner','user:owner','run-one',1)
    cid=scope.prepare('agent','read',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
    assert scope.call('agent',cid,'snapshot',{})['status']=='confirmed'
    root=next(iter(workers.values()));renew=root.renew
    def slow_renew(context):time.sleep(.1);return renew(context)
    monkeypatch.setattr(root,'renew',slow_renew)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resumed=list(pool.map(lambda _:service.bind('owner','user:owner','run-one',2,allow_resume=True),range(2)))
    assert all(not candidate.lost for candidate in resumed)
    assert len(workers)==1 and root.generation==2 and not root.closed


def test_invalid_browser_fill_keeps_secrets_out_of_trace(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('fill',{'observation_id':'o','element_id':'e','value':'synthetic-private-value','unexpected':'synthetic-private-value'})]),('Refused',[])])
    plan=runner.plan('owner',{'workflow':flow_for(['fill']),'input':{'message':'fixture'}})
    status,events=execute(runner,plan)
    assert status=='ok' and calls==[]
    final=next(event['state'] for event in events if event['type']=='run_finished')
    assert 'synthetic-private-value' not in json.dumps(final['steps'])


@pytest.mark.parametrize('missing_receipt',[False,True])
def test_final_wave_answer_survives_crash_before_queue_claim(tmp_path,monkeypatch,missing_receipt):
    from copy import deepcopy
    from app.models import McpServer
    from app.services.run_worker import RunWorker
    from app.services.job_queue import InMemoryJobQueue
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    monkeypatch.setenv('STUDIO_AGENT_PARALLEL_TOOLS','4')
    service.mcp.repo.save(McpServer(id='browser-two',owner='owner',scope='user',transport='managed',adapter='browser',name='Second browser',settings='{"allowed_origins":["https://example.com"],"require_mutating_approval":true}',created=time.time()))
    flow=flow_for(['click']);agent=next(node for node in flow['nodes'] if node['type']=='agent')
    one=agent['data']['tools'][0];one['name']='click_one'
    two=deepcopy(one);two.update(name='click_two',server_id='browser-two');agent['data']['tools'].append(two)
    args={'observation_id':'o','element_id':'e'}
    responses(monkeypatch,[('',[call('click_one',args,'one'),call('click_two',args,'two')]),('Done',[])])
    plan=runner.plan('owner',{'workflow':flow,'input':{'message':'fixture'}});plan.run_id='settled-wave'
    assert execute(runner,plan)[0]=='waiting'
    cp=json.loads(runner.runs.get(plan.run_id).checkpoint);assert len(cp['waits'])==2 and len(cp['browser_intents'])==2
    slots=[item['node'] for item in cp['waits']]
    assert runner.plan_resume('owner',plan.run_id,'approved',node=slots[0]).pending_wave
    if missing_receipt:
        # Crash after the final wave answer/closed inbox, before its browser receipt.
        assert runner.absorb_wave(plan.run_id,node=slots[1],value='approved')[0]=='go'
        runner.approvals.answered_slot(plan.run_id,slots[1])
    else:assert runner.plan_resume('owner',plan.run_id,'approved',node=slots[1]).previous is not None
    cp=json.loads(runner.runs.get(plan.run_id).checkpoint);assert cp['wave_ready'] and cp['waits']==[]
    jobs=[];service.approvals.enqueue=jobs.append
    assert service.approvals.recover_decisions(time.time()+6)>0
    assert all(job.get('wave') for job in jobs)
    worker=RunWorker(InMemoryJobQueue(),lambda:runner)
    assert asyncio.run(worker.resume_job(runner,jobs[0]))=='ok'
    assert len(calls)==(1 if missing_receipt else 2)
    for job in jobs:assert asyncio.run(worker.resume_job(runner,job)) is None
    assert len(calls)==(1 if missing_receipt else 2)


def test_account_purge_removes_target_text_even_when_cleanup_is_pending(tmp_path,monkeypatch):
    from app.repositories.user_data import UserDataRepository
    service,calls,workers=scoped_service(tmp_path,monkeypatch);enable_mutating_approval(service);runner=runner_for(service)
    responses(monkeypatch,[('',[call('click',{'observation_id':'o','element_id':'e'})])])
    plan=runner.plan('owner',{'workflow':flow_for(['click']),'input':{'message':'fixture'}});plan.run_id='purge-browser-intent'
    assert execute(runner,plan)[0]=='waiting'
    wait=runner.approvals.repo.latest_wait(plan.run_id);cid=wait.browser_intent_id
    row=service.repo.get(service.repo.command(cid).session_id)
    monkeypatch.setattr(type(next(iter(workers.values()))),'close',lambda self:False)
    service.close_run(plan.run_id)
    assert service.repo.get(row.id).cleanup_pending
    UserDataRepository(service.repo.db).purge('owner',runs=True)
    assert service.approvals.intents.get(cid) is None
    assert service.repo.get(row.id).cleanup_pending
