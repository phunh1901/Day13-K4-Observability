from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from .metrics import percentile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_records(log_path: Path, cutoff: datetime) -> tuple[list[dict[str, Any]], int]:
    if not log_path.exists():
        return [], 0

    records: list[dict[str, Any]] = []
    malformed = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and timestamp >= cutoff:
            record["_timestamp"] = timestamp
            records.append(record)
    return records, malformed


def _number_values(records: list[dict[str, Any]], field: str) -> list[float]:
    return [
        float(record[field])
        for record in records
        if isinstance(record.get(field), (int, float))
        and not isinstance(record.get(field), bool)
    ]


def _minute_series(
    records: list[dict[str, Any]], field: str | None = None
) -> list[dict[str, Any]]:
    buckets: dict[str, float] = defaultdict(float)
    for record in records:
        timestamp = record["_timestamp"]
        minute = timestamp.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")
        if field is None:
            buckets[minute] += 1
        elif isinstance(record.get(field), (int, float)):
            buckets[minute] += float(record[field])
    return [
        {"minute": minute, "value": round(value, 6)}
        for minute, value in sorted(buckets.items())
    ]


def _threshold_status(value: float, threshold: dict[str, Any]) -> str:
    objective = float(threshold["value"])
    if threshold["operator"] == "lte":
        return "within" if value <= objective else "breached"
    return "within" if value >= objective else "breached"


def _panel_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {panel["id"]: panel for panel in config["dashboard"]["panels"]}


def build_dashboard_snapshot(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dashboard_config = config["dashboard"]
    panels = _panel_config(config)
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    window_minutes = int(dashboard_config["time_range_minutes"])
    records, malformed = _load_records(
        log_path, generated_at - timedelta(minutes=window_minutes)
    )

    responses = [record for record in records if record.get("event") == "response_sent"]
    requests = [record for record in records if record.get("event") == "request_received"]
    failures = [record for record in records if record.get("event") == "request_failed"]

    latencies = [int(value) for value in _number_values(responses, "latency_ms")]
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    latency_threshold = panels["latency"]["threshold"]

    traffic_series = _minute_series(requests)
    current_rpm = traffic_series[-1]["value"] if traffic_series else 0.0
    traffic_threshold = panels["traffic"]["threshold"]

    error_rate = (len(failures) / len(requests) * 100) if requests else 0.0
    error_breakdown = Counter(
        str(record.get("error_type") or "unknown") for record in failures
    )
    error_threshold = panels["errors"]["threshold"]

    costs = _number_values(responses, "cost_usd")
    total_cost = round(sum(costs), 6)
    cost_threshold = panels["cost"]["threshold"]

    tokens_in = int(sum(_number_values(responses, "tokens_in")))
    tokens_out = int(sum(_number_values(responses, "tokens_out")))
    token_total = tokens_in + tokens_out
    token_threshold = panels["tokens"]["threshold"]

    qualities = _number_values(responses, "quality_score")
    quality_avg = round(mean(qualities), 4) if qualities else 0.0
    quality_threshold = panels["quality"]["threshold"]

    return {
        "title": dashboard_config["title"],
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "time_range_minutes": window_minutes,
        "refresh_seconds": dashboard_config["refresh_seconds"],
        "source": str(log_path),
        "records_in_window": len(records),
        "malformed_lines": malformed,
        "panels": {
            "latency": {
                "title": panels["latency"]["title"],
                "unit": panels["latency"]["unit"],
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "threshold": latency_threshold,
                "status": _threshold_status(p95, latency_threshold),
                "series": [
                    {
                        "timestamp": record["_timestamp"].isoformat().replace("+00:00", "Z"),
                        "value": record.get("latency_ms"),
                    }
                    for record in responses
                    if isinstance(record.get("latency_ms"), (int, float))
                ],
            },
            "traffic": {
                "title": panels["traffic"]["title"],
                "unit": panels["traffic"]["unit"],
                "count": len(requests),
                "rate_per_minute": current_rpm,
                "threshold": traffic_threshold,
                "status": _threshold_status(current_rpm, traffic_threshold),
                "series": traffic_series,
            },
            "errors": {
                "title": panels["errors"]["title"],
                "unit": panels["errors"]["unit"],
                "error_rate_pct": round(error_rate, 4),
                "count": len(failures),
                "breakdown": dict(sorted(error_breakdown.items())),
                "threshold": error_threshold,
                "status": _threshold_status(error_rate, error_threshold),
            },
            "cost": {
                "title": panels["cost"]["title"],
                "unit": panels["cost"]["unit"],
                "total": total_cost,
                "threshold": cost_threshold,
                "status": _threshold_status(total_cost, cost_threshold),
                "series": _minute_series(responses, "cost_usd"),
            },
            "tokens": {
                "title": panels["tokens"]["title"],
                "unit": panels["tokens"]["unit"],
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total": token_total,
                "threshold": token_threshold,
                "status": _threshold_status(token_total, token_threshold),
            },
            "quality": {
                "title": panels["quality"]["title"],
                "unit": panels["quality"]["unit"],
                "mean": quality_avg,
                "threshold": quality_threshold,
                "status": _threshold_status(quality_avg, quality_threshold),
            },
        },
    }


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day 13 AI Observability</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #08111f; color: #e8f0ff; }
    main { max-width: 1240px; margin: auto; padding: 32px; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: end; }
    h1 { margin: 0 0 8px; font-size: 30px; }
    .meta { color: #93a4bf; font-size: 14px; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 24px; }
    .panel { background: #101d30; border: 1px solid #263956; border-radius: 14px; padding: 18px; min-height: 190px; }
    .panel h2 { margin: 0; font-size: 16px; color: #b9c9df; }
    .value { font-size: 34px; font-weight: 700; margin: 18px 0 4px; }
    .detail { color: #93a4bf; line-height: 1.6; font-size: 14px; }
    .threshold { margin-top: 14px; border-top: 1px solid #263956; padding-top: 12px; }
    .within { color: #52d69b; } .breached { color: #ff7b86; }
    svg { width: 100%; height: 56px; margin-top: 12px; overflow: visible; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } header { align-items: start; flex-direction: column; } }
  </style>
</head>
<body><main>
  <header><div><h1 id="title">Day 13 AI Observability</h1><div class="meta" id="source"></div></div><div class="meta" id="updated"></div></header>
  <section class="grid" id="panels"></section>
</main>
<script>
const order = ["latency", "traffic", "errors", "cost", "tokens", "quality"];
const fmt = value => Number(value).toLocaleString(undefined, {maximumFractionDigits: 4});
function thresholdText(panel) {
  const sign = panel.threshold.operator === "lte" ? "≤" : "≥";
  return `${panel.status.toUpperCase()} · SLO ${sign} ${fmt(panel.threshold.value)} ${panel.unit}`;
}
function sparkline(values) {
  if (!values.length) return "";
  const max = Math.max(...values, 1), min = Math.min(...values, 0);
  const points = values.map((v, i) => `${(i / Math.max(values.length - 1, 1)) * 100},${52 - ((v - min) / Math.max(max - min, 1)) * 48}`).join(" ");
  return `<svg viewBox="0 0 100 56" preserveAspectRatio="none"><line x1="0" y1="52" x2="100" y2="52" stroke="#395171"/><polyline fill="none" stroke="#69a7ff" stroke-width="2" vector-effect="non-scaling-stroke" points="${points}"/></svg>`;
}
function panelBody(id, p) {
  if (id === "latency") return [`${fmt(p.p95)} ms`, `P50 ${fmt(p.p50)} · P95 ${fmt(p.p95)} · P99 ${fmt(p.p99)}`, sparkline(p.series.map(x => x.value))];
  if (id === "traffic") return [`${fmt(p.rate_per_minute)} rpm`, `${fmt(p.count)} requests in the last 60 min`, sparkline(p.series.map(x => x.value))];
  if (id === "errors") return [`${fmt(p.error_rate_pct)}%`, `${fmt(p.count)} failures · ${JSON.stringify(p.breakdown)}`, ""];
  if (id === "cost") return [`$${fmt(p.total)}`, `Total USD in the last 60 min`, sparkline(p.series.map(x => x.value))];
  if (id === "tokens") return [`${fmt(p.total)} tokens`, `Input ${fmt(p.tokens_in)} · Output ${fmt(p.tokens_out)}`, ""];
  return [`${fmt(p.mean)}`, `Mean quality score (0–1)`, ""];
}
async function refresh() {
  const response = await fetch("/dashboard/data", {cache: "no-store"});
  const data = await response.json();
  document.getElementById("title").textContent = data.title;
  document.getElementById("source").textContent = `Source: data/logs.jsonl · Range: last ${data.time_range_minutes} min · Refresh: ${data.refresh_seconds}s`;
  document.getElementById("updated").textContent = `Updated ${data.generated_at} · ${data.records_in_window} records`;
  document.getElementById("panels").innerHTML = order.map(id => {
    const p = data.panels[id], body = panelBody(id, p);
    return `<article class="panel"><h2>${p.title}</h2><div class="value">${body[0]}</div><div class="detail">${body[1]}</div>${body[2]}<div class="threshold ${p.status}">${thresholdText(p)}</div></article>`;
  }).join("");
  window.setTimeout(refresh, data.refresh_seconds * 1000);
}
refresh().catch(error => { document.getElementById("updated").textContent = `Dashboard error: ${error}`; });
</script></body></html>"""
