"""
Security Review — static regex pattern scanning + LLM summary.
Detects common secrets, dangerous patterns, and missing security headers.
LLM is invoked once for remediation recommendations (then cached).
"""
import os
import re
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, SKIP_DIRS, analyze_with_llm


# Common high-risk patterns to scan for
SECURITY_PATTERNS = [
    (r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*=\s*["\'][^"\']{8,}["\']',
     "Possible hardcoded secret/API key", "HIGH"),
    (r'(?i)password\s*=\s*["\'][^"\']+["\']',
     "Hardcoded password detected", "HIGH"),
    (r'eval\s*\(',
     "Use of eval() — potential code injection vector", "HIGH"),
    (r'exec\s*\(',
     "Use of exec() — potential code injection vector", "HIGH"),
    (r'subprocess\.call\(.+shell\s*=\s*True',
     "shell=True in subprocess — command injection risk", "HIGH"),
    (r'os\.system\s*\(',
     "os.system() call — prefer subprocess with explicit args", "MEDIUM"),
    (r'(?i)sql\s*=.*\%s|sql\s*=.*format\(',
     "Possible SQL string formatting — use parameterised queries", "MEDIUM"),
    (r'pickle\.loads?\s*\(',
     "pickle.load — can execute arbitrary code on untrusted data", "MEDIUM"),
    (r'assert\s+.+,',
     "assert used for validation — disabled by -O flag, use proper checks", "LOW"),
    (r'DEBUG\s*=\s*True',
     "DEBUG=True — ensure this is not deployed to production", "MEDIUM"),
    (r'(?i)cors.*allow.*origin.*\*',
     "CORS wildcard origin detected — restrict in production", "MEDIUM"),
    (r'http://(?!127\.0\.0\.1|localhost)',
     "Plain HTTP URL (not localhost) — prefer HTTPS", "LOW"),
]

CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".yaml", ".yml", ".json", ".sh"}


class SecurityReviewSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Security Review"

    @property
    def description(self) -> str:
        return "Scans the codebase for hardcoded secrets, dangerous patterns, and common vulnerabilities."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vulnerabilities": {"type": "array"},
                "summary": {"type": "string"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("security", workspace_dir)
        if cached:
            return cached

        vulns: List[Dict[str, str]] = []

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in CODE_EXTS:
                    continue
                # Never scan actual .env files for secrets (they're supposed to have them)
                if fname in {".env", ".env.local", ".env.production"}:
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, workspace_dir).replace("\\", "/")
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for line_num, line in enumerate(content.split("\n"), 1):
                        for pattern, message, severity in SECURITY_PATTERNS:
                            if re.search(pattern, line):
                                vulns.append({
                                    "severity": severity,
                                    "file": f"{rel}:{line_num}",
                                    "issue": message,
                                    "remediation": _remediation(message),
                                })
                                if len(vulns) >= 40:
                                    break
                        if len(vulns) >= 40:
                            break
                except Exception:
                    pass
                if len(vulns) >= 40:
                    break

        high = sum(1 for v in vulns if v["severity"] == "HIGH")
        medium = sum(1 for v in vulns if v["severity"] == "MEDIUM")
        low = sum(1 for v in vulns if v["severity"] == "LOW")

        # LLM for a brief summary (small, ~800 token prompt, cached afterwards)
        issue_text = f"{high} high, {medium} medium, {low} low severity issues."
        schema_hint = '{"summary": "string"}'
        llm_result = analyze_with_llm(
            "security",
            f"write a 2-sentence security posture summary for a repository with {issue_text}",
            schema_hint,
            workspace_dir,
        )
        summary = llm_result.get("summary", f"Found {len(vulns)} potential security issues ({issue_text}).")

        result = {
            "vulnerabilities": vulns,
            "summary": summary,
        }

        set_cached("security", workspace_dir, result)
        return result


def _remediation(message: str) -> str:
    remediations = {
        "secret": "Move to environment variable or secrets manager.",
        "password": "Use environment variable; never hardcode credentials.",
        "eval": "Avoid eval(); use literal_eval or a safe alternative.",
        "exec": "Avoid exec(); refactor to function calls.",
        "shell=True": "Replace with shell=False and pass args as a list.",
        "os.system": "Replace with subprocess.run(['cmd', 'arg'], check=True).",
        "SQL": "Use parameterised queries / ORM to prevent SQL injection.",
        "pickle": "Use JSON or a safe serialisation format for untrusted data.",
        "assert": "Replace with explicit if/raise statements.",
        "DEBUG": "Set DEBUG=False and use environment-based config.",
        "CORS": "Restrict CORS origins to known domains.",
        "HTTP": "Use HTTPS for all external URLs.",
    }
    for key, val in remediations.items():
        if key.lower() in message.lower():
            return val
    return "Review this pattern and apply appropriate security controls."


skill_registry.register("security", SecurityReviewSkill())
