from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


BANNED_IMPORTS = {"os", "subprocess", "socket", "requests", "httpx", "shutil"}
BANNED_CALLS = {"system", "popen", "remove", "unlink", "rmtree"}


def validate_generated_script(script_text: str) -> dict:
    try:
        tree = ast.parse(script_text)
    except SyntaxError as e:
        return {"ok": False, "reason": f"SyntaxError: {e}"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in BANNED_IMPORTS:
                    return {"ok": False, "reason": f"Banned import: {alias.name}"}
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in BANNED_IMPORTS:
                return {"ok": False, "reason": f"Banned import: {node.module}"}
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in BANNED_CALLS:
                return {"ok": False, "reason": f"Banned call: {fn.id}"}
            if isinstance(fn, ast.Attribute) and fn.attr in BANNED_CALLS:
                return {"ok": False, "reason": f"Banned call: {fn.attr}"}

    return {"ok": True, "reason": "Script passed validation"}


def write_repro_script(output_path: str, script_text: str) -> dict:
    verdict = validate_generated_script(script_text)
    if not verdict["ok"]:
        return {"ok": False, "tool_name": "write_repro_script", "summary": verdict["reason"]}

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_text, encoding="utf-8")
    return {
        "ok": True,
        "tool_name": "write_repro_script",
        "summary": f"Wrote repro script to {path}",
        "path": str(path),
    }


def run_python_script(
    script_path: str,
    cwd: str,
    timeout_sec: int = 8,
    env: dict | None = None,
) -> dict:
    abs_script_path = str(Path(script_path).resolve())
    abs_cwd = str(Path(cwd).resolve())

    proc = subprocess.run(
        [sys.executable, abs_script_path],
        cwd=abs_cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    return {
        "ok": True,
        "tool_name": "run_python_script",
        "summary": f"exit_code={proc.returncode}",
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "timed_out": False,
    }


def validate_repro_failure(execution_result: dict, expected_signature: str) -> dict:
    stdout = execution_result.get("stdout", "") or ""
    stderr = execution_result.get("stderr", "") or ""
    exit_code = execution_result.get("exit_code", 0)

    stderr_match = expected_signature in stderr
    stdout_match = expected_signature in stdout

    natural_failure = exit_code != 0 and stderr_match
    assisted_match = stdout_match and exit_code == 0

    matched = natural_failure or assisted_match

    if natural_failure:
        match_mode = "natural_failure"
    elif assisted_match:
        match_mode = "assisted_stdout_match"
    elif stderr_match:
        match_mode = "stderr_signature_but_zero_exit"
    elif stdout_match:
        match_mode = "stdout_signature_only"
    else:
        match_mode = "no_match"

    return {
        "ok": True,
        "tool_name": "validate_repro_failure",
        "summary": f"matched_expected_signature={matched}; match_mode={match_mode}",
        "matched_expected_signature": matched,
        "expected_signature": expected_signature,
        "natural_failure": natural_failure,
        "match_mode": match_mode,
    }
