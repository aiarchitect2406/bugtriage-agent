"""Unit Tests for Typed ADK 2.0 Tools."""

import pytest
from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.tools.git_tools import create_draft_pull_request

def test_sanitize_logs_and_extract_stack():
    raw_logs = '2026-08-04 12:00:01 ERROR app.services.payment - java.lang.NullPointerException: Address object is null at File "app/services/payment_checkout.py", line 42, in process_checkout token=secret_bearer_token_12345 user_email=john.doe@example.com'
    res = sanitize_logs_and_extract_stack(
        issue_id="BUG-2026-001",
        title="NullPointerException in PaymentGateway",
        description="Checkout crash",
        raw_logs=raw_logs
    )
    assert res["status"] == "SUCCESS"
    sanitized = res["sanitized_report"]
    assert "john.doe@example.com" not in sanitized["sanitized_logs"]
    assert "secret_bearer_token_12345" not in sanitized["sanitized_logs"]
    assert len(sanitized["stack_frames"]) == 1
    assert sanitized["stack_frames"][0]["file_path"] == "app/services/payment_checkout.py"
    assert sanitized["stack_frames"][0]["line_number"] == 42
    assert sanitized["detected_exception_type"] == "NullPointerException"

def test_query_similar_bugs_by_vector_duplicate():
    candidates = [
        {
            "issue_id": "BUG-2026-001",
            "title": "NullPointerException in PaymentGateway on checkout",
            "description": "User reported NullPointerException when submitting checkout with empty address field."
        }
    ]
    res = query_similar_bugs_by_vector(
        issue_id="BUG-2026-002",
        bug_title="NullPointerException in PaymentGateway on checkout",
        bug_description="User reported NullPointerException when submitting checkout with empty address field.",
        candidate_historical_bugs=candidates
    )
    assert res["status"] == "SUCCESS"
    assert res["dedupe_result"]["is_duplicate"] is True
    assert res["dedupe_result"]["matching_parent_issue_id"] == "BUG-2026-001"
    assert res["dedupe_result"]["similarity_score"] >= 0.85

def test_resolve_codeowners_and_blame():
    stack_frames = [{"file_path": "app/services/payment_checkout.py", "line_number": 42}]
    res = resolve_codeowners_and_blame(
        issue_id="BUG-2026-001",
        stack_frames=stack_frames,
        severity_input="Blocker"
    )
    assert res["status"] == "SUCCESS"
    ctx = res["enrichment_context"]
    assert ctx["primary_owner"] == "@payments-team"
    assert ctx["priority"] == "P0"
    assert ctx["sla_target_hours"] == 2

def test_execute_reproduction_and_sandbox_fix():
    res = execute_reproduction_and_sandbox_fix(
        issue_id="BUG-2026-001",
        stack_trace="NullPointerException in payment_gateway.py",
        source_file_path="services/payment_gateway.py"
    )
    assert res["status"] == "SUCCESS"
    assert "def test_reproduce" in res["reproduction_test"]["test_code"]
    assert "payment_gateway.py" in res["fix_patch"]["diff_patch"]
    assert res["sandbox_result"]["status"] == "PASSED"

def test_create_draft_pull_request():
    res = create_draft_pull_request(
        issue_id="BUG-2026-001",
        reviewer_handle="@payments-team"
    )
    assert res["status"] == "SUCCESS"
    assert res["pull_request_number"] > 0
    assert "https://github.com/" in res["pull_request_url"]
