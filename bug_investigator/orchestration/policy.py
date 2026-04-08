from __future__ import annotations


def default_next_action(state: dict) -> dict:
    max_retries = state.get("_max_retries", 2)
    repro_tries = state.get("retry_counts", {}).get("reproduction", 0)

    if not state.get("log_analysis"):
        return {
            "next_action": "run_log_analyst",
            "reason": "Need grounded log evidence before deeper investigation.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.9,
        }

    if not state.get("repo_context"):
        return {
            "next_action": "run_repo_context",
            "reason": "Need code context from the repo.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.9,
        }

    # repro missing entirely
    if not state.get("repro_exec"):
        if repro_tries >= max_retries:
            return {
                "next_action": "halt_partial",
                "reason": "Repro could not be produced successfully after retries.",
                "required_inputs_present": True,
                "blocking_gaps": ["validated repro"],
                "confidence": 0.8,
            }
        return {
            "next_action": "run_reproduction",
            "reason": "Need a deterministic repro before patch planning.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.9,
        }

    # repro exists but did not match
    if not state.get("repro_exec", {}).get("matched_expected_signature"):
        if repro_tries >= max_retries:
            return {
                "next_action": "halt_partial",
                "reason": "Repro did not match expected failure signature after retries.",
                "required_inputs_present": True,
                "blocking_gaps": ["validated repro"],
                "confidence": 0.8,
            }
        return {
            "next_action": "run_reproduction",
            "reason": "Repro did not yet match the expected failure signature.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.8,
        }

    if not state.get("fix_plan"):
        return {
            "next_action": "run_fix_planner",
            "reason": "Need root cause hypothesis and patch plan.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.9,
        }

    review = state.get("review")
    if not review:
        return {
            "next_action": "run_reviewer",
            "reason": "Need critic validation before finalization.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.9,
        }

    verdict = review.get("verdict")
    if verdict == "approve" and review.get("approved") is True:
        return {
            "next_action": "finalize",
            "reason": "Review approved the investigation.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.95,
        }

    if verdict == "revise_repro":
        if repro_tries >= max_retries:
            return {
                "next_action": "halt_partial",
                "reason": "Reviewer requested repro revision but retries are exhausted.",
                "required_inputs_present": True,
                "blocking_gaps": ["validated repro"],
                "confidence": 0.8,
            }
        return {
            "next_action": "run_reproduction",
            "reason": "Reviewer requested repro revision.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.8,
        }

    if verdict == "revise_fix_plan":
        return {
            "next_action": "run_fix_planner",
            "reason": "Reviewer requested stronger fix plan grounding.",
            "required_inputs_present": True,
            "blocking_gaps": [],
            "confidence": 0.8,
        }

    return {
        "next_action": "halt_partial",
        "reason": "No safe path forward.",
        "required_inputs_present": True,
        "blocking_gaps": [],
        "confidence": 0.6,
    }


def enforce_policy(state: dict, proposed: dict) -> dict:
    allowed = {
        "run_log_analyst",
        "run_repo_context",
        "run_reproduction",
        "run_fix_planner",
        "run_reviewer",
        "finalize",
        "halt_partial",
    }

    if proposed.get("next_action") not in allowed:
        return default_next_action(state)

    # cannot review before a grounded fix plan exists
    if proposed["next_action"] == "run_reviewer" and not state.get("fix_plan"):
        return default_next_action(state)

    # cannot finalize unless review approved and repro matched
    if proposed["next_action"] == "finalize":
        review = state.get("review")
        repro_exec = state.get("repro_exec", {})
        if not review:
            return default_next_action(state)
        if review.get("approved") is not True or review.get("verdict") != "approve":
            return default_next_action(state)
        if not repro_exec.get("matched_expected_signature"):
            return default_next_action(state)
        if not state.get("fix_plan"):
            return default_next_action(state)

    return proposed


def route_from_decision(state: dict) -> str:
    action = state["coordinator_decision"]["next_action"]
    mapping = {
        "run_log_analyst": "log_analyst",
        "run_repo_context": "repo_context",
        "run_reproduction": "reproduction",
        "run_fix_planner": "fix_planner",
        "run_reviewer": "reviewer",
        "finalize": "finalize",
        "halt_partial": "finalize",
    }
    return mapping[action]


def apply_retry_update(state: dict, node_name: str) -> dict:
    retries = dict(state.get("retry_counts", {}))
    retries[node_name] = retries.get(node_name, 0) + 1
    return {"retry_counts": retries}
