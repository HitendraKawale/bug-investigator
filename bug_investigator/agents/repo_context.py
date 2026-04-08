from __future__ import annotations

from pathlib import Path

from bug_investigator.agents.base import BaseAgent
from bug_investigator.tools.repo import find_symbol_usages, read_file_snippet, read_repo_tree


class RepoContextAgent(BaseAgent):
    name = "RepoContextAgent"

    def run(self, state: dict) -> dict:
        self.trace("agent_start")
        repo_path = state["repo_path"]

        tree = read_repo_tree(repo_path)
        service_file = str(Path(repo_path) / "service.py")
        client_file = str(Path(repo_path) / "client.py")
        cache_file = str(Path(repo_path) / "cache.py")

        service_snippet = read_file_snippet(service_file)
        client_snippet = read_file_snippet(client_file)
        cache_snippet = read_file_snippet(cache_file)
        usages = find_symbol_usages(repo_path, "fetch_profile")

        result = {
            "repo_tree": tree["tree_text"],
            "key_files": [
                service_snippet,
                client_snippet,
                cache_snippet,
            ],
            "symbol_usages": usages["hits"],
            "suspected_bug_path": "service.py cache-miss branch calling async client incorrectly",
        }
        self.trace("agent_end", suspected_bug_path=result["suspected_bug_path"])
        return {"repo_context": result}
