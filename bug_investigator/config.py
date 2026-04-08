from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    llm_provider: str
    llm_model: str
    llm_base_url: str | None
    llm_api_key: str | None
    trace_to_console: bool
    max_retries_per_step: int
    repro_timeout_sec: int


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    model = os.getenv("LLM_MODEL", "qwen2.5:14b-instruct").strip()

    if provider == "openai":
        base_url = os.getenv("LLM_BASE_URL") or None
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    else:
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("LLM_API_KEY", "ollama")

    return Settings(
        llm_provider=provider,
        llm_model=model,
        llm_base_url=base_url,
        llm_api_key=api_key,
        trace_to_console=_to_bool(os.getenv("TRACE_TO_CONSOLE"), True),
        max_retries_per_step=int(os.getenv("MAX_RETRIES_PER_STEP", "2")),
        repro_timeout_sec=int(os.getenv("REPRO_TIMEOUT_SEC", "8")),
    )
