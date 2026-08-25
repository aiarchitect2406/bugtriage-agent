"""Pydantic Schemas for Code Remediation, Test Generation, Fix Patching, and Sandbox Execution."""

from typing import List, Optional
from pydantic import BaseModel, Field

class ReproductionTestInput(BaseModel):
    """Input for Generating a Standalone Failing Reproduction Test."""
    issue_id: str = Field(..., description="Target issue ID")
    stack_trace: str = Field(..., description="Sanitized stack trace")
    source_code_context: str = Field(..., description="Relevant source code lines from repository")
    expected_behavior: str = Field(..., description="Expected execution result")
    actual_behavior: str = Field(..., description="Actual error or exception observed")

class ReproductionTestOutput(BaseModel):
    """Generated Self-Contained Unit Test Code."""
    issue_id: str
    test_file_name: str = Field(..., description="Proposed test filename, e.g. test_bug_2026_101.py")
    test_code: str = Field(..., description="Complete executable pytest Python test code")
    framework: str = Field("pytest", description="Test framework used: 'pytest' or 'unittest'")

class FixPatchInput(BaseModel):
    """Input for Generating a Root Cause Fix Patch."""
    issue_id: str
    reproduction_test_code: str
    source_file_path: str
    existing_source_code: str
    error_summary: str

class FixPatchOutput(BaseModel):
    """Synthesized Unified Diff Fix Patch."""
    issue_id: str
    target_file_path: str
    diff_patch: str = Field(..., description="Unified git diff patch string")
    explanation: str = Field(..., description="Root cause explanation and fix rationale")

class SandboxExecutionResult(BaseModel):
    """Execution Status from Containerized Local Test Sandbox."""
    status: str = Field(..., description="Execution status: 'PASSED', 'FAILED', or 'ERROR'")
    reproduction_test_failed_first: bool = Field(..., description="True if test failed prior to patch application (confirming reproduction)")
    patch_applied_cleanly: bool = Field(..., description="True if git diff patch applied cleanly")
    post_patch_test_passed: bool = Field(..., description="True if pytest passed after patch application")
    stdout: str = Field("", description="Captured stdout from pytest run")
    stderr: str = Field("", description="Captured stderr from pytest run")
    execution_time_ms: float = Field(0.0, description="Test suite runtime in milliseconds")

class CodeReviewInput(BaseModel):
    """Input for Independent Peer Code Review by Claude."""
    issue_id: str = Field(..., description="Target issue ID")
    target_file_path: str = Field(..., description="Path of the modified source file")
    diff_patch: str = Field(..., description="Unified git diff patch string")
    patch_explanation: str = Field(..., description="Explanation from generator model")
    reproduction_test_code: str = Field(..., description="Pytest reproduction unit test code")
    source_context: Optional[str] = Field(None, description="Surrounding source code context")

class CodeReviewResult(BaseModel):
    """Structured Peer Code Review Output from Claude Reviewer."""
    verdict: str = Field(..., description="Review verdict: 'APPROVED' or 'CHANGES_REQUESTED'")
    score: int = Field(..., description="Overall code quality score out of 100")
    security_verdict: str = Field(..., description="Security assessment: 'PASS' or 'FAIL'")
    feedback_comments: List[str] = Field(default_factory=list, description="Actionable review comments and suggestions")
    cwe_checks: List[str] = Field(default_factory=list, description="Checked security CWEs (e.g., CWE-476, CWE-89, CWE-79)")
    reviewer_model: str = Field("claude-3-5-sonnet", description="Model used for independent peer review")
    summary: str = Field("", description="One-line summary of review assessment")

