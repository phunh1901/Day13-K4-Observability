from __future__ import annotations

import httpx

from app.llm_provider import OpenAIResponsesLLM


def test_openai_responses_provider_parses_text_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = __import__("json").loads(request.content)
        assert payload["model"] == "gpt-5.6-luna"
        assert payload["max_output_tokens"] == 120
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.6-luna-2026-08-01",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Safe answer"}],
                    }
                ],
                "usage": {"input_tokens": 42, "output_tokens": 17},
            },
        )

    client = OpenAIResponsesLLM(
        api_key="test-key", transport=httpx.MockTransport(handler)
    )
    response = client.generate("hello", max_output_tokens=120)

    assert response.text == "Safe answer"
    assert response.usage.input_tokens == 42
    assert response.usage.output_tokens == 17


def test_openai_provider_fails_closed_without_key() -> None:
    client = OpenAIResponsesLLM(api_key=None)
    client.api_key = None

    try:
        client.generate("hello")
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("provider must reject missing credentials")
