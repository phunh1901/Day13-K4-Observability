from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import audit
from app.incidents import disable
from app.main import app


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture real control-API audit events as submission evidence"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "bonus-audit-log.jsonl",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()
    audit.AUDIT_LOG_PATH = args.output

    enable_id = f"req-{uuid.uuid4().hex[:8]}"
    disable_id = f"req-{uuid.uuid4().hex[:8]}"
    try:
        with TestClient(app) as client:
            enabled = client.post(
                "/incidents/rag_slow/enable", headers={"x-request-id": enable_id}
            )
            disabled = client.post(
                "/incidents/rag_slow/disable", headers={"x-request-id": disable_id}
            )
    finally:
        disable("rag_slow")

    if enabled.status_code != 200 or disabled.status_code != 200:
        print("Failed to exercise incident control API", file=sys.stderr)
        return 1
    print(f"Wrote two correlated audit events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
