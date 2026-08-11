# Official challenge investigation evidence

- Challenge: `day13-k4-observability-v1`
- Affected feature: `monitoring`
- Metric symptom: P95 approximately 2650 ms, above the released 2000 ms challenge threshold.
- Langfuse trace: `830e202f4edbdb24b6cbea131f32eca0`; generation `run` is 2.652 seconds and child span `rag_retrieve` is 2.501 seconds.
- Correlated application request: `req-55d79463`, session `k4-challenge-s01`, `response_sent.latency_ms=2651` at `2026-08-11T13:36:18.692653Z`.
- Root cause: released scenario `rag_slow` activates the 2.5-second retrieval delay in `app/mock_rag.py`.
- Mitigation performed: disable `rag_slow` after evidence capture.
- Proposed code fix: retrieval timeout plus fallback; this proposal is not represented as already implemented.
- Preventive control implemented: `HighTailLatency` early warning at P95 > 2000 ms for five minutes, ahead of the 3000 ms SLO breach.

The submitted `trace-waterfall.png` demonstrates the baseline trace structure.
The dedicated challenge waterfall with the explicit `rag_retrieve` child span is
stored as `challenge-trace-waterfall.png`. The trace ID and correlated runtime log
record are retained here so the trace can also be reopened in Langfuse during
grading.
