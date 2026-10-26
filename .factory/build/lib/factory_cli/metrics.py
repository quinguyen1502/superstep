from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import FACTORY_CONFIG_PATH, USAGE_SCOPES
from .models import FactoryConfig
from .project import FactoryError, atomic_write, load_config
from .storage import StoreError, UsageRecord, open_store

TableSpec = Tuple[str, List[str], List[List[str]]]
GRANULARITIES = ("day", "week", "month")


@dataclass
class Kpi:
    """A single KPI card with an optional period-over-period delta."""

    label: str
    value: str
    delta: str = ""
    alert: bool = False


@dataclass
class Chart:
    """A comparison chart with numeric series for plotext, bars, or text."""

    title: str
    kind: str  # "bar" | "hbar" | "multi"
    labels: List[str] = field(default_factory=list)
    series: List[List[float]] = field(default_factory=list)
    series_names: List[str] = field(default_factory=list)
    value_fmt: str = "int"  # "int" | "money" | "pct"
    alerts: List[bool] = field(default_factory=list)


@dataclass
class DashboardView:
    """Everything the dashboard renders: KPI cards, charts, and detail tables."""

    summary: List[Kpi] = field(default_factory=list)
    charts: List[Chart] = field(default_factory=list)
    tables: List[TableSpec] = field(default_factory=list)
    granularity: str = "day"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_usage(
    project_dir: Path,
    scope: str,
    ref: str,
    tool_id: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    note: Optional[str] = None,
) -> int:
    if scope not in USAGE_SCOPES:
        raise FactoryError(f"Usage scope must be one of: {', '.join(USAGE_SCOPES)}.")
    if not ref.strip():
        raise FactoryError("Usage --ref must not be empty.")
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    record = UsageRecord(
        scope=scope,
        ref=ref,
        tool_id=tool_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        recorded_at=_now(),
        note=note,
    )
    try:
        store.record_usage(record)
    except StoreError as exc:
        raise FactoryError(str(exc)) from exc
    print(f"Recorded usage: {scope}:{ref} ({record.total_tokens} tokens) via {tool_id}")
    _warn_if_over_budget(config, store, f"{scope}:{ref}")
    return 0


_USAGE_ALIASES = {
    "tool": "tool_id",
    "in": "input_tokens",
    "out": "output_tokens",
    "cost": "cost_usd",
}


def _parse_usage_file(path: Path) -> List[dict]:
    import csv
    import json

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        return list(csv.DictReader(text.splitlines()))
    stripped = text.strip()
    if stripped.startswith("["):
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise FactoryError(f"Usage import must be a JSON array or JSONL: {path}")
        return data
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def import_usage(project_dir: Path, source: str) -> int:
    path = Path(source)
    if not path.is_file():
        raise FactoryError(f"Usage import file not found: {source}")
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    try:
        rows = _parse_usage_file(path)
    except (ValueError, OSError) as exc:
        raise FactoryError(f"Could not parse usage import: {exc}") from exc
    imported = 0
    for raw in rows:
        normalized = {_USAGE_ALIASES.get(key, key): value for key, value in raw.items()}
        record = UsageRecord.from_dict(normalized)
        if record.scope not in USAGE_SCOPES:
            raise FactoryError(
                f"Usage import row has invalid scope: {record.scope!r} "
                f"(must be one of {', '.join(USAGE_SCOPES)})."
            )
        if not record.ref.strip():
            raise FactoryError("Usage import row is missing 'ref'.")
        if not record.recorded_at:
            record.recorded_at = _now()
        try:
            store.record_usage(record)
        except StoreError as exc:
            raise FactoryError(str(exc)) from exc
        imported += 1
    print(f"Imported {imported} usage record(s) from {source}")
    return 0


def capture_usage(
    project_dir: Path,
    tool_id: str,
    ref: str,
    scope: str = "task",
    source: Optional[str] = None,
    note: Optional[str] = None,
) -> int:
    """Parse a coding tool's JSON output and record one usage entry."""
    import sys

    from .usage_capture import normalize_tool_id, parse_tool_usage

    if source:
        path = Path(source)
        if not path.is_file():
            raise FactoryError(f"Tool output file not found: {source}")
        text = path.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    input_tokens, output_tokens, cost_usd = parse_tool_usage(text)
    return record_usage(
        project_dir,
        scope=scope,
        ref=ref,
        tool_id=normalize_tool_id(tool_id),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        note=note,
    )


def _warn_if_over_budget(config: FactoryConfig, store, key: str) -> None:
    limit = config.budgets.get(key)
    if not limit:
        return
    used = store.usage_for_key(key)
    if used > limit:
        print(
            f"Warning: budget for {key} exceeded: {used}/{limit} tokens "
            f"(+{used - limit})."
        )


TOTAL_LABEL = "TOTAL"
_SUMMABLE = {"In", "Out", "Total", "Cost", "Entries"}


def _append_total(columns: List[str], rows: List[List[str]]) -> List[List[str]]:
    """Append a TOTAL row that sums the numeric columns."""
    if not rows:
        return rows
    total = [TOTAL_LABEL] + ["" for _ in columns[1:]]
    for index, column in enumerate(columns):
        if column not in _SUMMABLE:
            continue
        running = 0.0
        for row in rows:
            try:
                running += float(row[index])
            except (ValueError, IndexError):
                pass
        total[index] = f"{running:.4f}" if column == "Cost" else str(int(running))
    return rows + [total]


def _aggregate_rows(store, by: str, config: FactoryConfig) -> Tuple[List[str], List[List[str]]]:
    aggregates = store.aggregate_usage(by="ref" if by == "ref" else by)
    if by == "ref":
        columns = ["Ref", "In", "Out", "Total", "Cost", "Budget", "Remaining"]
        rows = []
        for agg in aggregates:
            limit = config.budgets.get(agg.key)
            budget = str(limit) if limit else "-"
            remaining = str(limit - agg.total_tokens) if limit else "-"
            rows.append(
                [
                    agg.key,
                    str(agg.input_tokens),
                    str(agg.output_tokens),
                    str(agg.total_tokens),
                    f"{agg.cost_usd:.4f}",
                    budget,
                    remaining,
                ]
            )
        return columns, _append_total(columns, rows)
    columns = [by.capitalize(), "In", "Out", "Total", "Cost", "Entries"]
    rows = [
        [
            agg.key,
            str(agg.input_tokens),
            str(agg.output_tokens),
            str(agg.total_tokens),
            f"{agg.cost_usd:.4f}",
            str(agg.entries),
        ]
        for agg in aggregates
    ]
    return columns, _append_total(columns, rows)


def _by_day_rows(store) -> Tuple[List[str], List[List[str]]]:
    """Group usage by calendar day (UTC) from each record's timestamp."""
    from collections import defaultdict

    days: dict = defaultdict(lambda: [0, 0, 0.0, 0])
    for record in store.list_usage():
        day = (record.recorded_at or "")[:10] or "unknown"
        bucket = days[day]
        bucket[0] += int(record.input_tokens)
        bucket[1] += int(record.output_tokens)
        bucket[2] += float(record.cost_usd)
        bucket[3] += 1
    columns = ["Day", "In", "Out", "Total", "Cost", "Entries"]
    rows = []
    for day in sorted(days):
        input_tokens, output_tokens, cost, entries = days[day]
        rows.append(
            [
                day,
                str(input_tokens),
                str(output_tokens),
                str(input_tokens + output_tokens),
                f"{cost:.4f}",
                str(entries),
            ]
        )
    return columns, _append_total(columns, rows)


def _budget_rows(store, config: FactoryConfig) -> Tuple[List[str], List[List[str]]]:
    columns = ["Key", "Limit", "Used", "Remaining", "Status"]
    rows = []
    for key in sorted(config.budgets):
        limit = config.budgets[key]
        used = store.usage_for_key(key)
        remaining = limit - used
        status = "OVER" if used > limit else "ok"
        rows.append([key, str(limit), str(used), str(remaining), status])
    return columns, rows


def build_dashboard_tables(project_dir: Path) -> List[TableSpec]:
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    tables: List[TableSpec] = []
    by_ref_cols, by_ref_rows = _aggregate_rows(store, "ref", config)
    tables.append(("By task/agent", by_ref_cols, by_ref_rows))
    by_tool_cols, by_tool_rows = _aggregate_rows(store, "tool", config)
    tables.append(("By tool", by_tool_cols, by_tool_rows))
    by_day_cols, by_day_rows = _by_day_rows(store)
    tables.append(("By day", by_day_cols, by_day_rows))
    if config.budgets:
        budget_cols, budget_rows = _budget_rows(store, config)
        tables.append(("Budgets", budget_cols, budget_rows))
    return tables


def _bucket_key(recorded_at: str, granularity: str) -> str:
    """Map a timestamp to a day, ISO week, or month bucket label (UTC)."""
    stamp = (recorded_at or "")[:10]
    if not stamp:
        return "unknown"
    if granularity == "month":
        return stamp[:7]
    if granularity == "week":
        try:
            year, week, _ = datetime.fromisoformat(stamp).isocalendar()
            return f"{year}-W{week:02d}"
        except ValueError:
            return "unknown"
    return stamp


def _trend(store, granularity: str) -> Tuple[List[str], List[float], List[float]]:
    from collections import defaultdict

    tokens: dict = defaultdict(int)
    cost: dict = defaultdict(float)
    for record in store.list_usage():
        bucket = _bucket_key(record.recorded_at, granularity)
        tokens[bucket] += record.total_tokens
        cost[bucket] += record.cost_usd
    labels = sorted(tokens)
    return labels, [float(tokens[b]) for b in labels], [cost[b] for b in labels]


def _period_totals(records, granularity: str):
    from collections import defaultdict

    tokens: dict = defaultdict(int)
    cost: dict = defaultdict(float)
    for record in records:
        bucket = _bucket_key(record.recorded_at, granularity)
        tokens[bucket] += record.total_tokens
        cost[bucket] += record.cost_usd
    return tokens, cost


def _delta(current: float, previous: float) -> str:
    if previous <= 0:
        return "▲ new" if current > 0 else "—"
    change = (current - previous) / previous * 100
    if abs(change) < 0.5:
        return "≈ 0%"
    arrow = "▲" if change > 0 else "▼"
    return f"{arrow} {abs(change):.0f}%"


def _summary(store, config: FactoryConfig) -> List[Kpi]:
    records = store.list_usage()
    total_tokens = sum(record.total_tokens for record in records)
    total_cost = sum(record.cost_usd for record in records)
    tracked = len({(record.scope, record.ref) for record in records})
    over_budget = sum(
        1 for key, limit in config.budgets.items() if store.usage_for_key(key) > limit
    )
    # Today vs yesterday, and this week vs last week.
    day_tokens, _day_cost = _period_totals(records, "day")
    today = datetime.now(timezone.utc).date().isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    week_tokens, _week_cost = _period_totals(records, "week")
    iso = datetime.now(timezone.utc).isocalendar()
    this_week = f"{iso[0]}-W{iso[1]:02d}"
    last = (datetime.now(timezone.utc) - timedelta(days=7)).isocalendar()
    last_week = f"{last[0]}-W{last[1]:02d}"
    return [
        Kpi("Total tokens", f"{total_tokens:,}"),
        Kpi("Total cost", f"${total_cost:,.2f}"),
        Kpi("Entries", str(len(records))),
        Kpi(
            "Today (tok)",
            f"{day_tokens.get(today, 0):,}",
            _delta(day_tokens.get(today, 0), day_tokens.get(yesterday, 0)),
        ),
        Kpi(
            "This week (tok)",
            f"{week_tokens.get(this_week, 0):,}",
            _delta(week_tokens.get(this_week, 0), week_tokens.get(last_week, 0)),
        ),
        Kpi("Over budget", str(over_budget), alert=over_budget > 0),
    ]


def _charts(store, config: FactoryConfig, granularity: str) -> List[Chart]:
    charts: List[Chart] = []

    labels, tokens, cost = _trend(store, granularity)
    charts.append(
        Chart(
            f"Tokens by {granularity} (t: day/week/month)",
            "bar",
            labels,
            [tokens],
            ["tokens"],
        )
    )
    charts.append(
        Chart(
            f"Cost by {granularity} (USD)",
            "bar",
            labels,
            [cost],
            ["usd"],
            value_fmt="money",
        )
    )

    top_cost = sorted(
        store.aggregate_usage("ref"), key=lambda agg: agg.cost_usd, reverse=True
    )[:5]
    charts.append(
        Chart(
            "Top task/agent by cost",
            "bar",
            [a.key for a in top_cost],
            [[a.cost_usd for a in top_cost]],
            ["usd"],
            value_fmt="money",
        )
    )

    tools = store.aggregate_usage("tool")
    charts.append(
        Chart(
            "Tokens by tool",
            "bar",
            [a.key for a in tools],
            [[float(a.total_tokens) for a in tools]],
            ["tokens"],
        )
    )

    # Cost per 1K tokens — comparable "unit price" across tools.
    charts.append(
        Chart(
            "Cost per 1K tokens by tool",
            "bar",
            [a.key for a in tools],
            [[(a.cost_usd / a.total_tokens * 1000) if a.total_tokens else 0.0 for a in tools]],
            ["usd/1k"],
            value_fmt="money",
        )
    )

    # Input vs output tokens per tool.
    charts.append(
        Chart(
            "Input vs output by tool",
            "multi",
            [a.key for a in tools],
            [
                [float(a.input_tokens) for a in tools],
                [float(a.output_tokens) for a in tools],
            ],
            ["in", "out"],
        )
    )

    # Budget burn — used as a percentage of each limit.
    if config.budgets:
        keys = sorted(config.budgets)
        percents = []
        alerts = []
        for key in keys:
            limit = config.budgets[key]
            used = store.usage_for_key(key)
            pct = (used / limit * 100) if limit else 0.0
            percents.append(pct)
            alerts.append(used > limit)
        charts.append(
            Chart(
                "Budget burn (% of limit)",
                "hbar",
                keys,
                [percents],
                ["% used"],
                value_fmt="pct",
                alerts=alerts,
            )
        )

    return charts


def build_dashboard(project_dir: Path, granularity: str = "day") -> DashboardView:
    if granularity not in GRANULARITIES:
        granularity = "day"
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    return DashboardView(
        summary=_summary(store, config),
        charts=_charts(store, config, granularity),
        tables=build_dashboard_tables(project_dir),
        granularity=granularity,
    )


def _render_text_table(title: str, columns: List[str], rows: List[List[str]]) -> str:
    widths = [len(col) for col in columns]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    header = "  ".join(col.ljust(widths[index]) for index, col in enumerate(columns))
    lines = [title, header, "  ".join("-" * width for width in widths)]
    if not rows:
        lines.append("(no records)")
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return "\n".join(lines)


def render_usage_text(project_dir: Path, by: str) -> str:
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    if by == "budget":
        columns, rows = _budget_rows(store, config)
        return _render_text_table("Budgets", columns, rows)
    columns, rows = _aggregate_rows(store, by, config)
    return _render_text_table(f"Usage by {by}", columns, rows)


def _render_summary_text(summary: List[Kpi]) -> str:
    cells = []
    for kpi in summary:
        cell = f"{kpi.label}: {kpi.value}"
        if kpi.delta:
            cell += f" ({kpi.delta})"
        cells.append(cell)
    return "Summary\n" + "   ".join(cells)


def _fmt_value(value: float, value_fmt: str) -> str:
    if value_fmt == "money":
        return f"${value:,.4f}"
    if value_fmt == "pct":
        return f"{value:.0f}%"
    return f"{int(round(value)):,}"


def _unicode_bar(value: float, maximum: float, width: int = 24) -> str:
    if maximum <= 0:
        return ""
    filled = max(0, min(width, int(round(width * value / maximum))))
    return "█" * filled + "░" * (width - filled)


def render_chart_text(chart: Chart) -> str:
    """Render a chart as Unicode bars for the text fallback / non-TTY mode."""
    if not chart.labels:
        return f"{chart.title}\n(no records)"
    label_width = max(len(label) for label in chart.labels)
    lines = [chart.title]
    if chart.kind == "multi":
        for index, label in enumerate(chart.labels):
            parts = [
                f"{name} {_fmt_value(chart.series[s][index], chart.value_fmt)}"
                for s, name in enumerate(chart.series_names)
            ]
            lines.append(f"{label.ljust(label_width)}  " + "  ".join(parts))
        return "\n".join(lines)
    values = chart.series[0]
    maximum = max(values) if values else 0
    for index, label in enumerate(chart.labels):
        bar = _unicode_bar(values[index], maximum)
        marker = "  OVER" if chart.alerts and chart.alerts[index] else ""
        lines.append(
            f"{label.ljust(label_width)}  {bar}  "
            f"{_fmt_value(values[index], chart.value_fmt)}{marker}"
        )
    return "\n".join(lines)


def render_dashboard_text(project_dir: Path, granularity: str = "day") -> str:
    view = build_dashboard(project_dir, granularity)
    parts = [_render_summary_text(view.summary)]
    parts.extend(render_chart_text(chart) for chart in view.charts)
    parts.extend(
        _render_text_table(title, columns, rows) for title, columns, rows in view.tables
    )
    return "\n\n".join(parts)


# -- budgets (stored on FactoryConfig) ---------------------------------------


def metrics_problems(project_dir: Path) -> Tuple[List[str], List[str]]:
    """Validate the storage backend reachability and metrics integrity."""
    errors: List[str] = []
    warnings: List[str] = []
    config_path = project_dir / FACTORY_CONFIG_PATH
    if not config_path.is_file():
        return errors, warnings
    try:
        config = FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return errors, warnings  # config problems are reported by validate itself
    try:
        store = open_store(project_dir, config)
        store.list_usage()
    except Exception as exc:  # noqa: BLE001 - any backend failure is a finding
        # A shared Postgres mirror may simply be offline during validation.
        if config.storage_backend == "folder+postgres":
            warnings.append(f"storage mirror unreachable: {exc}")
        else:
            errors.append(f"storage backend error: {exc}")
    return errors, warnings


def set_budget(project_dir: Path, key: str, limit: int) -> int:
    config = load_config(project_dir)
    scope = key.split(":", 1)[0] if ":" in key else ""
    if scope not in USAGE_SCOPES:
        raise FactoryError(
            "Budget key must look like 'task:TASK-0001' or 'agent:developer'."
        )
    if limit < 0:
        raise FactoryError("Budget limit must be a non-negative integer.")
    config.budgets[key] = limit
    try:
        config.validate()
    except ValueError as exc:
        raise FactoryError(str(exc)) from exc
    atomic_write(project_dir / FACTORY_CONFIG_PATH, config.to_yaml())
    print(f"Set budget {key} = {limit} tokens")
    return 0


def remove_budget(project_dir: Path, key: str) -> int:
    config = load_config(project_dir)
    if key not in config.budgets:
        raise FactoryError(f"No budget set for: {key}")
    del config.budgets[key]
    atomic_write(project_dir / FACTORY_CONFIG_PATH, config.to_yaml())
    print(f"Removed budget {key}")
    return 0


def list_budgets(project_dir: Path) -> int:
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    columns, rows = _budget_rows(store, config)
    print(f"Budget enforcement: {config.budget_enforcement}")
    print(_render_text_table("Budgets", columns, rows))
    return 0
