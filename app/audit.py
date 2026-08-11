from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pii import scrub_text


AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
_WRITE_LOCK = threading.Lock()


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def write_audit_event(
    *,
    action: str,
    resource: str,
    outcome: str,
    correlation_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": "audit_event",
        "actor": "control-api",
        "action": action,
        "resource": resource,
        "outcome": outcome,
        "correlation_id": correlation_id,
        "details": details or {},
    }
    safe_record = _sanitize(record)
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(safe_record, ensure_ascii=False, sort_keys=True)
    with _WRITE_LOCK:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(rendered + "\n")
    return safe_record
