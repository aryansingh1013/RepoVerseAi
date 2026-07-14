import json
from typing import Dict, Any, Optional
from backend.skills.registry import skill_registry

class SkillManager:
    """
    Orchestrator for executing AI Skills and generating standardized Markdown reports.
    """
    def run_skill(self, slug: str, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        skill = skill_registry.get_skill(slug)
        if not skill:
            raise ValueError(f"Skill '{slug}' not found in registry.")

        print(f"SkillManager: Running skill '{slug}'...")
        try:
            return skill.execute(query, agent_graph, workspace_dir)
        except Exception as e:
            print(f"SkillManager Error executing '{slug}': {e}")
            return {
                "error": f"Failed to execute skill workflow: {str(e)}",
                "citations": [],
                "confidence": 0.0
            }

    def export_report(self, slug: str, result: Dict[str, Any]) -> str:
        """
        Converts a skill's structured JSON output into a clean, comprehensive Markdown report.
        """
        skill = skill_registry.get_skill(slug)
        if not skill:
            return f"# Error: Skill '{slug}' not found."

        title = f"# RepoVerse AI - {skill.name} Report\n"
        desc = f"> {skill.description}\n\n"
        divider = "---\n\n"
        
        body = ""
        # Render standard sections based on skill results dynamically
        if slug == "overview":
            body += "## 🌌 Repository landing Overview\n\n"
            body += f"**Summary:** {result.get('summary', 'No summary generated.')}\n\n"
            body += "### 🛠️ Tech Stack & Programming Languages\n"
            for tech in result.get("tech_stack", []):
                body += f"- `{tech}`\n"
            body += "\n### ⭐ Key Entry Points\n"
            for ep in result.get("entry_points", []):
                body += f"- `{ep}`\n"
            body += "\n### ⚙️ Main Components & Dependencies\n"
            for comp in result.get("main_components", []):
                body += f"- `{comp}`\n"
                
        elif slug == "architecture":
            body += "## 🏛️ System Architecture Analysis\n\n"
            body += f"**Core Layout:** {result.get('description', '')}\n\n"
            body += "### 📊 Architectural Layers\n"
            for layer in result.get("layers", []):
                body += f"- **{layer.get('name', '')}**: {layer.get('description', '')}\n"
            if result.get("diagram"):
                body += "\n### 🗺️ Mermaid Layer Diagram\n\n"
                body += f"```mermaid\n{result.get('diagram')}\n```\n\n"
                
        elif slug == "health":
            body += "## 🩺 Code Cleanliness Scorecard\n\n"
            body += f"### 📊 Overall Health Score: **{result.get('score', 0)}/100**\n\n"
            body += "### ⚠️ Identified Quality Issues\n"
            for issue in result.get("issues", []):
                body += f"- **[{issue.get('severity', 'LOW')}]** {issue.get('file', '')}: {issue.get('message', '')}\n"
            body += "\n### 🧹 Proposed Refactoring Actions\n"
            for opt in result.get("recommendations", []):
                body += f"- [ ] {opt}\n"
                
        elif slug == "dependencies":
            body += "## 🔌 Import Dependency Explorer\n\n"
            body += "### 🔗 Dependencies Relations Map\n\n"
            body += "| Source Module | Target Module | Type |\n"
            body += "| :--- | :--- | :--- |\n"
            for rel in result.get("dependencies_map", []):
                body += f"| `{rel.get('source')}` | `{rel.get('target')}` | {rel.get('relation_type', 'imports')} |\n"
            if result.get("circular_dependencies"):
                body += "\n### 🚨 Circular References Warning\n"
                for circ in result.get("circular_dependencies", []):
                    body += f"- Circular Chain: `{' ➔ '.join(circ)}`\n"
                    
        elif slug == "timeline":
            body += "## 📅 Repository Timeline History\n\n"
            body += "### 🔨 Commit Chronologies & Milestones\n"
            for item in result.get("timeline", []):
                body += f"- **{item.get('date', '')}** (by *{item.get('author', 'Unknown')}*): {item.get('message', '')}\n"
            body += "\n### 🏆 Top Repository Contributors\n"
            for c in result.get("contributors", []):
                body += f"- **{c.get('name', '')}**: {c.get('commits', 0)} commits\n"
                
        elif slug == "learning":
            body += "## 🎓 Developer Onboarding Lessons\n\n"
            for idx, lesson in enumerate(result.get("lessons", [])):
                body += f"### Lesson {idx + 1}: {lesson.get('title', '')}\n\n"
                body += f"{lesson.get('content', '')}\n\n"
            body += "### 📝 Quiz Time\n\n"
            for idx, q in enumerate(result.get("quiz", [])):
                body += f"**Q{idx + 1}: {q.get('question', '')}**\n"
                for i, opt in enumerate(q.get("options", [])):
                    body += f" - {chr(65+i)}) {opt}\n"
                body += f"\n*Correct Answer: {q.get('answer', '')}*\n\n"
                
        elif slug == "readme":
            body += "## 📝 Auto-Generated README template\n\n"
            body += result.get("markdown", "")
            
        elif slug == "security":
            body += "## 🛡️ Codebase Security Audit Report\n\n"
            body += "### 🚨 Found Vulnerability Alerts\n\n"
            body += "| Severity | Target File | Vulnerability Alert | Recommendation |\n"
            body += "| :--- | :--- | :--- | :--- |\n"
            for issue in result.get("vulnerabilities", []):
                body += f"| **{issue.get('severity', 'LOW')}** | `{issue.get('file', '')}` | {issue.get('issue', '')} | {issue.get('remediation', '')} |\n"
                
        elif slug == "performance":
            body += "## ⚡ Runtime Performance Review\n\n"
            body += "### ⚙️ Optimization Insights\n"
            for item in result.get("optimizations", []):
                body += f"- **[{item.get('impact', 'MEDIUM')}]** {item.get('file', '')}: {item.get('issue', '')}\n"
                body += f"  - *Fix Proposal:* {item.get('suggestion', '')}\n\n"

        else:
            # Fallback formatting
            body += f"```json\n{json.dumps(result, indent=2)}\n```"

        footer = "\n---\n*Report generated automatically by RepoVerse AI Skills Engine.*"
        return title + desc + divider + body + footer

skill_manager = SkillManager()
