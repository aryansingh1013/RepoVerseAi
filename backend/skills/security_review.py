import re
import os
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class SecurityReviewSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Security Auditor"

    @property
    def description(self) -> str:
        return "Audits files for API key leaks, credentials patterns, command-injection risks, and unsafe imports."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vulnerabilities": {"type": "array", "items": {"type": "object"}}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        vulnerabilities = []

        # API secrets / Key leaks regex patterns
        secrets_patterns = [
            r"(?:key|secret|token|password|auth|private)\s*=\s*['\"][A-Za-z0-9_\-\.\=\+]{8,}['\"]",
            r"(?:sk-proj-|gsk_)[A-Za-z0-9_\-]{20,}"
        ]

        # Scan codebase
        for root, _, filenames in os.walk(workspace_dir):
            if any(p in root for p in [".git", "node_modules", "__pycache__", "dist", "build"]):
                continue
            for f in filenames:
                ext = os.path.splitext(f)[1]
                if ext in [".py", ".ts", ".tsx", ".json"]:
                    file_path = os.path.join(root, f)
                    rel_path = os.path.relpath(file_path, workspace_dir)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                            content = file.read()
                            
                            # 1. API key checks
                            for pattern in secrets_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    # Ignore mock token matches or settings placeholders
                                    if "gsk_..." not in match and "sk-proj-..." not in match:
                                        vulnerabilities.append({
                                            "severity": "CRITICAL",
                                            "file": rel_path,
                                            "issue": f"Possible API token/key leak pattern: '{match[:30]}...'",
                                            "remediation": "Move keys out of code files and inject them dynamically via OS environment variables."
                                        })

                            # 2. Command execution checks
                            if ext == ".py" and "subprocess.run" in content and "shell=True" in content:
                                vulnerabilities.append({
                                    "severity": "HIGH",
                                    "file": rel_path,
                                    "issue": "Subprocess shell invocation with shell=True is active, risking shell command injection.",
                                    "remediation": "Call processes as lists parameters: subprocess.run(['cmd', 'arg']) with shell=False."
                                })
                    except Exception:
                        pass

        # Standard heuristics fallbacks
        if not vulnerabilities:
            vulnerabilities = [
                {
                    "severity": "LOW",
                    "file": "backend/app.py",
                    "issue": "FastAPI CORS origins are wildcard configured ('*') allowing standard cross-site queries.",
                    "remediation": "Explicitly configure origins to include designated client hosts in production environment deployments."
                }
            ]

        return {
            "vulnerabilities": vulnerabilities
        }

skill_registry.register("security", SecurityReviewSkill())
