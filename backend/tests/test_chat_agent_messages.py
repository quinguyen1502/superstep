"""TASK-0214: in a chat, the Agent node sends the current message to the model once. The conversation field holds the
earlier exchanges plus this message (DEC-0052); an Agent whose task prompt already carries the message
(`{{state.message}}`) leaves that last history item out. Exact message lists for turns 1 and 3, with and without a
Human node answered in the chat (TASK-0210)."""
import json
from app.engine import agents
from tests.test_chat_sessions import H, chat, node, say, user, wait_turns, STATE

TOOL = {"name": "lookup_order", "description": "Find the status of an order", "source": "builtin", "function": "lookup_order"}


def flow(*middle):
    ns = [node("s", "start"), *middle, node("e", "end")]
    return {"name": "Agent chat", "state": STATE, "nodes": ns,
            "edges": [{"id": str(i), "source": a["id"], "target": b["id"]} for i, (a, b) in enumerate(zip(ns, ns[1:]))]}


def agent(prompt="{{state.message}}"):
    return node("bot", "agent", prompt=prompt, history_field="messages", output_field="reply", tools=[TOOL])


def record(monkeypatch):
    seen = []
    def fake(messages, tools, model, cred=None, on_usage=None, on_token=None, mock=False, locale="en", parallel=None):
        seen.append(json.loads(json.dumps(messages))); return (f"answer {len(seen)}", [])
    monkeypatch.setattr(agents, "call_agent", fake)
    return seen


def U(x): return {"role": "user", "content": x}
def A(x): return {"role": "assistant", "content": x}


def test_start_agent_end_sends_each_message_once(monkeypatch):
    seen = record(monkeypatch)
    tok = user(); _wid, sid = chat(tok, flow(agent()))
    for i, m in enumerate(["hi", "my order A1", "thanks"], 1):
        assert say(tok, {"chat_session_id": sid, "message": m})[-1]["status"] == "ok"; wait_turns(tok, sid, 2 * i)
    assert seen[0] == [U("hi")]
    assert seen[2] == [U("hi"), A("answer 1"), U("my order A1"), A("answer 2"), U("thanks")]


def test_a_prompt_around_the_message_keeps_it_once(monkeypatch):
    seen = record(monkeypatch)
    tok = user(); _wid, sid = chat(tok, flow(agent("Help this customer. Message: {{state.message}}")))
    say(tok, {"chat_session_id": sid, "message": "hi"}); wait_turns(tok, sid, 2)
    assert seen[0] == [U("Help this customer. Message: hi")]


def test_a_prompt_without_the_message_keeps_the_history_whole(monkeypatch):
    seen = record(monkeypatch)
    tok = user(); _wid, sid = chat(tok, flow(agent("Answer the last user message.")))
    say(tok, {"chat_session_id": sid, "message": "hi"}); wait_turns(tok, sid, 2)
    assert seen[0] == [U("hi"), U("Answer the last user message.")]


def test_human_answer_then_agent(monkeypatch):
    seen = record(monkeypatch)
    ask = node("ask", "human", prompt="Sure about {{state.message}}?", output_field="ok")
    tok = user(); _wid, sid = chat(tok, flow(ask, agent()))
    n = 0
    for m in ["refund A1", "refund A2", "refund A3"]:
        assert say(tok, {"chat_session_id": sid, "message": m})[-1]["status"] == "waiting"
        n += 2; q = wait_turns(tok, sid, n)["turns"][-1]
        assert say(tok, {"chat_session_id": sid, "resume_run_id": q["run_id"], "response": "yes"})[-1]["status"] == "ok"
        n += 2; wait_turns(tok, sid, n)
    assert len(seen) == 3
    assert seen[0] == [U("refund A1")]
    assert seen[2] == [U("refund A1"), A("Sure about refund A1?"), U("yes"), A("answer 1"),
                       U("refund A2"), A("Sure about refund A2?"), U("yes"), A("answer 2"), U("refund A3")]
