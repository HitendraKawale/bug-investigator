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
Only return Python code in script_text. Do not include markdown fences.
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()

    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    if text.lower().startswith("python\n"):
        text = text.split("\n", 1)[1].strip()

    return text.strip()


class ReproductionAgent(BaseAgent):
    name = "ReproductionAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")
        out_dir = Path(state["output_dir"]) / "repro"
        out_dir.mkdir(parents=True, exist_ok=True)

        default_script = f"""from pathlib import Path
import sys

REPO_ROOT = Path(r"{Path(state['repo_path']).resolve()}").resolve()
sys.path.insert(0, str(REPO_ROOT))

from cache import CACHE
from service import get_user_tier

CACHE.clear()

if __name__ == "__main__":
    print(get_user_tier("new_user_123"))
"""

        fallback = {
            "repro_strategy": "Force cache miss, call sync tier lookup, reproduce coroutine indexing failure.",
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
        script_text = llm_script if llm_script else default_script

        script_path = str((out_dir / "repro_case.py").resolve())

        write_result = write_repro_script(script_path, script_text)
        if not write_result["ok"]:
            self.trace("repro_invalid_llm_script", reason=write_result["summary"])

            # hard fallback to deterministic script instead of stopping early
            write_result = write_repro_script(script_path, default_script)
            if not write_result["ok"]:
                self.trace("agent_end", error=write_result["summary"])
                return {
                    "repro": {
                        "error": write_result["summary"],
                        "script_path": script_path,
                        "expected_failure_signature": fallback["expected_failure_signature"],
                    }
                }
            script_text = default_script
            result = fallback

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
            stderr=exec_result.get("stderr", ""),
        )
        return {
            "repro": repro,
            "repro_exec": repro_exec,
        }
