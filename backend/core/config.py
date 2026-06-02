from __future__ import annotations
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OllamaConfig:
    base_url: str
    model_general: str
    model_code: str
    model_reasoning: str
    model_embed: str
    stream: bool = True


@dataclass
class MemoryConfig:
    chroma_dir: str
    notion_collection: str
    conversation_collection: str
    file_collection: str
    top_k: int = 5
    chunk_strategy: str = "heading"


@dataclass
class ServerConfig:
    host: str
    port: int
    frontend_dist: str
    open_browser_on_start: bool = True


@dataclass
class SchedulerConfig:
    digest_cron: str
    notion_sync_cron: str
    reindex_cron: str


@dataclass
class DigestConfig:
    write_to_notion: bool = True
    print_to_terminal: bool = True


@dataclass
class UserConfig:
    name: str
    timezone: str
    role: str


@dataclass
class LLMConfig:
    provider: str        # "ollama" | "openai" | "anthropic"
    model: str
    api_key: str
    base_url: str        # Ollama only
    embed_model: str     # Ollama: "nomic-embed-text"; OpenAI: "text-embedding-3-small"
    model_code: str = ""
    model_reasoning: str = ""


@dataclass
class WeatherConfig:
    latitude: float
    longitude: float
    location_name: str


@dataclass
class ConnectorsConfig:
    weather: WeatherConfig
    rss_sources: list[str] = field(default_factory=list)
    notion_enabled: bool = True
    gmail_enabled: bool = True
    calendar_enabled: bool = True
    classroom_enabled: bool = True
    github_enabled: bool = True
    discord_enabled: bool = True


@dataclass
class NexusConfig:
    data_dir: Path
    notion_cache_dir: Path
    timezone: str
    user: UserConfig
    llm: LLMConfig
    ollama: OllamaConfig   # kept for backwards compat
    memory: MemoryConfig
    server: ServerConfig
    scheduler: SchedulerConfig
    digest: DigestConfig
    connectors: ConnectorsConfig


def load_config(path: Path | str | None = None) -> NexusConfig:
    if path is None:
        path = Path("nexus.toml")
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}. Copy nexus.toml.example to nexus.toml.")
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    required_sections = ["nexus", "memory", "server", "scheduler", "digest", "connectors"]
    for section in required_sections:
        if section not in raw:
            raise ValueError(
                f"✗ Missing [{section}] in {path}\n"
                f"  Fix: Add the section to your config, or run: nexus init"
            )

    n = raw["nexus"]
    o = raw.get("ollama", {})
    m = raw["memory"]
    s = raw["server"]
    sc = raw["scheduler"]
    d = raw["digest"]
    cw = raw["connectors"].get("weather", {})
    cr = raw["connectors"].get("rss", {})

    if not cw:
        raise ValueError(
            "✗ Missing [connectors.weather] in config\n"
            "  Fix: Add weather coordinates to your config, or run: nexus init"
        )

    # [user] section — defaults if missing
    u = raw.get("user", {})
    user = UserConfig(
        name=u.get("name", "User"),
        timezone=u.get("timezone", n.get("timezone", "UTC")),
        role=u.get("role", ""),
    )

    # [llm] section — falls back to [ollama] values for backwards compat
    lm = raw.get("llm", {})
    llm = LLMConfig(
        provider=lm.get("provider", "ollama"),
        model=lm.get("model", o.get("model_general", "llama3.2")),
        api_key=lm.get("api_key", ""),
        base_url=lm.get("base_url", o.get("base_url", "http://localhost:11434")),
        embed_model=lm.get("embed_model", o.get("model_embed", "nomic-embed-text")),
        model_code=lm.get("model_code", o.get("model_code", "")),
        model_reasoning=lm.get("model_reasoning", o.get("model_reasoning", "")),
    )

    # expand data_dir first, then build notion_cache_dir default
    data_dir = Path(n["data_dir"]).expanduser()
    notion_cache_dir = Path(n.get("notion_cache_dir", str(data_dir / "notion_cache"))).expanduser()

    ollama_cfg = OllamaConfig(**{k: o[k] for k in OllamaConfig.__dataclass_fields__}) if o and all(k in o for k in OllamaConfig.__dataclass_fields__) else OllamaConfig(
        base_url=llm.base_url,
        model_general=llm.model,
        model_code=llm.model_code,
        model_reasoning=llm.model_reasoning,
        model_embed=llm.embed_model,
    )

    return NexusConfig(
        data_dir=data_dir,
        notion_cache_dir=notion_cache_dir,
        timezone=n.get("timezone", user.timezone),
        user=user,
        llm=llm,
        ollama=ollama_cfg,
        memory=MemoryConfig(**{k: m[k] for k in MemoryConfig.__dataclass_fields__}),
        server=ServerConfig(**{k: s[k] for k in ServerConfig.__dataclass_fields__}),
        scheduler=SchedulerConfig(**{k: sc[k] for k in SchedulerConfig.__dataclass_fields__}),
        digest=DigestConfig(**{k: d[k] for k in DigestConfig.__dataclass_fields__}),
        connectors=ConnectorsConfig(
            weather=WeatherConfig(**cw),
            rss_sources=cr.get("sources", []),
            notion_enabled=raw["connectors"].get("notion", {}).get("enabled", True),
            gmail_enabled=raw["connectors"].get("gmail", {}).get("enabled", True),
            calendar_enabled=raw["connectors"].get("calendar", {}).get("enabled", True),
            classroom_enabled=raw["connectors"].get("classroom", {}).get("enabled", True),
            github_enabled=raw["connectors"].get("github", {}).get("enabled", True),
            discord_enabled=raw["connectors"].get("discord", {}).get("enabled", True),
        ),
    )
