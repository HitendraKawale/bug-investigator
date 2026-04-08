from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bug_investigator.config import Settings
from bug_investigator.io.trace import TraceLogger
from bug_investigator.llm import LLMClient


@dataclass
class AgentContext:
    settings: Settings
    llm: LLMClient
    tracer: TraceLogger


class BaseAgent:
    name = "BaseAgent"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def trace(self, event: str, **data) -> None:
        self.ctx.tracer.event(event, agent=self.name, **data)

    def invoke_json_or_fallback(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            self.trace("llm_call", payload_keys=list(user_payload.keys()))
            result = self.ctx.llm.invoke_json(system_prompt, user_payload)
            self.trace("llm_result", result_keys=list(result.keys()))
            return result
        except Exception as e:
            self.trace("llm_fallback", error=str(e))
            return fallback
