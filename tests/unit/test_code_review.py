"""Unit tests for Claude Code Review Tool and CodeReviewAgent."""

import pytest
from app.models.remediation import CodeReviewResult, CodeReviewInput
from app.tools.review_tools import review_code_patch_with_claude, _run_high_assurance_static_review
from app.models.bug_report import SanitizedBugReport, EnrichmentContext

def test_review_code_patch_deterministic():
    """Validates deterministic static code review output format and security verdicts."""
    diff_patch = """
--- a/services/payment_gateway.py
+++ b/services/payment_gateway.py
@@ -10,2 +10,4 @@
 def process_checkout(payload):
+    if payload is None:
+        raise ValueError("Invalid payload")
     return payload.get("amount", 0)
"""
    repro_test = """
def test_checkout_null_payload():
    result = process_checkout({"amount": 100})
    assert result == 100
"""
    result = _run_high_assurance_static_review(
        issue_id="BUG-2026-101",
        target_file_path="services/payment_gateway.py",
        diff_patch=diff_patch,
        patch_explanation="Added defensive null-check on incoming payload to prevent CWE-476.",
        reproduction_test_code=repro_test,
        model_name="claude-sonnet-4-6"
    )
    
    assert isinstance(result, dict)
    assert result["verdict"] in ["APPROVED", "CHANGES_REQUESTED"]
    assert result["score"] >= 90
    assert result["security_verdict"] == "PASS"
    assert any("CWE-476" in check for check in result["cwe_checks"])
    assert "LGTM" in result["summary"] or "Approved" in result["summary"]

def test_code_review_tool_execution():
    """Validates review_code_patch_with_claude tool with reproduction test and diff patch."""
    diff_patch = """
--- a/services/payment_gateway.py
+++ b/services/payment_gateway.py
@@ -10,3 +10,6 @@
 def process_checkout(payload: dict) -> dict:
+    if payload is None:
+        return {"status": "error", "message": "Payload cannot be None", "amount": 0}
     return {"status": "success", "amount": payload.get("amount", 0)}
"""
    repro_test = """
import pytest

def test_process_checkout_with_none_payload():
    result = process_checkout(None)
    assert result["status"] == "error"
    assert result["amount"] == 0

def test_process_checkout_valid():
    result = process_checkout({"amount": 100})
    assert result["status"] == "success"
    assert result["amount"] == 100
"""
    review_output = review_code_patch_with_claude(
        issue_id="BUG-2026-101",
        target_file_path="services/payment_gateway.py",
        diff_patch=diff_patch,
        patch_explanation="Fixed null pointer dereference by validating incoming payload before accessing dictionary keys.",
        reproduction_test_code=repro_test,
    )
    
    assert review_output["verdict"] in ["APPROVED", "CHANGES_REQUESTED"]
    assert isinstance(review_output["score"], int)
    assert review_output["score"] >= 0
    assert review_output["security_verdict"] in ["PASS", "FAIL"]
    assert "claude" in review_output["reviewer_model"].lower()

