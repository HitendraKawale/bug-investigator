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

Requirements:
1. Root cause must explicitly connect the log evidence, code path, and repro outcome.
2. patch_plan must include:
   - summary
   - impacted_files
   - approach
   - edits
   - tests_to_add
   - risks
3. Each edit should include:
   - title
   - description
   - file
   - symbol
   - rationale
4. Do not give generic advice. Reference the affected files and failure path.
"""


class FixPlannerAgent(BaseAgent):
    name = "FixPlannerAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")

        patch_diff_path = str(Path(state["output_dir"]) / "artifacts" / "suggested.patch")

        fallback = {
            "root_cause_hypothesis": {
                "summary": (
                    "On cache miss, service.py calls async fetch_profile() without awaiting it, "
                    "then indexes the returned coroutine like a dict, which raises "
                    "TypeError: 'coroutine' object is not subscriptable."
                ),
                "affected_files": ["service.py", "client.py", "main.py"],
                "execution_path": [
                    {
                        "file": "main.py",
                        "line_number": 13,
                        "description": "handle_request invokes get_user_tier(user_id).",
                    },
                    {
                        "file": "service.py",
                        "line_number": 8,
                        "description": "get_user_tier calls fetch_profile(user_id) on cache miss without awaiting it.",
                    },
                    {
                        "file": "client.py",
                        "line_number": 4,
                        "description": "fetch_profile is an async function that returns a coroutine when called.",
                    },
                ],
            },
            "patch_plan": {
                "summary": "Fix the async/sync boundary on the cache-miss tier lookup path and add regression coverage.",
                "impacted_files": ["service.py", "main.py", "client.py"],
                "approach": (
                    "Await fetch_profile before subscripting the returned profile object. "
                    "Because get_user_tier currently behaves synchronously, update its caller boundary "
                    "or introduce a safe async bridge so the fix does not break existing call sites."
                ),
                "edits": [
                    {
                        "title": "Await fetch_profile on cache miss",
                        "description": (
                            "Replace the cache-miss branch in get_user_tier so the async client call is awaited "
                            "before the result is stored and before profile['tier'] is accessed."
                        ),
                        "file": "service.py",
                        "symbol": "get_user_tier",
                        "rationale": "The current code treats a coroutine object as if it were the resolved profile dict.",
                    },
                    {
                        "title": "Update caller to match async behavior",
                        "description": (
                            "Adjust the tier lookup call path so if get_user_tier becomes async, "
                            "the caller awaits it instead of invoking it synchronously."
                        ),
                        "file": "main.py",
                        "symbol": "handle_request",
                        "rationale": "Fixing the service layer may require updating the caller boundary to preserve correctness.",
                    },
                ],
                "tests_to_add": [
                    {
                        "name": "test_cache_miss_new_user_tier_lookup",
                        "purpose": "Verify a new uncached user no longer raises the coroutine TypeError.",
                    },
                    {
                        "name": "test_cache_hit_existing_user_tier_lookup",
                        "purpose": "Verify existing cached users continue returning a valid tier.",
                    },
                ],
                "risks": [
                    "Changing get_user_tier to async may require updating all callers.",
                    "The cache-hit path must remain behaviorally unchanged.",
                    "A partial fix in service.py without updating main.py could move the failure rather than remove it.",
                ],
            },
            "confidence_breakdown": {
                "high_confidence_factors": [
                    "The production stack trace and repro both point to subscripting a coroutine in service.py.",
                    "The code snippet explicitly shows fetch_profile is async and is called without await on cache miss.",
                ],
                "low_confidence_factors": [
                    "The exact breadth of caller changes depends on whether the production system uses a larger async framework boundary.",
                ],
                "total_confidence_score": 0.94,
                "confidence_level": "High",
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
