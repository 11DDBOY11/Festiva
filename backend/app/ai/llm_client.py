"""LLM Client interface, provider implementations, and factory.

Supports swappable providers (Groq, OpenAI, Fake) behind a unified interface with
deterministic structured output and repair mechanisms.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _clean_json_markdown(text: str) -> str:
    """Strip markdown code block fences if present in LLM response."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


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


class GroqLLMClient(LLMClient):
    """Real LLM provider using Groq API with fast Llama-3 models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = api_key if api_key is not None else (settings.GROQ_API_KEY or settings.LLM_API_KEY)
        if not key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Set GROQ_API_KEY in your .env file "
                "or export it in your environment."
            )
        # Lazy import of groq package
        try:
            from groq import Groq

            self.client = Groq(api_key=key)
        except ImportError:
            raise RuntimeError("The 'groq' package is not installed. Run 'pip install groq'.")

        self.model = model or settings.LLM_MODEL or "openai/gpt-oss-120b"
        # Verify model availability on current Groq account and pick best available chat model
        try:
            available_ids = [m.id for m in self.client.models.list().data]
            if self.model not in available_ids:
                candidates = [
                    "openai/gpt-oss-120b",
                    "llama-3.3-70b-versatile",
                    "qwen/qwen3.8-27b",
                    "openai/gpt-oss-20b",
                ]
                for cand in candidates:
                    if cand in available_ids:
                        self.model = cand
                        break
        except Exception as list_err:
            logger.debug("Could not verify available models: %s", list_err)

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        temperature = kwargs.get("temperature", 0.2)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        full_system = (
            (system_prompt.strip() + "\n\n" if system_prompt else "")
            + "CRITICAL: You must respond ONLY with a raw, valid JSON object "
            f"that strictly conforms to this JSON Schema:\n{schema_json}\n"
            "Do not wrap in backticks or markdown."
        )

        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]

        # First attempt with JSON mode
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=kwargs.get("temperature", 0.1),
        )
        raw_text = _clean_json_markdown(response.choices[0].message.content or "")

        try:
            return response_model.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as first_err:
            logger.warning(
                "LLM structured response failed schema validation. Attempting self-repair."
            )
            # Self-repair prompt
            repair_messages = list(messages)
            repair_messages.append({"role": "assistant", "content": raw_text})
            repair_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your output failed validation with error:\n{first_err}\n"
                        "Please correct the output and return only the valid JSON object."
                    ),
                }
            )
            repair_resp = self.client.chat.completions.create(
                model=self.model,
                messages=repair_messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            repaired_text = _clean_json_markdown(repair_resp.choices[0].message.content or "")
            return response_model.model_validate_json(repaired_text)


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory function returning the configured LLM client."""
    selected_provider = (provider or settings.LLM_PROVIDER).lower()

    if selected_provider == "fake":
        return FakeLLMClient()
    elif selected_provider == "groq":
        key = settings.GROQ_API_KEY or settings.LLM_API_KEY
        if not key:
            # If in dev or test and no key provided, fallback to FakeLLMClient
            if settings.ENV in ("dev", "test"):
                logger.info("No GROQ_API_KEY found in dev/test environment; using FakeLLMClient.")
                return FakeLLMClient()
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq in non-dev env.")
        return GroqLLMClient()
    elif selected_provider in ("openai", "gemini"):
        raise NotImplementedError(
            f"Hosted provider '{selected_provider}' requires configured API key and SDK. "
            "Use LLM_PROVIDER=groq."
        )
    else:
        raise ValueError(f"Unknown LLM provider: {selected_provider}")
