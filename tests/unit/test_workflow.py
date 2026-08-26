"""Unit Tests for ADK 2.0 Workflow and Autonomous Coordinator Pipeline."""

import pytest
from app.workflow import bug_triage_workflow, TriageCoordinator, run_triage_workflow
from app.models.bug_report import BugReport


def test_workflow_edges_and_name():
    assert bug_triage_workflow.name == "bug_triage_workflow"
    assert len(bug_triage_workflow.edges) >= 5


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

