from __future__ import annotations

from pathlib import Path


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
