# Bug Investigator

A LangGraph-based multi-agent bug investigation system.

It ingests:

- a bug report
- logs
- a small repo snapshot

It outputs:

- a minimal repro script
- a root-cause hypothesis
- a patch plan
- a final structured JSON report

## Features

- LangGraph workflow
- LLM coordinator with Python policy guardrails
- OpenAI and Ollama-compatible model backend
- deterministic tools for logs, repo inspection, and sandboxed repro execution
- JSONL tracing
- reviewer/critic loop

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest
bug-investigator run \
  --bug-report inputs/bug_report.md \
  --logs inputs/app.log \
  --repo inputs/mini_repo \
  --out outputs/run_001 bug-investigator
```
