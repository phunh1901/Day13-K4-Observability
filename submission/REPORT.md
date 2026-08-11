# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Nhóm LPV
- Repository URL: https://github.com/phunh1901/Day13-K4-Observability-LPV
- Commit SHA cuối: 975d592
- Thành viên và vai trò:
  - Ngô Hoàng Phú: Role A — Logging & PII (Correlation ID, Context Metadata, PII Redaction)
  - Đinh Quốc Việt: Role B — Tracing & Prompt Versioning (Langfuse Traces, Prompt v1/v2, Version Labels & Rollback)
  - Nguyễn Trung Long: Role C — Dashboard, SLO & Alerts (6 Panel Dashboard, SLOs, Alert Rules & Runbook)

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 sau khi merge Role A CP1 (`submission/evidence/cp2-log-validator.txt`)
- Tổng số traces: > 10 (ghi nhận 264+ traces trên Langfuse)
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `/dashboard`; runtime data `/dashboard/data`; snapshot `submission/evidence/cp2-dashboard-runtime.json`


### Baseline trước khi merge Role A CP1

--- Lab Verification Results ---
Total log records analyzed: 21
Records with missing required fields: 20
Records with missing enrichment (context): 20
Unique correlation IDs found: 0
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
- [FAILED] Missing required fields (ts, level, etc.)
- [FAILED] Correlation ID propagation (less than 2 unique IDs)
- [FAILED] Log enrichment (missing user_id_hash, etc.)
+ [PASSED] PII scrubbing

Estimated Score: 30/100



### After merge Role A CP1
--- Lab Verification Results ---
Total log records analyzed: 21
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 10
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing

Estimated Score: 100/100

## 3. Logging và tracing

- Evidence correlation ID: `{"service": "api", "event": "request_received", "correlation_id": "req-2e63ddb0", "user_id_hash": "2055254ee30a", "session_id": "s01", "feature": "qa", "model": "claude-sonnet-4-5", "env": "dev"}`
- Evidence PII redaction: `{"payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "correlation_id": "req-2e63ddb0"}`
- Evidence trace waterfall: ![Trace Waterfall](./evidence/trace-waterfall.png)
- Giải thích một span đáng chú ý: Span `run` thể hiện toàn bộ quy trình sinh câu trả lời của agent, đo lường latency (0.15s), tính toán chi phí ($0.001794), gắn nhãn session/user_id_hash và trích xuất đúng prompt managed `day13-chat` v1 từ Langfuse.

## 4. Prompt versioning

- Prompt name: day13-chat
- Version/label baseline: v1 (production)
- Version/label candidate: v2 (candidate)
- Trace ID của mỗi version:
  - Baseline (v1 / production): `b9c4549e9a7ddd85cb9e4715d37aee27`
  - Candidate (v2 / candidate): `29936f94fca5f071e230b77d574cf0c2`
- Bằng chứng đổi label hoặc rollback: Đã kiểm chứng chuyển label từ `production` (v1) sang `candidate` (v2) và rollback về `production` (v1). Trace metadata trên Langfuse ghi nhận chính xác `prompt_version` và `prompt_label` tương ứng.
![Prompt Versions](./evidence/prompt-versions.png)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel`; xem `submission/evidence/cp2-dashboard-validator.txt`.
- Evidence dashboard: `submission/evidence/cp2-dashboard-runtime.json` chứa dữ liệu thật của đủ sáu panel trong cửa sổ 60 phút. Ảnh UI cần lưu thành `submission/evidence/cp2-dashboard.png`.
- SLO đã chọn và lý do: P95 <= 3000 ms, error rate <= 2%, daily cost <= 2.50 USD và quality trung bình >= 0.75. Các ngưỡng phản ánh tail latency, độ tin cậy, ngân sách và chất lượng đầu ra; cùng giá trị được dùng trong dashboard và `config/slo.yaml`.
- Alert rules và runbook: `config/alert_rules.yaml` có HighTailLatency, HighRequestErrorRate và DailyCostBudgetRisk; owner, duration, user impact, bước điều tra và mitigation nằm trong `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1`
- Triệu chứng từ metrics: Tail latency P95 tăng đột biến vượt ngưỡng 2000ms (đạt ~2650ms), tập trung chủ yếu ở các request thuộc feature `monitoring`.
- Trace ID liên quan: `dfc9e5f03c4310e1d2b37f35bb02e321` (trên Langfuse hiển thị span RAG/retrieval chiếm ~2.5s).
- Log line/correlation ID liên quan: `correlation_id: req-d67985c4`
  ```json
  {"service": "api", "latency_ms": 2659, "tokens_in": 35, "tokens_out": 160, "cost_usd": 0.002505, "quality_score": 0.8, "payload": {"answer_preview": "Starter answer. Teams should improve this output logic and add better quality ch..."}, "event": "response_sent", "model": "claude-sonnet-4-5", "session_id": "k4-challenge-s01", "env": "dev", "feature": "monitoring", "user_id_hash": "f00ba60b3772", "correlation_id": "req-d67985c4", "level": "info", "ts": "2026-08-11T09:55:30.230856Z"}
  ```
- Root cause: Cờ incident `rag_slow` trong `app/mock_rag.py` ở trạng thái `True`, kích hoạt `time.sleep(2.5)` làm chậm quá trình truy xuất văn bản RAG.
- Fix action: Tắt cờ incident bằng API `/incidents/rag_slow/disable` (hoặc `python scripts/inject_incident.py --disable`) và bổ sung timeout 2.0s cho truy vấn RAG.
- Preventive measure: Thiết lập Alert rule `HighTailLatency` khi P95 > 3000ms trong 5m; cấu hình Circuit Breaker và Fallback response khi RAG timeout.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Ngô Hoàng Phú | Role A — Logging, Correlation ID & PII Redaction | `f009dca`, `975d592` | Hiểu cách lan truyền Correlation ID xuyên suốt HTTP request và cách scrub PII dữ liệu nhạy cảm trước khi lưu JSON log. |
| Đinh Quốc Việt | Role B — Tracing & Prompt Versioning | `a25dfb4` | Hiểu cách gắn metadata cho Trace/Generation trên Langfuse và quy trình đổi label/rollback prompt an toàn. |
| Nguyễn Trung Long | Role C — Dashboard, SLO & Alerts | `287ea96`, `e415399`, `0487ef6` | Thấu hiểu contract 6 panel dashboard, cách định nghĩa SLI/SLO và xây dựng Alert rule kèm Runbook sự cố. |
