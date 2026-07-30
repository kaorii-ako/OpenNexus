"""Tests for provider/key/model resolution.

This layer is where "it silently does nothing" bugs live, so the cases here are
the ones that actually bit during development: an unresolved "auto" provider
looking up a nonexistent AUTO_API_KEY, and a custom OpenAI-compatible endpoint
being handed OpenAI's default model.
"""
from __future__ import annotations

import pytest

from backend.core.config import LLMConfig
from backend.core.llm import factory


def cfg(**kwargs) -> LLMConfig:
    base = dict(
        provider="openai",
        model="",
        api_key="",
        base_url="http://localhost:11434",
        embed_model="",
    )
    base.update(kwargs)
    return LLMConfig(**base)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


# --- api key resolution -------------------------------------------------------


def test_config_key_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    assert factory.resolve_api_key(cfg(api_key="from-config"), "openai") == "from-config"


def test_env_key_used_when_config_empty(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    assert factory.resolve_api_key(cfg(), "openai") == "from-env"


def test_auto_provider_must_pass_resolved_provider(monkeypatch):
    """Regression: `provider="auto"` looked up ENV_KEYS["auto"], found nothing,
    and reported "no API key" while OPENAI_API_KEY was sitting right there."""
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    config = cfg(provider="auto")
    assert factory.resolve_api_key(config) == ""                # unresolved
    assert factory.resolve_api_key(config, "openai") == "from-env"  # resolved


def test_missing_key_returns_empty(monkeypatch):
    assert factory.resolve_api_key(cfg(), "openai") == ""


# --- provider resolution ------------------------------------------------------


def test_explicit_provider_is_not_probed(monkeypatch):
    monkeypatch.setattr(factory, "ollama_reachable", lambda *a, **k: pytest.fail("probed"))
    assert factory.resolve_provider(cfg(provider="openai")) == "openai"


def test_auto_prefers_local_ollama(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(factory, "ollama_reachable", lambda *a, **k: True)
    assert factory.resolve_provider(cfg(provider="auto")) == "ollama"


def test_auto_falls_back_to_cloud_key(monkeypatch):
    monkeypatch.setattr(factory, "ollama_reachable", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert factory.resolve_provider(cfg(provider="auto")) == "anthropic"


def test_auto_with_nothing_available_explains(monkeypatch):
    monkeypatch.setattr(factory, "ollama_reachable", lambda *a, **k: False)
    with pytest.raises(factory.LLMUnavailable) as exc:
        factory.resolve_provider(cfg(provider="auto"))
    assert "OPENAI_API_KEY" in str(exc.value)


# --- custom OpenAI-compatible endpoints ---------------------------------------


def test_openai_base_url_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    assert factory.openai_base_url(cfg()) == "https://integrate.api.nvidia.com/v1"


def test_config_base_url_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://from-env/v1")
    assert factory.openai_base_url(cfg(openai_base_url="https://from-config/v1")) == "https://from-config/v1"


def test_ollama_base_url_is_not_used_as_openai_endpoint():
    """`base_url` is Ollama's address and must never leak into the OpenAI client."""
    assert factory.openai_base_url(cfg(base_url="http://localhost:11434")) == ""


def test_custom_endpoint_without_model_refuses(monkeypatch):
    """Regression: the OpenAI default model 404s on a non-OpenAI endpoint."""
    monkeypatch.setenv("OPENAI_API_KEY", "nvapi-x")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    with pytest.raises(factory.LLMUnavailable) as exc:
        factory.create_backend(cfg(model=""))
    assert "no safe default" in str(exc.value)


def test_custom_endpoint_with_model_builds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "nvapi-x")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    backend = factory.create_backend(cfg(model="meta/llama-3.2-3b-instruct"))
    assert backend.model == "meta/llama-3.2-3b-instruct"
    assert backend.base_url == "https://integrate.api.nvidia.com/v1"
    # OpenAI's embedding default must not be assumed on a foreign endpoint.
    assert backend.embed_model == ""


def test_plain_openai_gets_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    backend = factory.create_backend(cfg())
    assert backend.model == "gpt-4o-mini"
    assert backend.embed_model == "text-embedding-3-small"


def test_missing_key_raises_actionable_error():
    with pytest.raises(factory.LLMUnavailable) as exc:
        factory.create_backend(cfg(provider="openai"))
    assert "OPENAI_API_KEY" in str(exc.value)


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        factory.create_backend(cfg(provider="hotdog"))


def test_ollama_backend_builds_without_service_running(monkeypatch):
    """Constructing a backend must not require the service to be up."""
    monkeypatch.setattr(factory, "ollama_reachable", lambda *a, **k: False)
    backend = factory.create_backend(cfg(provider="ollama", model="llama3.2"))
    assert backend.model == "llama3.2"
