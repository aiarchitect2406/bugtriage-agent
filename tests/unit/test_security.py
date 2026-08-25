"""Unit tests for Zero-Trust Security, SPIFFE Identity, Policy Server, and Ephemeral Sandbox."""

import os
import pytest
from app.security.spiffe import SPIFFEIdentityAuthority, JITSecurityContext
from app.security.policy_server import PolicyServer
from app.security.sandbox import EphemeralAgentSandbox

def test_spiffe_identity_generation():
    """Verifies that each agent receives an attested SPIFFE ID."""
    spiffe_id = SPIFFEIdentityAuthority.get_spiffe_id("remediation")
    assert spiffe_id == "spiffe://bugtriage.enterprise/agent/remediation"

def test_jit_downscoped_context():
    """Verifies JIT token is downscoped to target tool only."""
    jit_ctx = SPIFFEIdentityAuthority.issue_jit_context(
        agent_role="remediation",
        target_tool="execute_reproduction_and_sandbox_fix"
    )
    assert jit_ctx.agent_role == "remediation"
    assert jit_ctx.allowed_tools == ["execute_reproduction_and_sandbox_fix"]
    assert "target_repo/services/*.py" in jit_ctx.allowed_file_patterns

def test_file_tree_allowlist_enforcement():
    """Verifies deny-by-default file tree validation."""
    jit_ctx = SPIFFEIdentityAuthority.issue_jit_context("remediation")
    
    # Allowed paths
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, "target_repo/services/payment_gateway.py") is True
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, "services/auth_service.py") is True
    
    # Denied paths (Path traversal, .env, /etc)
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, "../../.env") is False
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, "/etc/passwd") is False
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, ".git/config") is False
    assert SPIFFEIdentityAuthority.validate_path_access(jit_ctx, "app/config.py") is False

def test_policy_server_structural_gating_unauthorized_tool():
    """Verifies Layer 1 blocks unauthorized tool calls."""
    ingestion_ctx = SPIFFEIdentityAuthority.issue_jit_context("ingestion")
    res = PolicyServer.evaluate_tool_invocation(
        tool_name="create_draft_pull_request",
        tool_args={"issue_id": "BUG-001"},
        security_ctx=ingestion_ctx
    )
    assert res.is_allowed is False
    assert res.layer_failed == "STRUCTURAL"
    assert "not permitted" in res.reason

def test_policy_server_structural_gating_denied_path():
    """Verifies Layer 1 blocks access to denied paths."""
    remediation_ctx = SPIFFEIdentityAuthority.issue_jit_context(
        "remediation",
        "execute_reproduction_and_sandbox_fix"
    )
    res = PolicyServer.evaluate_tool_invocation(
        tool_name="execute_reproduction_and_sandbox_fix",
        tool_args={"issue_id": "BUG-001", "source_file_path": "/etc/shadow"},
        security_ctx=remediation_ctx
    )
    assert res.is_allowed is False
    assert res.layer_failed == "STRUCTURAL"
    assert "File-tree allowlist violation" in res.reason

def test_policy_server_semantic_gating_secret_leak():
    """Verifies Layer 2 blocks unmasked credentials in tool payloads."""
    remediation_ctx = SPIFFEIdentityAuthority.issue_jit_context("remediation")
    res = PolicyServer.evaluate_tool_invocation(
        tool_name="execute_reproduction_and_sandbox_fix",
        tool_args={"issue_id": "BUG-001", "stack_trace": "api_key='sk-1234567890abcdef1234567890'"},
        security_ctx=remediation_ctx
    )
    assert res.is_allowed is False
    assert res.layer_failed == "SEMANTIC"
    assert "Unmasked secrets" in res.reason

def test_policy_server_semantic_gating_command_injection():
    """Verifies Layer 2 blocks command injection payloads."""
    remediation_ctx = SPIFFEIdentityAuthority.issue_jit_context("remediation")
    res = PolicyServer.evaluate_tool_invocation(
        tool_name="execute_reproduction_and_sandbox_fix",
        tool_args={"issue_id": "BUG-001", "stack_trace": "rm -rf /"},
        security_ctx=remediation_ctx
    )
    assert res.is_allowed is False
    assert res.layer_failed == "SEMANTIC"
    assert "Dangerous instruction" in res.reason

def test_ephemeral_agent_sandbox_lifecycle():
    """Verifies that EphemeralAgentSandbox provisions, runs, and cleans up completely."""
    sandbox = EphemeralAgentSandbox()
    sandbox_dir = sandbox.provision_sandbox()
    assert os.path.exists(sandbox_dir)
    
    test_file, code = sandbox.synthesize_repro_test_in_sandbox("BUG-TEST-001", "services/payment_gateway.py")
    assert test_file.startswith("test_bug_test_001")
    assert os.path.exists(os.path.join(sandbox_dir, "target_repo", "tests", test_file))
    
    diff, exp = sandbox.apply_patch_in_sandbox("services/payment_gateway.py", "BUG-TEST-001")
    assert "calculate_tax" in diff or "state" in diff
    
    # Teardown
    sandbox.teardown_sandbox()
    assert not os.path.exists(sandbox_dir)
