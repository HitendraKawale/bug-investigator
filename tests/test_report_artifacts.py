import json
from pathlib import Path


def test_run_005_artifacts_exist():
    report_path = Path("outputs/run_005/investigation_report.json")
    patch_path = Path("outputs/run_005/artifacts/suggested.patch")

    assert report_path.exists(), f"Missing report: {report_path}"
    assert patch_path.exists(), f"Missing patch diff: {patch_path}"


def test_run_005_report_has_expected_shape():
    report_path = Path("outputs/run_005/investigation_report.json")
    data = json.loads(report_path.read_text(encoding="utf-8"))

    assert data["status"] == "completed"
    assert "triage_summary" in data
    assert "log_analysis" in data
    assert "repo_context" in data
    assert "reproduction" in data
    assert "review_verdict" in data
    assert "trace_artifacts" in data

    reproduction = data["reproduction"]
    assert "execution" in reproduction
    assert reproduction["execution"]["matched_expected_signature"] is True

    review = data["review_verdict"]
    assert review["approved"] is True
    assert review["verdict"] == "approve"


def test_run_005_patch_diff_is_non_empty():
    patch_path = Path("outputs/run_005/artifacts/suggested.patch")
    text = patch_path.read_text(encoding="utf-8").strip()

    assert text != ""
    assert "--- a/" in text or "+++" in text or "@@" in text
