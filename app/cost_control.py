from __future__ import annotations

import os


OPENAI_LUNA_INPUT_COST_PER_MILLION = 1.0
OPENAI_LUNA_OUTPUT_COST_PER_MILLION = 6.0
FAKE_INPUT_COST_PER_MILLION = 3.0
FAKE_OUTPUT_COST_PER_MILLION = 15.0
DEFAULT_OUTPUT_TOKEN_LIMIT = 120


def parse_output_token_limit(raw_value: str | None) -> int | None:
    """Parse the configured cap; 'off' preserves uncapped benchmark behavior."""
    if raw_value is None or not raw_value.strip():
        return DEFAULT_OUTPUT_TOKEN_LIMIT
    normalized = raw_value.strip().lower()
    if normalized in {"off", "none", "unlimited"}:
        return None
    try:
        value = int(normalized)
    except ValueError as exc:
        raise ValueError(
            "LLM_MAX_OUTPUT_TOKENS must be a positive integer or 'off'"
        ) from exc
    if value <= 0:
        raise ValueError("LLM_MAX_OUTPUT_TOKENS must be greater than zero")
    return value


def configured_output_token_limit() -> int | None:
    return parse_output_token_limit(os.getenv("LLM_MAX_OUTPUT_TOKENS"))


def apply_output_token_limit(requested_tokens: int, limit: int | None) -> int:
    if requested_tokens < 0:
        raise ValueError("requested_tokens cannot be negative")
    return requested_tokens if limit is None else min(requested_tokens, limit)


def estimate_cost_usd(
    tokens_in: int,
    tokens_out: int,
    *,
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> float:
    input_cost = (tokens_in / 1_000_000) * input_cost_per_million
    output_cost = (tokens_out / 1_000_000) * output_cost_per_million
    return round(input_cost + output_cost, 6)


def configured_pricing(provider: str) -> tuple[float, float]:
    if provider == "openai":
        default_input = OPENAI_LUNA_INPUT_COST_PER_MILLION
        default_output = OPENAI_LUNA_OUTPUT_COST_PER_MILLION
    else:
        default_input = FAKE_INPUT_COST_PER_MILLION
        default_output = FAKE_OUTPUT_COST_PER_MILLION
    return (
        float(os.getenv("LLM_INPUT_COST_PER_MILLION", str(default_input))),
        float(os.getenv("LLM_OUTPUT_COST_PER_MILLION", str(default_output))),
    )
