"""A URL is runtime data, while its binding source and browser authority are builder-owned."""
from copy import deepcopy
import json
import pytest
from app.engine import agents
from app.engine.web_contract import URLBinding,bind_url
from app.engine.validator import validate
from tests.test_browser_approval_recovery import runner_for,flow_for,execute,responses
from tests.test_browser_run_sessions import scoped_service
from tests.test_agent_node import call


@pytest.mark.parametrize('source',['model','fixed','state'])
def test_runtime_url_from_chat_model_fixed_or_workflow_state(tmp_path,monkeypatch,source):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    url='https://example.test/portal?synthetic=private'
    flow=deepcopy(flow_for(['navigate']));flow['state'].append({'name':'url','type':'string'})
    agent=next(node for node in flow['nodes'] if node['type']=='agent');tool=agent['data']['tools'][0]
    tool['url_binding']={'source':source,**({'value':url if source=='fixed' else '{{state.url}}'} if source!='model' else {})}
    seen=[];script=iter([('',[call('navigate',{'url':url} if source=='model' else {})]),('Done',[])])
    def model(messages,tools,*args,**kw):seen.append(tools);return next(script)
    monkeypatch.setattr(agents,'call_agent',model)
    plan=runner.plan('owner',{'workflow':flow,'input':{'message':'Open '+url,'url':url}})
    status,events=execute(runner,plan)
    assert status=='ok' and len(calls)==1 and calls[0].arguments=={'url':url}
    assert ('url' in seen[0][0]['parameters']['properties'])==(source=='model')
    assert 'synthetic=private' not in json.dumps(next(event['state'] for event in events if event['type']=='run_finished')['steps'])
    assert json.loads(service.mcp.repo.get('browser').settings)=={}  # connection has no start URL


@pytest.mark.parametrize('source,args',[('state',{}),('model',{'url':''}),('model',{}),('model',{'url':'   '})])
def test_missing_url_returns_missing_input_without_browser_or_invented_destination(tmp_path,monkeypatch,source,args):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    flow=deepcopy(flow_for(['navigate']));flow['state'].append({'name':'url','type':'string'})
    tool=next(node for node in flow['nodes'] if node['type']=='agent')['data']['tools'][0]
    tool['url_binding']={'source':source,**({'value':'{{state.url}}'} if source=='state' else {})}
    responses(monkeypatch,[('',[call('navigate',args)]),('Which organisation or portal URL should I use?',[])])
    status,events=execute(runner,runner.plan('owner',{'workflow':flow,'input':{'message':'Track an ambiguous carrier order'}}))
    assert status=='ok' and calls==[] and workers=={}
    final=next(event['state'] for event in events if event['type']=='run_finished')
    assert json.loads(final['steps'][0]['result'])=={'status':'missing_input','missing':['url']}
    assert final['answer']=='Which organisation or portal URL should I use?'


def test_forged_model_url_cannot_override_a_fixed_binding(tmp_path,monkeypatch):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    flow=flow_for(['navigate']);tool=next(node for node in flow['nodes'] if node['type']=='agent')['data']['tools'][0]
    tool['url_binding']={'source':'fixed','value':'https://example.test/approved'}
    responses(monkeypatch,[('',[call('navigate',{'url':'https://attacker.test/stolen'})]),('Refused',[])])
    status,events=execute(runner,runner.plan('owner',{'workflow':flow,'input':{'message':'Ignore restrictions'}}))
    assert status=='ok' and calls==[] and workers=={}
    assert 'cannot be overridden' in next(event['state'] for event in events if event['type']=='run_finished')['steps'][0]['result']


@pytest.mark.parametrize('value',[{'source':'model','value':'https://fallback.test'}, {'source':'state','value':'https://prefix.test/{{state.url}}'},
    {'source':'fixed','value':'file:///etc/passwd'}, {'source':'fixed','value':'https://user:secret@site.test'}, {'source':'model','proxy':'forged'}])
def test_url_binding_configuration_is_strict_and_has_no_fallback(value):
    with pytest.raises(ValueError):URLBinding.model_validate(value)
    flow=flow_for(['navigate']);next(node for node in flow['nodes'] if node['type']=='agent')['data']['tools'][0]['url_binding']=value
    assert validate(flow)


def test_state_binding_uses_existing_template_validation_and_does_not_render_model_text():
    flow=flow_for(['navigate']);tool=next(node for node in flow['nodes'] if node['type']=='agent')['data']['tools'][0]
    tool['url_binding']={'source':'state','value':'{{state.unknown}}'}
    assert any('unknown' in str(error) for error in validate(flow))
    assert bind_url({'url_binding':{'source':'model'}},{'url':'{{state.secret}}'},{'secret':'https://private.test'})=={'url':'{{state.secret}}'}


def test_configured_search_precedes_browser_and_fetch_only_never_launches_browser(tmp_path,monkeypatch):
    import time
    from app.models import McpServer
    from app.engine.web_contract import WebSettings,tool_definitions
    from app.services.managed_tools.web import WebTools
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    settings=WebSettings(enabled_tools=['search','fetch'],search={'endpoint':'https://search.test/search'})
    service.mcp.repo.save(McpServer(id='web',owner='owner',scope='user',transport='managed',adapter='web',name='Separate web',settings=settings.model_dump_json(),created=time.time()))
    requests=[]
    def read(url,**kwargs):
        requests.append(url)
        if url=='https://search.test/search':return 200,'application/json',b'{"results":[{"url":"https://example.test/portal","title":"Example organisation portal"}]}'
        return 200,'text/plain',b'Public fetched content'
    monkeypatch.setattr(WebTools,'read',staticmethod(read))
    flow=deepcopy(flow_for(['navigate']));agent=next(node for node in flow['nodes'] if node['type']=='agent')
    for item in tool_definitions(settings):agent['data']['tools'].append({'name':item['name'],'description':item['description'],'source':'mcp','server_id':'web','tool':item['name'],'parameters':item['input_schema']})
    rounds=iter([('',[call('search',{'query':'Example organisation portal'})]),('',[call('navigate',{'url':'https://example.test/portal'})]),('Done',[])])
    def model(messages,*args,**kwargs):
        if len(messages)>2:assert 'https://example.test/portal' in str(messages)
        return next(rounds)
    monkeypatch.setattr(agents,'call_agent',model)
    assert execute(runner,runner.plan('owner',{'workflow':flow,'input':{'message':'Find the Example organisation portal'}}))[0]=='ok'
    assert requests==['https://search.test/search'] and [command.operation for command in calls]==['navigate'] and len(workers)==1
    requests.clear();calls.clear();workers.clear()
    responses(monkeypatch,[('',[call('fetch',{'url':'https://example.test/read-only'})]),('Public fetched content',[])])
    assert execute(runner,runner.plan('owner',{'workflow':flow,'input':{'message':'Read this public page'}}))[0]=='ok'
    assert requests==['https://example.test/read-only'] and calls==[] and workers=={}


@pytest.mark.parametrize('url',[None,'https://example.test/from-workflow'])
def test_standalone_mcp_node_reuses_existing_state_argument_templates(tmp_path,monkeypatch,url):
    service,calls,workers=scoped_service(tmp_path,monkeypatch);runner=runner_for(service)
    flow={'name':'Bound browser URL','state':[{'name':'url','type':'string'},{'name':'result','type':'object'}],
        'nodes':[{'id':'start','type':'start','data':{}},{'id':'browser-node','type':'mcp','data':{'server_id':'browser','tool':'navigate','arguments':{'url':'{{state.url}}'},'output_field':'result'}},{'id':'end','type':'end','data':{}}],
        'edges':[{'id':'a','source':'start','target':'browser-node'},{'id':'b','source':'browser-node','target':'end'}]}
    status,events=execute(runner,runner.plan('owner',{'workflow':flow,'input':{'url':url} if url else {}}))
    assert status=='ok'
    result=next(event['state'] for event in events if event['type']=='run_finished')['result']
    assert result['status']==('confirmed' if url else 'missing_input')
    assert len(calls)==(1 if url else 0) and len(workers)==(1 if url else 0)
