"""Native ADK 2.0 Progressive Disclosure Skill Loader & Discovery Catalog.

Grounded in Google ADK recipes (long-horizon-harness), this module implements
runtime discovery and progressive disclosure for SKILL.md modular capabilities.
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field

from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.tools.review_tools import review_code_patch_with_claude
from app.tools.git_tools import create_draft_pull_request
from app.hitl.card_renderer import render_a2ui_review_card

logger = logging.getLogger(__name__)

# Global registry mapping tool names in SKILL.md frontmatter to callable Python tools
TOOL_REGISTRY: Dict[str, Callable] = {
    "sanitize_logs_and_extract_stack": sanitize_logs_and_extract_stack,
    "query_similar_bugs_by_vector": query_similar_bugs_by_vector,
    "resolve_codeowners_and_blame": resolve_codeowners_and_blame,
    "execute_reproduction_and_sandbox_fix": execute_reproduction_and_sandbox_fix,
    "review_code_patch_with_claude": review_code_patch_with_claude,
    "create_draft_pull_request": create_draft_pull_request,
    "render_a2ui_review_card": render_a2ui_review_card,
}


class SkillMetadata(BaseModel):
    """Metadata parsed from a SKILL.md YAML frontmatter."""
    name: str = Field(description="Unique identifier for the skill")
    description: str = Field(description="One-line summary of skill domain and responsibility")
    activation_cues: List[str] = Field(default_factory=list, description="Keywords and triggers that activate this skill")
    tools: List[str] = Field(default_factory=list, description="List of tool function names bound to this skill")
    skill_dir: str = Field(description="Directory path where SKILL.md resides")
    skill_md_path: str = Field(description="Absolute path to the SKILL.md file")


class SkillCatalog:
    """Manages runtime discovery and progressive disclosure of SKILL.md modules."""

    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            # Default to 'skills' directory at repository root
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.skills_dir = repo_root / "skills"

        self._skills_cache: Dict[str, SkillMetadata] = {}
        self._instructions_cache: Dict[str, str] = {}
        self.reload_skills()

    def reload_skills(self) -> None:
        """Discovers and parses all SKILL.md files in the skills directory."""
        self._skills_cache.clear()
        self._instructions_cache.clear()

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return

        for skill_path in self.skills_dir.glob("*/SKILL.md"):
            try:
                content = skill_path.read_text(encoding="utf-8")
                frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
                
                if frontmatter_match:
                    yaml_text = frontmatter_match.group(1)
                    body_markdown = frontmatter_match.group(2).strip()
                    meta_dict = yaml.safe_load(yaml_text) or {}
                else:
                    meta_dict = {"name": skill_path.parent.name, "description": "Domain skill"}
                    body_markdown = content.strip()

                name = meta_dict.get("name", skill_path.parent.name)
                description = meta_dict.get("description", "Domain skill module")
                activation_cues = meta_dict.get("activation_cues", [])
                tools = meta_dict.get("tools", [])

                metadata = SkillMetadata(
                    name=name,
                    description=description,
                    activation_cues=activation_cues,
                    tools=tools,
                    skill_dir=str(skill_path.parent),
                    skill_md_path=str(skill_path),
                )
                self._skills_cache[name] = metadata
                self._instructions_cache[name] = body_markdown
                logger.debug(f"Loaded skill: {name} from {skill_path}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_path}: {e}")

    def list_skills(self) -> List[SkillMetadata]:
        """Returns metadata for all discovered skills."""
        return list(self._skills_cache.values())

    def get_skills_manifest(self) -> str:
        """Generates Level 1 Discovery Index for Root Agent system prompts.
        
        Keeps prompt token count lightweight while informing the model of all
        available domain capabilities and their trigger cues.
        """
        lines = ["# Available Domain Skills (Progressive Disclosure Catalog)", ""]
        for meta in self.list_skills():
            cues = ", ".join(meta.activation_cues) if meta.activation_cues else "general"
            tools = ", ".join(meta.tools) if meta.tools else "none"
            lines.append(f"### Skill: `{meta.name}`")
            lines.append(f"- **Description**: {meta.description}")
            lines.append(f"- **Activation Cues**: {cues}")
            lines.append(f"- **Bound Tools**: {tools}")
            lines.append("")
        lines.append("To load detailed instructions and bind tools for any skill, call `load_skill_instruction(skill_name)`. ")
        return "\n".join(lines)

    def load_skill_context(self, skill_name: str) -> Dict[str, Any]:
        """Level 2 Progressive Disclosure: Loads full markdown instructions and tool definitions on demand."""
        if skill_name not in self._skills_cache:
            # Fallback fuzzy match
            for name, meta in self._skills_cache.items():
                if skill_name.lower() in name.lower() or name.lower() in skill_name.lower():
                    skill_name = name
                    break

        if skill_name not in self._skills_cache:
            raise KeyError(f"Skill '{skill_name}' not found. Available skills: {list(self._skills_cache.keys())}")

        metadata = self._skills_cache[skill_name]
        body = self._instructions_cache.get(skill_name, "")
        tool_callables = self.get_skill_tools(skill_name)

        return {
            "name": metadata.name,
            "description": metadata.description,
            "activation_cues": metadata.activation_cues,
            "tools_declared": metadata.tools,
            "tool_callables": tool_callables,
            "instruction_markdown": body,
            "skill_dir": metadata.skill_dir,
        }

    def get_skill_tools(self, skill_name: str) -> List[Callable]:
        """Resolves tool names declared in SKILL.md frontmatter to callable functions."""
        if skill_name not in self._skills_cache:
            return []
        tool_names = self._skills_cache[skill_name].tools
        return [TOOL_REGISTRY[t] for t in tool_names if t in TOOL_REGISTRY]


# Global default instance
_default_catalog = SkillCatalog()


def get_skill_catalog() -> SkillCatalog:
    """Returns the singleton SkillCatalog instance."""
    return _default_catalog


# Native ADK Tools for Progressive Disclosure (usable directly by LlmAgent)

def discover_available_skills() -> List[Dict[str, Any]]:
    """ADK Tool: Discovers all available domain skills in the progressive disclosure catalog.
    
    Returns a lightweight summary list of skill names, descriptions, and activation triggers.
    """
    catalog = get_skill_catalog()
    return [
        {
            "skill_name": meta.name,
            "description": meta.description,
            "activation_cues": meta.activation_cues,
            "tools": meta.tools,
        }
        for meta in catalog.list_skills()
    ]


def load_skill_instruction(skill_name: str) -> str:
    """ADK Tool: Dynamically loads full domain instructions and code standards for a skill on demand.
    
    Call this tool when addressing a specific bug triage phase (e.g., 'sandbox-remediation',
    'peer-code-review-claude', 'log-sanitization-dlp', 'vector-deduplication').
    """
    catalog = get_skill_catalog()
    try:
        context = catalog.load_skill_context(skill_name)
        return (
            f"=== LOADED SKILL: {context['name']} ===\n"
            f"Description: {context['description']}\n\n"
            f"{context['instruction_markdown']}"
        )
    except KeyError as e:
        return f"Error loading skill: {str(e)}"
