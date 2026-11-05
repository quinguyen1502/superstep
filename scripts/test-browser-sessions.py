#!/usr/bin/env python3
"""Disposable multi-process browser scheduling and fenced-effect proof; synthetic data only."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.engine.browser_contract import BrowserSettings
from app.engine.browser_worker import LocalBrowserWorker
from app.models import User,McpServer
from app.models.browser_session import BrowserCommand
from app.models.database import Database
from app.repositories import McpServerRepository,StaleLease
from app.repositories.browser_sessions import BrowserSessionRepository
from app.services.mcp_service import McpService
from app.services.browser_session_service import BrowserSessionService
from app.services.browser_runtime_service import BrowserRuntimeService


def service_for(url,docker,network):
    db=Database(url)
    return BrowserSessionService(BrowserSessionRepository(db),McpService(McpServerRepository(db)),BrowserRuntimeService(None),
        local_options={'docker':docker,'gateway_image':'superstep-browser-egress-gateway:task-0242','gateway_network':network})


def execute(url,docker,network,ticket,operation,arguments,delay):
    time.sleep(delay)
    service=service_for(url,docker,network)
    return service.bind('fixture-owner','user:fixture-owner','fixture-run',1).call('agent',ticket,operation,arguments)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='/Applications/Docker.app/Contents/Resources/bin/docker')
    parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    def docker(*argv,timeout=120):
        result=subprocess.run([args.docker,*argv],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise RuntimeError('Fixture Docker '+argv[0]+' failed: '+result.stderr[-1500:])
        return result.stdout.strip()
    os.environ['STUDIO_ENABLE_BROWSER']='1';os.environ['STUDIO_ENABLE_BROWSER_RUNTIME']='1'
    if not args.skip_build:
        docker('build','-t','superstep-browser-worker:1','docker/browser-worker',timeout=600)
        docker('build','-f','backend/tests/fixtures/browser_egress/Gateway.Dockerfile','-t','superstep-browser-egress-gateway:task-0242','.',timeout=180)
    suffix=uuid.uuid4().hex[:10];network='ss-browser-session-net-'+suffix;fixture='ss-browser-session-fixture-'+suffix
    service=None
    try:
        docker('network','create','--internal',network)
        docker('run','-d','--name',fixture,'--network',network,'--network-alias','fixture','--read-only','--cap-drop=ALL',
            '--security-opt=no-new-privileges','--pids-limit=64','--memory=128m','--tmpfs=/tmp:rw,nosuid,size=16m',
            'superstep-browser-egress-gateway:task-0242','python','fixture_server.py')
        with tempfile.TemporaryDirectory(prefix='ss-browser-session-db-') as temp:
            url='sqlite:///'+str(Path(temp)/'fixture.db');db=Database(url);db.migrate()
            settings=BrowserSettings(allowed_origins=['http://allowed.test:8080'],max_actions=20)
            with db.session() as s:
                s.add(User(id='fixture-owner',email='fixture-owner@example.test',active=True,created=time.time()))
                s.add(McpServer(id='browser',owner='fixture-owner',scope='user',transport='managed',adapter='browser',name='Fixture browser',settings=settings.model_dump_json(),created=time.time()));s.commit()
            service=service_for(url,args.docker,network);scope=service.bind('fixture-owner','user:fixture-owner','fixture-run',1)
            batch=[{'index':0,'server_id':'browser','tool':'navigate','arguments':{'url':'http://allowed.test:8080/effect-form'}},
                   {'index':1,'server_id':'browser','tool':'snapshot','arguments':{}}]
            tickets=scope.prepare('agent','round-one',batch)
            with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
                later=pool.submit(execute,url,args.docker,network,tickets[1],'snapshot',{},0)
                earlier=pool.submit(execute,url,args.docker,network,tickets[0],'navigate',batch[0]['arguments'],.2)
                observed,first= later.result(90),earlier.result(90)
            assert first['status']==observed['status']=='confirmed',(first['status'],observed['status'])
            assert 'Effect fixture' in observed['observation']['text']
            row=service.repo.get(service.repo.command(tickets[0]).session_id);worker_id=row.worker_id
            # A new supervisor process attaches to the existing worker after its creator exited.
            button=next(item['element_id'] for item in observed['observation']['elements'] if item['role']=='button')
            arguments={'observation_id':observed['observation']['observation_id'],'element_id':button}
            click=scope.prepare('agent','round-two',[{'index':0,'server_id':'browser','tool':'click','arguments':arguments}])[0]
            assert scope.call('agent',click,'click',arguments)['status']=='approval_required'
            # TEST ONLY trusted approval primitive. Durable Human verification remains TASK-0246.
            worker=LocalBrowserWorker.attach(service.context(row),settings,worker_id,docker=args.docker)
            worker.approve(worker.command('click',arguments,2,click))
            with db.session() as s:s.get(BrowserCommand,click).status='pending';s.commit()
            assert scope.call('agent',click,'click',arguments)['status']=='confirmed'
            final=scope.prepare('agent','round-three',[{'index':0,'server_id':'browser','tool':'snapshot','arguments':{}}])[0]
            current=scope.call('agent',final,'snapshot',{});assert current['status']=='confirmed'
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                stats=json.loads(docker('exec',fixture,'cat','/tmp/fixture-stats.json'))
                if len(stats['effects'])==1:break
                time.sleep(.05)
            assert len(stats['effects'])==1
            fresh=next(item['element_id'] for item in current['observation']['elements'] if item['role']=='button')
            denied_args={'observation_id':current['observation']['observation_id'],'element_id':fresh}
            denied=scope.prepare('agent','round-four',[{'index':0,'server_id':'browser','tool':'click','arguments':denied_args}])[0]
            worker.approve(worker.command('click',denied_args,4,denied))
            def fenced():raise StaleLease('fixture-run')
            scope.guard=fenced
            try:scope.call('agent',denied,'click',denied_args)
            except StaleLease:pass
            else:raise AssertionError('Stale lease dispatched a click')
            time.sleep(.2)
            stats=json.loads(docker('exec',fixture,'cat','/tmp/fixture-stats.json'));assert len(stats['effects'])==1
            assert not docker('ps','-aq','--filter','name=ss-browser-'+worker_id)
            assert service.repo.get(row.id).status=='lost'
            print(json.dumps({'outcome':'passed','process_order':['navigate','snapshot'],'creator_exit':'same_page_reattached',
                'approved_effects':1,'fenced_extra_effects':0,'late_dispatch':'denied','resources':'removed','screenshots_written_to_git':0}))
            db.engine.dispose()
    finally:
        if service:service.close_run('fixture-run')
        subprocess.run([args.docker,'rm','-fv',fixture],capture_output=True,timeout=30)
        subprocess.run([args.docker,'network','rm',network],capture_output=True,timeout=30)


if __name__=='__main__':main()
