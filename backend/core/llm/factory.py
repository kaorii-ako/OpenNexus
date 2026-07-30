from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

from backend.core.config import LLMConfig
from backend.core.llm.base import LLMBackend

ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "ollama": "llama3.2",
}


class LLMUnavailable(RuntimeError):
    """No usable backend, with an explanation the user can act on."""


def resolve_api_key(cfg: LLMConfig, provider: str | None = None) -> str:
    """Config key first, then the provider's conventional environment variable.

    Keeping the key out of nexus.toml is the normal way to hold an API key, so
    an empty config field is not an error — it is a signal to check the env.

    `provider` must be the *resolved* provider: with `provider = "auto"` in the
    config there is no "auto" environment variable to look up.
    """
    if cfg.api_key:
        return cfg.api_key
    env_name = ENV_KEYS.get(provider or cfg.provider, "")
    return os.environ.get(env_name, "") if env_name else ""


def openai_base_url(cfg: LLMConfig) -> str:
    """A custom OpenAI-compatible endpoint, if one is configured.

    `base_url` in [llm] is Ollama's address, so it is deliberately not reused
    here. A non-Ollama OpenAI-compatible endpoint comes from `openai_base_url`
    in [llm], or from the OPENAI_BASE_URL environment variable the official
    client already honours.
    """
    explicit = getattr(cfg, "openai_base_url", "") or ""
    return explicit or os.environ.get("OPENAI_BASE_URL", "")


def ollama_reachable(base_url: str, timeout: float = 0.6) -> bool:
    """Cheap TCP probe. Avoids a long HTTP timeout when Ollama simply is not up."""
    parsed = urlparse(base_url or "http://localhost:11434")
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 11434)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def resolve_provider(cfg: LLMConfig) -> str:
    """Pick a provider, honouring an explicit choice and probing only for "auto".

    "auto" prefers a local Ollama when one is actually running — nothing leaves
    the machine — and falls back to whichever cloud key is present.
    """
    provider = (cfg.provider or "ollama").lower()
    if provider != "auto":
        return provider

    if ollama_reachable(cfg.base_url):
        return "ollama"
    for candidate, env in ENV_KEYS.items():
        if os.environ.get(env):
            return candidate

    raise LLMUnavailable(
        "provider is 'auto' but nothing is available: Ollama is not reachable at "
        f"{cfg.base_url or 'http://localhost:11434'} and neither OPENAI_API_KEY nor "
        "ANTHROPIC_API_KEY is set.\n"
        "  Fix: start Ollama (`ollama serve`), or export an API key, or set an "
        "explicit provider in nexus.toml."
    )


def create_backend(cfg: LLMConfig) -> LLMBackend:
    provider = resolve_provider(cfg)
    model = cfg.model or DEFAULT_MODELS.get(provider, "")

    if provider == "ollama":
        # Deliberately not probed here. Constructing a backend must not require
        # the service to be running — that would make the object unusable in
        # tests and offline, and a connection error at call time is clearer
        # about what actually failed.
        from backend.core.llm.ollama import OllamaBackend

        return OllamaBackend(
            base_url=cfg.base_url,
            model=model,
            embed_model=cfg.embed_model,
        )

    if provider == "openai":
        key = resolve_api_key(cfg, provider)
        if not key:
            raise LLMUnavailable(
                "provider is 'openai' but no API key was found.\n"
                "  Fix: export OPENAI_API_KEY, or set api_key in [llm] in nexus.toml."
            )

        # An OpenAI-compatible endpoint that is not OpenAI: NVIDIA NIM, Groq,
        # Together, vLLM, LM Studio. The model catalogue there is completely
        # different, so the OpenAI default is guaranteed wrong and we say so
        # rather than letting it fail as an opaque 404.
        base_url = openai_base_url(cfg)
        if base_url and not cfg.model:
            raise LLMUnavailable(
                f"a custom OpenAI-compatible endpoint is configured ({base_url}) but no "
                "model is set.\n"
                "  That endpoint does not serve OpenAI's models, so there is no safe "
                "default to fall back on.\n"
                "  Fix: set model in [llm] in nexus.toml to one the endpoint serves."
            )

        from backend.core.llm.openai import OpenAIBackend

        return OpenAIBackend(
            api_key=key,
            model=model,
            embed_model=cfg.embed_model or ("" if base_url else "text-embedding-3-small"),
            base_url=base_url,
        )

    if provider == "anthropic":
        key = resolve_api_key(cfg, provider)
        if not key:
            raise LLMUnavailable(
                "provider is 'anthropic' but no API key was found.\n"
                "  Fix: export ANTHROPIC_API_KEY, or set api_key in [llm] in nexus.toml."
            )
        from backend.core.llm.anthropic import AnthropicBackend

        return AnthropicBackend(api_key=key, model=model)

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Valid options: 'auto', 'ollama', 'openai', 'anthropic'"
    )
