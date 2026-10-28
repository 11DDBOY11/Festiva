"""Tests for LLMClient interface and FakeLLMClient."""

import importlib
import inspect
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.ai.llm_client import FakeLLMClient, LLMClient, get_llm_client


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


def test_all_llm_client_subclasses_can_be_instantiated() -> None:
    """Regression test: assert every LLMClient subclass in the repo can be instantiated.

    Guarantees no abstract methods (such as stream, generate, generate_structured)
    are missing from any test, replay, or production LLMClient subclass.
    """
    backend_dir = Path(__file__).resolve().parent.parent

    # Dynamically import any repo modules defining LLMClient subclasses
    for py_path in backend_dir.rglob("*.py"):
        if any(p in py_path.parts for p in [".venv", "__pycache__", "site-packages"]):
            continue
        rel = py_path.relative_to(backend_dir)
        try:
            content = py_path.read_text(encoding="utf-8")
        except Exception:
            continue

        if "LLMClient" in content and "class " in content:
            mod_name = ".".join(rel.with_suffix("").parts)
            try:
                importlib.import_module(mod_name)
            except Exception:
                pass

    subclasses = LLMClient.__subclasses__()
    class_names = [cls.__name__ for cls in subclasses]

    # Verify key known subclasses are registered
    assert "FakeLLMClient" in class_names
    assert "GroqLLMClient" in class_names
    assert "ReplayLLMClient" in class_names

    dummy_kwargs = {
        "api_key": "mock_test_key_12345",
        "recordings": {},
    }

    for cls in subclasses:
        # 1. Assert class has 0 unimplemented abstract methods
        assert not cls.__abstractmethods__, (
            f"Subclass {cls.__name__} has unimplemented abstract methods: {cls.__abstractmethods__}"
        )

        # 2. Inspect __init__ to supply safe mock parameters if required
        sig = inspect.signature(cls.__init__)
        call_kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "args", "kwargs"):
                continue
            if param.default is inspect.Parameter.empty:
                call_kwargs[param_name] = dummy_kwargs.get(param_name, "mock")

        # 3. Assert instantiation succeeds without TypeError
        instance = cls(**call_kwargs)
        assert isinstance(instance, LLMClient)

        # 4. Assert stream method exists and returns an iterable without abstract error
        stream_res = instance.stream("Test prompt")
        assert hasattr(stream_res, "__iter__")


def test_unimplemented_abstract_method_fails_instantiation() -> None:
    """Verify ABC safeguards: omitting stream() raises TypeError upon instantiation."""

    class IncompleteLLMClient(LLMClient):
        def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
            return "ok"

        def generate_structured(self, prompt: str, response_model: type, **kwargs):
            return response_model()

    assert "stream" in IncompleteLLMClient.__abstractmethods__

    with pytest.raises(TypeError, match="Can't instantiate abstract class IncompleteLLMClient"):
        IncompleteLLMClient()
