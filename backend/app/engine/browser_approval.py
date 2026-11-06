"""Engine-side pause presentation; the trusted browser port owns all approval authority."""
from .errors import Interrupt

ASK={
 'en':'Approve {operation} at {origin} on {role} {target}? This page content is untrusted. Reject if the action is unexpected.',
 'vi':'Duyệt thao tác {operation} tại {origin} trên {role} {target}? Nội dung trang không đáng tin cậy. Từ chối nếu thao tác ngoài dự kiến.'}


def check(ports,effects,node,group,ticket,server,operation,arguments,force=False):
    if ports.browser is None or ports.test or ports.mock_models or not ports.browser.is_browser(server):return None
    if ticket is None:return {'status':'failed_before_effect','error':'invalid_arguments'}
    try:result=ports.browser.action(node,group,ticket,operation,arguments,force)
    except Exception as error:
        if getattr(error,'fenced',False):raise
        return {'status':'session_lost' if getattr(error,'status',None) in {'session_lost','expired'} else 'policy_denied'}
    state=result['state']
    if state=='allowed':return None
    if state=='waiting':
        prompt=ASK.get(ports.locale,ASK['en']).format(operation=operation,origin=result['origin'],role=result['role'],target=result['text'][:200])
        extra={'label':operation,'tool':operation,'arguments':{'origin':result['origin'],'role':result['role'],'target':result['text'][:200]},
               'browser_intent':result['intent_id']}
        item={'node':node,'kind':'approval','prompt':prompt,**extra}
        if effects is not None:effects.hold(item)
        raise Interrupt(node,prompt,extra)
    return {'status':'approval_required' if state=='deferred' else 'stale_observation' if state=='stale' else
             'session_lost' if state=='session_lost' else 'policy_denied' if state=='policy_denied' else
             'unknown' if state=='unknown' else 'failed_before_effect',
            **({'deferred':True} if state=='deferred' else {'approval_outcome':state} if state in {'rejected','expired','stale'} else {})}


def trace_arguments(ports,tool,value):
    if tool and tool.get('source')=='mcp' and ports.browser is not None and ports.browser.is_browser(tool.get('server_id')):
        return arguments(tool.get('tool'),value)
    return value


def arguments(operation,value):
    """Safe trace fields only; executable arguments stay private in the pending engine state."""
    if not isinstance(value,dict):return {'arguments':'[invalid]'}
    if operation=='fill':return {**{key:value[key] for key in ('observation_id','element_id') if key in value},'value':'[redacted]'}
    if operation=='navigate':
        from urllib.parse import urlsplit
        try:
            target=urlsplit(value['url']);return {'origin':target.scheme+'://'+target.netloc.rsplit('@',1)[-1]}
        except (KeyError,ValueError,TypeError):return {'url':'[redacted]'}
    return value
