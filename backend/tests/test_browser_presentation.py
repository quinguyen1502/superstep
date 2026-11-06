"""Browser intermediate state stays private across live and persisted chat views."""
import json
from app.engine.browser_presentation import detail, visitor_event, reply
from app.services.public_chat_service import public_event
from app.services.chat_session_service import steps_of
from tests.test_agent_node import call
from tests.test_browser_approval_recovery import runner_for, flow_for, execute, responses
from tests.test_browser_run_sessions import scoped_service


def test_real_run_events_are_marked_and_filtered_even_when_another_node_echoes_state(tmp_path, monkeypatch):
    service, calls, workers = scoped_service(tmp_path, monkeypatch)
    runner = runner_for(service)
    responses(monkeypatch, [('', [call('navigate', {'url': 'https://example.test/private?token=synthetic-private'})]), ('Safe final answer', [])])
    plan = runner.plan('owner', {'workflow': flow_for(['navigate']), 'input': {'message': 'synthetic-private-input'}})
    plan.run_id = 'browser-presentation-run'
    status, events = execute(runner, plan)
    assert status == 'ok'
    nodes = [event for event in events if event['type'] in {'node_started', 'node_finished'}]
    assert nodes and all(event.get('browser_private') for event in nodes)
    owner_steps = steps_of(events, 'full', allow_browser=True)
    public_steps = steps_of(events, 'full')
    assert 'synthetic-private-input' in json.dumps(owner_steps)
    assert 'synthetic-private-input' not in json.dumps(public_steps)
    assert 'observation_id' not in json.dumps(public_steps)
    assert 'command_id' not in json.dumps(public_steps)
    live = [result for event in events if (result := public_event(event, 'full', 'answer'))]
    assert 'synthetic-private-input' not in json.dumps(live)
    assert 'observation_id' not in json.dumps(live)
    tool = next(event['agent'] for event in events if isinstance(event.get('agent'), dict) and event['agent'].get('kind') == 'tool')
    assert tool['browser']['operation'] == 'navigate' and tool['browser']['status'] == 'confirmed'
    assert any(step.get('browser', {}).get('status') == 'confirmed' for step in public_steps)


def test_browser_wait_public_context_cannot_expose_a_target_or_intent():
    event = {'type': 'run_waiting', 'node': 'agent/__tool', 'node_type': 'agent_tool', 'label': 'Review',
        'browser_private': True, 'browser_intent': 'private-intent', 'tool': 'fill', 'prompt': 'private target text',
        'arguments': {'value': 'private-fill'}, 'state': {'cookie': 'private-cookie'}}
    result = public_event(event, 'full', 'answer')
    assert result['browser'] == {'operation': 'fill', 'status': 'approval_required'}
    assert not any(value in json.dumps(result) for value in ['private-intent', 'private target', 'private-fill', 'private-cookie'])


def test_public_allowlist_refuses_forged_detail_and_does_not_change_nonbrowser_chat():
    event = {'type': 'node_finished', 'node': 'm', 'node_type': 'mcp', 'browser_private': True,
        'input': {'secret': 'private'}, 'delta': {'artifact_id': 'private'}, 'browser': {
            'operation': 'evaluate', 'status': 'unknown', 'approval': 'approved', 'artifact_id': 'private',
            'observation': {'text': 'private'}, 'cookie': 'private', 'remote_endpoint': 'private'}}
    assert visitor_event(event)['browser'] == {'status': 'unknown', 'approval': 'approved'}
    assert 'private' not in json.dumps(public_event(event, 'full', 'answer'))
    ordinary = {'type': 'node_finished', 'node': 'm', 'node_type': 'tool', 'delta': {'answer': 'visible'}}
    assert public_event(ordinary, 'full', 'answer')['delta'] == ordinary['delta']


def test_owner_observation_is_bounded_and_raw_worker_reply_does_not_publish_handles():
    result = {'command_id': 'private-command', 'generation': 1, 'sequence': 2, 'status': 'confirmed',
        'observation': {'origin': 'https://user:password@example.test/path?token=private#private', 'page_generation': 3,
            'text': '<script>untrusted</script>' * 1000, 'elements': [{'element_id': 'private-element', 'role': 'button', 'text': 'x' * 1000}] * 200},
        'artifact_id': 'private-image'}
    shown = detail('snapshot', result)
    assert shown['observation']['origin'] == 'https://example.test'
    assert len(shown['observation']['text']) == 4000 and len(shown['observation']['elements']) == 20
    assert all(len(item['text']) == 160 and 'element_id' not in item for item in shown['observation']['elements'])
    assert reply({'result': result}) == {'result': {'status': 'confirmed'}}
    assert json.loads(reply(json.dumps(result))) == {'status': 'confirmed'}


def test_legacy_history_and_later_state_echoes_are_private_without_new_event_markers():
    result = {'command_id': 'private-command', 'generation': 1, 'status': 'confirmed', 'observation': {'text': 'private-page'}}
    events = [
        {'type': 'node_finished', 'node': 'browse', 'node_type': 'mcp', 'input': {'token': 'private-input'}, 'delta': {'result': result}},
        {'type': 'node_finished', 'node': 'reply', 'node_type': 'llm', 'input': {'result': result}, 'delta': {'answer': 'permitted final answer'}},
    ]
    assert 'private-' not in json.dumps(steps_of(events, 'full'))
    assert 'private-page' in json.dumps(steps_of(events, 'full', allow_browser=True))
    # Malformed user data is not a valid browser envelope and cannot break the filter.
    assert visitor_event({'type': 'node_finished', 'delta': {'command_id': 'x', 'generation': 1, 'status': {}}})['delta']['status'] == {}


def test_browser_wait_does_not_persist_private_prompt_into_chat_turns():
    from types import SimpleNamespace
    from app.services.chat_session_service import ChatSessionService
    saved = []
    sessions = SimpleNamespace(get=lambda sid: object(), add_turn=saved.append)
    trigger = SimpleNamespace(reply_field='answer')
    chat = ChatSessionService(sessions, SimpleNamespace(get=lambda tid: trigger), None, None, None)
    message = SimpleNamespace(ref=json.dumps({'session': 'fixture'}), trigger_id='trigger')
    run = SimpleNamespace(id='run', status='waiting', checkpoint='{}', events=json.dumps([
        {'type': 'run_waiting', 'node': 'fill', 'browser_intent': 'private-intent', 'prompt': 'private target from page'}]))
    chat.answer(message, run, {'waiting': {'node': 'fill'}})
    assert saved[0].text == '' and saved[0].answered_by == 'reviewer'

def test_visitor_event_preserves_transport_errors():
    frame = {'type': 'error', 'error': {'code': 'RATE_LIMITED', 'message': 'slow down'}, 'ts': 1,
             'browser_private': True, 'delta': {'command_id': 'x', 'generation': 1, 'status': 'unknown'}}
    assert visitor_event(frame) == {'type': 'error', 'error': {'code': 'RATE_LIMITED', 'message': 'slow down'}, 'ts': 1}

