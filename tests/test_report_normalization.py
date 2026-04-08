from bug_investigator.report_normalization import (
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
    out = normalize_patch_plan(patch_plan)
    assert "edits" in out
    assert out["edits"][0]["title"] == "await fetch_profile"


def test_build_validation_plan_contains_command():
    reproduction = {
        "command": ["python", "outputs/run_005/repro/repro_case.py"]
    }
    patch_plan = {
        "tests_to_add": ["test_cache_miss_tier_lookup"]
    }
    out = build_validation_plan(reproduction, patch_plan)
    assert len(out["commands"]) == 1
    assert "python" in out["commands"][0]
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
    reproduction = {"execution": {"matched_expected_signature": True}}
    review = {"verdict": "approve"}
    patch_plan = {"edits": [{"title": "fix"}]}
    out = build_run_summary(triage, root_cause, reproduction, review, patch_plan)
    assert out["repro_matched_expected_signature"] is True
    assert out["reviewer_verdict"] == "approve"
    assert out["patch_plan_ready"] is True
