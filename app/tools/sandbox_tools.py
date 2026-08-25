"""ADK Tool for Pytest Reproduction Generation, Fix Patching, and Ephemeral Sandbox Execution.

Follows Section 5 Enterprise Security & Sandboxing:
- Gated via Two-Layer Policy Server (Structural + Semantic Gating).
- Enforces Zero Ambient Authority via SPIFFE Identity and JIT Downscoping.
- Provisions an Ephemeral Agent Sandbox (isolated directory/subprocess) to generate and test code without mutating host environment.
"""

import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.remediation import (
    ReproductionTestOutput,
    FixPatchOutput,
    SandboxExecutionResult
)
from app.security import (
    PolicyServer,
    SPIFFEIdentityAuthority,
    EphemeralAgentSandbox,
)

class ExecuteSandboxInput(BaseModel):
    """Input payload for executing reproduction, patching, and sandbox validation."""
    issue_id: str = Field(..., description="Target issue ID")
    stack_trace: Optional[str] = Field(None, description="Sanitized stack trace or error log")
    source_file_path: Optional[str] = Field(None, description="Target source file path")
    existing_source_code: Optional[str] = Field(None, description="Current file source code")

class ExecuteSandboxOutput(BaseModel):
    """Output payload from sandbox reproduction and fix execution."""
    status: str = Field(..., description="'SUCCESS' or 'ERROR'")
    reproduction_test: Optional[ReproductionTestOutput] = Field(None, description="Generated pytest code")
    fix_patch: Optional[FixPatchOutput] = Field(None, description="Synthesized unified diff patch")
    sandbox_result: Optional[SandboxExecutionResult] = Field(None, description="Sandbox test execution status")
    message: str = Field(..., description="Human-readable outcome summary")
    recovery_hint: Optional[str] = Field(None, description="Corrective guidance on failure")

def execute_reproduction_and_sandbox_fix(
    issue_id: str,
    stack_trace: Optional[str] = None,
    source_file_path: Optional[str] = None,
    existing_source_code: Optional[str] = None
) -> Dict[str, Any]:
    """Synthesizes a reproduction test, executes it in an Ephemeral Agent Sandbox,
    applies the fix patch in the sandbox, and verifies the fix passes cleanly.

    Args:
        issue_id: Target bug issue identifier (e.g. 'BUG-2026-001').
        stack_trace: Sanitized stack trace or error log indicating the failure point.
        source_file_path: Path to the failing source file.
        existing_source_code: Optional string containing current code content.

    Returns:
        Dict[str, Any]: A dictionary serialized from ExecuteSandboxOutput containing
            status ('SUCCESS' or 'ERROR'), reproduction_test, fix_patch, sandbox_result,
            message, and recovery_hint.

    Raises:
        None: All exceptions are caught and returned in the structured dictionary.
    """
    start_time = time.time()
    try:
        # Step 1: Security Gating via Two-Layer Policy Server
        jit_ctx = SPIFFEIdentityAuthority.issue_jit_context(
            agent_role="remediation",
            target_tool="execute_reproduction_and_sandbox_fix"
        )
        policy_eval = PolicyServer.evaluate_tool_invocation(
            tool_name="execute_reproduction_and_sandbox_fix",
            tool_args={
                "issue_id": issue_id,
                "stack_trace": stack_trace,
                "source_file_path": source_file_path,
                "existing_source_code": existing_source_code
            },
            security_ctx=jit_ctx
        )
        if not policy_eval.is_allowed:
            return ExecuteSandboxOutput(
                status="ERROR",
                message=f"Zero-Trust Policy Violation [{policy_eval.layer_failed}]: {policy_eval.reason}",
                recovery_hint=policy_eval.recovery_hint
            ).model_dump()

        # Step 2: Provision Isolated Ephemeral Agent Sandbox
        sandbox = EphemeralAgentSandbox()
        sandbox.provision_sandbox()

        rel_path = source_file_path or "services/payment_gateway.py"
        
        # Step 3: Synthesize Reproduction Test inside Sandbox
        test_file_name, repro_code = sandbox.synthesize_repro_test_in_sandbox(issue_id, rel_path)
        
        # Step 4: Run Initial Pytest in Sandbox (Expect initial run)
        init_run = sandbox.execute_pytest_in_sandbox(test_file_name)
        repro_failed_first = (init_run["returncode"] != 0)

        # Step 5: Synthesize and Apply Fix Patch inside Sandbox
        diff_patch, explanation = sandbox.apply_patch_in_sandbox(rel_path, issue_id)
        patch_clean = bool(diff_patch)

        # Step 6: Re-run Pytest in Sandbox (Verify Fix)
        post_run = sandbox.execute_pytest_in_sandbox(test_file_name)
        post_passed = (post_run["returncode"] == 0)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        sandbox_stdout = post_run["stdout"] or init_run["stdout"]

        # Step 7: Teardown and reset Ephemeral Sandbox
        sandbox.teardown_sandbox()

        if post_passed:
            return ExecuteSandboxOutput(
                status="SUCCESS",
                reproduction_test=ReproductionTestOutput(
                    issue_id=issue_id,
                    test_file_name=test_file_name,
                    test_code=repro_code,
                    framework="pytest"
                ),
                fix_patch=FixPatchOutput(
                    issue_id=issue_id,
                    target_file_path=rel_path,
                    diff_patch=diff_patch,
                    explanation=explanation
                ),
                sandbox_result=SandboxExecutionResult(
                    status="PASSED",
                    reproduction_test_failed_first=repro_failed_first,
                    patch_applied_cleanly=patch_clean,
                    post_patch_test_passed=True,
                    stdout=sandbox_stdout,
                    stderr=post_run["stderr"],
                    execution_time_ms=duration_ms
                ),
                message=f"Ephemeral sandbox pytest executed in {duration_ms}ms: reproduction ran, patch applied cleanly in isolated sandbox, post-patch test PASSED.",
                recovery_hint=None
            ).model_dump()
        else:
            return ExecuteSandboxOutput(
                status="ERROR",
                message=f"Post-patch pytest failed in ephemeral sandbox with exit code {post_run['returncode']}.",
                recovery_hint="Inspect sandbox test output and refine LLM patch logic."
            ).model_dump()

    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return ExecuteSandboxOutput(
            status="ERROR",
            message=f"Ephemeral sandbox execution encountered exception after {duration_ms}ms: {str(exc)}",
            recovery_hint="Check sandbox dependencies and file permissions."
        ).model_dump()
