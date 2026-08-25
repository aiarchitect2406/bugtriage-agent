"""Dynamic Skill Registry and Progressive Disclosure Engine for ADK 2.0.

This module implements progressive disclosure (Section 3.1 & Section 6 of the Agent Specification):
- Discovers and indexes skills from markdown definitions (SKILL.md).
- Avoids pre-loading all tool schemas and lengthy instructions into the root context window at startup.
- Dynamically loads specific skill instructions and attaches only the required tool schemas when activation cues are triggered.
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field

from app.observability.logger import StructuredLogger

logger = logging.getLogger(__name__)

class SkillDescriptor(BaseModel):
    """Lightweight metadata descriptor for an indexed skill."""
    name: str = Field(..., description="Unique skill name (kebab-case)")
    description: str = Field(..., description="Brief one-line summary of capability")
    activation_cues: List[str] = Field(default_factory=list, description="Trigger keywords/phrases")
    tools: List[str] = Field(default_factory=list, description="Bound tool function names")
    skill_path: str = Field(..., description="File path to SKILL.md")
    instruction_cache: Optional[str] = Field(default=None, description="Cached instruction body")

class DynamicSkillRegistry:
    """Enterprise Progressive Disclosure Registry for managing dynamic agent skills."""

    _instance: Optional["DynamicSkillRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DynamicSkillRegistry, cls).__new__(cls)
            cls._instance._skills = {}
            cls._instance._tool_map = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._register_default_tools()
            self.discover_skills()
            self._initialized = True

    def _register_default_tools(self) -> None:
        """Registers callable tool functions into the registry tool map."""
        from app.tools import (
            sanitize_logs_and_extract_stack,
            query_similar_bugs_by_vector,
            resolve_codeowners_and_blame,
            execute_reproduction_and_sandbox_fix,
            create_draft_pull_request,
        )
        from app.hitl.card_renderer import render_a2ui_review_card

        self._tool_map = {
            "sanitize_logs_and_extract_stack": sanitize_logs_and_extract_stack,
            "query_similar_bugs_by_vector": query_similar_bugs_by_vector,
            "resolve_codeowners_and_blame": resolve_codeowners_and_blame,
            "execute_reproduction_and_sandbox_fix": execute_reproduction_and_sandbox_fix,
            "render_a2ui_review_card": render_a2ui_review_card,
            "create_draft_pull_request": create_draft_pull_request,
        }

    def discover_skills(self, search_dirs: Optional[List[str]] = None) -> Dict[str, SkillDescriptor]:
        """Scans skill directories, indexing lightweight descriptors with progressive disclosure."""
        root = os.getcwd()
        dirs_to_search = search_dirs or [
            os.path.join(root, "skills"),
            os.path.join(root, ".agents", "skills")
        ]

        self._skills.clear()

        for base_dir in dirs_to_search:
            if not os.path.exists(base_dir):
                continue
            for entry in os.listdir(base_dir):
                skill_dir = os.path.join(base_dir, entry)
                skill_md_path = os.path.join(skill_dir, "SKILL.md")
                if os.path.isdir(skill_dir) and os.path.exists(skill_md_path):
                    descriptor = self._parse_skill_metadata(skill_md_path)
                    if descriptor:
                        self._skills[descriptor.name] = descriptor

        logger.info(f"DynamicSkillRegistry: Indexed {len(self._skills)} skills with progressive disclosure.")
        return self._skills

    def _parse_skill_metadata(self, skill_md_path: str) -> Optional[SkillDescriptor]:
        """Parses YAML frontmatter from a SKILL.md file without loading full bodies into main prompt."""
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if frontmatter_match:
                fm_raw = frontmatter_match.group(1)
                metadata = yaml.safe_load(fm_raw) or {}
                return SkillDescriptor(
                    name=metadata.get("name", os.path.basename(os.path.dirname(skill_md_path))),
                    description=metadata.get("description", "Enterprise capability skill"),
                    activation_cues=metadata.get("activation_cues", []),
                    tools=metadata.get("tools", []),
                    skill_path=skill_md_path,
                )
            else:
                name = os.path.basename(os.path.dirname(skill_md_path))
                return SkillDescriptor(
                    name=name,
                    description=f"Domain skill for {name}",
                    activation_cues=[name.replace("-", "_")],
                    tools=[],
                    skill_path=skill_md_path
                )
        except Exception as exc:
            logger.warning(f"Failed to parse skill metadata at {skill_md_path}: {exc}")
            return None

    def get_progressive_prompt_catalog(self, filter_domain_only: bool = True) -> str:
        """Returns a token-efficient summary catalog of indexed skills for the root coordinator prompt.
        
        This prevents context window bloat by only providing names, summaries, and activation cues,
        omitting all heavy tool schemas and complete markdown instructions.
        """
        lines = [
            "Available Domain Skills (Loaded on-demand via Progressive Disclosure):"
        ]
        for name, desc in self._skills.items():
            if filter_domain_only and ("agent-" in name or "spec-" in name or "zero-" in name or "session-" in name or "eval-" in name or "observability-" in name or "adk-" in name):
                continue
            cues = ", ".join(f"'{c}'" for c in desc.activation_cues[:4])
            short_desc = desc.description.split(".")[0]
            lines.append(f"- **{name}**: {short_desc}. (Activation cues: [{cues}])")
        return "\n".join(lines)


    def load_skill_instructions(self, skill_name: str) -> str:
        """Progressively loads the complete markdown instruction body only when the skill is activated."""
        descriptor = self._skills.get(skill_name)
        if not descriptor:
            return f"Skill '{skill_name}' not found in registry."

        if descriptor.instruction_cache:
            return descriptor.instruction_cache

        try:
            with open(descriptor.skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Remove YAML frontmatter if present
            clean_content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)
            descriptor.instruction_cache = clean_content.strip()
            return descriptor.instruction_cache
        except Exception as exc:
            return f"Error loading instructions for {skill_name}: {exc}"

    def get_tools_for_skill(self, skill_name: str) -> List[Callable]:
        """Dynamically retrieves only the specific tool functions bound to the activated skill."""
        descriptor = self._skills.get(skill_name)
        if not descriptor:
            return []

        tools = []
        for tool_name in descriptor.tools:
            if tool_name in self._tool_map:
                tools.append(self._tool_map[tool_name])
        return tools

    def resolve_skill_by_cue(self, cue_or_task: str) -> Optional[SkillDescriptor]:
        """Resolves the appropriate skill based on an incoming trigger cue or task keyword."""
        cue_lower = cue_or_task.lower()
        for name, desc in self._skills.items():
            if name.lower() in cue_lower:
                return desc
            for cue in desc.activation_cues:
                if cue.lower() in cue_lower:
                    return desc
        return None
