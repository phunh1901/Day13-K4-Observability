# Team Execution Plan

## Team Roles

* **Member A — Logging & PII:** correlation IDs, structured logs, metadata, PII redaction, log evidence.
* **Member B — Tracing & Prompt Versioning:** Langfuse tracing, prompt v1/v2, labels, rollback, trace evidence.
* **Member C — Dashboard & Reliability:** dashboard, metrics, SLOs, alerts, runbooks, metric evidence.

## Checkpoints

### CP0 — Setup and Baseline

**Owners:** A, B, C

* Set up the environment and Langfuse access.
* Run the API, load test, validators, and test suite.
* Record baseline results and confirm `data/logs.jsonl` is generated.

**Exit criteria:** application runs and baseline results are recorded.

### CP1 — Core Implementation

* **A:** implement correlation ID propagation, structured metadata, and PII redaction.
* **B:** verify tracing integration and configure managed prompt versions and labels.
* **C:** implement the six-panel dashboard and draft SLOs, alerts, and runbooks.

**Exit criteria:** each observability pillar works independently.

### CP2 — Validation and Evidence

* **A:** validate logging, verify PII protection, and collect log evidence.
* **B:** create at least 10 traces, verify prompt metadata, perform label switch/rollback, and collect trace evidence.
* **C:** validate all six dashboard panels, finalize SLOs/alerts/runbooks, and collect dashboard evidence.

**Dependency:** C uses validated runtime logs produced by A.

### CP3 — Practice Incident

* **C:** identify the symptom from metrics.
* **B:** identify the abnormal trace or span.
* **A:** confirm the root cause using correlated logs.
* **All:** agree on corrective and preventive actions.

**Exit criteria:** complete Metrics → Traces → Logs → Root Cause investigation.

### CP4 — Official Challenge

Repeat the CP3 investigation flow using the official challenge configuration. Do not modify `config/challenge.json`.

**Exit criteria:** root cause is supported by metric, trace, and log evidence.

### CP5 — Submission and Demo

* **A:** final log validation, PII/secret check, logging report section.
* **B:** trace and prompt-version evidence, tracing report section.
* **C:** dashboard validation, SLO/alert evidence, reliability report section.
* **All:** run the full test suite, verify commit/PR evidence, finalize the report, and rehearse the demo.

**Exit criteria:** tests pass, evidence is complete, and all contributions are traceable.

