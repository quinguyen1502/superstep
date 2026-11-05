"""Recipes reuse workflow/MCP/child-run seams and the same live-browser approval boundary."""
import asyncio,json,time,uuid
from copy import deepcopy
from pathlib import Path
import pytest
from app.core.errors import AppError
from app.engine import agents,browser_recipes
from app.engine.browser_contract import Observation,ObservedElement
from app.engine.browser_worker import BrowserWorkerError
from app.engine.validator import validate
from app.models import Run,Workflow
from app.repositories import WorkflowTokenRepository
from app.services.job_queue import InMemoryJobQueue
from app.services.run_worker import RunWorker
from app.services.trigger_service import TriggerService
from app.services.workflow_mcp_service import WorkflowMcpService
from tests.test_browser_run_sessions import scoped_service
from tests.test_browser_approval_recovery import runner_for,execute

ROOT=Path(__file__).resolve().parents[2]


def recipe():return json.loads((ROOT/'examples/browser/lookup_shipment.json').read_text())


def fixture(tmp_path,monkeypatch):
    import app.services.browser_session_service as module
    service,calls,workers=scoped_service(tmp_path,monkeypatch);original=module.LocalBrowserWorker.call
    def call(self,command):
        result=original(self,command).model_copy(update={'generation':self.generation})
        if command.operation in {'navigate','snapshot'}:
            observation=Observation(observation_id='observation-'+str(command.sequence),page_generation=command.sequence+1,origin='https://example.test',text='Fixture',
                elements=[ObservedElement(element_id='order-'+str(command.sequence),role='textbox',text='Order ID'),
                    ObservedElement(element_id='submit-'+str(command.sequence),role='button',text='Track shipment'),
                    ObservedElement(element_id='status-'+str(command.sequence),role='status',text='In transit')])
            result=result.model_copy(update={'observation':observation})
        if command.operation=='extract':result=result.model_copy(update={'extracted':{'status':'In transit'}})
        return result
    monkeypatch.setattr(module.LocalBrowserWorker,'call',call)
    return service,calls,workers,runner_for(service)


def finish(runner,plan):
    status,events=execute(runner,plan);reviews=[]
    while status=='waiting':
        wait=runner.approvals.repo.latest_wait(plan.run_id)
        reviews.append(wait.node_id)
        plan=runner.plan_resume('owner',plan.run_id,'approved',node=wait.node_id)
        status,events=execute(runner,plan)
    return status,events,reviews


def test_recipe_reuses_one_page_and_two_human_approvals_with_only_declared_output(tmp_path,monkeypatch):
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    flow=recipe();assert validate(flow)==[]
    for i,url in enumerate(['https://example.test/first','https://example.test/second']):
        plan=runner.plan('owner',{'workflow':flow,'input':{'url':url,'order_id':'ORDER-'+str(i)}});plan.run_id='recipe-'+str(i)
        status,events,reviews=finish(runner,plan)
        assert status=='ok' and reviews==['fill','submit']
        final=next(event['state'] for event in events if event['type']=='run_finished')
        assert list(final)==['shipment'] and final['shipment']['extracted']=={'status':'In transit'}
    assert len(workers)==2 and all(worker.closed for worker in workers.values())
    assert [command.operation for command in calls]==['navigate','fill','snapshot','click','snapshot','extract']*2
    assert [command.arguments['url'] for command in calls if command.operation=='navigate']==['https://example.test/first','https://example.test/second']
    assert [command.arguments['value'] for command in calls if command.operation=='fill']==['ORDER-0','ORDER-1']


@pytest.mark.parametrize('change',['version','unknown_input','sequence','agent','target','connection','retry'])
def test_recipe_rejects_invalid_versions_inputs_sequences_and_authority(tmp_path,monkeypatch,change):
    flow=recipe();inp={'url':'https://example.test/','order_id':'ORDER'}
    if change=='version':flow['browser_recipe']['version']=True
    if change=='unknown_input':inp['proxy']='http://attacker.test'
    if change=='sequence':flow['nodes']*=3
    if change=='agent':flow['nodes'][1]['type']='agent'
    if change=='target':flow['nodes'][2]['data']['target']['observation_field']='fill_result'
    if change=='connection':flow['nodes'][1]['data']['server_id']='forged'
    if change=='retry':flow['nodes'][2]['data']['retry']={'max_attempts':2}
    with pytest.raises(AppError) as caught:browser_recipes.validate_input(flow,inp)
    assert caught.value.code==('MCP_ARGUMENT_INVALID' if change=='unknown_input' else 'BROWSER_RECIPE_INVALID')


@pytest.mark.parametrize('layout',['missing','ambiguous'])
def test_changed_layout_stops_without_starting_an_agent_or_effect(tmp_path,monkeypatch,layout):
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    import app.services.browser_session_service as module
    original=module.LocalBrowserWorker.call
    def changed(self,command):
        result=original(self,command)
        if result.observation:
            elements=[element for element in result.observation.elements if element.role!='textbox']
            if layout=='ambiguous':elements+= [ObservedElement(element_id='one',role='textbox',text='Order ID'),ObservedElement(element_id='two',role='textbox',text='Order ID')]
            result=result.model_copy(update={'observation':result.observation.model_copy(update={'elements':elements})})
        return result
    monkeypatch.setattr(module.LocalBrowserWorker,'call',changed)
    monkeypatch.setattr(agents,'call_agent',lambda *a,**kw:pytest.fail('A recipe cannot turn into an Agent'))
    status,events=execute(runner,runner.plan('owner',{'workflow':recipe(),'input':{'url':'https://example.test/','order_id':'ORDER'}}))
    assert status=='error' and [command.operation for command in calls]==['navigate']
    assert any('missing or ambiguous' in str(event) for event in events if event['type']=='error')


def test_recipe_mock_is_offline_and_forged_execution_marker_cannot_share_a_page(tmp_path,monkeypatch):
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    plan=runner.plan('owner',{'workflow':recipe(),'input':{'url':'https://example.test/','order_id':'ORDER'}})
    plan.ports.test=True
    status,events=execute(runner,plan)
    assert status=='ok' and calls==[] and workers=={}
    assert next(event['state'] for event in events if event['type']=='run_finished')['shipment']=={'status':'dry_run','operation':'extract'}
    normal=recipe();normal.pop('browser_recipe')
    for node in normal['nodes']:node['data']['_browser_recipe']=True
    assert all(not node['data'].get('_browser_recipe') for node in browser_recipes.prepare(normal)['nodes'])


def test_recipe_rejection_remains_visible_and_stops_before_fill(tmp_path,monkeypatch):
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    plan=runner.plan('owner',{'workflow':recipe(),'input':{'url':'https://example.test/','order_id':'ORDER'}});plan.run_id='rejected-recipe'
    assert execute(runner,plan)[0]=='waiting'
    status,events=execute(runner,runner.plan_resume('owner',plan.run_id,'rejected',node='fill'))
    assert status=='error' and [command.operation for command in calls]==['navigate']
    assert any('rejected' in str(event) for event in events if event['type']=='error')


def test_queued_recipe_keeps_accepted_snapshot_when_saved_workflow_changes(tmp_path,monkeypatch):
    service,calls,workers,runner=fixture(tmp_path,monkeypatch);flow=recipe()
    runner.workflows.save('recipe','lookup_shipment',json.dumps(flow),time.time(),'owner')
    jobs=InMemoryJobQueue();triggers=TriggerService(runner.workflows,runner.runs,WorkflowTokenRepository(service.repo.db),jobs)
    rid=triggers.queue('recipe','owner',{'url':'https://example.test/','order_id':'ORDER'})
    stored=json.loads(runner.runs.get(rid).checkpoint)
    assert stored['kind']=='browser_recipe' and stored['workflow']==flow
    modified=deepcopy(flow);modified['nodes'][2]['data']['target']['text']='Changed selector'
    runner.workflows.update_name('recipe','Changed',json.dumps(modified),time.time())
    assert runner.plan_recipe(runner.runs.get(rid)).workflow==flow
    assert runner.plan_recover(runner.runs.get(rid),fence=2).workflow==flow
    service.mcp.repo.delete('browser')
    assert asyncio.run(RunWorker(jobs,lambda:runner).run_job(jobs.dequeue(.1)))=='error'
    assert calls==[] and workers=={}


def test_unknown_child_outcome_blocks_new_recipe_child_and_parent_fork(tmp_path,monkeypatch):
    from app.models import BrowserIntent,BrowserCommand,BrowserSession
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    flow=recipe();runner.workflows.save('recipe','lookup_shipment',json.dumps(flow),time.time(),'owner')
    runner.runs.add(Run(id='parent',workflow_id='adhoc',owner='owner',status='waiting',started=time.time()))
    runner.runs.add(Run(id='child',parent_run_id='parent',workflow_id='recipe',owner='owner',status='error',started=time.time()))
    now=time.time()
    with service.repo.db.session() as s:
        s.add(BrowserSession(id='unknown-child-session',owner='owner',principal_id='user:owner',run_id='child',group_id='recipe',connection_id='browser',configuration='a'*64,
            lease_generation=1,provider='local',status='unknown',created=now,touched=now,expires=now+60));s.commit()
        s.add(BrowserCommand(id='unknown-command',session_id='unknown-child-session',position=0,body_hash='b'*64,status='unknown'));s.commit()
    assert service.repo.has_history('parent') and service.repo.has_history('parent',uncertain=True)
    scope=service.bind('owner','user:owner','forked',1,forked_from='parent');assert scope.lost
    with pytest.raises(BrowserWorkerError):scope.prepare('recipe','new',[{'index':0,'server_id':'browser','tool':'navigate','arguments':{'url':'https://example.test/'}}])
    runner.jobs=lambda:InMemoryJobQueue()
    plan=runner.plan('owner',{'workflow':flow,'input':{'url':'https://example.test/','order_id':'ORDER'}})
    with pytest.raises(AppError) as caught:runner._child_starter('parent',plan,'owner')('new-call',flow,None,{'url':'https://example.test/','order_id':'ORDER'},{'workflow_id':'recipe'})
    assert caught.value.code=='BROWSER_RUNTIME_UNAVAILABLE' and calls==[] and workers=={}


def test_existing_agent_workflow_slot_runs_snapshotted_recipe_child(tmp_path,monkeypatch):
    from tests.test_agent_workflow_tools import supervisor,tool
    from tests.test_agent_node import call
    from tests.test_browser_approval_recovery import responses
    service,calls,workers,runner=fixture(tmp_path,monkeypatch);flow=recipe()
    runner.workflows.save('recipe','lookup_shipment',json.dumps(flow),time.time(),'owner')
    jobs=InMemoryJobQueue();runner.jobs=lambda:jobs;worker=RunWorker(jobs,lambda:runner)
    parent=supervisor(tool('recipe',name='lookup_shipment',inputs=['url','order_id'],outputs=['shipment']))
    responses(monkeypatch,[('',[call('lookup_shipment',{'url':'https://example.test/','order_id':'ORDER'})]),('Done',[])])
    plan=runner.plan('owner',{'workflow':parent,'input':{'message':'Track order'}});plan.run_id='recipe-parent'
    changed=deepcopy(flow);changed['nodes'][2]['data']['target']['text']='Changed after planning'
    runner.workflows.update_name('recipe','Changed',json.dumps(changed),time.time())
    assert execute(runner,plan)[0]=='waiting'
    child=runner.runs.children(plan.run_id)[0]
    assert json.loads(child.checkpoint)['workflow']['nodes'][2]['data']['target']['text']=='Order ID'
    assert asyncio.run(worker.run_job(jobs.dequeue(.1)))=='waiting'
    for node in ['fill','submit']:
        wait=runner.approvals.repo.latest_wait(child.id);assert wait.node_id==node
        status,_=execute(runner,runner.plan_resume('owner',child.id,'approved',node=node))
    assert status=='ok'
    assert asyncio.run(worker.run_job(jobs.dequeue(.1)))=='ok'
    assert runner.runs.get(plan.run_id).status=='ok' and len(runner.runs.children(plan.run_id))==1
    assert len(calls)==6 and len(workers)==1 and json.loads(runner.runs.get(child.id).final_state)['shipment']['extracted']['status']=='In transit'


def test_recipe_agent_slot_rejects_extra_arguments_before_child_creation(tmp_path,monkeypatch):
    from tests.test_agent_workflow_tools import supervisor,tool
    from tests.test_agent_node import call
    from tests.test_browser_approval_recovery import responses
    service,calls,workers,runner=fixture(tmp_path,monkeypatch);flow=recipe()
    runner.workflows.save('recipe','lookup_shipment',json.dumps(flow),time.time(),'owner');runner.jobs=lambda:InMemoryJobQueue()
    parent=supervisor(tool('recipe',name='lookup_shipment',inputs=['url','order_id'],outputs=['shipment']))
    responses(monkeypatch,[('',[call('lookup_shipment',{'url':'https://example.test/','order_id':'ORDER','proxy':'forged'})]),('Refused',[])])
    plan=runner.plan('owner',{'workflow':parent,'input':{'message':'Track order'}});plan.run_id='forged-recipe'
    assert execute(runner,plan)[0]=='ok' and runner.runs.children(plan.run_id)==[] and workers=={} and calls==[]


@pytest.mark.parametrize('value',[{'url':'https://example.test/'}, {'url':'https://example.test/','order_id':''},
    {'url':'https://example.test/','order_id':'x'*3000}, {'url':'https://example.test/','order_id':{'profile':'forged'}}])
def test_recipe_input_bounds_and_required_types_fail_before_queue(value):
    with pytest.raises(AppError) as caught:browser_recipes.validate_input(recipe(),value)
    assert caught.value.code=='MCP_ARGUMENT_INVALID'


def test_recipe_visibility_is_existing_workflow_tool_authorization(tmp_path,monkeypatch):
    from tests.test_agent_workflow_tools import supervisor,tool
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    runner.workflows.save('foreign-recipe','lookup_shipment',json.dumps(recipe()),time.time(),'other-owner')
    parent=supervisor(tool('foreign-recipe',name='lookup_shipment',inputs=['url','order_id'],outputs=['shipment']))
    plan=runner.plan('owner',{'workflow':parent,'input':{'message':'Track order'}})
    assert plan.invalid and execute(runner,plan)[0]=='error' and calls==[] and workers=={}


from tests.test_db_postgres import fresh_pg,URL


@pytest.mark.skipif(not URL.startswith('postgresql'),reason='requires disposable TEST_DATABASE_URL')
def test_postgres_recursive_browser_history_includes_uncertain_child(fresh_pg):
    from app.models import BrowserSession,BrowserCommand
    from app.repositories.browser_sessions import BrowserSessionRepository
    db=fresh_pg;db.migrate();now=time.time()
    with db.session() as s:
        s.add(Run(id='pg-recipe-child',parent_run_id='pg-recipe-parent',owner='owner',workflow_id='recipe',status='error',started=now))
        s.add(BrowserSession(id='pg-recipe-session',owner='owner',principal_id='user:owner',run_id='pg-recipe-child',group_id='recipe',connection_id='browser',configuration='a'*64,
            lease_generation=1,provider='local',status='unknown',created=now,touched=now,expires=now+60));s.commit()
        s.add(BrowserCommand(id='pg-recipe-command',session_id='pg-recipe-session',position=0,body_hash='b'*64,status='unknown'));s.commit()
    repo=BrowserSessionRepository(db)
    assert repo.has_history('pg-recipe-parent') and repo.has_history('pg-recipe-parent',uncertain=True)
    assert not repo.has_history('unrelated',uncertain=True)


from tests.test_mcp_server import base,session,body,H
from tests.test_approval_channels import until


def test_generic_mcp_recipe_schema_human_receipts_and_completed_result_no_replay(base,tmp_path,monkeypatch):
    import httpx
    from app.api.deps import run_service
    service,calls,workers,runner=fixture(tmp_path,monkeypatch)
    flow=recipe()
    with httpx.Client(base_url=base) as client:
        auth=client.post('/api/auth/register',json={'email':uuid.uuid4().hex+'@example.test','password':'secret12'}).json()['data'];jwt=auth['token']
        conn=client.post('/api/mcp/servers',headers=H(jwt),json={'name':'Recipe browser','transport':'managed','adapter':'browser','settings':{}}).json()['data']
        flow['browser_recipe']['connection_id']=conn['id']
        for node in flow['nodes']:
            if node['type']=='mcp':node['data']['server_id']=conn['id']
        wid=client.post('/api/workflows',headers=H(jwt),json=flow).json()['data']['id']
        token=client.post('/api/workflows/'+wid+'/tokens',headers=H(jwt),json={'name':'Recipe fixture'}).json()['data']['token']
        assert client.put('/api/workflows/'+wid+'/mcp',headers=H(jwt),json={'enabled':True}).status_code==200
        async def run(mcp):
            definitions=(await mcp.list_tools()).tools;schema=definitions[0].inputSchema
            assert schema['additionalProperties'] is False and schema['required']==['url','order_id']
            invalid=await mcp.call_tool(definitions[0].name,{'url':'https://example.test/','order_id':'ORDER','profile':'forged'})
            assert invalid.isError and calls==[]
            waiting=body(await mcp.call_tool(definitions[0].name,{'url':'https://example.test/','order_id':'ORDER'}))
            assert waiting['status']=='waiting' and [command.operation for command in calls]==['navigate']
            rid=waiting['run_id']
            # A workflow token/model can provide the word, but has no human receipt.
            unverified=body(await mcp.call_tool('resume_run',{'run_id':rid,'response':'approved'}))
            assert unverified['status']=='waiting' and [command.operation for command in calls]==['navigate']
            for node in ['fill','submit']:
                response=client.post('/api/approvals/inbox/'+rid,headers=H(jwt),json={'node':node,'response':'approved'})
                assert response.status_code==200,response.text
                until(lambda:(row:=run_service().runs.get(rid)) is not None and (row.status=='ok' if node=='submit' else row.status=='waiting' and run_service().approvals.repo.latest_wait(rid).node_id=='submit'))
            final=body(await mcp.call_tool('get_run',{'run_id':rid}))
            assert final['status']=='ok' and list(final['final_state'])==['shipment'] and len(calls)==6
            assert body(await mcp.call_tool('get_run',{'run_id':rid}))['final_state']==final['final_state'] and len(calls)==6
        session(base,token,run)
