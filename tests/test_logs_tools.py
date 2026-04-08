from pathlib import Path

from bug_investigator.tools.logs import count_error_signatures, extract_stack_traces, search_logs


def test_extract_stack_traces():
    log_path = str(Path("inputs/app.log"))
    result = extract_stack_traces(log_path)
    assert result["ok"] is True
    assert len(result["traces"]) >= 1
    assert "TypeError" in result["traces"][0]["text"]


def test_search_logs():
    log_path = str(Path("inputs/app.log"))
    result = search_logs(log_path, r"never awaited")
    assert result["ok"] is True
    assert len(result["matches"]) >= 1


def test_count_error_signatures():
    log_path = str(Path("inputs/app.log"))
    result = count_error_signatures(log_path)
    assert result["ok"] is True
    assert len(result["signatures"]) >= 1
