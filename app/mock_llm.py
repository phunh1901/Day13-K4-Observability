from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .cost_control import apply_output_token_limit
from .incidents import STATE


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int
    requested_output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def generate(self, prompt: str, *, max_output_tokens: int | None = None) -> FakeResponse:
        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        requested_output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            requested_output_tokens *= 4
        output_tokens = apply_output_token_limit(requested_output_tokens, max_output_tokens)
        answer = (
            "Starter answer. Teams should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        return FakeResponse(
            text=answer,
            usage=FakeUsage(input_tokens, output_tokens, requested_output_tokens),
            model=self.model,
        )
