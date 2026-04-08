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


def _normalize_edit_item(item: Any) -> dict:
    if isinstance(item, str):
        return {
            "title": item.strip(),
            "description": "",
            "file": "",
            "symbol": "",
            "rationale": "",
        }

    if not isinstance(item, dict):
        return {
            "title": str(item),
            "description": "",
            "file": "",
            "symbol": "",
            "rationale": "",
        }

    title = _pick_text(
        item,
        [
            "title",
            "step",
            "change",
            "action",
            "name",
            "summary",
        ],
    )

    description = _pick_text(
        item,
        [
            "description",
            "details",
            "rationale",
            "explanation",
            "why",
        ],
    )

    file_path = _pick_text(item, ["file", "path", "target_file"])
    symbol = _pick_text(item, ["symbol", "function", "method", "target_symbol"])
    rationale = _pick_text(item, ["rationale", "reason", "why"])

    return {
        "title": title,
        "description": description,
        "file": file_path,
        "symbol": symbol,
        "rationale": rationale,
    }


def normalize_patch_plan(patch_plan: dict | list | None) -> dict | None:
    if not patch_plan:
        return None

    raw_items = []
    summary = ""
    tests_to_add = []
    risks = []

    if isinstance(patch_plan, list):
        raw_items = patch_plan

    elif isinstance(patch_plan, dict):
        summary = patch_plan.get("summary", "") or patch_plan.get("overview", "") or ""

        if "edits" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("edits"))
        elif "steps" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("steps"))
        elif "changes" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("changes"))
        elif "actions" in patch_plan:
            raw_items = _ensure_list(patch_plan.get("actions"))
        else:
            # treat the dict itself as one edit if it looks like a single edit object
            if any(
                key in patch_plan
                for key in ["step", "change", "action", "title", "description", "file", "symbol"]
            ):
                raw_items = [patch_plan]

        tests_to_add = _ensure_list(
            patch_plan.get("tests_to_add") or patch_plan.get("tests") or patch_plan.get("validation_tests")
        )
        risks = _ensure_list(
            patch_plan.get("risks") or patch_plan.get("regression_risks")
        )

    edits = [_normalize_edit_item(item) for item in raw_items]

    # drop fully empty edits
    edits = [
        edit
        for edit in edits
        if any(
            (edit.get("title"), edit.get("description"), edit.get("file"), edit.get("symbol"), edit.get("rationale"))
        )
    ]

    if not summary:
        if edits:
            summary = "Apply the planned code changes and add regression coverage."
        else:
            summary = ""

    return {
        "summary": summary,
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
