from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard import build_dashboard_snapshot


def test_runtime_dashboard_aggregates_all_six_panels(tmp_path: Path) -> None:
    now = datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc)
    records = [
        {"ts": "2026-08-11T07:59:00Z", "event": "request_received"},
        {"ts": "2026-08-11T07:59:01Z", "event": "request_received"},
        {
            "ts": "2026-08-11T07:59:02Z",
            "event": "response_sent",
            "latency_ms": 1000,
            "cost_usd": 0.1,
            "tokens_in": 10,
            "tokens_out": 20,
            "quality_score": 0.9,
        },
        {
            "ts": "2026-08-11T07:59:03Z",
            "event": "response_sent",
            "latency_ms": 4000,
            "cost_usd": 0.2,
            "tokens_in": 30,
            "tokens_out": 40,
            "quality_score": 0.7,
        },
        {
            "ts": "2026-08-11T07:59:04Z",
            "event": "request_failed",
            "error_type": "TimeoutError",
        },
        {"ts": "2026-08-11T05:00:00Z", "event": "request_received"},
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )

    snapshot = build_dashboard_snapshot(log_path, now=now)

    assert set(snapshot["panels"]) == {
        "latency", "traffic", "errors", "cost", "tokens", "quality"
    }
    assert snapshot["records_in_window"] == 5
    assert snapshot["panels"]["latency"]["p95"] == 4000
    assert snapshot["panels"]["latency"]["status"] == "breached"
    assert snapshot["panels"]["traffic"]["count"] == 2
    assert snapshot["panels"]["errors"]["error_rate_pct"] == 50
    assert snapshot["panels"]["errors"]["breakdown"] == {"TimeoutError": 1}
    assert snapshot["panels"]["cost"]["total"] == 0.3
    assert snapshot["panels"]["tokens"]["total"] == 100
    assert snapshot["panels"]["quality"]["mean"] == 0.8


def test_runtime_dashboard_ignores_malformed_and_out_of_window_logs(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        '{"ts":"2026-08-11T07:59:00Z","event":"request_received"}\nnot-json\n',
        encoding="utf-8",
    )

    snapshot = build_dashboard_snapshot(
        log_path, now=datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc)
    )

    assert snapshot["records_in_window"] == 1
    assert snapshot["malformed_lines"] == 1
