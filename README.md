# Bug Investigator

A LangGraph-based multi-agent bug investigation system that:

1. reads a bug report, logs, and a repo snapshot,
2. reproduces the issue with a generated script,
3. proposes a root-cause hypothesis,
4. outputs a patch plan and validation steps.

## Input mode

This project uses **Option A: Provided Mini-Repo**.

Included inputs:
- `inputs/bug_report.md`
- `inputs/app.log`
- `inputs/mini_repo/`

## Agents

- Triage Agent
- Log Analyst Agent
- Reproduction Agent
- Fix Planner Agent
- Reviewer/Critic Agent
- Coordinator Agent
- Repo Context Agent

## Tech

- Python
- LangGraph
- Typer CLI
- Ollama or OpenAI-compatible model backend
- Streamlit (tiny optional UI)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
uv sync --extra dev
cp .env.example .env
```
## Example ```.env```
```
#ollama
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b-instruct
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
TRACE_TO_CONSOLE=true
MAX_RETRIES_PER_STEP=2
REPRO_TIMEOUT_SEC=8

#OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your_key_here
TRACE_TO_CONSOLE=true
MAX_RETRIES_PER_STEP=2
REPRO_TIMEOUT_SEC=8
```

## Run tests
```bash
uv run pytest
```

## Run CLI
#### if repo forked locally
```bash
uv run bug-investigator \
  --bug-report inputs/bug_report.md \
  --logs inputs/app.log \
  --repo inputs/mini_repo \
  --out outputs/run_demo
```
#### if you have a github url(although you will need to pass the bug report and logs locally
```bash
uv run bug-investigator \
  --bug-report inputs/bug_report.md \
  --logs inputs/app.log \
  --repo https://github.com/example/repo \
  --out outputs/run_demo_remote
```
## Run Streamlit ui
```bash
uv run streamlit run streamlit_app.py
```
## Generated outputs

For each run, the system writes:

- ```outputs/<run_id>/repro/repro_case.py```
- ```outputs/<run_id>/investigation_report.json```
- ```outputs/<run_id>/artifacts/suggested.patch```
- ```outputs/<run_id>/trace.jsonl```


## Final JSON includes
- bug summary
- evidence
- repro artifact path + command
- root-cause hypothesis
- patch plan
- validation plan
- open questions
- trace artifact paths
