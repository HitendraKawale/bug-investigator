from __future__ import annotations

from typing import Any


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_triage_summary(triage: dict | None) -> dict | None:
    if not triage:
        return None

    suspected_area = triage.get("suspected_area")
    return {
        "problem_statement": triage.get("problem_statement", ""),
        "expected_behavior": triage.get("expected_behavior", ""),
        "actual_behavior": triage.get("actual_behavior", ""),
        "reproduction_hints": _ensure_list(triage.get("reproduction_hints")),
        "unknowns": _ensure_list(triage.get("unknowns")),
        "suspected_area": _ensure_list(suspected_area),
    }


def normalize_log_analysis(log_analysis: dict | None) -> dict | None:
    if not log_analysis:
        return None

    raw_traces = _ensure_list(log_analysis.get("stack_traces"))
    normalized_traces = []

    for item in raw_traces:
        if isinstance(item, dict):
            traceback_text = (
                item.get("traceback")
                or item.get("text")
                or item.get("excerpt")
                or ""
            )
        else:
            traceback_text = str(item)

        last_line = traceback_text.strip().splitlines()[-1] if traceback_text.strip() else ""
        exception_type = last_line.split(":", 1)[0].strip() if ":" in last_line else last_line

        normalized_traces.append(
            {
                "traceback": traceback_text,
                "exception_type": exception_type,
            }
        )

    return {
        "error_signatures": _ensure_list(log_analysis.get("error_signatures")),
        "stack_traces": normalized_traces,
        "deploy_correlation": log_analysis.get("deploy_correlation", {}),
        "red_herrings_rejected": _ensure_list(log_analysis.get("red_herrings_rejected")),
        "strongest_hypothesis": log_analysis.get("strongest_hypothesis", ""),
    }


def normalize_root_cause(
    root_cause: dict | None,
    fix_plan: dict | None,
    evidence: list[dict] | None,
) -> dict | None:
    if not root_cause:
        return None

    evidence_ids = [ev.get("evidence_id") for ev in (evidence or []) if ev.get("evidence_id")]

    confidence = {}
    if fix_plan and isinstance(fix_plan, dict):
        confidence = fix_plan.get("confidence_breakdown", {}) or {}

    summary = (
        root_cause.get("summary")
        or root_cause.get("description")
        or root_cause.get("failure_mechanism")
        or ""
    )

    return {
        "summary": summary,
        "affected_files": _ensure_list(root_cause.get("affected_files")),
        "execution_path": _ensure_list(root_cause.get("execution_path")),
        "supporting_evidence_ids": evidence_ids,
        "confidence": confidence,
    }


def normalize_patch_plan(patch_plan: dict | None) -> dict | None:
    if not patch_plan:
        return None

    if "edits" in patch_plan:
        edits = _ensure_list(patch_plan.get("edits"))
    else:
        edits = []
        for step in _ensure_list(patch_plan.get("steps")):
            if isinstance(step, dict):
                edits.append(
                    {
                        "title": step.get("step", ""),
                        "description": step.get("description", ""),
                    }
                )
            else:
                edits.append({"title": str(step), "description": ""})

    tests_to_add = _ensure_list(patch_plan.get("tests_to_add"))
    risks = _ensure_list(patch_plan.get("risks"))

    summary = patch_plan.get("summary")
    if not summary and edits:
        summary = "Apply the planned code changes and add regression coverage."
    elif not summary:
        summary = ""

    return {
        "summary": summary,
        "edits": edits,
        "tests_to_add": tests_to_add,
        "risks": risks,
    }


def build_validation_plan(
    reproduction: dict | None,
    patch_plan: dict | None,
) -> dict:
    commands = []
    if reproduction and reproduction.get("command"):
        cmd = reproduction["command"]
        if isinstance(cmd, list):
            commands.append(" ".join(str(x) for x in cmd))
        else:
            commands.append(str(cmd))

    regression_checks = [
        "Existing cached users still return a valid tier.",
        "New uncached users no longer raise TypeError when tier lookup is requested.",
        "Async profile fetch result is awaited before subscripting tier data.",
    ]

    tests_to_add = []
    if patch_plan:
        tests_to_add = _ensure_list(patch_plan.get("tests_to_add"))

    return {
        "commands": commands,
        "tests_to_add": tests_to_add,
        "regression_checks": regression_checks,
    }


def build_run_summary(
    triage: dict | None,
    root_cause: dict | None,
    reproduction: dict | None,
    review: dict | None,
    patch_plan: dict | None,
) -> dict:
    problem = ""
    if triage:
        problem = triage.get("problem_statement", "")

    repro_matched = False
    if reproduction:
        execution = reproduction.get("execution", {})
        repro_matched = bool(execution.get("matched_expected_signature"))

    primary_files = []
    if root_cause:
        primary_files = _ensure_list(root_cause.get("affected_files"))

    reviewer_verdict = ""
    if review:
        reviewer_verdict = review.get("verdict", "")

    patch_ready = bool(patch_plan and patch_plan.get("edits"))

    return {
        "problem": problem,
        "repro_matched_expected_signature": repro_matched,
        "reviewer_verdict": reviewer_verdict,
        "primary_files": primary_files,
        "patch_plan_ready": patch_ready,
    }
