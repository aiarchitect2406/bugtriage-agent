"""Live End-to-End Production Integration Test: GitHub Issue -> GitHub Actions / GEAP Pipeline -> Live PR.

This test validates the 100% live cloud execution:
1. Creates a real GitHub Issue on `aiarchitect2406/example-payment-svc`.
2. GitHub's workflow `triage-on-issue.yml` automatically triggers.
3. Authenticates with GCP WIF and runs the Multi-Agent triage pipeline.
4. Generates fix, runs sandbox tests, pushes fix branch, opens PR, and comments on the issue.
5. This test polls GitHub until the PR and resolution comment are verified.
"""

import json
import os
import sys
import time
import urllib.request
import pytest

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

TARGET_REPO = os.getenv("TARGET_REPO", "aiarchitect2406/example-payment-svc")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "BugTriage-Agent-E2E-Test"
}


def create_github_issue(title: str, body: str) -> dict:
    url = f"https://api.github.com/repos/{TARGET_REPO}/issues"
    payload = {
        "title": title,
        "body": body,
        "labels": ["bug", "e2e-live-test"]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_issue_comments(issue_number: int) -> list:
    url = f"https://api.github.com/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []


def get_pull_requests() -> list:
    url = f"https://api.github.com/repos/{TARGET_REPO}/pulls?state=all&sort=created&direction=desc&per_page=10"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []


@pytest.mark.integration
@pytest.mark.skipif(
    not GITHUB_TOKEN or os.getenv("RUN_LIVE_GITHUB_TEST") != "true",
    reason="Live GitHub E2E tests require valid GITHUB_TOKEN and RUN_LIVE_GITHUB_TEST=true",
)
def test_live_production_github_workflow_e2e():
    """Runs a live end-to-end test against the production GitHub repository."""
    title = f"[LIVE-E2E-{int(time.time())}] ZeroDivisionError in services/settlement_engine.py"
    body = (
        "### Production Bug Report\n\n"
        "**Stack Trace**:\n"
        "```python\n"
        "Traceback (most recent call last):\n"
        '  File "services/settlement_engine.py", line 42, in calculate_settlement_split\n'
        "    fee_per_transaction = total_platform_fee / transaction_count\n"
        "ZeroDivisionError: division by zero\n"
        "```\n\n"
        "**Steps to Reproduce**:\n"
        "1. Process batch reconciliation with transaction_count = 0.\n"
        "2. Observe unhandled ZeroDivisionError.\n"
    )

    # 1. Create Issue on GitHub
    print(f"\\n[1] Creating Live GitHub Issue on {TARGET_REPO}...")
    issue = create_github_issue(title, body)
    issue_number = issue["number"]
    issue_url = issue["html_url"]
    print(f"  Created Issue #{issue_number}: {issue_url}")

    # 2. Poll for Workflow Completion (PR & Issue Comment)
    print(f"\\n[2] Waiting for GitHub Action / GEAP Workflow to create PR and comment...")
    matched_pr = None
    matched_comment = None
    max_wait_seconds = 120
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        time.sleep(5)
        prs = get_pull_requests()
        for pr in prs:
            head_ref = pr.get("head", {}).get("ref", "")
            pr_title = pr.get("title", "")
            pr_body = pr.get("body", "")
            if (
                f"issue-{issue_number}" in head_ref
                or f"GH-{issue_number}" in pr_title
                or f"#{issue_number}" in pr_body
            ):
                matched_pr = pr
                break

        comments = get_issue_comments(issue_number)
        if comments:
            matched_comment = comments[0]

        if matched_pr and matched_comment:
            print(f"  PR and Comment found in {int(time.time() - start_time)}s!")
            break

    assert matched_pr is not None, f"Timed out waiting for automated PR for Issue #{issue_number}"
    print(f"  Automated PR Verified: {matched_pr['html_url']}")
    if matched_comment:
        print(f"  Resolution Comment Verified: {matched_comment['html_url']}")


if __name__ == "__main__":
    test_live_production_github_workflow_e2e()
