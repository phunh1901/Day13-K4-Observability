from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from .mock_llm import FakeLLM


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    usage: ProviderUsage
    model: str


class OpenAIResponsesLLM:
    provider = "openai"

    def __init__(
        self,
        *,
        model: str = "gpt-5.6-luna",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def ready(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    chunks.append(str(content["text"]))
        return "\n".join(chunks).strip()

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int | None = None,
        text_verbosity: str = "low",
    ) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )
        request_payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "reasoning": {"effort": "none"},
            "text": {"verbosity": text_verbosity},
        }
        if max_output_tokens is not None:
            request_payload["max_output_tokens"] = max_output_tokens
        with httpx.Client(
            timeout=self.timeout_seconds, transport=self.transport
        ) as client:
            response = client.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
        if response.is_error:
            raise RuntimeError(
                f"OpenAI Responses API returned HTTP {response.status_code}"
            )
        payload = response.json()
        text = self._extract_text(payload)
        if not text:
            raise RuntimeError("OpenAI Responses API returned no output text")
        usage = payload.get("usage") or {}
        return ProviderResponse(
            text=text,
            usage=ProviderUsage(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
            ),
            model=str(payload.get("model") or self.model),
        )


def build_llm(model: str | None = None):
    provider = os.getenv("LLM_PROVIDER", "fake").strip().lower()
    if provider == "openai":
        return OpenAIResponsesLLM(
            model=model or os.getenv("LLM_MODEL", "gpt-5.6-luna"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    if provider == "fake":
        llm = FakeLLM(model=model or os.getenv("LLM_MODEL", "claude-sonnet-4-5"))
        llm.provider = "fake"
        llm.ready = True
        return llm
    raise ValueError("LLM_PROVIDER must be 'openai' or 'fake'")
