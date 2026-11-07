#!/usr/bin/env python3
"""Real Chromium typed workflow recipe, approved effects and lost-ack refusal; disposable fixtures only."""
import argparse,asyncio,importlib.util,json,os,subprocess,sys,tempfile,time,uuid
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.engine.browser_contract import BrowserSettings
from app.engine.browser_worker import LocalBrowserWorker,BrowserWorkerError
from app.models import User,McpServer
from app.models.database import Database
from app.repositories import ApprovalRepository,UserRepository,WorkflowRepository,RunRepository,NodeResultRepository
from app.services.approval_service import ApprovalService
from app.services.channel_service import ChannelService
from app.services.run_service import RunService
import app.services.browser_session_service as session_module
spec=importlib.util.spec_from_file_location('session_fixture',ROOT/'scripts/test-browser-sessions.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)


class DropAckWorker(LocalBrowserWorker):
    def _rpc(self,method,value,timeout=65):
        result=super()._rpc(method,value,timeout)
        if method=='command' and value.operation=='click' and result.get('status')=='confirmed':raise BrowserWorkerError()
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--docker',default='/Applications/Docker.app/Contents/Resources/bin/docker')
    parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    def docker(*argv,timeout=120):
        result=subprocess.run([args.docker,*argv],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise RuntimeError('Recipe fixture Docker '+argv[0]+' failed: '+result.stderr[-1500:])
        return result.stdout.strip()
    os.environ['STUDIO_ENABLE_BROWSER']='1';os.environ['STUDIO_ENABLE_BROWSER_RUNTIME']='1'
    if not args.skip_build:
        docker('build','-t','superstep-browser-worker:1','docker/browser-worker',timeout=600)
        docker('build','-f','backend/tests/fixtures/browser_egress/Gateway.Dockerfile','-t','superstep-browser-egress-gateway:task-0242','.',timeout=180)
    suffix=uuid.uuid4().hex[:10];network='ss-browser-recipe-net-'+suffix;site='ss-browser-recipe-fixture-'+suffix
    service=None;db=None;temporary=tempfile.TemporaryDirectory(prefix='ss-browser-recipe-db-')
    try:
        docker('network','create','--internal',network)
        docker('run','-d','--name',site,'--network',network,'--network-alias','fixture','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
            '--pids-limit=64','--memory=128m','--tmpfs=/tmp:rw,nosuid,size=16m','superstep-browser-egress-gateway:task-0242','python','fixture_server.py')
        url='sqlite:///'+str(Path(temporary.name)/'fixture.db');db=Database(url);db.migrate()
        settings=BrowserSettings(allowed_origins=['http://allowed.test:8080'],max_actions=20)
        with db.session() as s:
            s.add(User(id='fixture-owner',email='fixture-owner@example.test',active=True,created=time.time()))
            s.add(McpServer(id='browser',owner='fixture-owner',scope='user',transport='managed',adapter='browser',name='Recipe fixture',settings=settings.model_dump_json(),created=time.time()));s.commit()
        service=fixture_module.service_for(url,args.docker,network)
        waits,users,runs,workflows=ApprovalRepository(db),UserRepository(db),RunRepository(db),WorkflowRepository(db)
        approvals=ApprovalService(waits,users,workflows,runs,ChannelService(waits,users,{}),background=False,browser=lambda:service.approvals)
        runner=RunService(workflows,runs,mcp=service.mcp,browser=service,approvals=approvals,ledger=NodeResultRepository(db));service.runs=runs
        flow=json.loads((ROOT/'examples/browser/lookup_shipment.json').read_text())
        def execute(plan):
            events=[]
            async def send(event):events.append(event);return True
            async def listen():await asyncio.Event().wait()
            return asyncio.run(runner.execute(plan,send,listen,'fixture-owner')),events
        def invoke(name,definition=flow):
            plan=runner.plan('fixture-owner',{'workflow':definition,'input':{'url':'http://allowed.test:8080/shipment?portal='+name,'order_id':'SYNTHETIC-'+name}})
            plan.run_id='recipe-'+name;status,events=execute(plan);reviewed=[]
            while status=='waiting':
                wait=waits.latest_wait(plan.run_id);reviewed.append(wait.node_id)
                plan=runner.plan_resume('fixture-owner',plan.run_id,'approved',node=wait.node_id);status,events=execute(plan)
            return status,events,reviewed,plan.run_id
        for name in ['one','two']:
            status,events,reviewed,rid=invoke(name)
            assert status=='ok' and reviewed==['fill','submit'],(status,reviewed)
            output=next(event['state'] for event in events if event['type']=='run_finished')
            assert list(output)==['shipment'] and output['shipment']['extracted']=={'status':'Submitted SYNTHETIC-'+name}
            assert not service.repo.list_active(run_id=rid)
        original=session_module.LocalBrowserWorker;session_module.LocalBrowserWorker=DropAckWorker
        try:status,events,reviewed,rid=invoke('lost-ack')
        finally:session_module.LocalBrowserWorker=original
        assert status=='error' and reviewed==['fill','submit']
        assert service.repo.has_history(rid,uncertain=True)
        blocked=service.bind('fixture-owner','user:fixture-owner',rid,2)
        try:blocked.prepare('recipe','retry',[{'index':0,'server_id':'browser','tool':'navigate','arguments':{'url':'http://allowed.test:8080/shipment'}}])
        except BrowserWorkerError:pass
        else:raise AssertionError('A recipe rebuilt its page after an unknown effect')
        changed=deepcopy(flow);changed['nodes'][2]['data']['target']['text']='Unexpected layout'
        assert invoke('changed',changed)[0]=='error'
        effects=json.loads(docker('exec',site,'cat','/tmp/fixture-stats.json'))['effects']
        assert len(effects)==3,effects
        print(json.dumps({'outcome':'passed','invocations':2,'urls':'per_call','human_approvals_per_call':2,'shared_page_actions':6,
            'output':'declared_only','layout_change':'stopped','ack_lost_after_effect':'unknown','effects_total':3,'repeated_effects':0,'screenshots_written_to_git':0}))
    finally:
        if service:
            for row in service.repo.list_active():service.close(row)
        subprocess.run([args.docker,'rm','-fv',site],capture_output=True)
        subprocess.run([args.docker,'network','rm',network],capture_output=True)
        if service:service.repo.db.engine.dispose()
        if db:db.engine.dispose()
        temporary.cleanup()


if __name__=='__main__':main()
