"""Dynamic Subagent Factory for Progressive Disclosure in Google ADK 2.0.

Implements Level 3 Isolated Subagent Execution as described in the ADK
long-horizon-harness pattern: subagents are instantiated on-demand with
domain-specific skills and executed in isolated context windows.
"""

import logging
from typing import Dict, Any, Optional, List
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from app.config import Config
from app.skills.loader import get_skill_catalog, SkillCatalog

logger = logging.getLogger(__name__)


class DynamicSubagentFactory:
    """Factory that constructs ephemeral, skill-bound ADK subagents on demand."""

    def __init__(self, catalog: Optional[SkillCatalog] = None):
        self.catalog = catalog or get_skill_catalog()

    def create_subagent_for_skill(
        self,
        skill_name: str,
        model_name: Optional[str] = None,
        extra_tools: Optional[List[Any]] = None,
    ) -> Agent:
        """Instantiates a dedicated Google ADK Agent bound to a discovered SKILL.md.
        
        Args:
            skill_name: Name of the skill to bind (e.g., 'sandbox-remediation', 'peer-code-review-claude').
            model_name: Optional model override (defaults to Config.FAST_MODEL or Config.REASONING_MODEL).
            extra_tools: Optional additional tools to bind.

        Returns:
            Configured `google.adk.agents.Agent` instance with isolated instructions and tools.
        """
        skill_context = self.catalog.load_skill_context(skill_name)
        
        instructions = (
            f"You are a specialized subagent executing the skill: '{skill_context['name']}'.\n\n"
            f"=== DOMAIN GUIDELINES & SPECIFICATION ===\n"
            f"{skill_context['instruction_markdown']}\n\n"
            f"=== EXECUTION PROTOCOL ===\n"
            f"Use your assigned tools to accomplish the task. Return concise, structured results."
        )

        tools = list(skill_context["tool_callables"])
        if extra_tools:
            tools.extend(extra_tools)

        # Use reasoning model for code synthesis/remediation, fast model for triage/routing
        if model_name:
            chosen_model_str = model_name
        elif "remediation" in skill_name or "reasoning" in skill_name:
            chosen_model_str = Config.REASONING_MODEL
        else:
            chosen_model_str = Config.FAST_MODEL

        subagent = Agent(
            name=f"subagent_{skill_name.replace('-', '_')}",
            model=Gemini(
                model=chosen_model_str,
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
            instruction=instructions,
            description=skill_context["description"],
            tools=tools,
        )
        
        logger.debug(f"Instantiated dynamic subagent for skill: {skill_name} with {len(tools)} tools")
        return subagent


_default_factory = DynamicSubagentFactory()


def get_subagent_factory() -> DynamicSubagentFactory:
    """Returns the singleton DynamicSubagentFactory instance."""
    return _default_factory
