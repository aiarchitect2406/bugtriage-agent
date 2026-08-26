"""Comprehensive End-to-End Pipeline Integration Tests for ADK 2.0 Agent."""

import pytest
from app.models.bug_report import BugReport
from app.workflow import TriageCoordinator, run_triage_workflow
from app.config import Config


@pytest.fixture
def coordinator():
    """Initializes the TriageCoordinator."""
    return TriageCoordinator()


def test_e2e_pipeline_full_lifecycle(coordinator):
    """Verifies the complete end-to-end lifecycle of a new high-severity bug:

    1. Raw Alert Ingestion with PII tokens (email, auth secret).
    2. PII Redaction & Stack Frame Extraction.
    3. Vector Deduplication check (Non-duplicate).
    4. CODEOWNERS Resolution & SLA Calculation (@payments-team, P0, 2h).
    5. Automated Reproduction Test Synthesis & Sandbox Validation.
    6. Maker-Checker Peer Code Review with Claude Sonnet.
    7. Automated Pull Request Creation on target repository.
    """
    # 1. Raw Alert with PII
    raw_alert = BugReport(
        issue_id="BUG-E2E-001",
        title="NullPointerException in PaymentGateway on checkout",
        description="Checkout process crashes when customer attempts to pay with null address.",
        raw_logs='File "app/services/payment_checkout.py", line 42, in process_checkout token=bearer_sec_9999 user_email=lead_dev@ecommerce.org',
        source_system="Sentry",
        metadata={"severity": "Blocker"}
    )

    # 2. Execute Pipeline
    result = coordinator.execute_triage_pipeline(raw_alert)

    # 3. Assertions on Triage Stage
    assert result["status"] == "PR_CREATED"
    assert result["issue_id"] == "BUG-E2E-001"
    assert result["primary_owner"] == "@payments-team"
    assert result["priority"] == "P0"
    assert result["sla_target_hours"] == 2
    assert result["sandbox_status"] == "PASSED"
    assert "def test_" in result["failing_test_code"]
    assert len(result["proposed_diff_patch"]) > 0

    # 4. Verify PR Details
    assert "pull_request_url" in result
    assert result["pull_request_number"] is not None
    assert result["code_review"]["verdict"] == "APPROVED"
    assert result["code_review"]["score"] >= 80


def test_e2e_duplicate_noise_suppression(coordinator):
    """Verifies that an incoming duplicate alert is semantically detected and suppressed."""
    alert_primary = BugReport(
        issue_id="BUG-MASTER-100",
        title="Database connection timeout in checkout worker",
        description="Checkout worker unable to reach postgres database pool after 30s.",
        raw_logs='File "app/services/db.py", line 88, in connect_pool',
        source_system="PagerDuty",
        metadata={"severity": "Critical"}
    )

    # Run primary
    res_primary = coordinator.execute_triage_pipeline(alert_primary)
    assert res_primary["status"] in ["PR_CREATED", "NEEDS_ATTENTION"]

    # Run duplicate
    alert_duplicate = BugReport(
        issue_id="BUG-DUP-101",
        title="Database connection timeout in checkout worker",
        description="Checkout worker unable to reach postgres database pool after 30s.",
        raw_logs='File "app/services/db.py", line 88, in connect_pool',
        source_system="Sentry",
        metadata={"severity": "Critical"}
    )

    historical = [{
        "issue_id": alert_primary.issue_id,
        "title": alert_primary.title,
        "description": alert_primary.description
    }]

    res_duplicate = coordinator.execute_triage_pipeline(alert_duplicate, historical_candidates=historical)

    assert res_duplicate["status"] == "DUPLICATE_LINKED"
    assert res_duplicate["parent_issue_id"] == "BUG-MASTER-100"
    assert res_duplicate["similarity_score"] >= 0.85
    assert "Duplicate detected" in res_duplicate["explanation"]

