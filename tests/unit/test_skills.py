"""Unit tests for DynamicSkillRegistry and Progressive Disclosure Engine."""

import pytest
from app.skills.registry import DynamicSkillRegistry, SkillDescriptor

def test_dynamic_skill_discovery():
    """Verifies that DynamicSkillRegistry discovers and indexes all domain skills."""
    registry = DynamicSkillRegistry()
    skills = registry.discover_skills()
    
    assert len(skills) >= 5
    assert "log-sanitization-dlp" in skills
    assert "vector-deduplication" in skills
    assert "ownership-routing" in skills
    assert "sandbox-remediation" in skills
    assert "hitl-pull-request" in skills

def test_progressive_prompt_catalog_is_compact():
    """Verifies that the prompt catalog does not leak heavy tool schemas into root prompt."""
    registry = DynamicSkillRegistry()
    catalog = registry.get_progressive_prompt_catalog()
    
    # Prompt catalog should contain skill names and cues, but NOT full tool schemas
    assert "Available Domain Skills" in catalog
    assert "log-sanitization-dlp" in catalog
    assert "sanitize_logs" in catalog
    assert "sandbox-remediation" in catalog
    # Ensure it is token-efficient (compact string under 2000 chars)
    assert len(catalog) < 2000

def test_on_demand_skill_instruction_loading():
    """Verifies that detailed markdown instructions are loaded only on demand."""
    registry = DynamicSkillRegistry()
    instructions = registry.load_skill_instructions("sandbox-remediation")
    
    assert "Skill: Sandbox Reproduction" in instructions
    assert "gemini-3.1-pro-preview" in instructions

def test_dynamic_tool_binding():
    """Verifies that specific tool callables are bound on-demand per activated skill."""
    registry = DynamicSkillRegistry()
    tools = registry.get_tools_for_skill("sandbox-remediation")
    
    assert len(tools) == 1
    assert tools[0].__name__ == "execute_reproduction_and_sandbox_fix"

def test_resolve_skill_by_cue():
    """Verifies that activation cues resolve to the correct skill."""
    registry = DynamicSkillRegistry()
    desc = registry.resolve_skill_by_cue("dedupe_issues")
    assert desc is not None
    assert desc.name == "vector-deduplication"
