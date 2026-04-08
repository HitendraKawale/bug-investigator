from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from bug_investigator.agents.base import AgentContext
from bug_investigator.agents.coordinator import CoordinatorAgent
from bug_investigator.agents.fix_planner import FixPlannerAgent
from bug_investigator.agents.log_analyst import LogAnalystAgent
from bug_investigator.agents.repo_context import RepoContextAgent
from bug_investigator.agents.reproduction import ReproductionAgent
from bug_investigator.agents.reviewer import ReviewerAgent
from bug_investigator.agents.triage import TriageAgent
from bug_investigator.io.writers import write_json
from bug_investigator.orchestration.policy import (
    apply_retry_update,
    default_next_action,
    enforce_policy,
    route_from_decision,
)
from bug_investigator.schemas import FinalReport
from bug_investigator.state import InvestigationState


def _normalize_patch_plan(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"steps": value}
    return {"raw": value}


def _normalize_root_cause(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    return {"raw": value}


def build_graph(ctx: AgentContext):
    triage_agent = TriageAgent(ctx)
    log_agent = LogAnalystAgent(ctx)
    repo_agent = RepoContextAgent(ctx)
    repro_agent = ReproductionAgent(ctx)
    fix_agent = FixPlannerAgent(ctx)
    review_agent = ReviewerAgent(ctx)
    coordinator_agent = CoordinatorAgent(ctx)

    graph = StateGraph(InvestigationState)

    def triage_node(state: InvestigationState):
        return triage_agent.run(state)

    def log_analyst_node(state: InvestigationState):
        return log_agent.run(state)

    def repo_context_node(state: InvestigationState):
        return repo_agent.run(state)

    def reproduction_node(state: InvestigationState):
        update = repro_agent.run(state)
        update_retry = apply_retry_update(state, "reproduction")
        update.update(update_retry)
        return update

    def fix_planner_node(state: InvestigationState):
        return fix_agent.run(state)

    def reviewer_node(state: InvestigationState):
        return review_agent.run(state)

    def coordinator_node(state: InvestigationState):
        baseline = default_next_action(state)
        proposed = coordinator_agent.run(state, baseline)["coordinator_decision"]
        safe = enforce_policy(state, proposed)

        ctx.tracer.event(
            "policy_routed_action",
            proposed_next_action=proposed.get("next_action"),
            safe_next_action=safe.get("next_action"),
            reason=safe.get("reason"),
        )

        return {"coordinator_decision": safe}

    def finalize_node(state: InvestigationState):
        review = state.get("review") or {}
        repro_exec = state.get("repro_exec") or {}
        fix_plan = state.get("fix_plan") or {}

        normalized_root_cause = _normalize_root_cause(
            fix_plan.get("root_cause_hypothesis")
        )
        normalized_patch_plan = _normalize_patch_plan(
            fix_plan.get("patch_plan")
        )

        completed = (
            review.get("approved") is True
            and review.get("verdict") == "approve"
            and repro_exec.get("matched_expected_signature") is True
            and bool(normalized_patch_plan)
        )

        status = "completed" if completed else "partial"

        report = FinalReport(
            run_id=state["run_id"],
            status=status,
            input_artifacts={
                "bug_report_path": state["bug_report_path"],
                "log_path": state["log_path"],
                "repo_path": state["repo_path"],
            },
            triage_summary=state.get("triage"),
            log_analysis=state.get("log_analysis"),
            repo_context=state.get("repo_context"),
            reproduction={
                **(state.get("repro") or {}),
                **({"execution": state.get("repro_exec")} if state.get("repro_exec") else {}),
            },
            root_cause=normalized_root_cause,
            patch_plan=normalized_patch_plan,
            review_verdict=state.get("review"),
            evidence=state.get("evidence_registry", []),
            open_questions=state.get("open_questions", []),
            trace_artifacts={
                "trace_jsonl_path": state.get("trace_path", ""),
                "patch_diff_path": state.get("patch_diff_path", ""),
            },
        )

        final_report_path = str(Path(state["output_dir"]) / "investigation_report.json")
        write_json(final_report_path, report.model_dump())
        return {
            "status": status,
            "final_report_path": final_report_path,
        }

    graph.add_node("triage", triage_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("log_analyst", log_analyst_node)
    graph.add_node("repo_context", repo_context_node)
    graph.add_node("reproduction", reproduction_node)
    graph.add_node("fix_planner", fix_planner_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "triage")
    graph.add_edge("triage", "coordinator")
    graph.add_edge("log_analyst", "coordinator")
    graph.add_edge("repo_context", "coordinator")
    graph.add_edge("reproduction", "coordinator")
    graph.add_edge("fix_planner", "coordinator")
    graph.add_edge("reviewer", "coordinator")
    graph.add_edge("finalize", END)

    graph.add_conditional_edges(
        "coordinator",
        route_from_decision,
        {
            "log_analyst": "log_analyst",
            "repo_context": "repo_context",
            "reproduction": "reproduction",
            "fix_planner": "fix_planner",
            "reviewer": "reviewer",
            "finalize": "finalize",
        },
    )

    return graph.compile()
