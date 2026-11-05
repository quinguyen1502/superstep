#!/usr/bin/env python3
"""Opt-in disposable HTTPS controller + isolated Chromium/profile proof. Synthetic secrets only."""
import argparse
from functools import partial
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import uvicorn
from app.browser_controller import create_app
from app.engine.browser_contract import BrowserSettings, ExecutionContext
from app.engine.browser_profiles import parse_seed
from app.engine.browser_remote import ApprovedController, RemoteBrowserWorker, RemoteTransport
from app.engine.browser_worker import LocalBrowserWorker, BrowserWorkerError
from app.engine.browser_cleanup import reap_controller
from app.services.browser_controller_service import BrowserControllerService


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='/Applications/Docker.app/Contents/Resources/bin/docker')
    parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    def docker(*argv,timeout=120):
        result=subprocess.run([args.docker,*argv],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        if result.returncode: raise RuntimeError('Fixture Docker '+argv[0]+' failed: '+result.stderr[-1500:])
        return result.stdout.strip()
    if not args.skip_build:
        docker('build','-t','superstep-browser-worker:1','docker/browser-worker',timeout=600)
        docker('build','-f','backend/tests/fixtures/browser_egress/Gateway.Dockerfile','-t','superstep-browser-egress-gateway:task-0242','.',timeout=180)
        docker('build','-f','backend/tests/fixtures/browser_egress/ProfileWorker.Dockerfile','-t','superstep-browser-profile-fixture:task-0244','.',timeout=300)
    suffix=uuid.uuid4().hex[:10];identity='fixture-'+suffix
    network,fixture='ss-browser-remote-net-'+suffix,'ss-browser-remote-fixture-'+suffix
    token='synthetic-control-token-'+uuid.uuid4().hex
    context=ExecutionContext(principal_id='user:synthetic-owner',run_id='remote-'+suffix,group_id='agent',connection_id='browser',configuration='a'*64,lease_generation=1)
    service=None;server=None;workers=[]
    try:
        docker('network','create','--internal',network)
        docker('run','-d','--name',fixture,'--network',network,'--network-alias','fixture','--read-only','--cap-drop=ALL',
               '--security-opt=no-new-privileges','--pids-limit=64','--memory=128m','--tmpfs=/tmp:rw,nosuid,size=16m',
               'superstep-browser-egress-gateway:task-0242','python','fixture_server.py')
        with tempfile.TemporaryDirectory(prefix='ss-browser-remote-tls-') as temp:
            cert,key=str(Path(temp)/'cert.pem'),str(Path(temp)/'key.pem')
            docker('cp',fixture+':/fixture/fixture-cert.pem',cert);docker('cp',fixture+':/fixture/fixture-key.pem',key)
            factory=partial(LocalBrowserWorker,docker=args.docker,image='superstep-browser-profile-fixture:task-0244',
                            gateway_image='superstep-browser-egress-gateway:task-0242',gateway_network=network,resource_owner=identity)
            proxy={'mode':'custom','server':'http://fixture-proxy:8081','auth':'basic'}
            proxy_secrets={'proxy_username':'synthetic-user','proxy_password':'synthetic-password'}
            service=BrowserControllerService(factory,approved_proxies=[proxy['server']],
                operator_default={'proxy':proxy,'secrets':proxy_secrets})
            # TLS listener is outside every network=none browser namespace. No HTTP fallback.
            listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(create_app(service,token),ssl_certfile=cert,ssl_keyfile=key,access_log=False,log_level='error'))
            thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);thread.start()
            deadline=time.monotonic()+10
            while not server.started and time.monotonic()<deadline: time.sleep(.05)
            assert server.started
            transport=RemoteTransport(ApprovedController('https://controller.test:'+str(port),'127.0.0.1'),token,tls=ssl.create_default_context(cafile=cert))
            worker=RemoteBrowserWorker(context,BrowserSettings(provider='controlled_remote',allowed_origins=['http://allowed.test:8080'],max_actions=20),transport)
            workers.append(worker);worker.start()
            first=worker.call(worker.command('navigate',{'url':'http://allowed.test:8080/form'},0));assert first.status=='confirmed',first.status
            field=next(item.element_id for item in first.observation.elements if item.role=='textbox')
            fill=worker.command('fill',{'observation_id':first.observation.observation_id,'element_id':field,'value':'synthetic-value'},1)
            assert worker.call(fill).status=='approval_required';worker.approve(fill);assert worker.call(fill).status=='confirmed'
            second=worker.call(worker.command('snapshot',{},2));button=next(item.element_id for item in second.observation.elements if item.role=='button')
            click=worker.command('click',{'observation_id':second.observation.observation_id,'element_id':button},3)
            worker.approve(click);assert worker.call(click).status=='confirmed'
            third=worker.call(worker.command('snapshot',{},4));status=next(item.element_id for item in third.observation.elements if item.text=='Submitted')
            extracted=worker.call(worker.command('extract',{'observation_id':third.observation.observation_id,'fields':{'status':status}},5))
            assert extracted.extracted=={'status':'Submitted'}
            capture=worker.call(worker.command('screenshot',{},6));assert worker.artifact(capture.artifact_id).startswith(b'\x89PNG')
            assert worker.call(worker.command('navigate',{'url':'http://127.0.0.1:9090/private'},7)).status=='policy_denied'
            worker.close()
            for mode in ['custom','operator_default']:
                routed=RemoteBrowserWorker(context.model_copy(update={'group_id':mode}),
                    BrowserSettings(provider='controlled_remote',allowed_origins=['https://allowed.test:8443','http://allowed.test:8082'],
                                    proxy=proxy if mode=='custom' else {'mode':'operator_default'}),transport)
                workers.append(routed);routed.start(secrets=proxy_secrets if mode=='custom' else {})
                assert routed.call(routed.command('navigate',{'url':'https://allowed.test:8443/'},0)).status=='confirmed'
                assert routed.call(routed.command('navigate',{'url':'http://allowed.test:8082/no-direct-fallback'},1)).status!='confirmed'
                routed.close()
            settings=BrowserSettings(provider='controlled_remote',profile={'name':'fixture-profile','origins':['https://allowed.test:8443']})
            raw=json.dumps({'cookies':[{'name':'login','value':'synthetic-cookie','domain':'allowed.test','path':'/','expires':-1,'httpOnly':True,'secure':True,'sameSite':'Lax'}],
                            'origins':[{'origin':'https://allowed.test:8443','localStorage':[{'name':'login','value':'synthetic-storage'}]}]})
            profile=RemoteBrowserWorker(context.model_copy(update={'group_id':'profile'}),settings,transport);workers.append(profile)
            profile.start(profile_seed=parse_seed(settings,context.principal_id,raw))
            observed=profile.call(profile.command('navigate',{'url':'https://allowed.test:8443/profile'},0))
            assert observed.status=='confirmed',observed.status
            assert 'Stored login' in observed.observation.text
            assert 'synthetic-cookie' not in observed.model_dump_json() and 'synthetic-storage' not in observed.model_dump_json()
            for sequence,url in enumerate(['https://other.test:8443/profile','https://sub.allowed.test:8443/profile','https://allowed.test:8082/profile'],1):
                assert profile.call(profile.command('navigate',{'url':url},sequence)).status=='policy_denied'
            capture=profile.call(profile.command('screenshot',{},4));assert profile.artifact(capture.artifact_id).startswith(b'\x89PNG')
            profile.close()
            anonymous=RemoteBrowserWorker(context.model_copy(update={'group_id':'anonymous'}),BrowserSettings(provider='controlled_remote',allowed_origins=['https://allowed.test:8443']),transport)
            workers.append(anonymous);anonymous.start()
            empty=anonymous.call(anonymous.command('navigate',{'url':'https://allowed.test:8443/profile'},0));assert empty.status=='confirmed'
            assert 'Anonymous' in empty.observation.text and 'Stored login' not in empty.observation.text;anonymous.close()
            stats=json.loads(docker('exec',fixture,'cat','/tmp/fixture-stats.json'))
            profiles=[item for item in stats['requests'] if item['path']=='/profile']
            assert len(profiles)==2 and [item['profile_cookie'] for item in profiles]==[True,False],profiles
            assert all(item['host']=='allowed.test:8443' for item in profiles)
            assert not any(item['leaked_proxy_auth'] for item in stats['requests'])
            assert not any(item['path']=='/no-direct-fallback' for item in stats['requests'])
            assert len(stats['connects']) >= 4
            # Restart cleanup addresses only this controller's labels, including volume leftovers.
            orphan=factory(context.model_copy(update={'group_id':'restart'}),BrowserSettings());orphan.start()
            reap_controller(args.docker,identity)
            assert not docker('ps','-aq','--filter','label=superstep.browser.controller='+identity)
            assert not docker('volume','ls','-q','--filter','label=superstep.browser.controller='+identity)
            orphan.close()
            print(json.dumps({'outcome':'passed','transport':'HTTPS_verified_pinned','proxy_modes':['direct','custom','operator_default'],'proxy_failure':'no_direct_fallback','operations':['navigate','snapshot','fill','click','extract','screenshot'],
                              'profile_cookie':'approved_host_only','local_storage':'approved_origin_only','other_origin_subdomain_port':'denied',
                              'separate_session':'anonymous','secret_text':'redacted','restart_cleanup':'own_labels_only','screenshots_written_to_git':0}))
            server.should_exit=True;thread.join(10)
    finally:
        for worker in workers: worker.close()
        if service: service.close()
        if server: server.should_exit=True
        subprocess.run([args.docker,'rm','-fv',fixture],capture_output=True,timeout=30)
        subprocess.run([args.docker,'network','rm',network],capture_output=True,timeout=30)


if __name__=='__main__': main()
