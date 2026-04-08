from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    run_id: str
    status: str

    bug_report_path: str
    log_path: str
    repo_path: str
    output_dir: str

    raw_bug_report: str
    raw_logs: str

    triage: dict
    log_analysis: dict
    repo_context: dict
    repro: dict
    repro_exec: dict
    fix_plan: dict
    review: dict
    coordinator_decision: dict

    evidence_registry: list[dict]
    open_questions: list[dict]
    retry_counts: dict[str, int]

    trace_path: str
    final_report_path: str
    patch_diff_path: str


def init_state(
    run_id: str,
    bug_report_path: str,
    log_path: str,
    repo_path: str,
    output_dir: str,
) -> InvestigationState:
    return InvestigationState(
        run_id=run_id,
        status="running",
        bug_report_path=bug_report_path,
        log_path=log_path,
        repo_path=repo_path,
        output_dir=output_dir,
        evidence_registry=[],
        open_questions=[],
        retry_counts={},
    )
