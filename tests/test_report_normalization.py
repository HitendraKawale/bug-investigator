from bug_investigator.report_normalization import (
    build_bug_summary,
    build_open_questions,
    build_run_summary,
    build_validation_plan,
    normalize_log_analysis,
    normalize_patch_plan,
    normalize_root_cause,
    normalize_triage_summary,
)


def test_normalize_triage_wraps_suspected_area():
    triage = {
        "problem_statement": "bug",
        "expected_behavior": "x",
        "actual_behavior": "y",
        "reproduction_hints": "hint",
        "unknowns": "unknown",
        "suspected_area": "service.py cache miss branch",
    }
    out = normalize_triage_summary(triage)
    assert isinstance(out["suspected_area"], list)
    assert len(out["suspected_area"]) == 1


def test_normalize_patch_plan_from_steps():
    patch_plan = {
        "steps": [
            {"step": "await fetch_profile", "description": "fix async bug"}
        ]
    }
    root_cause = {"affected_files": ["service.py", "client.py"]}
    out = normalize_patch_plan(patch_plan, root_cause)
    assert "edits" in out
    assert out["edits"][0]["title"] == "await fetch_profile"
    assert out["edits"][0]["description"] == "fix async bug"
    assert out["impacted_files"] == ["service.py", "client.py"]
    assert len(out["risks"]) >= 1


def test_normalize_patch_plan_from_single_dict_shape():
    patch_plan = {
        "step": "await fetch_profile(user_id)",
        "description": "await the async function before subscripting the result",
        "file": "service.py",
        "symbol": "get_user_tier",
    }
    out = normalize_patch_plan(patch_plan, {"affected_files": ["service.py"]})
    assert len(out["edits"]) == 1
    assert out["edits"][0]["title"] == "await fetch_profile(user_id)"
    assert out["edits"][0]["file"] == "service.py"


def test_normalize_patch_plan_from_list_of_strings():
    patch_plan = ["await fetch_profile(user_id)", "add regression test"]
    out = normalize_patch_plan(patch_plan, {"affected_files": ["service.py"]})
    assert len(out["edits"]) == 2
    assert out["edits"][0]["title"] == "await fetch_profile(user_id)"


def test_build_validation_plan_contains_command():
    reproduction = {
        "command": ["python", "outputs/run_005/repro/repro_case.py"]
    }
    patch_plan = {
        "tests_to_add": ["test_cache_miss_tier_lookup"]
    }
    out = build_validation_plan(reproduction, patch_plan)
    assert len(out["commands"]) >= 2
    assert "python" in out["commands"][0]
    assert "uv run pytest" in out["commands"]
    assert "test_cache_miss_tier_lookup" in out["tests_to_add"]


def test_normalize_root_cause_adds_confidence_and_evidence_ids():
    root_cause = {
        "description": "missing await",
        "affected_files": ["service.py", "client.py"],
        "execution_path": [{"file": "service.py", "line_number": 8}],
    }
    fix_plan = {
        "confidence_breakdown": {"overall": 0.93}
    }
    evidence = [
        {"evidence_id": "ev1"},
        {"evidence_id": "ev2"},
    ]
    out = normalize_root_cause(root_cause, fix_plan, evidence)
    assert out["summary"] == "missing await"
    assert out["confidence"]["overall"] == 0.93
    assert out["supporting_evidence_ids"] == ["ev1", "ev2"]


def test_build_run_summary():
    triage = {"problem_statement": "tier lookup fails"}
    root_cause = {"affected_files": ["service.py"]}
    reproduction = {"execution": {"matched_expected_signature": True, "exit_code": 1}}
    review = {"verdict": "approve"}
    patch_plan = {"edits": [{"title": "fix"}]}
    out = build_run_summary(triage, root_cause, reproduction, review, patch_plan)
    assert out["repro_matched_expected_signature"] is True
    assert out["repro_exit_code"] == 1
    assert out["reviewer_verdict"] == "approve"
    assert out["patch_plan_ready"] is True


def test_normalize_log_analysis_deploy_dict_to_list():
    log_analysis = {
        "error_signatures": [],
        "stack_traces": [{"traceback": "Traceback...\nTypeError: bad"}],
        "deploy_correlation": {"date": "2026-04-05"},
        "red_herrings_rejected": [],
        "strongest_hypothesis": "x",
    }
    out = normalize_log_analysis(log_analysis)
    assert isinstance(out["deploy_correlation"], list)
    assert out["stack_traces"][0]["exception_type"] == "TypeError"


def test_build_bug_summary_high_severity():
    triage = {
        "actual_behavior": "Returns HTTP 500 for affected new users",
        "problem_statement": "Tier lookup fails for new users",
    }
    reproduction = {"execution": {"natural_failure": True}}
    out = build_bug_summary(triage, None, reproduction)
    assert out["severity"] == "high"
    assert "HTTP 500" in out["severity_reason"]


def test_build_open_questions_from_unknowns():
    triage = {"unknowns": ["Does cache involvement affect the issue?"]}
    out = build_open_questions([], triage)
    assert len(out) == 1
    assert out[0]["blocking"] is False
