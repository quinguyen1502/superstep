"""AI review of a waiting approval (TASK-0187, REQ-0081, DEC-0075 decision 1).

`review()` runs before anyone is asked and returns what to do. The order (REQ-0081 business rules):
kill switches -> rules -> demo -> daily cap -> judge -> threshold.
- Rules: a matching `reject` rule rejects without the judge; a matching `human` rule sends the request to people.
- Auto mode answers only when the judge approves with at least `min_confidence`. The judge's reject, its escalate, a low
  confidence, an `injection` flag, an error, a timeout, an invalid answer, a missing credential, the demo and the daily
  cap all send the request to people (fail-safe). The AI never rejects on its own (owner decision 2).
- Suggest mode never answers: the opinion is shown to people.
Outcomes: approved | rejected | escalated | suggested (None: AI review is paused, people are asked as usual).
"""
from __future__ import annotations
import time
from typing import Any, Callable, Dict, Optional
from ..core import config
from ..core.logging import get_logger
from ..engine import approval_judge, approval_policy

log = get_logger("auto_review")
DAY = 86400


def day_start(now: float) -> float: return now - now % DAY  # UTC midnight: the daily cap counts per workflow per UTC day


class AutoReviewService:
    def __init__(self, repo, switches, resolve: Callable[[str, str], Dict[str, Any]], judge: Callable[..., Dict[str, Any]] = approval_judge.ask,
                 now: Callable[[], float] = time.time):
        """repo: ApprovalRepository; switches: AutoApprovalService; resolve(uid, credential id) -> decrypted credential."""
        self.repo, self.switches, self.resolve, self.judge, self.now = repo, switches, resolve, judge, now

    def paused(self, wid: Optional[str]) -> bool: return self.switches.paused(wid)

    def review(self, owner: str, wid: Optional[str], policy: dict, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.paused(wid): return None
        auto = policy["mode"] == "auto"
        out: Dict[str, Any] = {"mode": policy["mode"], "outcome": "escalated", "decision": None, "confidence": None, "reason": None,
                               "model": None, "rules": [], "cause": None, "policy_hash": approval_policy.policy_hash(policy)}
        def done(outcome=None, **kw):
            out.update(kw); out["outcome"] = outcome or ("escalated" if auto else "suggested"); return out
        effect, hit = approval_policy.check(policy["rules"], request)
        out["rules"] = hit
        if effect == "reject": return done("rejected" if auto else "suggested", decision="reject", confidence=1.0, cause="rule", reason=f"rule {hit[0]}")
        if effect == "human": return done(decision="escalate", cause="rule", reason=f"rule {hit[0]}")
        if config.demo_mode(): return done(cause="demo")  # the demo's models are the offline mock: never answer
        if auto and wid and self.repo.count_auto(wid, day_start(self.now())) >= policy["max_per_day"]: return done(cause="cap")
        j = policy["judge"]
        try: cred = self.resolve(owner, j["credential_id"])
        except Exception: return done(cause="credential")
        out["model"] = j["model"] or None
        try: v = self.judge(j["instructions"], request, j["model"], cred)
        except approval_judge.JudgeError as e: return done(cause=e.cause)
        except Exception: log.exception("AI review failed"); return done(cause="error")
        out.update(decision=v["decision"], confidence=v["confidence"], reason=v["reason"])
        if "injection" in v["flags"]: return done(decision="escalate", cause="injection")
        if not auto: return done()
        if v["decision"] == "approve" and v["confidence"] >= policy["min_confidence"]: return done("approved")
        return done(cause="low_confidence" if v["decision"] == "approve" else f"judge_{v['decision']}")

    def stats(self, wid: str, days: int = 30) -> dict:
        """Per-workflow counts of the last `days` days for the Approvals page."""
        s = self.repo.auto_stats(wid, self.now() - days * DAY)
        agreed, disagreed = s.get("agreed", 0), s.get("disagreed", 0)
        return {"days": days, **{k: s.get(k, 0) for k in ("approved", "rejected", "escalated", "suggested")},
                "agreed": agreed, "disagreed": disagreed, "agreement": round(agreed / (agreed + disagreed), 3) if agreed + disagreed else None,
                "today": self.repo.count_auto(wid, day_start(self.now()))}
