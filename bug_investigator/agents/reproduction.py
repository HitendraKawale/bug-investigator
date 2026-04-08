from __future__ import annotations

from pathlib import Path
import re

from bug_investigator.agents.base import BaseAgent
from bug_investigator.tools.sandbox import run_python_script, validate_repro_failure, write_repro_script


REPRO_PROMPT = """
You are ReproductionAgent.

Return strict JSON with:
- repro_strategy
- script_text
- expected_failure_signature

Create the smallest deterministic Python repro.

Rules:
- The script must fail naturally with a non-zero exit code.
- Do not catch or suppress the target exception.
- Do not use markdown fences.
- Do not import imaginary helper modules such as bootstrap.
- Assume repo path bootstrap will be injected automatically.
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()

    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    if text.lower().startswith("python\n"):
        text = text.split("\n", 1)[1].strip()

    return text.strip()


def _bootstrap_header(repo_path: str) -> str:
    repo_abs = str(Path(repo_path).resolve())
    return f"""from pathlib import Path
import sys

REPO_ROOT = Path(r"{repo_abs}").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

"""


def _ensure_bootstrap(script_text: str, repo_path: str) -> str:
    header = _bootstrap_header(repo_path)
    text = script_text.lstrip()

    if "sys.path.insert(0" in text or "REPO_ROOT" in text:
        return text

    return header + text


def _looks_suspicious(script_text: str) -> bool:
    bad_patterns = [
        "from bootstrap import",
        "try:",
        "except TypeError",
        "except Exception",
        "traceback.print_exc()",
    ]
    lowered = script_text.lower()
    return any(p.lower() in lowered for p in bad_patterns)


class ReproductionAgent(BaseAgent):
    name = "ReproductionAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")
        out_dir = Path(state["output_dir"]) / "repro"
        out_dir.mkdir(parents=True, exist_ok=True)

        default_script = _ensure_bootstrap(
            """from cache import CACHE
from service import get_user_tier

CACHE.clear()

if __name__ == "__main__":
    print(get_user_tier("new_user_123"))
""",
            state["repo_path"],
        )

        fallback = {
            "repro_strategy": "Force cache miss, call sync tier lookup, reproduce coroutine indexing failure with a natural non-zero failure.",
            "script_text": default_script,
            "expected_failure_signature": "TypeError: 'coroutine' object is not subscriptable",
        }

        result = self.invoke_json_or_fallback(
            REPRO_PROMPT,
            {
                "triage": state.get("triage", {}),
                "log_analysis": state.get("log_analysis", {}),
                "repo_context": state.get("repo_context", {}),
            },
            fallback,
        )

        llm_script = _strip_code_fences(result.get("script_text", ""))
        script_text = default_script if not llm_script else _ensure_bootstrap(llm_script, state["repo_path"])

        if _looks_suspicious(script_text):
            self.trace("repro_suspicious_llm_script", reason="caught-exception or imaginary bootstrap pattern detected")
            script_text = default_script
            result = fallback

        script_path = str((out_dir / "repro_case.py").resolve())

        write_result = write_repro_script(script_path, script_text)
        if not write_result["ok"]:
            self.trace("repro_invalid_llm_script", reason=write_result["summary"])
            script_text = default_script
            result = fallback
            write_result = write_repro_script(script_path, script_text)

        if not write_result["ok"]:
            self.trace("agent_end", error=write_result["summary"])
            return {
                "repro": {
                    "error": write_result["summary"],
                    "script_path": script_path,
                    "expected_failure_signature": fallback["expected_failure_signature"],
                }
            }

        exec_result = run_python_script(
            script_path=script_path,
            cwd=state["output_dir"],
            timeout_sec=self.ctx.settings.repro_timeout_sec,
        )
        validation = validate_repro_failure(exec_result, result["expected_failure_signature"])

        should_fallback = (
            ("ModuleNotFoundError" in (exec_result.get("stderr", "") or ""))
            or ("ImportError" in (exec_result.get("stderr", "") or ""))
            or (validation.get("natural_failure") is not True)
        )

        if should_fallback and script_text != default_script:
            self.trace(
                "repro_retry_with_default",
                reason="generated script failed import/bootstrap or did not fail naturally with expected signature",
                stderr=exec_result.get("stderr", ""),
                stdout=exec_result.get("stdout", ""),
                match_mode=validation.get("match_mode"),
            )
            result = fallback
            script_text = default_script
            write_result = write_repro_script(script_path, script_text)

            if write_result["ok"]:
                exec_result = run_python_script(
                    script_path=script_path,
                    cwd=state["output_dir"],
                    timeout_sec=self.ctx.settings.repro_timeout_sec,
                )
                validation = validate_repro_failure(exec_result, result["expected_failure_signature"])

        repro = {
            "repro_strategy": result["repro_strategy"],
            "script_path": script_path,
            "command": ["python", script_path],
            "expected_failure_signature": result["expected_failure_signature"],
            "script_preview": script_text[:500],
        }

        repro_exec = {
            **exec_result,
            **validation,
        }

        self.trace(
            "agent_end",
            script_path=script_path,
            exit_code=exec_result.get("exit_code"),
            matched_expected_signature=validation.get("matched_expected_signature"),
            natural_failure=validation.get("natural_failure"),
            match_mode=validation.get("match_mode"),
            stderr=exec_result.get("stderr", ""),
        )
        return {
            "repro": repro,
            "repro_exec": repro_exec,
        }
