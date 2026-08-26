"""Unit tests for DLP Sanitization, Model Armor Redaction, and Sandbox Execution."""

import pytest
from app.tools.sanitize_tools import EnterprisePIIRedactor, sanitize_logs_and_extract_stack
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix


def test_enterprise_pii_redactor_regex_fallback():
    """Verifies that EnterprisePIIRedactor redacts emails and secrets."""
    redactor = EnterprisePIIRedactor()
    sample_text = "User email is john.doe@example.com with secret api_key=ghp_ABC123456789XYZ"
    sanitized, count = redactor.redact_text(sample_text)
    assert "[REDACTED_EMAIL]" in sanitized
    assert "john.doe@example.com" not in sanitized
    assert count >= 1




def test_sanitize_logs_and_extract_stack():
    """Verifies end-to-end log sanitization and stack trace extraction tool."""
    res = sanitize_logs_and_extract_stack(
        issue_id="BUG-TEST-001",
        title="Payment crash with user alice@company.com",
        description="Stack trace:\nFile 'payment_gateway.py', line 42, in process_checkout\nTypeError: 'NoneType' object",
        raw_logs="Authorization token: Bearer ghp_SecretToken123456",
        stack_trace=None,
        source_system="Sentry",
        metadata={"service": "payment-svc"}
    )
    assert res["status"] == "SUCCESS"
    report = res["sanitized_report"]
    assert report["issue_id"] == "BUG-TEST-001"
    assert "alice@company.com" not in report["cleaned_description"]


def test_sandbox_tools_subprocess_execution():
    """Verifies isolated subprocess sandbox test and fix execution."""
    result = execute_reproduction_and_sandbox_fix(
        issue_id="BUG-2026-NATIVE-001",
        stack_trace="TypeError: NoneType object is not subscriptable in payment_gateway.py",
        source_file_path="services/payment_gateway.py"
    )
    assert result["status"] == "SUCCESS"
    assert result["reproduction_test"]["framework"] == "pytest"
    assert result["sandbox_result"]["status"] == "PASSED"
    assert result["sandbox_result"]["post_patch_test_passed"] is True



