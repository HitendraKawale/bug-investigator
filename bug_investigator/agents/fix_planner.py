from __future__ import annotations

from pathlib import Path

from bug_investigator.agents.base import BaseAgent
from bug_investigator.tools.patching import generate_patch_diff


FIX_PLANNER_PROMPT = """
You are FixPlannerAgent.

Return strict JSON with:
- root_cause_hypothesis
- patch_plan
- confidence_breakdown

Root cause must cite the execution path and affected files.
"""


class FixPlannerAgent(BaseAgent):
    name = "FixPlannerAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")

        repo_path = Path(state["repo_path"])
        patch_diff_path = str(Path(state["output_dir"]) / "artifacts" / "suggested.patch")

        fallback = {
            "root_cause_hypothesis": {
                "summary": "On cache miss, service.py calls async fetch_profile() without awaiting it, then indexes the returned coroutine like a dict.",
                "affected_files": ["service.py", "client.py"],
                "supporting_evidence_ids": [
                    ev["evidence_id"]
                    for ev in state.get("evidence_registry", [])
                ],
            },
            "patch_plan": {
                "summary": "Fix async/sync boundary on cache-miss path.",
                "edits": [
                    {
                        "file": "service.py",
                        "symbol": "get_user_tier",
                        "change_type": "behavioral_fix",
                        "description": "Await fetch_profile() before indexing the returned profile object, or restructure caller boundary cleanly.",
                        "rationale": "The current code treats a coroutine object like a dict.",
                    },
                    {
                        "file": "tests/test_repro_regression.py",
                        "symbol": "test_cache_miss_tier_lookup",
                        "change_type": "test",
                        "description": "Add a regression test for uncached users.",
                        "rationale": "Bug only appears on cache miss path.",
                    },
                ],
            },
            "confidence_breakdown": {
                "repro_match": 1.0 if state.get("repro_exec", {}).get("matched_expected_signature") else 0.4,
                "stacktrace_alignment": 0.95,
                "code_alignment": 0.95,
                "overall": 0.93 if state.get("repro_exec", {}).get("matched_expected_signature") else 0.72,
            },
        }

        result = self.invoke_json_or_fallback(
            FIX_PLANNER_PROMPT,
            {
                "triage": state.get("triage", {}),
                "log_analysis": state.get("log_analysis", {}),
                "repo_context": state.get("repo_context", {}),
                "repro": state.get("repro", {}),
                "repro_exec": state.get("repro_exec", {}),
            },
            fallback,
        )

        diff_text = """--- a/service.py
+++ b/service.py
@@
-def get_user_tier(user_id: str) -> str:
+async def get_user_tier(user_id: str) -> str:
     profile = CACHE.get(user_id)
     if profile is None:
-        profile = fetch_profile(user_id)
+        profile = await fetch_profile(user_id)
         CACHE[user_id] = profile
     return profile["tier"]
"""
        generate_patch_diff(patch_diff_path, diff_text)

        self.trace("agent_end", patch_diff_path=patch_diff_path)
        return {
            "fix_plan": result,
            "patch_diff_path": patch_diff_path,
        }
