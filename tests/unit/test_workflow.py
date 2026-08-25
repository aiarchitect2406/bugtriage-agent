"""Unit Tests for ADK 2.0 Workflow and Guardrails."""

import pytest
from app.workflow import bug_triage_workflow
from app.plugins.guardrails import GuardrailPolicyPlugin
from app.agents.coordinator import TriageCoordinator
from app.models.bug_report import BugReport

def test_workflow_edges_and_name():
    assert bug_triage_workflow.name == "bug_triage_workflow"
    assert len(bug_triage_workflow.edges) >= 6

def test_guardrail_policy_plugin():
    plugin = GuardrailPolicyPlugin()
    
    # Valid: Blocker maps to P0 with domain owner
    valid_res = plugin.validate_triage_decision("Blocker", "P0", "@payments-team")
    assert valid_res["is_valid"] is True
    assert valid_res["status"] == "APPROVED"
    
    # Invalid: Blocker mapped to P1
    invalid_res = plugin.validate_triage_decision("Blocker", "P1", "@payments-team")
    assert invalid_res["is_valid"] is False
    assert invalid_res["status"] == "REJECTED_BY_GUARDRAIL"
    assert any("Severity 'Blocker' MUST map to Priority 'P0'" in v for v in invalid_res["violations"])

def test_end_to_end_triage_flow():
    coordinator = TriageCoordinator()
    report = BugReport(
        issue_id="BUG-2026-001",
        title="NullPointerException in PaymentGateway",
        description="Checkout crash",
        raw_logs='File "app/services/payment_checkout.py", line 42, in process_checkout token=secret_bearer_token_12345 user_email=john.doe@example.com',
        metadata={"severity": "Blocker"}
    )
    res = coordinator.execute_triage_pipeline(report)
    assert res["status"] == "PR_CREATED"
    assert res["primary_owner"] == "@payments-team"
    assert res["priority"] == "P0"
    assert res["sandbox_status"] == "PASSED"
    assert "pull_request_url" in res
    assert "a2ui_card" in res
