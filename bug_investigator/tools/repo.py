from __future__ import annotations

from pathlib import Path


def read_repo_tree(repo_path: str, max_depth: int = 4) -> dict:
    root = Path(repo_path)
    rows: list[str] = []

    def walk(path: Path, prefix: str = "", depth: int = 0) -> None:
        if depth > max_depth:
            return
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        for entry in entries:
            if entry.name.startswith("__pycache__"):
                continue
            rows.append(f"{prefix}{entry.name}")
            if entry.is_dir():
                walk(entry, prefix + "  ", depth + 1)

    walk(root)
    return {
        "ok": True,
        "tool_name": "read_repo_tree",
        "summary": f"Read repo tree for {repo_path}",
        "tree_text": "\n".join(rows),
    }


def read_file_snippet(
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    max_chars: int = 4000,
) -> dict:
    path = Path(file_path)
    lines = path.read_text(encoding="utf-8").splitlines()

    s = 1 if start_line is None else max(1, start_line)
    e = len(lines) if end_line is None else min(len(lines), end_line)
    snippet_lines = []
    for i in range(s - 1, e):
        snippet_lines.append(f"{i+1}: {lines[i]}")
    snippet = "\n".join(snippet_lines)[:max_chars]

    return {
        "ok": True,
        "tool_name": "read_file_snippet",
        "summary": f"Read {path.name} lines {s}-{e}",
        "snippet": snippet,
        "start_line": s,
        "end_line": e,
        "file_path": str(path),
    }


def find_symbol_usages(repo_path: str, symbol: str) -> dict:
    root = Path(repo_path)
    hits = []

    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for idx, line in enumerate(text.splitlines(), start=1):
            if symbol in line:
                hits.append({"file": str(path), "line_number": idx, "line": line.strip()})

    return {
        "ok": True,
        "tool_name": "find_symbol_usages",
        "summary": f"Found {len(hits)} usages for symbol={symbol!r}",
        "hits": hits,
    }
