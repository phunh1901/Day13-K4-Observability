from __future__ import annotations

import random

import pytest

from app.cost_control import (
    apply_output_token_limit,
    estimate_cost_usd,
    parse_output_token_limit,
)
from app.mock_llm import FakeLLM


def test_output_token_limit_parser() -> None:
    assert parse_output_token_limit(None) == 120
    assert parse_output_token_limit("120") == 120
    assert parse_output_token_limit("off") is None
    with pytest.raises(ValueError):
        parse_output_token_limit("0")


def test_token_cap_reduces_usage_without_changing_fake_answer(monkeypatch) -> None:
    monkeypatch.setattr("app.mock_llm.time.sleep", lambda _: None)
    llm = FakeLLM()
    random.seed(1304)
    uncapped = llm.generate("A representative prompt", max_output_tokens=None)
    random.seed(1304)
    capped = llm.generate("A representative prompt", max_output_tokens=120)

    assert capped.text == uncapped.text
    assert capped.usage.output_tokens <= 120
    assert capped.usage.output_tokens <= uncapped.usage.output_tokens
    assert capped.usage.requested_output_tokens == uncapped.usage.requested_output_tokens


def test_cost_estimate_uses_provider_pricing() -> None:
    assert estimate_cost_usd(
        1_000_000,
        1_000_000,
        input_cost_per_million=1,
        output_cost_per_million=6,
    ) == 7.0
    assert apply_output_token_limit(180, 120) == 120
