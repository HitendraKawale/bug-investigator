from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from bug_investigator.config import Settings


class TraceLogger:
    def __init__(self, path: str, settings: Settings):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = settings

    def event(self, event: str, **data) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **data,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        if self.settings.trace_to_console:
            summary = payload.copy()
            if "stdout" in summary and len(str(summary["stdout"])) > 180:
                summary["stdout"] = str(summary["stdout"])[:180] + "..."
            if "stderr" in summary and len(str(summary["stderr"])) > 180:
                summary["stderr"] = str(summary["stderr"])[:180] + "..."
            print(json.dumps(summary))
