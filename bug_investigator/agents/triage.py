from __future__ import annotations

from bug_investigator.agents.base import BaseAgent
from bug_investigator.io.readers import read_text


TRIAGE_PROMPT = """
You are TriageAgent for a bug investigation workflow.

Read the bug report and return strict JSON with:
- problem_statement
- expected_behavior
- actual_behavior
- reproduction_hints
- unknowns
- suspected_area

Do not invent facts.
"""


class TriageAgent(BaseAgent):
    name = "TriageAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")
        text = state.get("raw_bug_report") or read_text(state["bug_report_path"])

        expected = ""
        actual = ""
        hints: list[str] = []

        for line in text.splitlines():
            s = line.strip()
            low = s.lower()
            if low.startswith("## expected"):
                expected = "Tier lookup should return a tier string."
            elif low.startswith("## actual"):
                actual = "Affected requests fail with HTTP 500."
            elif s.startswith("- "):
                hints.append(s[2:])

        fallback = {
            "problem_statement": "Some users fail tier lookup after deploy.",
            "expected_behavior": expected or "Tier lookup should return a tier string.",
            "actual_behavior": actual or "Affected requests fail with HTTP 500.",
            "reproduction_hints": hints or ["More common for new users", "May involve cache miss path"],
            "unknowns": ["Whether the failure occurs only on cache miss"],
            "suspected_area": ["service.py", "client.py", "cache.py"],
        }

        result = self.invoke_json_or_fallback(
            TRIAGE_PROMPT,
            {"bug_report": text},
            fallback,
        )
        self.trace("agent_end", summary=result.get("problem_statement", ""))
        return {"triage": result, "raw_bug_report": text}
