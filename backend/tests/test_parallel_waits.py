"""Waits inside one parallel tool wave (TASK-0158, REQ-0076). The other calls finish, and the run resumes once."""
import pytest
from app.engine.effects import Effects
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from tests.test_agent_approval import ARGS, REFUND, refunds, resume, waiting_at  # noqa: F401 (refunds fixture)
from tests.test_agent_node import BUILTIN, call, final, script, wf


class Ledger:
    def __init__(self): self.rows = {}
    def get(self, nid, it): return self.rows.get((nid, it), (None,))[0]
    def put(self, nid, it, delta, key): self.rows.setdefault((nid, it), (delta, key))


@pytest.fixture(autouse=True)
def parallel(monkeypatch):
    monkeypatch.setenv("STUDIO_AGENT_PARALLEL_TOOLS", "4")


def test_an_approval_pauses_only_its_call_and_the_other_is_kept(monkeypatch):
    looked = []
    monkeypatch.setattr("app.engine.agents.call_tool", lambda fn, state, key, locale: looked.append(state["message"]) or "found")
    script(monkeypatch, [("", [call("lookup_order", {"message": "B200"}, "a"), call("send_refund", ARGS, "b")]), ("Done.", [])])
    flow = wf(tools=[BUILTIN, REFUND], steps_field="steps")
    effects = Effects("wave", ledger=Ledger())
    w = waiting_at(list(run_stream(flow, {"message": "x"}, effects=effects)))
    assert looked == ["B200"] and w["tool"] == "send_refund"
    assert set(w["checkpoint"]["nodes"]) == {"ag/__tool/1", "ag/__tool/2"}
    st = final(resume(w, "approved", flow, effects=effects))
    assert looked == ["B200"] and st["answer"] == "Done."
    assert [s["tool"] for s in st["steps"]] == ["lookup_order", "send_refund"]


def test_two_approvals_are_both_kept_and_the_round_resumes_once(monkeypatch, refunds):
    script(monkeypatch, [("", [call("send_refund", ARGS, "a"), call("send_refund", {**ARGS, "order": "C3"}, "b")]), ("Done.", [])])
    other = {**REFUND, "name": "send_refund"}
    flow = wf(tools=[other], steps_field="steps")
    effects = Effects("two", ledger=Ledger())
    w = waiting_at(list(run_stream(flow, {"message": "x"}, effects=effects)))
    holds = w["checkpoint"]["waits"]
    assert {h["node"] for h in holds} == {"ag/__tool/1", "ag/__tool/2"} and refunds[0] == []
    cp = w["checkpoint"]
    evs = list(run_stream(flow, {}, resume={**cp, "answers": {h["node"]: "approved" for h in holds}}, effects=effects))
    assert final(evs)["answer"] == "Done." and len(refunds[0]) == 2
    assert not any(e.get("reused") for e in evs if e["type"] == "node_finished" and str(e.get("node", "")).startswith("ag/__tool/"))


def test_a_restart_does_not_run_the_finished_call_again(monkeypatch):
    looked = []
    monkeypatch.setattr("app.engine.agents.call_tool", lambda fn, state, key, locale: looked.append(1) or "found")
    script(monkeypatch, [("", [call("lookup_order", {"message": "B200"}, "a"), call("send_refund", ARGS, "b")]), ("Done.", [])])
    flow = wf(tools=[BUILTIN, REFUND], steps_field="steps")
    effects = Effects("again", ledger=Ledger())
    w = waiting_at(list(run_stream(flow, {"message": "x"}, effects=effects)))
    evs = resume(w, "approved", flow, effects=effects)
    assert final(evs)["answer"] == "Done." and looked == [1]
    reused = [e["node"] for e in evs if e["type"] == "node_finished" and e.get("reused") and str(e["node"]).startswith("ag/__tool/")]
    assert reused == ["ag/__tool/1"]
