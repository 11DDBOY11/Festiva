"""Tests for LLMClient interface and FakeLLMClient."""

import pytest
from pydantic import BaseModel

from app.ai.llm_client import FakeLLMClient, get_llm_client


class SampleOutput(BaseModel):
    summary: str
    score: int = 10


def test_fake_llm_generate() -> None:
    client = FakeLLMClient(default_response="Custom mock response")
    response = client.generate("Plan an event in Mangaluru")
    assert response == "Custom mock response"
    assert len(client.call_history) == 1
    assert client.call_history[0]["prompt"] == "Plan an event in Mangaluru"


def test_fake_llm_generate_structured() -> None:
    expected = SampleOutput(summary="Grounded Plan", score=99)
    client = FakeLLMClient(structured_responses={SampleOutput: expected})

    result = client.generate_structured("Generate brief", response_model=SampleOutput)
    assert result == expected
    assert result.summary == "Grounded Plan"
    assert result.score == 99


def test_get_llm_client_factory() -> None:
    client = get_llm_client(provider="fake")
    assert isinstance(client, FakeLLMClient)

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_client(provider="invalid_provider")


def test_groq_llm_client_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ai.llm_client import GroqLLMClient

    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not configured"):
        GroqLLMClient(api_key="")

    monkeypatch.setattr("app.ai.llm_client.settings.GROQ_API_KEY", "")
    monkeypatch.setattr("app.ai.llm_client.settings.LLM_API_KEY", "")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not configured"):
        GroqLLMClient()
