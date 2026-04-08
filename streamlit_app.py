from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from bug_investigator.agents.base import AgentContext
from bug_investigator.config import load_settings
from bug_investigator.io.readers import ensure_dir
from bug_investigator.io.trace import TraceLogger
from bug_investigator.llm import LLMClient
from bug_investigator.orchestration.graph import build_graph
from bug_investigator.state import init_state


st.set_page_config(page_title="Bug Investigator", layout="wide")


def run_investigation(
    bug_report: str,
    logs: str,
    repo: str,
    out_dir: str,
) -> dict:
    settings = load_settings()
    ensure_dir(out_dir)

    run_id = Path(out_dir).name or f"run_{uuid.uuid4().hex[:8]}"
    trace_path = str(Path(out_dir) / "trace.jsonl")

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
        output_dir=out_dir,
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

    return final_state


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


st.title("Bug Investigator")
st.caption("Tiny UI for the LangGraph multi-agent bug investigation pipeline")

with st.sidebar:
    st.header("Inputs")

    bug_report_path = st.text_input("Bug report path", "inputs/bug_report.md")
    log_path = st.text_input("Log path", "inputs/app.log")
    repo_path = st.text_input("Repo path", "inputs/mini_repo")
    out_dir = st.text_input("Output dir", f"outputs/ui_run_{uuid.uuid4().hex[:6]}")

    run_clicked = st.button("Run investigation", type="primary", use_container_width=True)

    st.divider()
    st.subheader("Current model")
    try:
        settings = load_settings()
        st.code(
            f"provider={settings.llm_provider}\nmodel={settings.llm_model}",
            language="text",
        )
    except Exception as e:
        st.error(f"Could not load settings: {e}")


if run_clicked:
    with st.spinner("Running investigation..."):
        try:
            final_state = run_investigation(
                bug_report=bug_report_path,
                logs=log_path,
                repo=repo_path,
                out_dir=out_dir,
            )
            st.session_state["final_state"] = final_state
        except Exception as e:
            st.exception(e)

final_state = st.session_state.get("final_state")

if not final_state:
    st.info("Choose your input paths in the sidebar and click 'Run investigation'.")
    st.stop()

report_path = final_state.get("final_report_path")
status = final_state.get("status", "unknown")

left, right = st.columns([1, 1])

with left:
    st.subheader("Run result")
    st.metric("Status", status)
    st.text_input("Final report path", value=report_path or "", disabled=True)

with right:
    patch_diff_path = final_state.get("patch_diff_path", "")
    st.subheader("Artifacts")
    st.text_input("Patch diff path", value=patch_diff_path, disabled=True)
    trace_path = str(Path(out_dir) / "trace.jsonl")
    st.text_input("Trace path", value=trace_path, disabled=True)

if not report_path or not Path(report_path).exists():
    st.warning("No final report file found.")
    st.stop()

report = load_json(report_path)

st.divider()

summary = report.get("run_summary", {})
st.subheader("Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Reviewer verdict", summary.get("reviewer_verdict", ""))
c2.metric("Repro matched", str(summary.get("repro_matched_expected_signature", False)))
c3.metric("Repro exit code", str(summary.get("repro_exit_code", "")))
c4.metric("Patch ready", str(summary.get("patch_plan_ready", False)))

st.write(summary.get("problem", ""))

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Root cause", "Patch plan", "Reproduction", "Evidence", "Raw JSON"]
)

with tab1:
    st.json(report.get("root_cause", {}), expanded=True)

with tab2:
    st.json(report.get("patch_plan", {}), expanded=True)
    patch_path = report.get("trace_artifacts", {}).get("patch_diff_path")
    if patch_path and Path(patch_path).exists():
        st.code(Path(patch_path).read_text(encoding="utf-8"), language="diff")

with tab3:
    st.json(report.get("reproduction", {}), expanded=True)

with tab4:
    st.json(report.get("evidence", []), expanded=False)

with tab5:
    st.download_button(
        "Download report JSON",
        data=json.dumps(report, indent=2),
        file_name="investigation_report.json",
        mime="application/json",
    )
    st.code(json.dumps(report, indent=2), language="json")
