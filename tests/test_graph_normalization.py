from bug_investigator.orchestration.graph import _normalize_patch_plan, _normalize_root_cause


def test_normalize_patch_plan_from_list():
    value = [{"step": "do x"}, {"step": "do y"}]
    out = _normalize_patch_plan(value)
    assert isinstance(out, dict)
    assert "steps" in out
    assert len(out["steps"]) == 2


def test_normalize_patch_plan_from_dict():
    value = {"summary": "ok"}
    out = _normalize_patch_plan(value)
    assert out == value


def test_normalize_root_cause_from_list():
    value = [{"summary": "root cause"}]
    out = _normalize_root_cause(value)
    assert isinstance(out, dict)
    assert "items" in out
