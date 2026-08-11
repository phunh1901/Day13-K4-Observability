# Official challenge investigation evidence

- Challenge: `day13-k4-observability-v1`
- Affected feature: `monitoring`
- Metric symptom: P95 approximately 2650 ms, above the released 2000 ms challenge threshold.
- Langfuse trace: `dfc9e5f03c4310e1d2b37f35bb02e321`; retrieval/RAG accounts for approximately 2.5 seconds.
- Correlated application request: `req-d67985c4`, session `k4-challenge-s01`, `response_sent.latency_ms=2659` at `2026-08-11T09:55:30.230856Z`.
- Root cause: released scenario `rag_slow` activates the 2.5-second retrieval delay in `app/mock_rag.py`.
- Mitigation performed: disable `rag_slow` after evidence capture.
- Proposed code fix: retrieval timeout plus fallback; this proposal is not represented as already implemented.
- Preventive control implemented: `HighTailLatency` early warning at P95 > 2000 ms for five minutes, ahead of the 3000 ms SLO breach.

The submitted `trace-waterfall.png` demonstrates the trace structure but is a
baseline trace, not the challenge trace above. The trace ID and correlated runtime
log record are retained here so the challenge trace can be reopened in Langfuse
during grading.
