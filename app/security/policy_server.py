"""Two-Layer Hybrid Policy Server for Structural and Semantic Tool Gating (Section 5.3).

Layer 1: Structural Gating (Deterministic role/env checks, JIT token validation, file-tree allowlists)
Layer 2: Semantic Gating (Secondary LLM/heuristic safety scan on tool arguments)
"""

import re
import time
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.security.spiffe import JITSecurityContext, SPIFFEIdentityAuthority
from app.observability.pii_scrubber import EnterprisePIIRedactor

logger = logging.getLogger("PolicyServer")

class PolicyEvaluationResult(BaseModel):
    """Result of two-layer policy evaluation."""
    is_allowed: bool = Field(..., description="Whether tool execution is permitted")
    layer_failed: Optional[str] = Field(None, description="'STRUCTURAL' or 'SEMANTIC' if failed")
    reason: str = Field(..., description="Explanation of policy decision")
    recovery_hint: Optional[str] = Field(None, description="Guidance to resolve violation")

class PolicyServer:
    """Enterprise Policy Server gating all tool invocations under Zero-Trust."""

    UNMASKED_SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|bearer|auth[_-]?token)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{8,}['\"]"),
        re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----"),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    ]

    INJECTION_PATTERNS = [
        re.compile(r"(?i)ignore previous instructions"),
        re.compile(r"(?i)rm\s+-rf\s+/"),
        re.compile(r"(?i)chmod\s+777"),
        re.compile(r"(?i)cat\s+/etc/passwd"),
    ]

    @classmethod
    def evaluate_tool_invocation(
        cls,
        tool_name: str,
        tool_args: Dict[str, Any],
        security_ctx: Optional[JITSecurityContext] = None
    ) -> PolicyEvaluationResult:
        """Evaluates tool invocation against Layer 1 (Structural) and Layer 2 (Semantic) policies."""
        ctx = security_ctx or SPIFFEIdentityAuthority.issue_jit_context("coordinator", tool_name)

        # ---------------------------------------------------------------------
        # LAYER 1: STRUCTURAL GATING (Fast, Deterministic Role & Path Checks)
        # ---------------------------------------------------------------------
        # 1.1 Check token expiry
        if time.time() > ctx.expires_at:
            return PolicyEvaluationResult(
                is_allowed=False,
                layer_failed="STRUCTURAL",
                reason=f"JIT Security Context {ctx.token_id} has expired.",
                recovery_hint="Request a refreshed JIT security context before calling tool."
            )

        # 1.2 Check agent-to-tool permission
        if tool_name not in ctx.allowed_tools:
            return PolicyEvaluationResult(
                is_allowed=False,
                layer_failed="STRUCTURAL",
                reason=f"Agent with SPIFFE ID {ctx.spiffe_id} is not permitted to invoke '{tool_name}'.",
                recovery_hint=f"Agent '{ctx.agent_role}' must delegate this task to an authorized subagent."
            )

        # 1.3 Check file path against File-Tree Allowlist (if file path is provided in arguments)
        for path_arg in ["source_file_path", "target_file_path", "file_path"]:
            if path_arg in tool_args and tool_args[path_arg]:
                file_path = str(tool_args[path_arg])
                if not SPIFFEIdentityAuthority.validate_path_access(ctx, file_path):
                    return PolicyEvaluationResult(
                        is_allowed=False,
                        layer_failed="STRUCTURAL",
                        reason=f"File-tree allowlist violation: Access to '{file_path}' is denied.",
                        recovery_hint="Ensure target file is within target_repo/services/ or target_repo/tests/."
                    )

        # ---------------------------------------------------------------------
        # LAYER 2: SEMANTIC GATING (Safety, Secret Leakage, Command Injections)
        # ---------------------------------------------------------------------
        args_text = str(tool_args)

        # 2.1 Check for unmasked secrets in tool arguments
        for sec_pattern in cls.UNMASKED_SECRET_PATTERNS:
            if sec_pattern.search(args_text):
                return PolicyEvaluationResult(
                    is_allowed=False,
                    layer_failed="SEMANTIC",
                    reason="Semantic safety violation: Unmasked secrets or API credentials detected in tool arguments.",
                    recovery_hint="Scrub secrets using sanitize_logs_and_extract_stack before tool invocation."
                )

        # 2.2 Check for prompt injection / destructive system payloads
        for inj_pattern in cls.INJECTION_PATTERNS:
            if inj_pattern.search(args_text):
                return PolicyEvaluationResult(
                    is_allowed=False,
                    layer_failed="SEMANTIC",
                    reason="Semantic safety violation: Dangerous instruction or command injection detected.",
                    recovery_hint="Remove prohibited shell commands and system directives from the payload."
                )

        return PolicyEvaluationResult(
            is_allowed=True,
            reason=f"Approved: JIT SPIFFE ID {ctx.spiffe_id} authorized for '{tool_name}'."
        )
