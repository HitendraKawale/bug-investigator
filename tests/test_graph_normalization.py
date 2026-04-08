from bug_investigator.report_normalization import _ensure_list, normalize_patch_plan, normalize_root_cause


def test_ensure_list_wraps_scalar():
    assert _ensure_list("x") == ["x"]


def test_normalize_patch_plan_from_list_steps():
    patch_plan = {
        "steps": [{"step": "await fetch_profile", "description": "fix async bug"}]
    }
    out = normalize_patch_plan(patch_plan)
    assert "edits" in out
    assert out["edits"][0]["title"] == "await fetch_profile"


def test_normalize_root_cause_from_description():
    root_cause = {
        "description": "missing await on fetch_profile",
        "affected_files": ["service.py"],
    }
    fix_plan = {"confidence_breakdown": {"overall": 0.9}}
    evidence = [{"evidence_id": "ev1"}]

    out = normalize_root_cause(root_cause, fix_plan, evidence)
    assert out["summary"] == "missing await on fetch_profile"
    assert out["confidence"]["overall"] == 0.9
    assert out["supporting_evidence_ids"] == ["ev1"]
