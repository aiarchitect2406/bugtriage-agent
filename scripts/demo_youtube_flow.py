#!/usr/bin/env python3
"""
Interactive End-to-End Live Demo Runner for Autonomous Bug Triage Agent.
Designed for live YouTube demonstrations, architecture presentations, and evaluations.
"""

import sys
import os
import time
import json
import subprocess

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.bug_report import BugReport
from app.agents.coordinator import TriageCoordinator
from app.hitl.webhook_listener import process_hitl_webhook_signal
from app.models.hitl import WebhookSignalInput
from app.config import Config

# ANSI Color formatting for terminal presentation
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def print_banner():
    print(f"\n{CYAN}{BOLD}{'='*80}{RESET}")
    print(f"{CYAN}{BOLD}  🤖 GOOGLE ADK 2.0 & GEAP AUTONOMOUS BUG TRIAGE AGENT - LIVE DEMO{RESET}")
    print(f"{CYAN}{BOLD}{'='*80}{RESET}\n")
    print(f"{BOLD}Target Monitored Service:{RESET} {Config.TARGET_REPO_URL}")
    print(f"{BOLD}Agent Architecture:{RESET}      Google ADK 2.0 Multi-Agent Workflow + Gemini 3.1 Pro & 3.7 Flash")
    print(f"{BOLD}Security Model:{RESET}          SPIFFE Zero Ambient Authority + Ephemeral Sandboxing + Two-Layer Gating\n")

def run_interactive_demo():
    print(f"\n{YELLOW}{BOLD}[SCENE 1: INCOMING CRASH REPORT / GITHUB ISSUE]{RESET}")
    print(f"A high-priority crash alert is received from production monitoring...")
    
    sample_crash = {
        "issue_id": "BUG-2026-LIVE-001",
        "title": "NullPointerException in PaymentGateway on digital checkout",
        "raw_logs": (
            "2026-08-24 18:15:00 ERROR app.services.payment_gateway - "
            "Exception in thread 'pool-checkout-4': java.lang.NullPointerException: shipping_address is null "
            "at services.payment_gateway.calculate_tax (payment_gateway.py:12) "
            "user_token=secret_jwt_bearer_99999 user_email=alice.shopper@customer.com"
        ),
        "description": "Customer attempted to purchase a digital downloadable product with no shipping address."
    }
    
    print(f"\n{DIM}Alert Payload:{RESET}")
    print(f"  • Issue ID:   {sample_crash['issue_id']}")
    print(f"  • Title:      {sample_crash['title']}")
    print(f"  • Raw Logs:   {sample_crash['raw_logs']}")
    
    input(f"\n{GREEN}{BOLD}▶ Press [ENTER] to trigger Autonomous Agent Triage...{RESET}")
    
    start_time = time.time()
    report = BugReport(
        issue_id=sample_crash["issue_id"],
        title=sample_crash["title"],
        description=sample_crash["description"],
        raw_logs=sample_crash["raw_logs"],
        severity_hint="Blocker"
    )
    
    print(f"\n{YELLOW}{BOLD}[SCENE 2: AUTONOMOUS AGENT ORCHESTRATION IN PROGRESS]{RESET}")
    result = TriageCoordinator.run_triage_pipeline(report)
    elapsed = time.time() - start_time
    
    print(f"\n{GREEN}{BOLD}✔ Autonomous Processing Completed in {elapsed:.2f}s!{RESET}\n")
    
    print(f"{CYAN}{BOLD}--- STAGE RESULTS ---{RESET}")
    print(f"1. {BOLD}Cloud DLP Ingestion:{RESET}       Redacted {result['sanitized_report']['pii_redacted_count']} sensitive PII tokens")
    print(f"2. {BOLD}Vector Deduplication:{RESET}      Status = {'DUPLICATE' if result['is_duplicate'] else 'UNIQUE (Passed)'}")
    print(f"3. {BOLD}CODEOWNERS Routing:{RESET}        Assigned to {BOLD}{result['primary_owner']}{RESET} | Priority: {BOLD}{result['priority']}{RESET} | SLA: {BOLD}{result['sla_target_hours']}h{RESET}")
    print(f"4. {BOLD}Ephemeral Sandbox Status:{RESET}  {GREEN}{result['sandbox_status']}{RESET} (Isolated pytest verified)")
    
    print(f"\n{YELLOW}{BOLD}[SCENE 3: HUMAN-IN-THE-LOOP (HITL) 'THE VIBE DIFF' REVIEW CARD]{RESET}")
    print(f"{BOLD}Proposed Unified Diff Patch:{RESET}")
    print(f"{DIM}{result['proposed_diff_patch']}{RESET}")
    
    print(f"{BOLD}Sandbox Reproduction Test Code:{RESET}")
    print(f"{DIM}{result['failing_test_code']}{RESET}")
    
    print(f"\n{CYAN}{BOLD}Current State: {result['status']}{RESET}")
    print(f"The agent has paused execution awaiting human signoff.\n")
    
    choice = input(f"{BOLD}Developer Decision: [A]pprove & Open GitHub PR | [R]eject | [Q]uit? (Default: A): {RESET}").strip().upper()
    if not choice:
        choice = "A"
        
    if choice == "A":
        print(f"\n{YELLOW}{BOLD}[SCENE 4: DEVELOPER HMAC WEBHOOK APPROVAL & PR CREATION]{RESET}")
        webhook_sig = WebhookSignalInput(
            session_id=result["session_id"],
            issue_id=sample_crash["issue_id"],
            action="APPROVE",
            reviewer_id="@lead-payment-engineer",
            hmac_signature="valid-hmac-signature"
        )
        approval_res = process_hitl_webhook_signal(webhook_sig)
        
        print(f"\n{GREEN}{BOLD}🎉 PULL REQUEST CREATED SUCCESSFULLY!{RESET}")
        print(f"  • Status:       {approval_res['status']}")
        print(f"  • Action Taken: {approval_res['action_taken']}")
        print(f"  • PR URL:       {CYAN}{BOLD}{approval_res['pr_url']}{RESET}")
        print(f"  • Details:      {approval_res['message']}\n")
    else:
        print(f"\n{RED}Triage session closed or cancelled by reviewer.{RESET}")

def main():
    print_banner()
    print("Select Demo Mode:")
    print("  [1] Interactive End-to-End Walkthrough (Full Live Lifecycle)")
    print("  [2] Run Evaluation Suite (Golden Dataset)")
    print("  [3] Exit")
    
    choice = input("\nEnter choice [1-3] (Default: 1): ").strip()
    if choice == "2":
        subprocess.run([sys.executable, "tests/eval/run_eval.py"])
    elif choice == "3":
        sys.exit(0)
    else:
        run_interactive_demo()

if __name__ == "__main__":
    main()
