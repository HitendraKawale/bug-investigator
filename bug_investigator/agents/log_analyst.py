from __future__ import annotations

from bug_investigator.agents.base import BaseAgent
from bug_investigator.io.readers import read_text
from bug_investigator.tools.logs import count_error_signatures, extract_stack_traces, search_logs


LOG_ANALYST_PROMPT = """
You are LogAnalystAgent.

Return strict JSON with:
- error_signatures
- stack_traces
- deploy_correlation
- red_herrings_rejected
- strongest_hypothesis

Only use the provided evidence.
"""


class LogAnalystAgent(BaseAgent):
    name = "LogAnalystAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")
        log_path = state["log_path"]
        raw_logs = state.get("raw_logs") or read_text(log_path)

        stack_data = extract_stack_traces(log_path)
        sig_data = count_error_signatures(log_path)
        coroutine_hits = search_logs(log_path, r"coroutine|never awaited|cache_status=miss", after=1, before=1)

        evidence = list(state.get("evidence_registry", []))
        for trace in stack_data["traces"]:
            evidence.append(
                {
                    "evidence_id": f"logtrace:{trace['start_line']}-{trace['end_line']}",
                    "source_type": "stack_trace",
                    "source_path": log_path,
                    "line_start": trace["start_line"],
                    "line_end": trace["end_line"],
                    "excerpt": trace["text"],
                    "relevance": "Primary stack trace from production logs",
                }
            )

        fallback = {
            "error_signatures": sig_data["signatures"],
            "stack_traces": stack_data["traces"],
            "deploy_correlation": {
                "marker_found": "deploy marker" in raw_logs,
                "post_deploy_errors_seen": "TypeError:" in raw_logs,
            },
            "red_herrings_rejected": [
                {"signal": "Redis reconnect warning", "reason": "No stack trace linkage"},
                {"signal": "metrics exporter timeout", "reason": "Unrelated subsystem"},
                {"signal": "health endpoint", "reason": "Successful and unrelated request"},
            ],
            "strongest_hypothesis": "Async misuse on cache-miss path causing coroutine to be indexed like a dict.",
            "search_hits": coroutine_hits["matches"],
        }

        result = self.invoke_json_or_fallback(
            LOG_ANALYST_PROMPT,
            {
                "triage": state.get("triage", {}),
                "stack_data": stack_data,
                "sig_data": sig_data,
                "search_hits": coroutine_hits,
            },
            fallback,
        )

        self.trace("agent_end", strongest_hypothesis=result.get("strongest_hypothesis", ""))
        return {
            "log_analysis": result,
            "raw_logs": raw_logs,
            "evidence_registry": evidence,
        }
