"""LLM Client interface, provider implementations, and factory.

Supports swappable providers (fake, openai, etc.) behind a unified interface with
structured output support.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate raw text response from prompt."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Generate structured output validated against a Pydantic model."""
        pass


class FakeLLMClient(LLMClient):
    """Deterministic fake LLM client for testing and development."""

    def __init__(
        self,
        default_response: str = "Fake LLM text response",
        structured_responses: dict[type[BaseModel], BaseModel] | None = None,
    ) -> None:
        self.default_response = default_response
        self.structured_responses = structured_responses or {}
        self.call_history: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        self.call_history.append(
            {
                "type": "text",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "kwargs": kwargs,
            }
        )
        return self.default_response

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        self.call_history.append(
            {
                "type": "structured",
                "model": response_model.__name__,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "kwargs": kwargs,
            }
        )
        if response_model in self.structured_responses:
            return self.structured_responses[response_model]  # type: ignore[return-value]
        # Attempt to construct default model instance if possible
        try:
            return response_model()
        except Exception:
            raise ValueError(
                f"FakeLLMClient has no pre-configured response for model {response_model.__name__}"
            )


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory function returning the configured LLM client."""
    selected_provider = (provider or settings.LLM_PROVIDER).lower()

    if selected_provider == "fake":
        return FakeLLMClient()
    elif selected_provider in ("openai", "gemini"):
        # Hosted clients will be wired up when API keys are configured
        raise NotImplementedError(
            f"Hosted provider '{selected_provider}' requires configured API key and SDK."
        )
    else:
        raise ValueError(f"Unknown LLM provider: {selected_provider}")
