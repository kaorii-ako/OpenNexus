from __future__ import annotations
from backend.core.config import LLMConfig
from backend.core.llm.base import LLMBackend


def create_backend(cfg: LLMConfig) -> LLMBackend:
    if cfg.provider == "ollama":
        from backend.core.llm.ollama import OllamaBackend
        return OllamaBackend(
            base_url=cfg.base_url,
            model=cfg.model,
            embed_model=cfg.embed_model,
        )
    if cfg.provider == "openai":
        from backend.core.llm.openai import OpenAIBackend
        return OpenAIBackend(
            api_key=cfg.api_key,
            model=cfg.model,
            embed_model=cfg.embed_model or "text-embedding-3-small",
        )
    if cfg.provider == "anthropic":
        from backend.core.llm.anthropic import AnthropicBackend
        return AnthropicBackend(api_key=cfg.api_key, model=cfg.model)
    raise ValueError(
        f"Unknown LLM provider: '{cfg.provider}'. "
        "Valid options: 'ollama', 'openai', 'anthropic'"
    )
