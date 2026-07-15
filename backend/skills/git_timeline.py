"""
Git Timeline — reads from .git/logs/HEAD and git object store locally, 0 LLM tokens.
Falls back to a "no git repo" message gracefully.
"""
import os
import subprocess
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached


class GitTimelineSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Git Timeline"

    @property
    def description(self) -> str:
        return "Reads commit history and contributors directly from the local .git store — no LLM required."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "timeline": {"type": "array"},
                "contributors": {"type": "array"},
                "total_commits": {"type": "integer"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("timeline", workspace_dir)
        if cached:
            return cached

        git_dir = os.path.join(workspace_dir, ".git")
        timeline: List[Dict[str, str]] = []
        contributors: Dict[str, int] = {}

        if not os.path.exists(git_dir):
            result = {
                "timeline": [{"date": "—", "author": "—", "message": "No .git directory found in this workspace."}],
                "contributors": [],
                "total_commits": 0,
            }
            return result

        # Try running git log via subprocess
        try:
            proc = subprocess.run(
                ["git", "-C", workspace_dir, "log",
                 "--pretty=format:%H|%an|%ad|%s",
                 "--date=short",
                 "-n", "50"],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.strip().split("\n"):
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        _, author, date, message = parts
                        timeline.append({
                            "date": date,
                            "author": author,
                            "message": message[:120]
                        })
                        contributors[author] = contributors.get(author, 0) + 1
        except Exception as e:
            print(f"GitTimeline: git subprocess failed — {e}")

        # Fallback: read .git/logs/HEAD directly
        if not timeline:
            head_log = os.path.join(git_dir, "logs", "HEAD")
            if os.path.exists(head_log):
                try:
                    with open(head_log, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[-50:]
                    for line in reversed(lines):
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            meta, message = parts
                            meta_parts = meta.split(" ")
                            author = " ".join(meta_parts[3:-2]) if len(meta_parts) > 5 else "Unknown"
                            timeline.append({
                                "date": "—",
                                "author": author.replace("<", "").split(">")[0].strip(),
                                "message": message.strip()[:120]
                            })
                            contributors[author] = contributors.get(author, 0) + 1
                except Exception:
                    pass

        if not timeline:
            timeline = [{"date": "—", "author": "—", "message": "Could not read git history."}]

        contributor_list = sorted(
            [{"name": k, "commits": v} for k, v in contributors.items()],
            key=lambda x: -x["commits"]
        )[:10]

        result = {
            "timeline": timeline[:40],
            "contributors": contributor_list,
            "total_commits": len(timeline),
        }

        set_cached("timeline", workspace_dir, result)
        return result


skill_registry.register("timeline", GitTimelineSkill())
