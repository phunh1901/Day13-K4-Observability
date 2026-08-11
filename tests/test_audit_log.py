from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import audit
from app.incidents import disable
from app.main import app


def test_incident_control_writes_separate_correlated_audit_log(
    monkeypatch, tmp_path: Path
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", audit_path)

    with TestClient(app) as client:
        enabled = client.post(
            "/incidents/rag_slow/enable", headers={"x-request-id": "req-a1b2c3d4"}
        )
        disabled = client.post(
            "/incidents/rag_slow/disable", headers={"x-request-id": "req-e5f6a7b8"}
        )

    disable("rag_slow")
    assert enabled.status_code == 200
    assert disabled.status_code == 200
    records = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["action"] for record in records] == [
        "incident.enable",
        "incident.disable",
    ]
    assert records[0]["correlation_id"] == "req-a1b2c3d4"
    assert records[1]["correlation_id"] == "req-e5f6a7b8"
    assert all(record["actor"] == "control-api" for record in records)


def test_audit_log_scrubs_pii(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", audit_path)

    audit.write_audit_event(
        action="test",
        resource="incident/student@example.com",
        outcome="denied",
        correlation_id="req-12345678",
        details={"contact": "090 123 4567"},
    )

    content = audit_path.read_text(encoding="utf-8")
    assert "student@example.com" not in content
    assert "090 123 4567" not in content
    assert "REDACTED_EMAIL" in content
    assert "REDACTED_PHONE_VN" in content
