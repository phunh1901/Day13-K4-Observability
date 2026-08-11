# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighTailLatency
- Severity: warning
- SLI/SLO liên quan: P95 latency <= 3000 ms trong 99.5% cửa sổ 5 phút của 28 ngày.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời chậm, dễ timeout hoặc người dùng gửi lại request.
- Ba bước kiểm tra đầu tiên: (1) xác nhận P50/P95/P99 và traffic trong cùng cửa sổ; (2) mở trace chậm, so sánh span retrieval và generation; (3) tìm log bằng correlation ID để xác nhận feature, model và lỗi phụ thuộc.
- Mitigation tạm thời: tắt incident/feature gây chậm, giảm concurrency hoặc dùng fallback retrieval; theo dõi P95 ít nhất 10 phút sau mitigation.
- Owner: api-on-call

## Alert 2

- Tên: HighRequestErrorRate
- Severity: critical
- SLI/SLO liên quan: error rate <= 2% trong 99% cửa sổ 5 phút của 28 ngày.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút và có ít nhất 20 request để tránh cảnh báo do mẫu quá nhỏ.
- Ảnh hưởng tới người dùng: request thất bại hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên: (1) xem breakdown theo `error_type`; (2) mở trace của một request lỗi; (3) dùng correlation ID tìm log và kiểm tra dependency/incident tương ứng.
- Mitigation tạm thời: chuyển sang dependency/fallback khỏe, rollback thay đổi gần nhất, hoặc giới hạn feature lỗi; xác nhận error rate trở về dưới 2%.
- Owner: api-on-call

## Alert 3

- Tên: DailyCostBudgetRisk
- Severity: warning
- SLI/SLO liên quan: projected daily cost <= 2.50 USD trong cửa sổ 28 ngày.
- Điều kiện và thời gian duy trì: `projected_daily_cost_usd > 2.5` liên tục 15 phút.
- Ảnh hưởng tới người dùng: nguy cơ hết ngân sách, bị rate-limit hoặc phải dừng dịch vụ sớm.
- Ba bước kiểm tra đầu tiên: (1) so sánh cost và traffic theo phút; (2) kiểm tra `tokens_in`/`tokens_out` và model; (3) mở trace có cost cao và đối chiếu prompt/version cùng log correlation ID.
- Mitigation tạm thời: đặt giới hạn output token, chuyển model phù hợp hơn hoặc rate-limit feature gây tăng cost; theo dõi cost/request sau thay đổi.
- Owner: ai-platform-on-call
