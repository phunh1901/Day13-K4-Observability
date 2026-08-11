from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.cost_control import estimate_cost_usd
from app.llm_provider import OpenAIResponsesLLM
from app.mock_rag import retrieve
from app.pii import scrub_text
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE


def _prompt_for(payload: dict[str, str]) -> tuple[str, list[str], str]:
    safe_message = scrub_text(payload["message"])
    docs = retrieve(safe_message)
    prompt = (
        DEFAULT_PROMPT_TEMPLATE.replace("{{feature}}", payload["feature"])
        .replace("{{docs}}", "\n".join(docs))
        .replace("{{message}}", safe_message)
    )
    return prompt, docs, safe_message


def _quality(question: str, answer: str, docs: list[str]) -> float:
    score = 0.5
    if docs:
        score += 0.2
    if len(answer) > 40:
        score += 0.1
    if question.lower().split()[0:1] and any(
        token in answer.lower() for token in question.lower().split()[:3]
    ):
        score += 0.1
    return round(max(0.0, min(1.0, score)), 2)


def _run_configuration(
    *,
    client: OpenAIResponsesLLM,
    payloads: list[dict[str, str]],
    max_output_tokens: int,
    text_verbosity: str,
    input_price: float,
    output_price: float,
) -> dict:
    input_tokens = 0
    output_tokens = 0
    costs: list[float] = []
    latencies_ms: list[float] = []
    quality_scores: list[float] = []
    for payload in payloads:
        prompt, docs, safe_message = _prompt_for(payload)
        started = time.perf_counter()
        response = client.generate(
            prompt,
            max_output_tokens=max_output_tokens,
            text_verbosity=text_verbosity,
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        costs.append(
            estimate_cost_usd(
                response.usage.input_tokens,
                response.usage.output_tokens,
                input_cost_per_million=input_price,
                output_cost_per_million=output_price,
            )
        )
        quality_scores.append(_quality(safe_message, response.text, docs))
    return {
        "requests": len(payloads),
        "max_output_tokens": max_output_tokens,
        "text_verbosity": text_verbosity,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(sum(costs), 6),
        "latency_mean_ms": round(statistics.mean(latencies_ms), 2),
        "quality_mean": round(statistics.mean(quality_scores), 4),
    }


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Paired real-provider before/after cost benchmark"
    )
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-5.6-luna"))
    parser.add_argument("--baseline-limit", type=int, default=400)
    parser.add_argument("--optimized-limit", type=int, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.requests <= 0:
        parser.error("--requests must be positive")
    if args.optimized_limit >= args.baseline_limit:
        parser.error("--optimized-limit must be lower than --baseline-limit")
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is missing from .env", file=sys.stderr)
        return 2

    all_payloads = [
        json.loads(line)
        for line in (REPO_ROOT / "data" / "sample_queries.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    payloads = all_payloads[: args.requests]
    input_price = float(os.getenv("LLM_INPUT_COST_PER_MILLION", "1"))
    output_price = float(os.getenv("LLM_OUTPUT_COST_PER_MILLION", "6"))
    client = OpenAIResponsesLLM(model=args.model)

    before = _run_configuration(
        client=client,
        payloads=payloads,
        max_output_tokens=args.baseline_limit,
        text_verbosity="medium",
        input_price=input_price,
        output_price=output_price,
    )
    after = _run_configuration(
        client=client,
        payloads=payloads,
        max_output_tokens=args.optimized_limit,
        text_verbosity="low",
        input_price=input_price,
        output_price=output_price,
    )
    cost_saved = round(before["cost_usd"] - after["cost_usd"], 6)
    output_tokens_saved = before["output_tokens"] - after["output_tokens"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "provider": "openai",
        "model": args.model,
        "method": {
            "paired_inputs": len(payloads),
            "inputs": "first N records from data/sample_queries.jsonl",
            "pii_scrubbed_before_provider": True,
            "answers_or_prompts_stored": False,
            "pricing_usd_per_million": {
                "input": input_price,
                "output": output_price,
            },
        },
        "before": before,
        "after": after,
        "savings": {
            "output_tokens": output_tokens_saved,
            "output_tokens_pct": round(
                output_tokens_saved / before["output_tokens"] * 100, 2
            ),
            "cost_usd": cost_saved,
            "cost_pct": round(cost_saved / before["cost_usd"] * 100, 2),
            "quality_delta": round(
                after["quality_mean"] - before["quality_mean"], 4
            ),
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
