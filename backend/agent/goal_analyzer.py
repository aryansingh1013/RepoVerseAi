import json
from backend.agent.reasoning_models import Goal

class GoalAnalyzer:
    def __init__(self, llm_caller=None):
        self.llm_caller = llm_caller

    def analyze_goal(self, query: str) -> Goal:
        """
        Ingests user query, resolves intent, expected outcomes, and risks.
        """
        system_prompt = (
            "You are RepoVerse AI Goal Analyzer.\n"
            "Analyze the user's query and output a JSON object matching the following structure:\n"
            "{\n"
            "  \"intent\": \"explain | debug | comparison | refactor | general\",\n"
            "  \"expected_output\": \"Description of expected answer output format\",\n"
            "  \"required_knowledge\": [\"docs\", \"source\", \"git\", \"tests\"],\n"
            "  \"risk_level\": \"low | medium | high\",\n"
            "  \"confidence\": 0.95\n"
            "}\n\n"
            "Rules: Output ONLY raw JSON."
        )

        if self.llm_caller:
            response = self.llm_caller([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ], json_mode=True)
            if response:
                try:
                    data = json.loads(response)
                    return Goal(
                        intent=data.get("intent", "general"),
                        expected_output=data.get("expected_output", "Answer summary"),
                        required_knowledge=data.get("required_knowledge", []),
                        risk_level=data.get("risk_level", "low"),
                        confidence=data.get("confidence", 1.0)
                    )
                except Exception:
                    pass

        # Heuristic Fallback
        query_lower = query.lower()
        
        intent = "general"
        expected_output = "Text explanation"
        required_knowledge = ["source"]
        risk_level = "low"
        confidence = 0.8
        
        if "compare" in query_lower or "difference" in query_lower:
            intent = "comparison"
            expected_output = "Structural comparison overview"
            required_knowledge = ["source", "docs"]
        elif "pytest" in query_lower or "test" in query_lower or "bug" in query_lower or "error" in query_lower:
            intent = "debug"
            expected_output = "Error root cause analysis and fix proposal"
            required_knowledge = ["source", "tests"]
            risk_level = "high" # Running test commands has execution risk
        elif "explain" in query_lower or "how does" in query_lower:
            intent = "explain"
            expected_output = "Architectural explanation summary"
            required_knowledge = ["source"]
        elif "refactor" in query_lower or "change" in query_lower or "rewrite" in query_lower:
            intent = "refactor"
            expected_output = "Code patch draft diff"
            required_knowledge = ["source"]
            risk_level = "medium"

        return Goal(
            intent=intent,
            expected_output=expected_output,
            required_knowledge=required_knowledge,
            risk_level=risk_level,
            confidence=confidence
        )
