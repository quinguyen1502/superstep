"""TASK-0198 (REQ-0081, DEC-0075): the AI judge's tokens and cost count in the run's usage, like a model call of a node."""
import pytest
from app.engine import approval_judge as J
from app.engine.usage import make_usage
from app.services.telemetry import summarize
from tests.test_auto_review import H, c, inline, row, start, until, user  # noqa: F401  (fixtures)

USAGE = make_usage("openai", "gpt-4o-mini", 1000, 200)  # 1000 * 0.15 / 1e6 + 200 * 0.60 / 1e6 = 0.00027


@pytest.fixture
def judge(monkeypatch):
    box = {"answer": '{"decision": "approve", "confidence": 0.93, "reason": "small refund", "flags": []}'}
    def invoke(prompt, model, cred):
        if isinstance(box["answer"], Exception): raise box["answer"]
        return box["answer"], dict(USAGE)
    monkeypatch.setattr(J, "_invoke", invoke)
    return box


def reviews(r): return [e for e in r["events"] if e["type"] == "approval_review"]


def test_an_auto_approved_run_counts_the_judge(c, judge):
    owner = user(c); wid, rid = start(c, owner)
    done = until(lambda: (x := row(c, owner, wid, rid))["status"] == "ok" and x)
    [ev] = reviews(done)
    assert ev["node"] == "ask" and ev["outcome"] == "approved" and ev["usage"]["tokens"] == 1200
    assert done["metrics"]["tokens_in"] >= 1000 and done["metrics"]["tokens_out"] >= 200
    assert done["metrics"]["tokens_in"] == sum(e["usage"]["tokens_in"] for e in done["events"] if e.get("usage") and e["type"] in ("node_finished", "approval_review"))


@pytest.mark.parametrize("answer", ['{"decision": "approve", "confidence": 0.4, "reason": "unsure", "flags": []}', "not json"])
def test_a_step_sent_to_people_counts_the_judge_while_it_waits(c, judge, answer):
    """Escalated (or an answer that is not the JSON decision) still used tokens: the waiting run shows them now."""
    judge["answer"] = answer
    owner = user(c); wid, rid = start(c, owner)
    r = row(c, owner, wid, rid)
    assert r["status"] == "waiting" and len(reviews(r)) == 1
    assert r["metrics"]["tokens_in"] >= 1000 and r["metrics"]["tokens_out"] >= 200
    # the person's answer resumes the run; the final metrics keep the judge's tokens
    assert c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(owner["token"])).status_code == 200
    done = until(lambda: (x := row(c, owner, wid, rid))["status"] == "ok" and x)
    assert len(reviews(done)) == 1 and done["metrics"]["tokens_in"] >= 1000


def test_a_failed_call_without_an_answer_counts_nothing(c, judge):
    judge["answer"] = RuntimeError("provider down")
    owner = user(c); wid, rid = start(c, owner)
    assert reviews(row(c, owner, wid, rid)) == []


def test_summary_metrics_add_the_judge():
    evs = [{"type": "node_finished", "node": "llm", "usage": make_usage("openai", "gpt-4o-mini", 10, 5)},
           {"type": "approval_review", "node": "ask", "usage": USAGE}]
    m = summarize(evs, 0.0, 1.0)
    assert (m["tokens_in"], m["tokens_out"]) == (1010, 205) and m["cost_usd"] == pytest.approx(0.0000045 + 0.00027)
    unknown = dict(USAGE, cost_usd=None)  # a model without a price keeps the run's cost unknown, as for nodes
    assert summarize([{"type": "approval_review", "usage": unknown}], 0.0, 1.0)["cost_usd"] is None
