from bug_investigator.agents.reproduction import _ensure_bootstrap


def test_ensure_bootstrap_injects_repo_path():
    script = "from service import get_user_tier\nprint(get_user_tier('x'))\n"
    out = _ensure_bootstrap(script, "inputs/mini_repo")
    assert "sys.path.insert(0" in out
    assert "REPO_ROOT" in out
    assert "from service import get_user_tier" in out
