"""Unit tests for Claude Code Review Tool and CodeReviewAgent."""

import pytest
from app.models.remediation import CodeReviewResult, CodeReviewInput
from app.tools.review_tools import review_code_patch_with_claude
from app.agents.review import CodeReviewAgentRunner
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
    result = review_code_patch_with_claude(
        issue_id="BUG-2026-101",
        target_file_path="services/payment_gateway.py",
        diff_patch=diff_patch,
        patch_explanation="Added defensive null-check on incoming payload to prevent CWE-476.",
        reproduction_test_code=repro_test
    )
    
    assert isinstance(result, dict)
    assert result["verdict"] in ["APPROVED", "CHANGES_REQUESTED"]
    assert result["score"] >= 90
    assert result["security_verdict"] == "PASS"
    assert any("CWE-476" in check for check in result["cwe_checks"])
    assert "LGTM" in result["summary"] or "Approved" in result["summary"]

def test_code_review_agent_runner():
    """Validates CodeReviewAgentRunner integration with sanitized reports and observability."""
    runner = CodeReviewAgentRunner()
    
    sanitized_report = SanitizedBugReport(
        issue_id="BUG-2026-101",
        title="TypeError: NoneType object has no attribute get",
        cleaned_description="Process checkout throws AttributeError when payload is empty",
        sanitized_logs="Traceback: line 42 in process_checkout: AttributeError",
        detected_exception_type="AttributeError",
        pii_redacted_count=2,
    )
    enrichment_context = EnrichmentContext(
        issue_id="BUG-2026-101",
        affected_files=["services/payment_gateway.py"],
        primary_owner="@payments-team",
        secondary_owners=[],
        severity="Critical",
        priority="P0",
        sla_target_hours=4
    )
    
    diff_patch = """
+    if payload is None:
+        return False
"""
    repro_test = """
def test_bug_fix():
    assert True
"""
    review_output = runner.review_patch(
        sanitized_report=sanitized_report,
        enrichment_context=enrichment_context,
        diff_patch=diff_patch,
        patch_explanation="Fixed null pointer dereference",
        reproduction_test_code=repro_test,
        request_id="req-test-review"
    )
    
    assert review_output["verdict"] == "APPROVED"
    assert review_output["score"] >= 90
    assert review_output["security_verdict"] == "PASS"
    assert "claude" in review_output["reviewer_model"].lower()

