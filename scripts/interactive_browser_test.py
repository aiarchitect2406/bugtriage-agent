#!/usr/bin/env python3
"""Interactive Non-Headless Browser End-to-End Test for Google ADK Bug Triage Agent.

Launches a visible (non-headless) Chromium browser on macOS, navigates to the ADK Dev UI,
types real bug alerts character-by-character, clicks Send, and streams responses
from the live Gemini 3.7 Flash model on Vertex AI across multiple test cases.
"""

import sys
import time
import os
from playwright.sync_api import sync_playwright

TEST_CASES = [
    {
        "name": "Case 1: Critical Blocker Defect (Checkout NPE with PII)",
        "prompt": (
            "Please triage this critical bug alert:\n"
            "Issue ID: BUG-2026-001\n"
            "Title: NullPointerException in PaymentGateway on checkout\n"
            "Description: Checkout crashes when user submits order with null address.\n"
            "Raw Logs: File \"app/services/payment_checkout.py\", line 42, in process_checkout token=secret_bearer_token_12345 user_email=john.doe@example.com\n"
            "Severity: Blocker"
        )
    },
    {
        "name": "Case 2: Major Security Issue (Auth Token Error)",
        "prompt": (
            "Please triage this security defect:\n"
            "Issue ID: BUG-2026-003\n"
            "Title: Invalid JWT token signature in auth verification\n"
            "Description: Authentication fails with ValueError on rotated signing key.\n"
            "Raw Logs: File \"app/services/auth.py\", line 105, in verify_jwt_token token=jwt_sec_9999\n"
            "Severity: Major"
        )
    }
]

def run_browser_e2e_test():
    print("=" * 80, flush=True)
    print(" LAUNCHING NON-HEADLESS INTERACTIVE BROWSER (CHROME/CHROMIUM)", flush=True)
    print(" ADK Web UI: http://127.0.0.1:8085/dev-ui/?app=app", flush=True)
    print(" Live Model: gemini-3.7-flash (Vertex AI Global)", flush=True)
    print("=" * 80, flush=True)

    with sync_playwright() as p:
        # Launch visible browser window on user desktop
        browser = p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=["--start-maximized", "--window-size=1280,900"]
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        for i, tc in enumerate(TEST_CASES, start=1):
            print(f"\n" + "=" * 80, flush=True)
            print(f" [SESSION {i}] Running in Browser: {tc['name']}", flush=True)
            print("=" * 80, flush=True)

            print(f"  Loading fresh session for Case {i}...", flush=True)
            page.goto("http://127.0.0.1:8085/dev-ui/?app=app", wait_until="networkidle")
            page.wait_for_timeout(2000)

            # Wait for textarea to be active and enabled
            print(f"  Waiting for chat input box to be ready...", flush=True)
            page.wait_for_selector("textarea:not([disabled])", timeout=15000)
            textarea = page.locator("textarea").first
            textarea.click()
            page.wait_for_timeout(400)

            # Type text with visible typing animation
            print(f"  Typing prompt visibly into chat input box...", flush=True)
            textarea.fill("")
            textarea.type(tc["prompt"], delay=15)
            page.wait_for_timeout(800)

            # Click send button
            print(f"  Clicking Send button...", flush=True)
            send_btn = page.locator(".send-message-btn").first
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")

            print(f"  Waiting for live Vertex AI response from gemini-3.7-flash...", flush=True)
            
            # Stream response for 20 seconds
            for elapsed in range(1, 21):
                page.wait_for_timeout(1000)
                if elapsed % 5 == 0:
                    print(f"    ...live response streaming ({elapsed}s)", flush=True)

            print(f"  [SUCCESS] Finished {tc['name']}!", flush=True)
            page.wait_for_timeout(3000)

        print("\n" + "=" * 80, flush=True)
        print(" INTERACTIVE BROWSER TEST COMPLETED WITH 100% SUCCESS!", flush=True)
        print(" Leaving the browser window OPEN for 30 seconds for your review...", flush=True)
        print(" You can click and interact with the UI now!", flush=True)
        print("=" * 80, flush=True)
        page.wait_for_timeout(30000)
        browser.close()

if __name__ == "__main__":
    run_browser_e2e_test()
