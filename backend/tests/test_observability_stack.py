"""Compose observability profile: the dashboard and alert rules parse and only use metrics and labels the backend emits."""
import json
import re
from pathlib import Path
import yaml
from app.services import telemetry

ROOT = Path(__file__).resolve().parents[2]
OBS = ROOT / "deploy" / "observability"
DASHBOARD = OBS / "grafana" / "dashboards" / "superstep.json"
RULES = OBS / "grafana" / "provisioning" / "alerting" / "rules.yaml"
# Prometheus names: dots become underscores; the collector adds no unit or _total suffix (add_metric_suffixes: false).
SERIES = re.compile(r"\bstudio_[a-z0-9_]+")
GROUPING = re.compile(r"\b(?:by|without)\s*\(([^)]*)\)")
MATCHER = re.compile(r"\{([^}]*)\}")
EXTRA_LABELS = {"le", "instance", "job"}


def emitted() -> set[str]:
    """Metric names created in the telemetry module (instruments and observable gauges)."""
    src = Path(telemetry.__file__).read_text()
    names = re.findall(r'(?:create_[a-z_]+|gauge)\(\s*"(studio\.[a-z0-9_.]+)"', src)
    return {n.replace(".", "_") for n in names}


def check(expr: str, known: set[str]) -> list[str]:
    bad = []
    for s in SERIES.findall(expr):
        base = re.sub(r"_(bucket|sum|count)$", "", s)
        if s not in known and base not in known: bad.append(s)
    used = {x.strip() for g in GROUPING.findall(expr) for x in g.split(",") if x.strip()}
    used |= {m.split("=")[0].strip(" !~") for g in MATCHER.findall(expr) for m in g.split(",") if "=" in m}
    bad += sorted(f"label {x}" for x in used - telemetry.LABELS - EXTRA_LABELS)
    return bad


def exprs_of(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "expr" and isinstance(v, str): yield v
            else: yield from exprs_of(v)
    elif isinstance(obj, list):
        for v in obj: yield from exprs_of(v)


def test_emitted_names_are_found():
    names = emitted()
    for n in ("studio_runs", "studio_http_server_duration", "studio_queue_depth", "studio_schedules_overdue", "studio_process_cpu_time"):
        assert n in names


def test_dashboard_uses_emitted_metrics_only():
    d = json.loads(DASHBOARD.read_text())
    exprs = list(exprs_of(d["panels"]))
    assert len(exprs) > 30
    known = emitted(); bad = {e: check(e, known) for e in exprs if check(e, known)}
    assert bad == {}
    used = {re.sub(r"_(bucket|sum|count)$", "", s) for e in exprs for s in SERIES.findall(e)}
    # every gauge and counter that matters for operators has a panel
    assert {"studio_ready_db", "studio_ready_redis", "studio_worker_heartbeat_age", "studio_llm_unpriced", "studio_llm_fallbacks",
            "studio_approvals_waiting", "studio_webhooks_failed", "studio_schedules_disabled"} <= used
    assert all(p.get("datasource", {}).get("uid") in (None, "prometheus") for p in d["panels"])


def test_alert_rules_cover_the_minimum_list():
    doc = yaml.safe_load(RULES.read_text())
    rules = doc["groups"][0]["rules"]
    titles = {r["title"] for r in rules}
    assert {"Instance down", "Database down", "Redis down", "HTTP 5xx share", "Queue backlog (depth)", "Queue backlog (oldest run)",
            "Worker missing", "Run error rate", "Provider auth or unreachable", "Daily cost", "Overdue schedules", "Webhook failures",
            "In-memory run bus"} <= titles
    known = emitted()
    for r in rules:
        assert len(r["uid"]) <= 40 and re.fullmatch(r"[A-Za-z0-9_-]+", r["uid"])
        assert r["condition"] == "C"
        expr = r["data"][0]["model"]["expr"]; assert check(expr, known) == [], r["title"]
        threshold = r["data"][2]["model"]["conditions"][0]["evaluator"]["params"][0]
        assert isinstance(threshold, (int, float))  # anchors in x-thresholds resolved to numbers
        assert "$" not in json.dumps(r)  # Grafana would try to expand it
    assert set(doc["x-thresholds"]) >= {"queue_depth", "daily_cost_usd", "worker_heartbeat_age_s"}


def test_compose_profile_is_wired():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    svc = compose["services"]
    for name in ("otel-collector", "prometheus", "grafana", "jaeger"):
        assert "observability" in svc[name]["profiles"]
        image = svc[name]["image"]; assert ":" in image and not image.endswith(":latest")
        for v in svc[name].get("volumes", []):
            src = v.split(":")[0]
            if src.startswith("./"): assert (ROOT / src).exists(), src
    assert svc["grafana"]["ports"][0].startswith("127.0.0.1:")  # the default password is for local use only
    env = (OBS / "observability.env").read_text()
    assert "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318" in env and "STUDIO_OTEL_METRICS=1" in env
    for key in ("STUDIO_OTEL_METRICS", "OTEL_METRIC_EXPORT_INTERVAL", "STUDIO_GRAFANA_URL"):
        assert key in svc["api"]["environment"] and key in svc["worker"]["environment"]
    col = yaml.safe_load((OBS / "otel-collector.yaml").read_text())
    assert col["exporters"]["prometheus"]["add_metric_suffixes"] is False
    port = col["exporters"]["prometheus"]["endpoint"].rsplit(":", 1)[1]
    prom = yaml.safe_load((OBS / "prometheus.yml").read_text())
    assert prom["scrape_configs"][0]["static_configs"][0]["targets"] == [f"otel-collector:{port}"]
