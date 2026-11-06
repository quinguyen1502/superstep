"""Controlled RPC contracts: capability/auth/identity checks and unknown outcomes never replay."""
import json
import threading
import uuid
import pytest
import httpx
from fastapi.testclient import TestClient
from app.browser_controller import create_app
from app.core.errors import AppError
from app.engine.browser_contract import BrowserSettings, WorkerResult
from app.engine.browser_remote import (ApprovedController, RemoteTransport, RemoteBrowserWorker, RemoteOpen, CAPABILITIES)
from app.engine.browser_worker import BrowserWorkerError
from app.services.browser_controller_service import BrowserControllerService
from tests.test_browser_runtime import context, PNG

TOKEN = 'synthetic-controller-token-32-characters'


class FakeWorker:
    def __init__(self, context, settings):
        self.context, self.settings = context, settings
        self.session_id, self.generation, self.closed = uuid.uuid4().hex, 1, False
        self.cleanup_pending = False; self.calls = []; self.started = False
    def start(self, **kwargs): self.started = True; return self
    def call(self, command):
        self.calls.append(command)
        return WorkerResult(command_id=command.command_id, generation=1, sequence=command.sequence, status='confirmed', elapsed_ms=0)
    def approve(self, command): self.calls.append(command); return {'status':'approved'}
    def artifact(self, aid): return PNG
    def close(self): self.closed = True; return True


class ApiTransport:
    def __init__(self, client): self.client, self.calls = client, []
    def request(self, method, body=None, timeout=65):
        self.calls.append((method, body))
        result = self.client.request('GET' if method == 'info' else 'POST', '/v1/' + method,
                                     json=body, headers={'Authorization': 'Bearer '+TOKEN})
        if result.status_code != 200: raise BrowserWorkerError()
        return result.json()['data']


def test_remote_contract_identity_approval_and_no_replay():
    service = BrowserControllerService(FakeWorker, max_sessions=1)
    with TestClient(create_app(service, TOKEN)) as client:
        transport = ApiTransport(client)
        worker = RemoteBrowserWorker(context(), BrowserSettings(provider='browserless', allowed_origins=['https://example.com']), transport)
        worker.start(secrets={'unrelated':'never-pass'})
        entry = service.entries[worker.session_id]
        command = worker.command('snapshot', {}, 0)
        assert worker.call(command).status == 'confirmed'
        assert entry.worker.calls[-1].session_id == entry.worker.session_id != worker.session_id
        action = worker.command('fill', {'observation_id':'o','element_id':'e','value':'private'}, 1)
        assert worker.approve(action) == {'status':'approved'}
        assert worker.artifact('capture') == PNG
        foreign = command.model_copy(update={'context':context('intruder')})
        denied = client.post('/v1/command', json=foreign.model_dump(), headers={'Authorization':'Bearer '+TOKEN})
        assert denied.status_code == 403 and len(entry.worker.calls) == 2
        duplicate = next(body for method, body in transport.calls if method == 'open')
        assert client.post('/v1/open', json=duplicate, headers={'Authorization':'Bearer '+TOKEN}).status_code == 503
        assert worker.close() and entry.worker.closed
        # Tombstones prevent a repeated open from rebuilding page state after a lost response.
        assert client.post('/v1/open', json=duplicate, headers={'Authorization':'Bearer '+TOKEN}).status_code == 503
        assert not any('unrelated' in str(body) for _, body in transport.calls)


def test_control_api_auth_bounds_and_safe_errors():
    service = BrowserControllerService(FakeWorker)
    with TestClient(create_app(service, TOKEN)) as client:
        assert client.get('/v1/info').status_code == 401
        headers={'Authorization':'Bearer '+TOKEN}
        assert client.get('/v1/info', headers=headers).json()['data'] == CAPABILITIES
        invalid = client.post('/v1/open', headers=headers, json={'browserless_token':'must-not-echo'})
        assert invalid.status_code == 422 and 'must-not-echo' not in invalid.text
        assert client.post('/v1/open', headers=headers, content=b'x'*(256*1024+1)).status_code == 413
        assert client.get('/docs',headers=headers).status_code == 404
    with pytest.raises(ValueError): create_app(token='short')


def test_capability_refusal_before_open_and_lost_effect_is_unknown():
    class Transport:
        def __init__(self): self.calls=[]; self.bad=True
        def request(self, method, body=None, timeout=65):
            self.calls.append(method)
            if method=='info': return {**CAPABILITIES,'boundary':'raw_cdp'} if self.bad else CAPABILITIES
            if method=='open': return {'status':'ready','session_id':body['request_id'],'generation':1}
            if method=='close': return {'status':'closed'}
            raise BrowserWorkerError()
    transport=Transport(); worker=RemoteBrowserWorker(context(),BrowserSettings(provider='browserless', allowed_origins=['https://example.com']),transport)
    with pytest.raises(BrowserWorkerError) as caught: worker.start()
    assert caught.value.status=='unsupported' and transport.calls==['info']
    transport.bad=False; worker.start()
    assert worker.call(worker.command('click',{'observation_id':'o','element_id':'e'},0)).status=='unknown'
    assert transport.calls.count('command')==1 and worker.closed


def test_tls_pinning_redirect_refusal_and_no_environment_proxy(monkeypatch):
    observed=[]
    real_client=httpx.Client
    def client(**kwargs):
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False and kwargs['verify'] is True
        def handle(request):
            observed.append(request)
            return httpx.Response(302,headers={'location':'https://attacker.example'})
        return real_client(**kwargs,transport=httpx.MockTransport(handle))
    monkeypatch.setattr(httpx,'Client',client)
    transport=RemoteTransport(ApprovedController('https://controller.example','127.0.0.1'),TOKEN)
    with pytest.raises(BrowserWorkerError): transport.request('info')
    assert len(observed)==1 and observed[0].url.host=='127.0.0.1'
    assert observed[0].headers['Host']=='controller.example' and observed[0].extensions['sni_hostname']=='controller.example'
    for endpoint in ['wss://controller.example','http://controller.example','https://controller.example/?secret=1']:
        with pytest.raises(BrowserWorkerError): ApprovedController(endpoint,'127.0.0.1')
    with pytest.raises(BrowserWorkerError): RemoteTransport(ApprovedController('https://controller.example','127.0.0.1'),TOKEN,tls=False)


def test_endpoint_requires_independent_operator_approval_and_cleanup_filter(monkeypatch):
    from app.engine.browser_remote import approved_transport
    from app.engine.browser_cleanup import reap_controller
    secrets={'browserless_token':TOKEN}
    with pytest.raises(BrowserWorkerError): approved_transport(secrets, [])
    assert approved_transport(secrets,[ApprovedController('https://controller.example','10.0.0.4')]).controller.address=='10.0.0.4'
    calls=[]
    def run(argv, **kwargs):
        from types import SimpleNamespace
        calls.append(argv)
        output='a'*12+'\n' if argv[1:3]==['ps','-aq'] else 'ss-browser-'+'b'*32+'-socket\n' if argv[1:3]==['volume','ls'] else ''
        return SimpleNamespace(returncode=0,stdout=output)
    monkeypatch.setattr('app.engine.browser_cleanup.subprocess.run',run)
    reap_controller('synthetic-docker','controller-one')
    assert ['synthetic-docker','ps','-aq','--filter','label=superstep.browser.controller=controller-one'] in calls
    assert ['synthetic-docker','volume','ls','-q','--filter','label=superstep.browser.controller=controller-one'] in calls
    assert len(calls)==4
    with pytest.raises(BrowserWorkerError): reap_controller('synthetic-docker','')


def test_controller_capacity_counts_pending_cleanup_and_sweeps_tombstones():
    import time
    service=BrowserControllerService(FakeWorker,max_sessions=1)
    try:
        def request(): return RemoteOpen(context=context(),settings=BrowserSettings(provider='browserless', allowed_origins=['https://example.com']),request_id=uuid.uuid4().hex)
        first=request();service.open(first);entry=service.entries[first.request_id]
        entry.worker.closed=True;entry.worker.cleanup_pending=True
        with pytest.raises(AppError): service.open(request())
        entry.worker.cleanup_pending=False;entry.expires=time.monotonic()-1
        service.sweep();assert first.request_id not in service.entries
    finally: service.close()
