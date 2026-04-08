from bug_investigator.tools.sandbox import validate_repro_failure
from bug_investigator.agents.reproduction import _looks_suspicious


def test_validate_repro_failure_prefers_natural_failure():
    result = {
        "exit_code": 1,
        "stdout": "",
        "stderr": "TypeError: boom",
    }
    verdict = validate_repro_failure(result, "TypeError")
    assert verdict["matched_expected_signature"] is True
    assert verdict["natural_failure"] is True
    assert verdict["match_mode"] == "natural_failure"


def test_validate_repro_failure_detects_assisted_stdout_match():
    result = {
        "exit_code": 0,
        "stdout": "TypeError: boom",
        "stderr": "",
    }
    verdict = validate_repro_failure(result, "TypeError")
    assert verdict["matched_expected_signature"] is True
    assert verdict["natural_failure"] is False
    assert verdict["match_mode"] == "assisted_stdout_match"


def test_looks_suspicious_flags_bootstrap_and_try_except():
    assert _looks_suspicious("from bootstrap import *\nprint('x')\n") is True
    assert _looks_suspicious("try:\n    x = 1\nexcept Exception:\n    pass\n") is True
    assert _looks_suspicious("from service import get_user_tier\nprint(get_user_tier('u'))\n") is False
