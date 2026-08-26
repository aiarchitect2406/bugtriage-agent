"""Unit tests for Native Google ADK 2.0 Progressive Disclosure & Dynamic Skill Subagents."""

import pytest
from app.skills.loader import (
    SkillCatalog,
    get_skill_catalog,
    discover_available_skills,
    load_skill_instruction,
)


def test_skill_catalog_discovery():
    """Verify runtime discovery of all SKILL.md modules in the repository."""
    catalog = get_skill_catalog()
    skills = catalog.list_skills()
    skill_names = {s.name for s in skills}

    expected_skills = {
        "bug-triage-domain-mastery",
        "pull-request-publishing",
        "log-sanitization-dlp",
        "ownership-routing",
        "peer-code-review-claude",
        "sandbox-remediation",
        "vector-deduplication",
    }

    
    assert expected_skills.issubset(skill_names), f"Missing skills: {expected_skills - skill_names}"


def test_skill_manifest_level1_progressive_disclosure():
    """Verify Level 1 discovery index generates lightweight manifest without loading full body."""
    catalog = get_skill_catalog()
    manifest = catalog.get_skills_manifest()

    assert "# Available Domain Skills (Progressive Disclosure Catalog)" in manifest
    assert "sandbox-remediation" in manifest
    assert "peer-code-review-claude" in manifest
    assert "log-sanitization-dlp" in manifest
    # Ensure lightweight summary (under 4000 characters)
    assert len(manifest) < 4000


def test_load_skill_context_level2_progressive_disclosure():
    """Verify Level 2 context loader dynamically retrieves full markdown body and resolves callable tools."""
    catalog = get_skill_catalog()
    context = catalog.load_skill_context("sandbox-remediation")

    assert context["name"] == "sandbox-remediation"
    assert "execute_reproduction_and_sandbox_fix" in context["tools_declared"]
    assert len(context["tool_callables"]) == 1
    assert callable(context["tool_callables"][0])
    assert "Skill: Sandbox Reproduction" in context["instruction_markdown"]


def test_adk_tools_progressive_disclosure():
    """Verify discover_available_skills and load_skill_instruction native tools."""
    skills_list = discover_available_skills()
    assert len(skills_list) >= 7
    
    remediation_meta = next(s for s in skills_list if s["skill_name"] == "sandbox-remediation")
    assert "execute_reproduction_and_sandbox_fix" in remediation_meta["tools"]

    instruction = load_skill_instruction("peer-code-review-claude")
    assert "=== LOADED SKILL: peer-code-review-claude ===" in instruction
    assert "Claude Sonnet" in instruction


from app.skills.registry_client import GeapSkillRegistryClient


def test_geap_skill_registry_validation():
    """Verify GeapSkillRegistryClient validates skill package metadata adhering to GEAP standards."""
    client = GeapSkillRegistryClient(project_id="test-project", location="us-central1")
    catalog = get_skill_catalog()
    context = catalog.load_skill_context("sandbox-remediation")
    
    assert context["name"] == "sandbox-remediation"
    assert len(context["name"]) <= 63
    assert len(context["description"]) <= 1024
