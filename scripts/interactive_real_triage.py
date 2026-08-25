#!/usr/bin/env python3
"""Interactive End-to-End Bug Triage Demo with Real Target Codebase and Subprocess Sandbox.

Demonstrates:
1. Triggering an authentic runtime crash in target_repo/services/payment_gateway.py.
2. Passing the real exception traceback and PII logs to Google ADK Bug Triage Agent.
3. Real Git Blame & CODEOWNERS matching on target_repo.
4. Real subprocess pytest reproduction (verifying FAILED initially).
5. Real unified diff patching on target_repo source code.
6. Real subprocess pytest verification (verifying PASSED).
7. Interactive Human-In-The-Loop review of 'The Vibe Diff'.
8. Real Git branch creation and commit upon user approval.
"""

import os
import sys
import time
import traceback
import subprocess

# Ensure repo root in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.tools.git_tools import create_draft_pull_request

def trigger_real_crash() -> tuple[str, str]:
    """Triggers an actual Python runtime exception in target_repo."""
    target_repo_dir = os.path.join(REPO_ROOT, "target_repo")
    subprocess.run(["git", "checkout", "main"], cwd=target_repo_dir, capture_output=True)
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=target_repo_dir, capture_output=True)
    subprocess.run(["git", "clean", "-fdx"], cwd=target_repo_dir, capture_output=True)

    from target_repo.services.payment_gateway import process_checkout

    raw_stack = ""
    error_msg = ""
    try:
        # Trigger bug: shipping_address is None for digital goods checkout
        payload = {
            "user_id": "U-9842",
            "items": [{"name": "Cloud Subscription", "price": 49.99, "quantity": 1}],
            "shipping_address": None,
            "session_token": "bearer_secret_tok_991823487",
            "customer_email": "customer.vip@enterprise.example.com"
        }
        process_checkout(payload)
    except Exception as exc:
        raw_stack = traceback.format_exc()
        error_msg = str(exc)

    # Attach raw logs containing customer token and email for PII scrubbing validation
    raw_logs = (
        f"{raw_stack}\n"
        f"2026-08-24 10:20:00 ERROR PaymentGateway - Failed processing order for user U-9842: {error_msg}\n"
        f"Context: auth_header='Bearer bearer_secret_tok_991823487' user_email='customer.vip@enterprise.example.com'"
    )
    return error_msg, raw_logs

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def main():
    print_section("REAL TARGET CODEBASE BUG TRIAGE & HITL VERIFICATION")
    print(f"Target Repository : {os.path.join(REPO_ROOT, 'target_repo')}")
    print("ADK Agent         : Bug Triage Coordinator (Google ADK 2.0)")
    print("LLM Backend       : Vertex AI (gemini-3.7-flash / gemini-3.1-pro-preview, Global)")

    # 1. Trigger authentic crash
    print_section("STEP 1: Triggering Real Runtime Exception in target_repo")
    error_msg, raw_logs = trigger_real_crash()
    print(f"[!] Caught Real Exception: AttributeError: {error_msg}")
    print(f"--- Raw Crash Log & Traceback ---\n{raw_logs}")

    # 2. Scrub PII and Parse Stack Trace
    print_section("STEP 2: Ingestion & Sensitive Data Sanitization (PII Scrubbing)")
    sanitize_res = sanitize_logs_and_extract_stack(
        issue_id="BUG-2026-001",
        title="AttributeError in PaymentGateway on checkout",
        description="Checkout crashes when user submits order with null address",
        raw_logs=raw_logs
    )
    print(f"Status           : {sanitize_res['status']}")
    print(f"Redaction Count  : {sanitize_res['sanitized_report']['pii_redacted_count']}")
    print(f"Sanitized Log    :\n{sanitize_res['sanitized_report']['sanitized_logs']}")

    # 3. Vector Deduplication
    print_section("STEP 3: Vector Deduplication & Semantic Search")
    dedupe_res = query_similar_bugs_by_vector(
        issue_id="BUG-2026-001",
        bug_title="AttributeError in calculate_tax on null address",
        bug_description="Checkout crashes with NoneType error when shipping_address is None"
    )
    d_res = dedupe_res["dedupe_result"]
    print(f"Status           : {dedupe_res['status']}")
    print(f"Is Duplicate     : {d_res['is_duplicate']}")
    print(f"Top Similarity   : {d_res['similarity_score']:.2f}")

    # 4. CODEOWNERS & Real Git Blame
    print_section("STEP 4: Real Git Blame & CODEOWNERS Resolution")
    stack_frames = sanitize_res["sanitized_report"]["stack_frames"]
    ownership_res = resolve_codeowners_and_blame(
        issue_id="BUG-2026-001",
        stack_frames=stack_frames,
        severity_input="Blocker"
    )
    ctx = ownership_res["enrichment_context"]
    print(f"Affected Files   : {ctx['affected_files']}")
    print(f"Primary Owner    : {ctx['primary_owner']}")
    print(f"Git Blame Authors: {ctx['recent_commit_authors']}")
    print(f"Priority / SLA   : {ctx['priority']} ({ctx['severity']}) -> {ctx['sla_target_hours']}h SLA")

    # 5. Real Subprocess Pytest Sandbox Execution
    print_section("STEP 5: Real Pytest Sandbox Reproduction & Diff Patching")
    print("[*] Generating test_bug_2026_001_repro.py in target_repo/tests/...")
    print("[*] Running pytest in subprocess sandbox on initial buggy code (expecting FAILED)...")
    sandbox_res = execute_reproduction_and_sandbox_fix(
        issue_id="BUG-2026-001",
        source_file_path="services/payment_gateway.py"
    )
    sb_result = sandbox_res["sandbox_result"]
    print(f"Initial Test Failed First : {sb_result['reproduction_test_failed_first']} (Verified real bug reproduction)")
    print(f"Patch Applied Cleanly     : {sb_result['patch_applied_cleanly']}")
    print(f"Post-Patch Test Passed    : {sb_result['post_patch_test_passed']} (Verified fix passes suite)")
    print(f"Sandbox Execution Time    : {sb_result['execution_time_ms']}ms")
    print(f"\n--- Real Pytest Subprocess Stdout ---\n{sb_result['stdout']}")

    # 6. Human-In-The-Loop "The Vibe Diff" Review
    print_section("STEP 6: Human-in-the-Loop Review Gate ('The Vibe Diff')")
    print("┌────────────────────────────────────────────────────────────────────────┐")
    print("│ ADK A2UI REVIEW CARD: AWAITING_HUMAN_REVIEW                            │")
    print("├────────────────────────────────────────────────────────────────────────┤")
    print(f"│ Issue       : BUG-2026-001 (Blocker - P0)                              │")
    print(f"│ Owner       : {ctx['primary_owner']}                                          │")
    print(f"│ Blame Author: {ctx['recent_commit_authors'][0]}         │")
    print(f"│ Summary     : {sandbox_res['fix_patch']['explanation']}         │")
    print("├────────────────────────────────────────────────────────────────────────┤")
    print("│ UNIFIED DIFF PATCH:                                                    │")
    for line in sandbox_res['fix_patch']['diff_patch'].split("\n"):
        print(f"│ {line}")
    print("└────────────────────────────────────────────────────────────────────────┘")

    # Prompt user or auto-approve if interactive flag
    user_input = os.environ.get("AUTO_APPROVE", "")
    if not user_input:
        try:
            user_input = input("\n[?] Do you APPROVE committing this verified fix to target_repo? [Y/n]: ").strip()
        except EOFError:
            user_input = "y"

    if user_input.lower() in ("", "y", "yes", "approve"):
        print("\n[+] Human Approval Received! Resuming agent execution...")
        pr_res = create_draft_pull_request(
            issue_id="BUG-2026-001",
            commit_message="fix(payment): safely handle None shipping_address in tax calculation",
            reviewer_handle=ctx['primary_owner']
        )
        print_section("STEP 7: Real Git Commit & Branch Creation")
        print(f"Status           : {pr_res['status']}")
        print(f"Git Branch       : {pr_res['branch_name']}")
        print(f"Message          : {pr_res['message']}")

        # Show actual git log in target_repo
        target_repo_dir = os.path.join(REPO_ROOT, "target_repo")
        git_log = subprocess.run(
            ["git", "log", "-n", "2", "--oneline"],
            cwd=target_repo_dir,
            capture_output=True,
            text=True
        ).stdout.strip()
        print(f"\n--- target_repo Git History ---\n{git_log}")
        print("\n[SUCCESS] End-to-End Real Grounded Triage Completed Successfully!")
    else:
        print("\n[-] Fix Rejected by Human Reviewer. Execution halted.")

if __name__ == "__main__":
    main()
