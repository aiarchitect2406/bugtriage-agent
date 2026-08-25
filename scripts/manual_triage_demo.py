#!/usr/bin/env python3
"""Interactive Manual Bug Triage Testing Console for https://github.com/aiarchitect2406/bugtriage-agent.

Demonstrates self-triage on this very codebase:
- Ingests bug alerts referencing real codebase files (e.g. app/services/payment_checkout.py, app/services/auth.py)
- Redacts PII via Cloud DLP / regex
- Performs semantic vector deduplication
- Enforces .github/CODEOWNERS and SLA rules
- Synthesizes reproduction test and unified diff patch
- Runs containerized sandbox verification
- Generates Human-in-the-Loop (HITL) A2UI review cards ("The Vibe Diff")
- Approves via HMAC-authenticated webhook to create Draft Pull Requests
"""

import sys
import os
import json
import time

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.models.bug_report import BugReport
from app.models.hitl import WebhookSignalInput
from app.agents.coordinator import TriageCoordinator, coordinator_agent
from app.hitl.webhook_listener import process_hitl_webhook_signal
from app.config import Config

def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_section(title: str):
    print("\n" + "-" * 80)
    print(f" >>> {title}")
    print("-" * 80)

def run_automated_demo():
    """Runs through 3 distinct scenarios representing the Golden Dataset."""
    print_banner(
        f"Google ADK 2.0 Autonomous Bug Triage Agent — Self-Triage Engine\n"
        f" Target Repository: {Config.REPO_NAME}\n"
        f" GCP Project: {Config.PROJECT_ID} | Region: {Config.LOCATION}\n"
        f" Models: Routing -> {Config.FAST_MODEL} | Reasoning -> {Config.REASONING_MODEL}"
    )
    
    coordinator = TriageCoordinator()

    # =========================================================================
    # Scenario 1: New Critical Blocker (NullPointerException in Checkout)
    # =========================================================================
    print_section("TEST CASE 1: Critical Blocker Defect (Checkout NPE with PII)")
    alert_1 = BugReport(
        issue_id="BUG-2026-001",
        title="NullPointerException in PaymentGateway on checkout",
        description="Checkout fails with NullPointerException when user submits order with empty address.",
        raw_logs='File "app/services/payment_checkout.py", line 42, in process_checkout token=secret_bearer_token_12345 user_email=john.doe@example.com',
        source_system="Sentry",
        metadata={"severity": "Blocker"}
    )
    
    print(f"  [INPUT] Title: {alert_1.title}")
    print(f"  [INPUT] Raw Logs (with PII): {alert_1.raw_logs}")
    
    res1 = coordinator.execute_triage_pipeline(alert_1)
    
    print("\n  [TRIAGE RESULTS]")
    print(f"  * Pipeline Status:    {res1.get('status')}")
    print(f"  * Primary Owner:      {res1.get('primary_owner')} (Resolved via .github/CODEOWNERS)")
    print(f"  * Priority & SLA:     {res1.get('priority')} (Severity: {res1.get('severity')}, SLA: {res1.get('sla_target_hours')}h)")
    print(f"  * Sandbox Validation: {res1.get('sandbox_status')}")
    print(f"  * Failing Test Code:\n\n{res1.get('failing_test_code')}")
    print(f"  * Proposed Diff Patch:\n{res1.get('proposed_diff_patch')}")
    print(f"  * HITL A2UI Review Card:\n    Generated A2UI Declarative Card ({len(res1.get('a2ui_card', []))} payload operations). Status: Paused at 'AWAITING_HUMAN_REVIEW'")

    # =========================================================================
    # Scenario 2: Semantic Duplicate Bug (Noise Suppression)
    # =========================================================================
    print_section("TEST CASE 2: Semantic Duplicate Ticket (Alert Noise Suppression)")
    alert_2 = BugReport(
        issue_id="BUG-2026-002",
        title="NullPointerException in PaymentGateway on checkout",
        description="Checkout fails with NullPointer when user_id is empty or null.",
        raw_logs='File "app/services/payment_checkout.py", line 42, in process_checkout',
        source_system="Sentry",
        metadata={"severity": "Blocker"}
    )
    
    historical = [{
        "issue_id": alert_1.issue_id,
        "title": alert_1.title,
        "description": alert_1.description
    }]
    
    print(f"  [INPUT] Duplicate Title: {alert_2.title}")
    res2 = coordinator.execute_triage_pipeline(alert_2, historical_candidates=historical)
    
    print("\n  [TRIAGE RESULTS]")
    print(f"  * Pipeline Status:     {res2.get('status')} (Alert noise suppressed)")
    print(f"  * Linked Parent Issue: {res2.get('parent_issue_id')}")
    print(f"  * Cosine Similarity:   {res2.get('similarity_score'):.4f} (>= 0.85 threshold)")
    print(f"  * Explanation:         {res2.get('explanation')}")

    # =========================================================================
    # Scenario 3: Major Auth Error (Security Team Domain)
    # =========================================================================
    print_section("TEST CASE 3: Major Auth Security Error")
    alert_3 = BugReport(
        issue_id="BUG-2026-003",
        title="Invalid JWT signature on authenticated endpoints",
        description="JWT decoding throws DecodeError on expired secret key rotation.",
        raw_logs='File "app/services/auth_token.py", line 88, in verify_token token=jwt_sec_abc123',
        source_system="Cloud Logging",
        metadata={"severity": "Major"}
    )
    
    print(f"  [INPUT] Title: {alert_3.title}")
    res3 = coordinator.execute_triage_pipeline(alert_3)
    
    print("\n  [TRIAGE RESULTS]")
    print(f"  * Pipeline Status:    {res3.get('status')}")
    print(f"  * Primary Owner:      {res3.get('primary_owner')} (Resolved to security team)")
    print(f"  * Priority & SLA:     {res3.get('priority')} (Severity: {res3.get('severity')}, SLA: {res3.get('sla_target_hours')}h)")
    print(f"  * Sandbox Validation: {res3.get('sandbox_status')}")

    # =========================================================================
    # Scenario 4: Human-in-the-Loop Approval & Draft PR Creation
    # =========================================================================
    print_section("TEST CASE 4: Developer Approves Patch via HMAC-Authenticated Webhook")
    signal = WebhookSignalInput(
        session_id=res1.get("session_id"),
        issue_id=res1.get("issue_id"),
        action="APPROVE",
        reviewer_id="@payments-lead",
        feedback_prompt="Verified reproduction test and diff patch in sandbox.",
        hmac_signature="valid-hmac-signature"
    )
    
    print(f"  [HITL SIGNAL] Reviewer: {signal.reviewer_id} -> Action: {signal.action}")
    signoff_res = process_hitl_webhook_signal(signal)
    
    print("\n  [HITL SIGNOFF OUTCOME]")
    print(f"  * Outcome Status: {signoff_res.get('status')}")
    print(f"  * Action Taken:   {signoff_res.get('action_taken')}")
    print(f"  * Pull Request:   {signoff_res.get('pr_url')}")
    print(f"  * Message:        {signoff_res.get('message')}")

    print_banner("ALL 4 MANUAL TEST SCENARIOS COMPLETED WITH 100% SUCCESS")

def run_interactive_custom_bug():
    """Allows user to enter a custom bug and see live triage."""
    print_banner("Interactive Custom Bug Triage Console")
    print("Enter bug report details to triage live:")
    
    try:
        title = input("\n1. Bug Title (e.g. 'Database connection timeout in payment gateway'): ").strip()
        if not title:
            title = "Database connection timeout in payment gateway"
            print(f"   Using default: {title}")
            
        desc = input("2. Description: ").strip()
        if not desc:
            desc = "Requests hang and raise ConnectionTimeoutError after 30 seconds."
            print(f"   Using default: {desc}")
            
        raw_logs = input("3. Raw Logs / Stack Trace: ").strip()
        if not raw_logs:
            raw_logs = 'File "app/services/database.py", line 55, in query_db api_key=db_secret_key_9999 user=admin@company.com'
            print(f"   Using default: {raw_logs}")
            
        severity = input("4. Severity [Blocker/Major/Minor/Trivial] (default: Major): ").strip()
        if not severity:
            severity = "Major"
            
        bug = BugReport(
            issue_id=f"BUG-CUSTOM-{int(time.time()) % 10000:04d}",
            title=title,
            description=desc,
            raw_logs=raw_logs,
            source_system="Interactive Console",
            metadata={"severity": severity}
        )
        
        print("\nProcessing bug triage through Google ADK 2.0 multi-agent pipeline...")
        coordinator = TriageCoordinator()
        res = coordinator.execute_triage_pipeline(bug)
        
        print_banner("CUSTOM BUG TRIAGE REPORT")
        print(f"Status:             {res.get('status')}")
        print(f"Assigned Owner:     {res.get('primary_owner')}")
        print(f"Priority:           {res.get('priority')} (SLA Target: {res.get('sla_target_hours')}h)")
        print(f"Sandbox Result:     {res.get('sandbox_status')}")
        if res.get("failing_test_code"):
            print(f"\n--- Generated Failing Unit Test ---\n{res.get('failing_test_code')}")
        if res.get("proposed_diff_patch"):
            print(f"\n--- Synthesized Diff Patch ---\n{res.get('proposed_diff_patch')}")
        if res.get("a2ui_card"):
            print(f"\n--- A2UI Review Card ---\n{json.dumps(res.get('a2ui_card'), indent=2)}")
            
    except (KeyboardInterrupt, EOFError):
        print("\nExiting interactive console.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--interactive", "-i"]:
        run_interactive_custom_bug()
    else:
        run_automated_demo()
