# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 sau khi merge Role A CP1 (`submission/evidence/cp2-log-validator.txt`)
- Tổng số traces:
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

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel`; xem `submission/evidence/cp2-dashboard-validator.txt`.
- Evidence dashboard: `submission/evidence/cp2-dashboard-runtime.json` chứa dữ liệu thật của đủ sáu panel trong cửa sổ 60 phút. Ảnh UI cần lưu thành `submission/evidence/cp2-dashboard.png`.
- SLO đã chọn và lý do: P95 <= 3000 ms, error rate <= 2%, daily cost <= 2.50 USD và quality trung bình >= 0.75. Các ngưỡng phản ánh tail latency, độ tin cậy, ngân sách và chất lượng đầu ra; cùng giá trị được dùng trong dashboard và `config/slo.yaml`.
- Alert rules và runbook: `config/alert_rules.yaml` có HighTailLatency, HighRequestErrorRate và DailyCostBudgetRisk; owner, duration, user impact, bước điều tra và mitigation nằm trong `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
