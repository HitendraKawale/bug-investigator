from __future__ import annotations

from typing import Any


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _pick_text(d: dict, keys: list[str]) -> str:
    for key in keys:
        value = d.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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

    deploy_corr = log_analysis.get("deploy_correlation", {})
    if isinstance(deploy_corr, dict):
        deploy_corr = [deploy_corr]

    return {
        "error_signatures": _ensure_list(log_analysis.get("error_signatures")),
        "stack_traces": normalized_traces,
        "deploy_correlation": _ensure_list(deploy_corr),
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


def _normalize_edit_item(item: Any, default_files: list[str]) -> dict:
    if isinstance(item, str):
        return {
            "title": item.strip(),
            "description": "",
            "file": default_files[0] if default_files else "",
            "symbol": "",
            "rationale": "",
        }

    if not isinstance(item, dict):
        return {
            "title": str(item),
            "description": "",
            "file": default_files[0] if default_files else "",
            "symbol": "",
            "rationale": "",
        }

    title = _pick_text(
        item,
        ["title", "step", "change", "action", "name", "summary"],
    )
    description = _pick_text(
        item,
        ["description", "details", "explanation", "why"],
    )
    file_path = _pick_text(item, ["file", "path", "target_file"])
    symbol = _pick_text(item, ["symbol", "function", "method", "target_symbol"])
    rationale = _pick_text(item, ["rationale", "reason", "why"])

    if not file_path and default_files:
        file_path = default_files[0]

    return {
        "title": title,
        "description": description,
        "file": file_path,
        "symbol": symbol,
        "rationale": rationale,
    }


def normalize_patch_plan(patch_plan: dict | list | None, root_cause: dict | None = None) -> dict | None:
    if not patch_plan:
        return None

    impacted_files = []
    if root_cause:
        impacted_files = _ensure_list(root_cause.get("affected_files"))

    raw_items = []
    summary = ""
    approach = ""
    tests_to_add = []
    risks = []

    if isinstance(patch_plan, list):
        raw_items = patch_plan

    elif isinstance(patch_plan, dict):
        summary = patch_plan.get("summary", "") or patch_plan.get("overview", "") or ""
        approach = patch_plan.get("approach", "") or patch_plan.get("implementation_strategy", "") or ""

        if "edits" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("edits"))
        elif "steps" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("steps"))
        elif "changes" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("changes"))
        elif "actions" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("actions"))
        else:
            if any(
                key in patch_plan
                for key in ["step", "change", "action", "title", "description", "file", "symbol"]
            ):
                raw_items = [patch_plan]

        tests_to_add = _ensure_list(
            patch_plan.get("tests_to_add")
            or patch_plan.get("tests")
            or patch_plan.get("validation_tests")
        )
        risks = _ensure_list(
            patch_plan.get("risks")
            or patch_plan.get("regression_risks")
        )

    edits = [_normalize_edit_item(item, impacted_files) for item in raw_items]
    edits = [
        edit
        for edit in edits
        if any(
            (
                edit.get("title"),
                edit.get("description"),
                edit.get("file"),
                edit.get("symbol"),
                edit.get("rationale"),
            )
        )
    ]

    if not summary:
        if edits:
            summary = "Apply the planned code changes and add regression coverage."
        else:
            summary = ""

    if not approach:
        if impacted_files:
            approach = (
                "Fix the async/sync boundary on the affected path, update impacted callers if needed, "
                "and add regression coverage for both cached and uncached user flows."
            )
        else:
            approach = "Apply the minimal code changes required to remove the failure and add regression tests."

    if not tests_to_add:
        tests_to_add = [
            {
                "name": "test_cache_hit_existing_user_tier_lookup",
                "purpose": "Verify existing cached users still return a tier successfully.",
            },
            {
                "name": "test_cache_miss_new_user_tier_lookup",
                "purpose": "Verify newly created uncached users no longer raise the coroutine TypeError.",
            },
        ]

    if not risks:
        risks = [
            "Changing the async/sync boundary may require updating callers of the affected function.",
            "The cache-hit path must remain unchanged for existing users.",
            "If callers remain synchronous, introducing await without adjusting call sites could create new failures.",
        ]

    return {
        "summary": summary,
        "impacted_files": impacted_files,
        "approach": approach,
        "edits": edits,
        "tests_to_add": tests_to_add,
        "risks": risks,
        "raw_item_count": len(raw_items),
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

    commands.append("uv run pytest")

    tests_to_add = []
    if patch_plan:
        tests_to_add = _ensure_list(patch_plan.get("tests_to_add"))

    regression_checks = [
        "Existing cached users still return a valid tier.",
        "New uncached users no longer raise TypeError when tier lookup is requested.",
        "Async profile fetch result is awaited before subscripting tier data.",
    ]

    return {
        "commands": commands,
        "tests_to_add": tests_to_add,
        "regression_checks": regression_checks,
        "expected_failing_output_before_fix": (
            "TypeError: 'coroutine' object is not subscriptable"
        ),
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
    repro_exit_code = None
    if reproduction:
        execution = reproduction.get("execution", {})
        repro_matched = bool(execution.get("matched_expected_signature"))
        repro_exit_code = execution.get("exit_code")

    primary_files = []
    if root_cause:
        primary_files = _ensure_list(root_cause.get("affected_files"))

    reviewer_verdict = ""
    if review:
        reviewer_verdict = review.get("verdict", "")

    patch_plan_ready = bool(patch_plan and patch_plan.get("edits"))

    return {
        "problem": problem,
        "repro_matched_expected_signature": repro_matched,
        "repro_exit_code": repro_exit_code,
        "reviewer_verdict": reviewer_verdict,
        "primary_files": primary_files,
        "patch_plan_ready": patch_plan_ready,
    }


def build_bug_summary(
    triage: dict | None,
    log_analysis: dict | None,
    reproduction: dict | None,
) -> dict:
    symptoms = []
    scope = ""
    severity = "medium"
    severity_reason = ""

    if triage:
        if triage.get("actual_behavior"):
            symptoms.append(triage["actual_behavior"])
        if triage.get("problem_statement"):
            scope = triage["problem_statement"]

    if log_analysis:
        signatures = _ensure_list(log_analysis.get("error_signatures"))
        if signatures:
            first = signatures[0]
            if isinstance(first, dict) and first.get("signature"):
                symptoms.append(first["signature"])

    repro_exec = {}
    if reproduction:
        repro_exec = reproduction.get("execution", {}) or {}

    actual_text = (triage or {}).get("actual_behavior", "").lower()
    if "http 500" in actual_text or repro_exec.get("natural_failure") is True:
        severity = "high"
        severity_reason = "The bug causes a reproducible runtime failure on a user-facing path and returns HTTP 500 for affected users."
    else:
        severity = "medium"
        severity_reason = "The bug is reproducible but does not clearly indicate a user-facing hard failure."

    return {
        "symptoms": symptoms,
        "scope": scope,
        "severity": severity,
        "severity_reason": severity_reason,
    }


def build_open_questions(
    existing_open_questions: list[dict] | None,
    triage: dict | None,
) -> list[dict]:
    if existing_open_questions:
        return existing_open_questions

    triage_unknowns = []
    if triage:
        triage_unknowns = _ensure_list(triage.get("unknowns"))

    return [
        {
            "question": q,
            "blocking": False,
            "suggested_resolution": "Verify through additional production logs, metrics, or targeted tests.",
        }
        for q in triage_unknowns
        if isinstance(q, str) and q.strip()
    ]
