from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from bug_investigator.config import Settings


def _extract_json(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1:
        raise ValueError("No JSON object found in model output")

    return json.loads(text[first:last + 1])


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = bool(settings.llm_api_key)
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    def invoke_text(self, system_prompt: str, user_payload: dict[str, Any]) -> str:
        content = json.dumps(user_payload, indent=2)
        resp = self.client.chat.completions.create(
            model=self.settings.llm_model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
        return resp.choices[0].message.content or ""

    def invoke_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict:
        raw = self.invoke_text(system_prompt, user_payload)
        return _extract_json(raw)
