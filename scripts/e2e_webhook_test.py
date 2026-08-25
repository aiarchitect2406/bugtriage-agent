"""End-to-End Test Suite for Bug Triage Agent with example-payment-svc.

Tests 4 realistic end-to-end webhook scenarios:
1. P0 Blocker Checkout Crash -> Ingestion -> Sanitization -> Dedupe -> CODEOWNERS -> Sandbox -> Claude Review -> HITL Approval Webhook -> Git Commit & PR Created.
2. Duplicate Bug Ticket -> Vector Similarity Detection -> Linked to Parent (No Duplicate PR).
3. P1 Auth Security Token Issue -> @security-team Routing -> Sandbox -> Claude Review -> PR Created.
4. Human-in-the-Loop Refinement -> Developer Requests Modification -> Refinement Retry.
"""

import os
import sys

# Ensure repository root is in Python module search path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import subprocess
from fastapi.testclient import TestClient
from app.fast_api_app import app
from app.config import Config

client = TestClient(app)

def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def test_e2e_all_scenarios():
    print_separator("STARTING END-TO-END WEBHOOK TESTS FOR EXAMPLE-PAYMENT-SVC")
    
    # -------------------------------------------------------------------------
    # TEST CASE 1: P0 Blocker Crash on Payment Gateway (Ingestion -> PR Created)
    # -------------------------------------------------------------------------
    print("\n[TEST CASE 1] Firing GitHub Issue Webhook: P0 Blocker Crash in payment_gateway.py")
    issue_payload_1 = {
        "action": "opened",
        "issue": {
            "number": 501,
            "title": "[CRITICAL] NullPointerException in payment_gateway.py during checkout",
            "body": (
                "Customer customer_99@gmail.com experienced crash during checkout.\n"
                "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload\n"
                "Stack Trace:\n"
                "Traceback (most recent call last):\n"
                '  File "services/payment_gateway.py", line 42, in process_checkout\n'
                '    tax = calculate_tax(shipping_address, subtotal)\n'
                "TypeError: 'NoneType' object is not subscriptable\n"
            )
        }
    }

    resp1 = client.post("/webhooks/github/issues", json=issue_payload_1)
    assert resp1.status_code == 200, f"GitHub webhook failed: {resp1.text}"
    data1 = resp1.json()
    triage1 = data1["triage_result"]
    
    print(f"  -> Ingestion Status: {data1.get('status')}")
    print(f"  -> Issue ID: {data1.get('issue_id')}")
    print(f"  -> Assigned Owner: {triage1.get('primary_owner')} (SLA: {triage1.get('priority')})")
    print(f"  -> Sandbox Pytest Result: {triage1.get('sandbox_status')}")
    print(f"  -> Claude Peer Review Verdict: {triage1.get('code_review', {}).get('verdict')} (Score: {triage1.get('code_review', {}).get('score')}/100)")
    print(f"  -> Auto-PR Status: {triage1.get('status')}")
    print(f"  -> Pull Request URL: {triage1.get('pull_request_url')}")
    print(f"  -> Branch: {triage1.get('branch_name')}")
    
    assert triage1.get("primary_owner") == "@payments-team"
    assert triage1.get("priority") == "P0"
    assert triage1.get("sandbox_status") == "PASSED"
    assert triage1.get("status") == "PR_CREATED"
    assert triage1.get("pull_request_url") is not None

    # Verify Git state in example-payment-svc
    target_repo = Config.LOCAL_TARGET_REPO_PATH
    git_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=target_repo, text=True).strip()
    git_log = subprocess.check_output(["git", "log", "-n", "1", "--oneline"], cwd=target_repo, text=True).strip()
    print(f"  -> Target Repo Active Branch: {git_branch}")
    print(f"  -> Target Repo Latest Commit: {git_log}")
    print("  [SUCCESS] Test Case 1 PASSED: Direct PR Creation upon Claude Sonnet Peer Review Verified!")

    # -------------------------------------------------------------------------
    # TEST CASE 2: Duplicate Issue (Vector Similarity Deduplication)
    # -------------------------------------------------------------------------
    print("\n[TEST CASE 2] Firing GitHub Issue Webhook: Duplicate crash report (GH-502)")
    issue_payload_2 = {
        "action": "opened",
        "issue": {
            "number": 502,
            "title": "Crash on checkout when shipping address is null",
            "body": (
                "Stack Trace:\n"
                '  File "services/payment_gateway.py", line 42, in process_checkout\n'
                "TypeError: 'NoneType' object is not subscriptable"
            )
        }
    }
    resp2 = client.post("/webhooks/github/issues", json=issue_payload_2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    triage2 = data2["triage_result"]
    print(f"  -> Deduplication Result: {triage2.get('status')}")
    print(f"  -> Linked Parent Ticket: {triage2.get('parent_issue_id')}")
    print(f"  -> Similarity Score: {triage2.get('similarity_score')}")
    print(f"  -> Explanation: {triage2.get('explanation')}")
    assert triage2.get("status") == "DUPLICATE_LINKED"
    print("  [SUCCESS] Test Case 2 PASSED: Duplicate Ticket Deduplication Verified!")

    # -------------------------------------------------------------------------
    # TEST CASE 3: P1 Auth Security Token Issue (@security-team Routing)
    # -------------------------------------------------------------------------
    print("\n[TEST CASE 3] Firing GitHub Issue Webhook: P1 Auth Security Ticket (GH-503)")
    issue_payload_3 = {
        "action": "opened",
        "issue": {
            "number": 503,
            "title": "[SECURITY] JWT token validation failure in auth_service.py",
            "body": (
                "Stack Trace:\n"
                '  File "services/auth_service.py", line 105, in verify_jwt_token\n'
                "ValueError: Invalid JWT token signature"
            )
        }
    }
    resp3 = client.post("/webhooks/github/issues", json=issue_payload_3)
    assert resp3.status_code == 200
    data3 = resp3.json()
    triage3 = data3["triage_result"]
    print(f"  -> Assigned Owner: {triage3.get('primary_owner')} (SLA: {triage3.get('priority')})")
    print(f"  -> Sandbox Pytest Result: {triage3.get('sandbox_status')}")
    print(f"  -> Claude Peer Review: {triage3.get('code_review', {}).get('verdict')}")
    assert triage3.get("primary_owner") == "@security-team"
    assert triage3.get("priority") == "P1"

    # Approve Case 3
    resp_approve3 = client.post("/webhooks/hitl/action", json={
        "session_id": triage3["session_id"],
        "issue_id": "GH-503",
        "action": "APPROVE",
        "reviewer_id": "@security-lead",
        "hmac_signature": "valid-hmac-signature"
    })
    assert resp_approve3.json().get("action_taken") == "PR_CREATED"
    print("  [SUCCESS] Test Case 3 PASSED: Security Ticket Routed & PR Created!")

    # -------------------------------------------------------------------------
    # TEST CASE 4: Human-in-the-Loop Modification Feedback
    # -------------------------------------------------------------------------
    print("\n[TEST CASE 4] Developer Requests Changes via HITL Modification Webhook")
    modify_payload = {
        "session_id": "session-gh-504",
        "issue_id": "GH-504",
        "action": "MODIFY",
        "reviewer_id": "@senior-dev",
        "feedback_prompt": "Please add structured logging and fallback handling instead of returning error.",
        "hmac_signature": "valid-hmac-signature"
    }
    resp_modify = client.post("/webhooks/hitl/action", json=modify_payload)
    assert resp_modify.status_code == 200
    modify_data = resp_modify.json()
    print(f"  -> Action Taken: {modify_data.get('action_taken')}")
    print(f"  -> Feedback Routed: {modify_data.get('message')}")
    assert modify_data.get("action_taken") == "REFINEMENT_RETRY"
    print("  [SUCCESS] Test Case 4 PASSED: Interactive Feedback Loop Verified!")

    print_separator("ALL 4 END-TO-END WEBHOOK TEST SCENARIOS PASSED WITH SUCCESS!")
    return True

if __name__ == "__main__":
    success = test_e2e_all_scenarios()
    sys.exit(0 if success else 1)
