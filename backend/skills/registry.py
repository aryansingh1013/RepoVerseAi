from typing import Dict, List, Any
from backend.skills.base_skill import BaseSkill

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, slug: str, skill: BaseSkill):
        self._skills[slug] = skill
        print(f"SkillRegistry: Registered skill '{slug}' ({skill.name})")

    def get_skill(self, slug: str) -> BaseSkill:
        return self._skills.get(slug)

    def list_skills(self) -> List[Dict[str, Any]]:
        return [
            {
                "slug": slug,
                "name": skill.name,
                "description": skill.description,
                "required_capabilities": skill.required_capabilities,
                "result_schema": skill.result_schema
            }
            for slug, skill in self._skills.items()
        ]

skill_registry = SkillRegistry()
