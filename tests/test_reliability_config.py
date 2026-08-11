from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_slo_objectives_match_dashboard_thresholds() -> None:
    dashboard = _load_yaml("config/dashboard.yaml")["dashboard"]
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    slis = _load_yaml("config/slo.yaml")["slis"]

    assert slis["latency_p95_ms"]["objective"] == panels["latency"]["threshold"]["value"]
    assert slis["error_rate_pct"]["objective"] == panels["errors"]["threshold"]["value"]
    assert slis["daily_cost_usd"]["objective"] == panels["cost"]["threshold"]["value"]
    assert slis["quality_score_avg"]["objective"] == panels["quality"]["threshold"]["value"]
    assert all(sli.get("note") for sli in slis.values())


def test_alert_rules_are_actionable_and_link_to_runbooks() -> None:
    alerts = _load_yaml("config/alert_rules.yaml")["alerts"]
    runbooks = (REPO_ROOT / "docs" / "alerts.md").read_text(encoding="utf-8")

    assert len(alerts) == 3
    for index, alert in enumerate(alerts, start=1):
        assert alert["severity"] in {"warning", "critical"}
        assert alert["condition"]
        assert alert["type"] == "symptom-based"
        assert alert["owner"]
        assert alert["runbook"] == f"docs/alerts.md#alert-{index}"
        assert f"## Alert {index}" in runbooks
        assert alert["name"] in runbooks
