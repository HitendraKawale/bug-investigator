from pathlib import Path

from bug_investigator.tools.sandbox import (
    run_python_script,
    validate_generated_script,
    validate_repro_failure,
    write_repro_script,
)


def test_validate_generated_script_rejects_os_import():
    verdict = validate_generated_script("import os\nprint('x')\n")
    assert verdict["ok"] is False


def test_write_and_run_script(tmp_path: Path):
    script = "print('hello')\n"
    script_path = tmp_path / "ok.py"
    write_result = write_repro_script(str(script_path), script)
    assert write_result["ok"] is True

    run_result = run_python_script(str(script_path), cwd=str(tmp_path), timeout_sec=3)
    assert run_result["ok"] is True
    assert run_result["exit_code"] == 0
    assert "hello" in run_result["stdout"]


def test_validate_repro_failure():
    result = {
        "exit_code": 1,
        "stdout": "",
        "stderr": "TypeError: boom",
    }
    verdict = validate_repro_failure(result, "TypeError")
    assert verdict["matched_expected_signature"] is True
    assert verdict["natural_failure"] is True
    assert verdict["match_mode"] == "natural_failure"
