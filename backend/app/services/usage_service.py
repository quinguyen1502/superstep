"""Admin Usage page: runs, tokens and estimated cost over a window, top workflows, and product health counts.

Cost is an estimate from the price table (engine/usage.py, STUDIO_PRICES): a finished run whose model has no known
price has no cost and counts as unpriced, so every cost figure comes with the unpriced share. Child runs of workflow
tools are part of their parent run and are not counted on their own.
"""
from __future__ import annotations
import time
from typing import Optional
from ..core import config
from ..core import permissions as P
from ..core.errors import AppError

WINDOWS = {"24h": 24 * 3600, "7d": 7 * 86400, "30d": 30 * 86400}
BUCKETS = {"hour": 3600, "day": 86400}
DEFAULT_BUCKET = {"24h": "hour", "7d": "day", "30d": "day"}
SERIES_STATUSES = ("ok", "error", "timeout", "cancelled")
SCHEDULE_GRACE = 300  # seconds an enabled schedule may be late before it counts as overdue
HEALTH_WINDOW = 3600  # seconds of failed deliveries and expired approvals the gauges count
PEOPLE_LIMIT = 20  # rows of the per-user and per-team tables
DELETED_DOMAIN = "@deleted.invalid"  # address of an anonymised account (UserDataRepository.anonymise)


def _age(ts: Optional[float], now: float) -> Optional[float]: return round(max(0.0, now - ts), 1) if ts else None


class UsageService:
    def __init__(self, repo, access=None):
        self.repo, self.access = repo, access

    def _window(self, uid: str, window: str) -> tuple[float, float]:
        if self.access is not None: self.access.require(uid, P.USERS_MANAGE)
        if window not in WINDOWS: raise AppError("VALIDATION_ERROR", details=[{"field": "window", "message": "use 24h, 7d or 30d"}])
        until = time.time(); return until - WINDOWS[window], until

    def summary(self, uid: str, window: str = "7d", bucket: Optional[str] = None, sort: str = "runs") -> dict:
        since, until = self._window(uid, window)
        bucket = bucket or DEFAULT_BUCKET[window]
        if bucket not in BUCKETS: raise AppError("VALIDATION_ERROR", details=[{"field": "bucket", "message": "use hour or day"}])
        if sort not in ("runs", "cost"): raise AppError("VALIDATION_ERROR", details=[{"field": "sort", "message": "use runs or cost"}])
        size = BUCKETS[bucket]; t = self.repo.totals(since, until)
        by = t["by_status"]; runs = sum(by.values()); finished = sum(by.get(s, 0) for s in SERIES_STATUSES)
        n = int((until - since) // size) + (1 if (until - since) % size else 0)
        series = [{"start": since + i * size, **{s: 0 for s in SERIES_STATUSES}, "other": 0} for i in range(n)]
        for i, status, count in self.repo.series(since, until, size):
            if i >= 0: series[min(i, n - 1)][status if status in SERIES_STATUSES else "other"] += count  # rounding at the edge
        top = self.repo.top_workflows(since, until, 10, sort)
        for w in top: w["error_rate"] = round(w["errors"] / w["runs"], 4) if w["runs"] else None
        users = self.repo.users(since, until, sort, PEOPLE_LIMIT)
        for u in users: u["deleted"] = not u["email"] or u["email"].endswith(DELETED_DOMAIN)
        if any(u["deleted"] for u in users):
            for u in users:
                if u["deleted"]: u["email"] = None  # shown as a placeholder; anonymised addresses are not shown
        return {"window": window, "bucket": bucket, "bucket_seconds": size, "since": since, "until": until,
                "totals": {"runs": runs, "by_status": by, "success_rate": round(by.get("ok", 0) / finished, 4) if finished else None,
                           "tokens_in": t["tokens_in"], "tokens_out": t["tokens_out"], "cost_usd": round(t["cost_usd"], 6),
                           "unpriced_runs": t["unpriced_runs"], "unpriced_share": round(t["unpriced_runs"] / finished, 4) if finished else None},
                "series": series, "top_workflows": top, "grafana_url": config.grafana_url() or None,
                "models": self.repo.models(since, until), "models_since": self.repo.usage_since(),
                "users": users, "teams": self.repo.teams(since, until, sort, PEOPLE_LIMIT),
                "teams_shared_members": self.repo.shared_members(since, until), "slo": self.slo(until)}

    def slo(self, until: float) -> dict:
        run_target, api_target = config.slo_targets()
        total, ok = self.repo.run_slo(until - WINDOWS["30d"], until)
        observed = ok / total if total else None
        remaining = max(0.0, 1 - (1 - observed) / (1 - run_target)) if observed is not None else None
        return {"run_target": run_target, "run_observed": observed, "run_samples": total,
                "run_budget_remaining": remaining, "api_target": api_target}

    def health(self, uid: str, window: str = "7d") -> dict:
        since, until = self._window(uid, window)
        return self.counts(since, until)

    def channels(self, since: float, until: float) -> dict:
        """Chat trigger refusals by code and platform, and the refusal share of messages that were decided."""
        c = self.repo.chat_refusals(since, until); refused = sum(r["count"] for r in c["refused"])
        decided = refused + c["started"]
        return {**c, "refused_total": refused, "refusal_share": round(refused / decided, 4) if decided else None}

    def counts(self, since: float, now: Optional[float] = None) -> dict:
        """Product health: waiting and expired approvals, failed and retrying webhook deliveries, overdue schedules,
        schedules the scheduler turned off (with its note) and refused chat trigger messages. No permission check: the worker's gauges use it."""
        now = now or time.time()
        a = self.repo.approvals(since); w = self.repo.webhooks(since); s = self.repo.schedules(now - SCHEDULE_GRACE)
        return {"approvals": {"waiting": a["waiting"], "oldest_age_s": _age(a["oldest_created"], now), "expired": a["expired"]},
                "webhooks": w, "schedules": {"overdue": s["overdue"], "disabled": s["disabled"], "disabled_list": s["disabled_list"]},
                "channels": self.channels(since, now)}

    def gauges(self) -> dict:
        """Counts the worker exports as gauges (failed deliveries and expired approvals of the last hour)."""
        now = time.time()
        return {**self.counts(now - HEALTH_WINDOW, now), "browsers": {"active": self.repo.active_browsers(now)}}
