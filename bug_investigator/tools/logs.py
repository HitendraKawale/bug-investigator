from __future__ import annotations

import re
from pathlib import Path


def _read_lines(log_path: str) -> list[str]:
    return Path(log_path).read_text(encoding="utf-8").splitlines()


def search_logs(
    log_path: str,
    pattern: str,
    ignore_case: bool = True,
    before: int = 2,
    after: int = 2,
    max_matches: int = 50,
) -> dict:
    lines = _read_lines(log_path)
    flags = re.IGNORECASE if ignore_case else 0
    rx = re.compile(pattern, flags)

    matches = []
    for idx, line in enumerate(lines):
        if rx.search(line):
            start = max(0, idx - before)
            end = min(len(lines), idx + after + 1)
            excerpt = "\n".join(lines[start:end])
            matches.append(
                {
                    "line_number": idx + 1,
                    "match_line": line,
                    "excerpt": excerpt,
                    "start_line": start + 1,
                    "end_line": end,
                }
            )
            if len(matches) >= max_matches:
                break

    return {
        "ok": True,
        "tool_name": "search_logs",
        "summary": f"Found {len(matches)} matches for pattern={pattern!r}",
        "matches": matches,
    }


def extract_stack_traces(log_path: str, max_traces: int = 20) -> dict:
    lines = _read_lines(log_path)
    traces = []
    i = 0

    while i < len(lines):
        if "Traceback (most recent call last):" in lines[i]:
            start = i
            block = [lines[i]]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*Error:|^[A-Za-z_][A-Za-z0-9_\.]*Exception:|^TypeError:|^ValueError:|^RuntimeError:", lines[i]):
                    break
                i += 1

            traces.append(
                {
                    "start_line": start + 1,
                    "end_line": start + len(block),
                    "text": "\n".join(block),
                }
            )
            if len(traces) >= max_traces:
                break
        i += 1

    return {
        "ok": True,
        "tool_name": "extract_stack_traces",
        "summary": f"Extracted {len(traces)} stack traces",
        "traces": traces,
    }


def count_error_signatures(log_path: str, top_k: int = 10) -> dict:
    lines = _read_lines(log_path)
    counts: dict[str, int] = {}

    for line in lines:
        if "ERROR" in line or "TypeError:" in line or "ValueError:" in line or "RuntimeError:" in line:
            signature = line.strip()
            counts[signature] = counts.get(signature, 0) + 1

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return {
        "ok": True,
        "tool_name": "count_error_signatures",
        "summary": f"Counted {len(ranked)} signatures",
        "signatures": [{"signature": sig, "count": count} for sig, count in ranked],
    }


def get_log_window(log_path: str, start_line: int, end_line: int) -> dict:
    lines = _read_lines(log_path)
    start = max(1, start_line)
    end = min(len(lines), end_line)
    excerpt = "\n".join(lines[start - 1:end])
    return {
        "ok": True,
        "tool_name": "get_log_window",
        "summary": f"Lines {start}-{end}",
        "excerpt": excerpt,
        "start_line": start,
        "end_line": end,
    }
