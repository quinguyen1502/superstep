#!/usr/bin/env python3
"""Real target-bound approval/handoff/expiry/lost-ack proof on a disposable website and database."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.models import User,McpServer,ApprovalWait
from app.models.database import Database
from app.engine.browser_contract import BrowserSettings
from app.engine.browser_worker import LocalBrowserWorker,BrowserWorkerError
import app.services.browser_session_service as session_module
spec=importlib.util.spec_from_file_location('session_fixture',ROOT/'scripts/test-browser-sessions.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)


class DropAckWorker(LocalBrowserWorker):
    def _rpc(self,method,value,timeout=65):
        result=super()._rpc(method,value,timeout)
        if method=='command' and value.operation=='click' and result.get('status')=='confirmed':raise BrowserWorkerError()
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='/Applications/Docker.app/Contents/Resources/bin/docker')
    parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    def docker(*argv,timeout=120):
        r=subprocess.run([args.docker,*argv],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        if r.returncode:raise RuntimeError('Fixture Docker '+argv[0]+' failed: '+r.stderr[-1500:])
        return r.stdout.strip()
    os.environ['STUDIO_ENABLE_BROWSER']='1';os.environ['STUDIO_ENABLE_BROWSER_RUNTIME']='1'
    if not args.skip_build:
        docker('build','-t','superstep-browser-worker:1','docker/browser-worker',timeout=600)
        docker('build','-f','backend/tests/fixtures/browser_egress/Gateway.Dockerfile','-t','superstep-browser-egress-gateway:task-0242','.',timeout=180)
    suffix=uuid.uuid4().hex[:10];network='ss-browser-approval-net-'+suffix;destination='ss-browser-approval-fixture-'+suffix
    services=[]
    with tempfile.TemporaryDirectory(prefix='ss-browser-approval-db-') as temp:
        try:
            docker('network','create','--internal',network)
            docker('run','-d','--name',destination,'--network',network,'--network-alias','fixture','--read-only','--cap-drop=ALL',
                '--security-opt=no-new-privileges','--pids-limit=64','--memory=128m','--tmpfs=/tmp:rw,nosuid,size=16m',
                'superstep-browser-egress-gateway:task-0242','python','fixture_server.py')
            def effects():
                value=docker('exec',destination,'cat','/tmp/fixture-stats.json')
                return len(json.loads(value)['effects'])
            def scenario(name):
                url='sqlite:///'+str(Path(temp)/(name+'.db'));db=Database(url);db.migrate()
                settings=BrowserSettings(allowed_origins=['http://allowed.test:8080'],idle_timeout_s=30,lifetime_s=120,max_actions=20)
                with db.session() as s:
                    s.add(User(id='fixture-owner',email='fixture-owner@example.test',active=True,created=time.time()))
                    s.add(McpServer(id='browser',owner='fixture-owner',scope='user',transport='managed',adapter='browser',name='Fixture browser',settings=settings.model_dump_json(),created=time.time()));s.commit()
                service=fixture_module.service_for(url,args.docker,network);services.append(service)
                return service,service.bind('fixture-owner','user:fixture-owner','fixture-run',1),settings
            def observe(scope,path):
                cid=scope.prepare('agent','navigate',[{'index':0,'server_id':'browser','tool':'navigate','arguments':{'url':'http://allowed.test:8080'+path}}])[0]
                result=scope.call('agent',cid,'navigate',{'url':'http://allowed.test:8080'+path});assert result['status']=='confirmed',result['status']
                observation=result['observation'];button=next(item['element_id'] for item in observation['elements'] if item['role']=='button')
                return {'observation_id':observation['observation_id'],'element_id':button}
            def intent(scope,arguments):
                cid=scope.prepare('agent','click',[{'index':0,'server_id':'browser','tool':'click','arguments':arguments}])[0]
                assert scope.action('fixture-slot','agent',cid,'click',arguments)['state']=='waiting'
                return cid
            def approve(service,cid):
                wait=service.approvals.waits.add_wait(ApprovalWait(id=uuid.uuid4().hex,run_id='fixture-run',node_id='fixture-slot',owner='fixture-owner',
                    status='closed',outcome='answered',created=time.time(),browser_intent_id=cid),[])
                return service.approvals.record(wait,'fixture-owner','approved','studio')
            service,scope,settings=scenario('handoff');arguments=observe(scope,'/effect-form');cid=intent(scope,arguments)
            row=service.repo.get(service.repo.command(cid).session_id);old_context=service.context(row)
            old_supervisor=LocalBrowserWorker.attach(old_context,settings,row.worker_id,docker=args.docker)
            probe=old_supervisor.command('click',arguments,row.wire_sequence,'expired-grant-probe')
            proof=old_supervisor.inspect(probe)
            assert old_supervisor.approve(probe,target=proof,expires_at_ms=int(time.time()*1000)+2000)['status']=='approved'
            time.sleep(2.2)
            assert old_supervisor.call(probe).status=='approval_required' and effects()==0
            assert approve(service,cid)
            renewed=service.bind('fixture-owner','user:fixture-owner','fixture-run',2,allow_resume=True)
            fresh=service.repo.get(row.id);assert fresh.worker_id==row.worker_id and fresh.generation==2
            old_supervisor._check_idle()  # an old process's cleanup watchdog must use the worker clock, not kill a new fence
            assert not old_supervisor.closed
            if old_supervisor._idle_timer:old_supervisor._idle_timer.cancel()
            try:old_supervisor.health()
            except BrowserWorkerError:pass
            else:raise AssertionError('Old context retained page authority after handoff')
            assert renewed.call('agent',cid,'click',arguments)['status']=='confirmed'
            deadline=time.monotonic()+5
            while effects()!=1 and time.monotonic()<deadline:time.sleep(.05)
            assert effects()==1;service.close_run('fixture-run')
            service,scope,settings=scenario('target-change');arguments=observe(scope,'/mutable-effect');cid=intent(scope,arguments)
            docker('exec',destination,'python','-c',"from pathlib import Path;Path('/tmp/browser-mutate').touch()")
            time.sleep(1.2);assert approve(service,cid)
            assert scope.call('agent',cid,'click',arguments)['status']=='stale_observation' and effects()==1
            assert service.approvals.intents.get(cid).status=='stale';service.close_run('fixture-run')
            session_module.LocalBrowserWorker=DropAckWorker
            service,scope,settings=scenario('lost-ack');arguments=observe(scope,'/effect-form');cid=intent(scope,arguments)
            assert approve(service,cid)
            assert scope.call('agent',cid,'click',arguments)['status']=='unknown'
            assert effects()==2 and service.approvals.intents.get(cid).status=='unknown'
            assert scope.call('agent',cid,'click',arguments)['status'] in {'unknown','session_lost'} and effects()==2
            for candidate in [service.bind('fixture-owner','user:fixture-owner','fixture-run',2),service.bind('fixture-owner','user:fixture-owner','fork',1,forked_from='fixture-run')]:
                try:candidate.prepare('agent','retry',[{'index':0,'server_id':'browser','tool':'click','arguments':arguments}])
                except BrowserWorkerError:pass
                else:raise AssertionError('Unknown effect was admitted to replay')
            service.close_run('fixture-run');session_module.LocalBrowserWorker=LocalBrowserWorker
            service,scope,settings=scenario('expired-session');arguments=observe(scope,'/effect-form');cid=intent(scope,arguments)
            time.sleep(31)
            assert not approve(service,cid)
            assert scope.action('fixture-slot','agent',cid,'click',arguments)['state']=='expired'
            service.close_run('fixture-run');assert effects()==2
            print(json.dumps({'outcome':'passed','worker_grant_expiry':'no_effect','handoff':'same_page_new_fence_old_context_denied',
                'old_supervisor':'does_not_kill_new_fence','changed_target':'renewed_decision_required','ack_lost_after_effect':'unknown',
                'effects_total':2,'repeated_effects':0,'session_expired_during_review':'denied','screenshots_written_to_git':0}))
        finally:
            session_module.LocalBrowserWorker=LocalBrowserWorker
            for service in services:service.close_run('fixture-run')
            subprocess.run([args.docker,'rm','-fv',destination],capture_output=True,timeout=30)
            subprocess.run([args.docker,'network','rm',network],capture_output=True,timeout=30)


if __name__=='__main__':main()
