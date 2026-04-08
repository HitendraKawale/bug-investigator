from bug_investigator.orchestration.policy import default_next_action, enforce_policy


def test_default_next_action_prefers_log_analysis_first():
    state = {
        "triage": {"ok": True},
        "_max_retries": 2,
        "retry_counts": {},
    }
    decision = default_next_action(state)
    assert decision["next_action"] == "run_log_analyst"


def test_policy_blocks_finalize_without_review():
    state = {
        "triage": {"ok": True},
        "log_analysis": {"ok": True},
        "repo_context": {"ok": True},
        "repro_exec": {"matched_expected_signature": True},
        "fix_plan": {"ok": True},
        "_max_retries": 2,
        "retry_counts": {},
    }
    proposed = {
        "next_action": "finalize",
        "reason": "done",
        "required_inputs_present": True,
        "blocking_gaps": [],
        "confidence": 1.0,
    }
    safe = enforce_policy(state, proposed)
    assert safe["next_action"] != "finalize"
