from __future__ import annotations

from bug_investigator.agents.base import BaseAgent


COORDINATOR_PROMPT = """
You are CoordinatorAgent for a LangGraph bug investigation workflow.

Allowed next_action values:
- run_log_analyst
- run_repo_context
- run_reproduction
- run_fix_planner
- run_reviewer
- finalize
- halt_partial

Decide the next best step from the current state.
Return strict JSON with:
- next_action
- reason
- required_inputs_present
- blocking_gaps
- confidence
"""


class CoordinatorAgent(BaseAgent):
    name = "CoordinatorAgent"

    def run(self, state: dict, fallback_decision: dict) -> dict:
        self.trace("agent_start")
        result = self.invoke_json_or_fallback(
            COORDINATOR_PROMPT,
            {
                "triage_present": bool(state.get("triage")),
                "log_analysis_present": bool(state.get("log_analysis")),
                "repo_context_present": bool(state.get("repo_context")),
                "repro_present": bool(state.get("repro")),
                "repro_exec_present": bool(state.get("repro_exec")),
                "review_present": bool(state.get("review")),
                "retry_counts": state.get("retry_counts", {}),
            },
            fallback_decision,
        )
        self.trace("agent_end", next_action=result.get("next_action"))
        return {"coordinator_decision": result}
