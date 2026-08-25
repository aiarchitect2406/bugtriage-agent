"""Comprehensive End-to-End Pipeline & HITL Integration Tests for ADK 2.0 Agent."""

import pytest
import hmac
import hashlib
from app.models.bug_report import BugReport
from app.models.hitl import WebhookSignalInput
from app.agents.coordinator import TriageCoordinator
from app.hitl.webhook_listener import process_hitl_webhook_signal
from app.hitl.state_store import HITLStateStore
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
    6. HITL Gate State Persistence & A2UI Review Card Generation.
    7. HMAC Webhook Approval Signoff.
    8. GitHub Draft PR Creation.
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
    assert result["status"] == "AWAITING_HUMAN_REVIEW"
    assert result["issue_id"] == "BUG-E2E-001"
    assert result["primary_owner"] == "@payments-team"
    assert result["priority"] == "P0"
    assert result["sla_target_hours"] == 2
    assert result["sandbox_status"] == "PASSED"
    assert "test_reproduce" in result["failing_test_code"]
    assert "shipping_address" in result["proposed_diff_patch"] or "calculate_tax" in result["proposed_diff_patch"]
    
    # 4. Verify A2UI Card
    a2ui_card = result["a2ui_card"]
    assert isinstance(a2ui_card, list)
    assert len(a2ui_card) >= 2
    assert "beginRendering" in a2ui_card[0]
    assert "surfaceUpdate" in a2ui_card[1]

    # 5. Verify Session Persistence
    session_id = result["session_id"]
    saved_state = HITLStateStore.get_session_state(session_id)
    assert saved_state is not None
    assert saved_state.status == "AWAITING_HUMAN_REVIEW"

    # 6. Test Context Compaction
    compacted = HITLStateStore.compact_session_history(session_id, max_tokens=1000)
    assert compacted is not None

    # 7. Simulate Developer Approval via HMAC Webhook
    valid_hmac = "valid-hmac-signature"
    approval_signal = WebhookSignalInput(
        session_id=session_id,
        issue_id="BUG-E2E-001",
        action="APPROVE",
        reviewer_id="@lead-reviewer",
        feedback_prompt="Code patch verified against unit test suites.",
        hmac_signature=valid_hmac
    )
    
    approval_res = process_hitl_webhook_signal(approval_signal)
    
    # 8. Assert PR Creation
    assert approval_res["status"] == "SUCCESS"
    assert approval_res["action_taken"] == "PR_CREATED"
    assert "https://github.com/aiarchitect2406/bugtriage-agent/pull/" in approval_res["pr_url"]


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
    assert res_primary["status"] == "AWAITING_HUMAN_REVIEW"

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


def test_e2e_hitl_rejection_and_modification(coordinator):
    """Verifies developer MODIFY and REJECT workflows through the webhook listener."""
    alert = BugReport(
        issue_id="BUG-E2E-002",
        title="Invalid JWT token exception on profile fetch",
        description="Profile API returns 500 when token header is expired.",
        raw_logs='File "app/services/auth.py", line 105, in verify_jwt_token',
        source_system="Datadog",
        metadata={"severity": "Major"}
    )
    
    res = coordinator.execute_triage_pipeline(alert)
    session_id = res["session_id"]

    # 1. Test MODIFY action
    modify_signal = WebhookSignalInput(
        session_id=session_id,
        issue_id="BUG-E2E-002",
        action="MODIFY",
        reviewer_id="@security-lead",
        feedback_prompt="Please also handle ExpiredSignatureError separately.",
        hmac_signature="valid-hmac-signature"
    )
    modify_res = process_hitl_webhook_signal(modify_signal)
    assert modify_res["status"] == "SUCCESS"
    assert modify_res["action_taken"] == "REFINEMENT_RETRY"

    # 2. Test REJECT action
    reject_signal = WebhookSignalInput(
        session_id=session_id,
        issue_id="BUG-E2E-002",
        action="REJECT",
        reviewer_id="@security-lead",
        feedback_prompt="Known non-issue caused by maintenance window.",
        hmac_signature="valid-hmac-signature"
    )
    reject_res = process_hitl_webhook_signal(reject_signal)
    assert reject_res["status"] == "SUCCESS"
    assert reject_res["action_taken"] == "CLOSED_NO_ACTION"
