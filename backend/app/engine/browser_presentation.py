"""Bounded owner observations and an allowlist of visitor-visible browser facts."""
import json
from urllib.parse import urlsplit

OPERATIONS = {'navigate', 'snapshot', 'click', 'fill', 'extract', 'screenshot'}
STATUSES = {'confirmed', 'failed_before_effect', 'unknown', 'approval_required', 'challenge_required',
            'expired', 'session_lost', 'stale_observation', 'policy_denied', 'cancelled', 'missing_input', 'dry_run'}


def origin(value):
    try:
        target = urlsplit(value)
        if target.scheme not in {'http', 'https'} or not target.hostname: return None
        host = target.hostname
        return target.scheme + '://' + ('[' + host + ']' if ':' in host else host) + (':' + str(target.port) if target.port else '')
    except (ValueError, TypeError): return None


def facts(value):
    if not isinstance(value, dict): return {}
    out = {key: value[key] for key, allowed in [('operation', OPERATIONS), ('status', STATUSES),
           ('approval', {'approved', 'rejected', 'expired', 'stale'})] if isinstance(value.get(key), str) and value[key] in allowed}
    return out


def detail(operation, result):
    out = facts({'operation': operation, 'status': result.get('status'), 'approval': result.get('approval_outcome')})
    for key in ('sequence', 'generation', 'elapsed_ms'):
        if type(result.get(key)) is int: out[key] = result[key]
    observed = result.get('observation')
    if isinstance(observed, dict):
        safe_origin = origin(observed.get('origin'))
        out['observation'] = {'origin': safe_origin, 'page_generation': observed.get('page_generation'),
            'text': str(observed.get('text') or '')[:4000], 'elements': [
                {'role': str(item.get('role') or '')[:80], 'text': str(item.get('text') or '')[:160]}
                for item in (observed.get('elements') or [])[:20] if isinstance(item, dict)]}
    if isinstance(result.get('artifact_id'), str): out['artifact_id'] = result['artifact_id']
    if isinstance(result.get('extracted'), dict): out['extracted'] = {key: str(value)[:256] for key, value in list(result['extracted'].items())[:10]}
    return out


def private_workflow(workflow, ports, depth=0):
    if depth > 32: return True
    if workflow.get('browser_recipe'): return True
    for node in workflow.get('nodes') or []:
        data = node.get('data') or {}
        candidates = [data] if node.get('type') == 'mcp' else data.get('tools') or []
        for tool in candidates:
            if not isinstance(tool, dict): continue
            if tool.get('source') == 'workflow' and private_workflow(tool.get('snapshot') or {}, ports, depth + 1): return True
            if ports is not None and ports.browser is not None and tool.get('server_id') and ports.browser.is_browser(tool['server_id']): return True
    return False


def visitor_event(event):
    """Strip every intermediate payload on a browser run, including unrelated state echoes."""
    if not private_event(event): return event
    out = {key: event[key] for key in ('type', 'node', 'node_type', 'label', 'iteration', 'ts', 'duration_ms', 'status') if key in event}
    safe = facts(event.get('browser') or (event.get('agent') if isinstance(event.get('agent'), dict) else {}).get('browser'))
    if event.get('browser_intent'): safe = facts({'operation': event.get('tool'), 'status': 'approval_required'})
    if safe: out['browser'] = safe
    return out


def reply(value):
    """A raw worker envelope is diagnostic data, never a public chat answer."""
    if isinstance(value, dict):
        if 'command_id' in value and 'status' in value and ('sequence' in value or 'generation' in value):
            return facts(value)
        return {key: reply(item) for key, item in value.items()}
    if isinstance(value, list): return [reply(item) for item in value]
    if isinstance(value, str) and len(value) <= 256 * 1024 and value.lstrip().startswith(('{', '[')):
        try: parsed = json.loads(value)
        except (ValueError, RecursionError): return value
        clean = reply(parsed)
        if clean != parsed: return json.dumps(clean, ensure_ascii=False)
    return value


def private_event(event):
    if event.get('browser_private') or event.get('browser_intent') or event.get('browser') or (event.get('agent') if isinstance(event.get('agent'), dict) else {}).get('browser'): return True
    def envelope(value, depth=0):
        if depth > 8: return False
        if isinstance(value, dict):
            if 'command_id' in value and 'generation' in value and isinstance(value.get('status'), str) and value['status'] in STATUSES: return True
            if value.get('_truncated') and isinstance(value.get('preview'), str):
                return all('"' + key + '"' in value['preview'] for key in ('command_id', 'generation', 'status'))
            return any(envelope(item, depth + 1) for item in value.values())
        if isinstance(value, list): return any(envelope(item, depth + 1) for item in value)
        return False
    return envelope(event.get('delta')) or envelope(event.get('input'))
