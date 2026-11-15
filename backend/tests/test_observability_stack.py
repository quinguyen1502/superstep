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
COLLECTOR = OBS / "otel-collector.yaml"
# Postgres and Redis server metrics come from collector receivers, not the backend: the receivers' own names (OTel
# contrib 0.114, default or enabled in the collector config) plus the sqlquery metrics defined there.
RECEIVER_SERIES = re.compile(r"\b(?:postgresql|redis)_[a-z0-9_]+")
RECEIVER_METRICS = {"postgresql_backends", "postgresql_connection_max", "postgresql_commits", "postgresql_rollbacks", "postgresql_deadlocks",
                    "postgresql_db_size", "redis_memory_used", "redis_maxmemory", "redis_clients_connected", "redis_commands",
                    "redis_keys_evicted", "redis_db_keys"}
RECEIVER_LABELS = {"state", "db"}


def emitted() -> set[str]:
    """Metric names created in the telemetry module (instruments and observable gauges)."""
    src = Path(telemetry.__file__).read_text()
    names = re.findall(r'(?:create_[a-z_]+|gauge)\(\s*"(studio\.[a-z0-9_.]+)"', src)
    return {n.replace(".", "_") for n in names}


def receiver_metrics() -> set[str]:
    col = yaml.safe_load(COLLECTOR.read_text())
    sql = {m["metric_name"].replace(".", "_") for q in col["receivers"]["sqlquery/postgres"]["queries"] for m in q["metrics"]}
    return RECEIVER_METRICS | sql


def check(expr: str, known: set[str]) -> list[str]:
    bad = []
    for s in SERIES.findall(expr):
        base = re.sub(r"_(bucket|sum|count)$", "", s)
        if s not in known and base not in known: bad.append(s)
    servers = RECEIVER_SERIES.findall(expr)
    bad += [s for s in servers if s not in receiver_metrics()]
    used = {x.strip() for g in GROUPING.findall(expr) for x in g.split(",") if x.strip()}
    used |= {m.split("=")[0].strip(" !~") for g in MATCHER.findall(expr) for m in g.split(",") if "=" in m}
    recording_labels = {"window", "objective"} if "superstep:slo_" in expr else set()
    bad += sorted(f"label {x}" for x in used - telemetry.LABELS - EXTRA_LABELS - recording_labels - (RECEIVER_LABELS if servers else set()))
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
            "studio_approvals_waiting", "studio_webhooks_failed", "studio_schedules_disabled", "studio_db_pool_in_use"} <= used
    servers = {s for e in exprs for s in RECEIVER_SERIES.findall(e)}
    assert {"postgresql_activity_connections", "postgresql_commits", "postgresql_deadlocks", "postgresql_cache_hits", "postgresql_db_size",
            "redis_memory_used", "redis_clients_connected", "redis_commands", "redis_keys_evicted", "redis_db_keys"} <= servers
    assert all(p.get("datasource", {}).get("uid") in (None, "prometheus") for p in d["panels"])


def test_alert_rules_cover_the_minimum_list():
    doc = yaml.safe_load(RULES.read_text())
    rules = doc["groups"][0]["rules"]
    titles = {r["title"] for r in rules}
    assert {"Instance down", "Database down", "Redis down", "HTTP 5xx share", "Queue backlog (depth)", "Queue backlog (oldest run)",
            "Worker missing", "Run error rate", "Provider auth or unreachable", "Daily cost", "Overdue schedules", "Webhook failures",
            "In-memory run bus", "Postgres connections near limit", "Redis memory pressure"} <= titles
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


def test_collector_reads_postgres_and_redis_without_committed_credentials():
    col = yaml.safe_load(COLLECTOR.read_text())
    rec = col["receivers"]
    assert col["service"]["pipelines"]["metrics"]["receivers"] == ["otlp", "postgresql", "sqlquery/postgres", "redis"]
    assert rec["postgresql"]["username"] == "${env:POSTGRES_MONITOR_USER}" and rec["postgresql"]["password"] == "${env:POSTGRES_MONITOR_PASSWORD}"
    assert "password=${env:POSTGRES_MONITOR_PASSWORD}" in rec["sqlquery/postgres"]["datasource"]
    assert rec["postgresql"]["metrics"]["postgresql.deadlocks"]["enabled"] and rec["redis"]["metrics"]["redis.maxmemory"]["enabled"]
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]
    env = compose["otel-collector"]["environment"]
    assert env["POSTGRES_MONITOR_PASSWORD"] == "${POSTGRES_MONITOR_PASSWORD:-}" and env["REDIS_MONITOR_ENDPOINT"] == "redis:6379"
    mon = compose["postgres-monitor"]
    assert mon["profiles"] == ["observability"] and mon["environment"]["MONITOR_PASSWORD"] == "${POSTGRES_MONITOR_PASSWORD:-}"
    script = (OBS / "postgres-monitor.sh").read_text()
    assert "GRANT pg_monitor" in script and "exit 0" in script  # read-only role; skipped without a password
    for line in (ROOT / ".env.example").read_text().splitlines():
        if line.startswith("POSTGRES_MONITOR_PASSWORD="): assert line == "POSTGRES_MONITOR_PASSWORD="


HANDBOOK = ROOT / "handbook" / "docs"
LANGS = ("en", "vi")


def page(lang: str) -> str:
    return (HANDBOOK / lang / "operate" / "observability.md").read_text()


def handbook_alerts(lang: str) -> list[str]:
    """First column of the alert table: the table that holds the "Instance down" row (rule titles are English in both)."""
    lines = page(lang).splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("| Instance down |"))
    start = at
    while lines[start - 1].startswith("|"): start -= 1
    end = at
    while end < len(lines) and lines[end].startswith("|"): end += 1
    return [line.split("|")[1].strip() for line in lines[start + 2:end]]


def test_handbook_alert_list_matches_the_provisioned_rules():
    titles = [r["title"] for r in yaml.safe_load(RULES.read_text())["groups"][0]["rules"]]
    for lang in LANGS:
        assert sorted(handbook_alerts(lang)) == sorted(titles), lang


def test_handbook_names_only_emitted_metrics():
    names = {n.replace("_", ".") for n in emitted()}
    for lang in LANGS:
        named = set(re.findall(r"`(studio\.[a-z0-9_.]+)`", page(lang)))
        missing = {n for n in named if n not in names and n.replace(".", "_") not in emitted()}
        assert missing == set(), lang
    titles = [p["title"] for p in json.loads(DASHBOARD.read_text())["panels"] if p["type"] == "row"]
    assert titles == ["Server", "Database and Redis", "Queue and workers", "Runs and models", "Integrations and limits", "Product health"]
    for lang in LANGS:
        assert all(f"| {t} |" in page(lang) for t in titles), lang
