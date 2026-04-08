from __future__ import annotations

from bug_investigator.agents.base import BaseAgent


REVIEWER_PROMPT = """
You are ReviewerCriticAgent.

Return strict JSON with:
- verdict
- approved
- criticisms
- required_revisions

Allowed verdict values only:
- approve
- revise_repro
- revise_fix_plan
- halt_partial

Reject unsupported claims.
"""


def _normalize_verdict(verdict: str | None) -> str:
    allowed = {"approve", "revise_repro", "revise_fix_plan", "halt_partial"}
    if verdict in allowed:
        return verdict
    return "halt_partial"


class ReviewerAgent(BaseAgent):
    name = "ReviewerAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")

        repro_exec = state.get("repro_exec", {})
        fix_plan = state.get("fix_plan", {})
        matched = repro_exec.get("matched_expected_signature", False)

        if not matched:
            fallback = {
                "verdict": "revise_repro",
                "approved": False,
                "criticisms": [
                    "Repro did not match the expected logged failure signature."
                ],
                "required_revisions": [
                    {
                        "target_agent": "ReproductionAgent",
                        "instruction": "Exercise the cache miss path more explicitly and reproduce the same TypeError from logs.",
                    }
                ],
            }
        elif not fix_plan:
            fallback = {
                "verdict": "revise_fix_plan",
                "approved": False,
                "criticisms": ["No grounded fix plan was produced."],
                "required_revisions": [
                    {
                        "target_agent": "FixPlannerAgent",
                        "instruction": "Produce concrete file-level edits and rationale.",
                    }
                ],
            }
        else:
            fallback = {
                "verdict": "approve",
                "approved": True,
                "criticisms": [],
                "required_revisions": [],
            }

        result = self.invoke_json_or_fallback(
            REVIEWER_PROMPT,
            {
                "log_analysis": state.get("log_analysis", {}),
                "repo_context": state.get("repo_context", {}),
                "repro": state.get("repro", {}),
                "repro_exec": state.get("repro_exec", {}),
                "fix_plan": fix_plan,
            },
            fallback,
        )

        result["verdict"] = _normalize_verdict(result.get("verdict"))
        if result["verdict"] != "approve":
            result["approved"] = False

        self.trace("agent_end", verdict=result.get("verdict"))
        return {"review": result}
