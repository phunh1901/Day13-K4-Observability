# Bonus hardening

Ba hạng mục này bám trực tiếp vào rubric bonus và đều có test/evidence kiểm chứng.

## 1. Real-provider cost optimization

Runtime dùng OpenAI Responses API khi `.env` có:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
LLM_MAX_OUTPUT_TOKENS=120
LLM_INPUT_COST_PER_MILLION=1
LLM_OUTPUT_COST_PER_MILLION=6
OPENAI_API_KEY=
```

API key không được ghi vào log, evidence hoặc Git. `FakeLLM` chỉ còn là fallback
explicit cho public tests/offline development (`LLM_PROVIDER=fake`). Runtime log và
Langfuse metadata ghi provider, model và output-token limit.

Benchmark gửi cùng tập input đã scrub PII tới cùng model theo hai cấu hình:

- before: `max_output_tokens=400`, verbosity `medium`;
- after: `max_output_tokens=120`, verbosity `low`.

```bash
python scripts/benchmark_cost_control.py \
  --requests 5 \
  --output submission/evidence/bonus-real-llm-cost-before-after.json
```

Chỉ aggregate usage, latency, quality proxy và cost được lưu; prompt/answer không
được đưa vào evidence.

Kết quả đo thực tế ngày 2026-08-11 trên 5 input paired:

- output token: `693 -> 399`, giảm `42.42%`;
- estimated cost: `$0.004349 -> $0.002585`, giảm `40.56%`;
- mean quality proxy: `0.88 -> 0.88`, không suy giảm;
- mean latency: `3415.27 ms -> 2118.34 ms` (số liệu tham khảo, không dùng làm
  kết luận chính vì sample nhỏ và độ trễ mạng/provider có biến động).

Đây là benchmark nhỏ để chứng minh tác động của giới hạn output/verbosity, không
phải đánh giá chất lượng production quy mô lớn. Kết quả đầy đủ nằm tại
`submission/evidence/bonus-real-llm-cost-before-after.json`.

## 2. Separate audit log

Mỗi thao tác enable/disable incident tạo record riêng trong `data/audit.jsonl` với:

- timestamp, actor, action, resource và outcome;
- correlation ID khớp request điều khiển;
- details đã qua PII scrubbing.

Audit log tách khỏi application log và không commit. Tạo evidence an toàn bằng API
thật trong process test:

```bash
python scripts/capture_audit_evidence.py
```

## 3. Submission automation

Một lệnh chạy test suite, dashboard validator, runtime log validator, `git diff
--check`, secret scan trên toàn bộ file sẽ submit và kiểm tra evidence bắt buộc:

```bash
python scripts/verify_submission.py \
  --output submission/evidence/bonus-submission-verification.json
```

Nếu clone mới chưa có runtime log, chạy API/load test trước hoặc dùng
`--skip-runtime-logs` chỉ cho kiểm tra source tĩnh.
