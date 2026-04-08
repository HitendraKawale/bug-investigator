from __future__ import annotations

import uuid
from pathlib import Path

import typer

from bug_investigator.agents.base import AgentContext
from bug_investigator.config import load_settings
from bug_investigator.io.readers import ensure_dir
from bug_investigator.io.trace import TraceLogger
from bug_investigator.llm import LLMClient
from bug_investigator.orchestration.graph import build_graph
from bug_investigator.state import init_state

app = typer.Typer(help="Bug Investigator CLI")


@app.command()
def run(
    bug_report: str = typer.Option(..., exists=True, help="Path to bug report file"),
    logs: str = typer.Option(..., exists=True, help="Path to log file"),
    repo: str = typer.Option(..., exists=True, file_okay=False, help="Path to mini repo"),
    out: str = typer.Option(..., help="Output directory"),
):
    settings = load_settings()
    ensure_dir(out)

    run_id = Path(out).name or f"run_{uuid.uuid4().hex[:8]}"
    trace_path = str(Path(out) / "trace.jsonl")

    tracer = TraceLogger(trace_path, settings)
    llm = LLMClient(settings)
    ctx = AgentContext(settings=settings, llm=llm, tracer=tracer)

    tracer.event(
        "run_start",
        run_id=run_id,
        provider=settings.llm_provider,
        model=settings.llm_model,
    )

    graph = build_graph(ctx)
    state = init_state(
        run_id=run_id,
        bug_report_path=bug_report,
        log_path=logs,
        repo_path=repo,
        output_dir=out,
    )
    state["trace_path"] = trace_path
    state["_max_retries"] = settings.max_retries_per_step

    final_state = graph.invoke(state)

    tracer.event(
        "run_end",
        run_id=run_id,
        status=final_state.get("status", "unknown"),
        final_report_path=final_state.get("final_report_path", ""),
    )

    typer.echo(f"Done. Final report: {final_state.get('final_report_path')}")
    if final_state.get("patch_diff_path"):
        typer.echo(f"Suggested patch diff: {final_state['patch_diff_path']}")


if __name__ == "__main__":
    app()
