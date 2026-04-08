from __future__ import annotations

from pathlib import Path


def generate_patch_diff(output_path: str, diff_text: str) -> dict:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diff_text, encoding="utf-8")
    return {
        "ok": True,
        "tool_name": "generate_patch_diff",
        "summary": f"Wrote diff to {path}",
        "path": str(path),
    }
