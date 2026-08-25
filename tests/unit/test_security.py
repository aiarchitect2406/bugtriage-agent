"""Unit tests for Native ADK 2.0 Plugins, Model Armor Guardrails, and Sandbox Execution."""

import pytest
from app.plugins.guardrails import GuardrailPolicyPlugin
from app.observability.tracing import CloudObservabilityPlugin
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix



def test_guardrail_policy_plugin_blocker_p0_rule():
    """Verifies that GuardrailPolicyPlugin enforces Blocker -> P0 SLA rule."""
    plugin = GuardrailPolicyPlugin()
    
    # Valid mapping
    res = plugin.validate_triage_decision(severity="Blocker", priority="P0", primary_owner="@payments-core")
    assert res["is_valid"] is True
    assert res["status"] == "APPROVED"
    assert len(res["violations"]) == 0

    # Invalid: Blocker mapped to P1
    invalid_res = plugin.validate_triage_decision(severity="Blocker", priority="P1", primary_owner="@payments-core")
    assert invalid_res["is_valid"] is False
    assert invalid_res["status"] == "REJECTED_BY_GUARDRAIL"
    assert any("MUST map to Priority 'P0'" in v for v in invalid_res["violations"])


def test_guardrail_policy_plugin_p0_owner_rule():
    """Verifies that GuardrailPolicyPlugin enforces explicit team owner for P0 bugs."""
    plugin = GuardrailPolicyPlugin()
    
    # Invalid: P0 with generic fallback team
    invalid_res = plugin.validate_triage_decision(severity="Blocker", priority="P0", primary_owner="@core-triage-team")
    assert invalid_res["is_valid"] is False
    assert any("requires explicit domain owner" in v for v in invalid_res["violations"])


def test_cloud_observability_plugin_initialization():
    """Verifies that CloudObservabilityPlugin initializes with OpenTelemetry tracer."""
    plugin = CloudObservabilityPlugin()
    assert plugin.name == "cloud_observability_plugin"
    assert plugin.structured_logger is not None


def test_sandbox_tools_subprocess_execution():
    """Verifies isolated subprocess sandbox test and fix execution."""
    result = execute_reproduction_and_sandbox_fix(
        issue_id="BUG-2026-NATIVE-001",
        stack_trace="TypeError: NoneType object is not subscriptable in payment_gateway.py",
        source_file_path="services/payment_gateway.py"
    )
    assert result["status"] == "SUCCESS"
    assert result["reproduction_test"]["framework"] == "pytest"
    assert result["sandbox_result"]["status"] == "PASSED"
    assert result["sandbox_result"]["post_patch_test_passed"] is True


