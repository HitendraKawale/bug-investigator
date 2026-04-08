from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    source_path: str
    line_start: int | None = None
    line_end: int | None = None
    excerpt: str
    relevance: str


class CoordinatorDecision(BaseModel):
    next_action: str
    reason: str
    required_inputs_present: bool = True
    blocking_gaps: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class FinalReport(BaseModel):
    run_id: str
    status: str
    input_artifacts: dict
    run_summary: dict = Field(default_factory=dict)

    triage_summary: dict | None = None
    log_analysis: dict | None = None
    repo_context: dict | None = None
    reproduction: dict | None = None
    root_cause: dict | None = None
    patch_plan: dict | None = None
    validation_plan: dict | None = None
    review_verdict: dict | None = None

    evidence: list[dict] = Field(default_factory=list)
    open_questions: list[dict] = Field(default_factory=list)
    trace_artifacts: dict = Field(default_factory=dict)
