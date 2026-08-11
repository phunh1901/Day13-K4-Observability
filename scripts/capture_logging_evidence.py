from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

REQUIRED_CONTEXT = {
    "correlation_id",
    "user_id_hash",
    "session_id",
    "feature",
    "model",
}


def _records(path: Path) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            parsed.append(value)
    return parsed


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Capture real correlation-ID and PII-redaction log evidence"
    )
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("submission/evidence/log-correlation-pii.jsonl"),
    )
    args = parser.parse_args()

    if not args.logs.is_file():
        print(f"Error: {args.logs} does not exist", file=sys.stderr)
        return 1

    records = _records(args.logs)
    redacted = next(
        (
            record
            for record in records
            if record.get("service") == "api"
            and record.get("event") == "request_received"
            and "[REDACTED_" in json.dumps(record, ensure_ascii=False)
            and REQUIRED_CONTEXT.issubset(record)
        ),
        None,
    )
    if redacted is None:
        print(
            "Error: no enriched request_received record with redacted PII was found",
            file=sys.stderr,
        )
        return 1

    correlation_id = redacted["correlation_id"]
    response = next(
        (
            record
            for record in records
            if record.get("service") == "api"
            and record.get("event") == "response_sent"
            and record.get("correlation_id") == correlation_id
            and REQUIRED_CONTEXT.issubset(record)
        ),
        None,
    )
    if response is None:
        print(
            f"Error: no response_sent record matches correlation ID {correlation_id}",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True)
        for record in (redacted, response)
    )
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(f"Captured 2 sanitized records for {correlation_id} in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
