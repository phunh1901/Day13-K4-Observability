from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

REQUIRED_EVIDENCE = (
    "submission/evidence/challenge-trace-waterfall.png",
    "submission/evidence/cp2-dashboard.png",
    "submission/evidence/cp2-dashboard-validator.txt",
    "submission/evidence/cp2-log-validator.txt",
    "submission/evidence/log-correlation-pii.jsonl",
    "submission/evidence/prompt-versions.png",
    "submission/evidence/prompt-v1-production-after-rollback.png",
    "submission/evidence/prompt-v2-production-before-rollback.png",
    "submission/evidence/trace-waterfall.png",
    "submission/evidence/traces-list.png",
)
SECRET_PATTERNS = {
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Langfuse secret key": re.compile(r"\bsk-lf-[A-Za-z0-9_-]{10,}\b"),
    "GitHub token": re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def _run(name: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    return {
        "name": name,
        "status": "passed" if result.returncode == 0 else "failed",
        "command": command,
        "returncode": result.returncode,
        "output_tail": output[-2000:],
    }


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return [REPO_ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def _secret_scan() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in _tracked_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative_path = str(path.relative_to(REPO_ROOT))
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append({"file": relative_path, "type": label})
    return {
        "name": "submission file secret scan",
        "status": "passed" if not findings else "failed",
        "findings": findings,
    }


def _evidence_check() -> dict[str, Any]:
    missing = [
        path
        for path in REQUIRED_EVIDENCE
        if not (REPO_ROOT / path).is_file() or (REPO_ROOT / path).stat().st_size == 0
    ]
    return {
        "name": "required evidence files",
        "status": "passed" if not missing else "failed",
        "required": list(REQUIRED_EVIDENCE),
        "missing": missing,
    }


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Run the Day 13 submission gate")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--skip-runtime-logs",
        action="store_true",
        help="Skip validate_logs.py when data/logs.jsonl is unavailable",
    )
    args = parser.parse_args()

    checks = [
        _run("test suite", [sys.executable, "-m", "pytest", "-q"]),
        _run("dashboard contract", [sys.executable, "scripts/validate_dashboard.py"]),
        _run("git diff check", ["git", "diff", "--check"]),
        _secret_scan(),
        _evidence_check(),
    ]
    log_path = REPO_ROOT / "data" / "logs.jsonl"
    if log_path.exists():
        checks.insert(
            2, _run("runtime log validation", [sys.executable, "scripts/validate_logs.py"])
        )
    elif not args.skip_runtime_logs:
        checks.insert(
            2,
            {
                "name": "runtime log validation",
                "status": "failed",
                "reason": "data/logs.jsonl is missing; run the API and load test first",
            },
        )

    passed = all(check["status"] == "passed" for check in checks)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "checks": checks,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
