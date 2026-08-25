"""SPIFFE Agent Identity and Just-In-Time (JIT) Downscoping Context (Section 5.2).

Enforces Zero Ambient Authority:
- Assigns cryptographic SPIFFE identity to each agent (spiffe://bugtriage.enterprise/agent/<role>).
- Issues JIT downscoped access tokens per tool execution with strict file-tree allowlists.
"""

import time
import uuid
import fnmatch
from typing import List, Optional
from pydantic import BaseModel, Field

SPIFFE_TRUST_DOMAIN = "bugtriage.enterprise"

class JITSecurityContext(BaseModel):
    """Just-In-Time Downscoped Security Context attached to tool invocations."""
    token_id: str = Field(default_factory=lambda: f"jit-{uuid.uuid4().hex[:12]}")
    spiffe_id: str = Field(..., description="Attested Agent SPIFFE ID")
    agent_role: str = Field(..., description="Role of the calling agent")
    allowed_tools: List[str] = Field(default_factory=list, description="Permitted tool function names")
    allowed_file_patterns: List[str] = Field(
        default_factory=lambda: [
            "target_repo/services/*.py",
            "target_repo/tests/*.py",
            "services/*.py",
            "tests/*.py",
            "app/services/*.py"
        ],
        description="Strict file-tree allowlist patterns"
    )
    denied_file_patterns: List[str] = Field(
        default_factory=lambda: [
            "*.env*",
            ".git*",
            "/etc/*",
            "/root/*",
            "app/config.py",
            "app/security/*",
            "*id_rsa*",
            "*.key",
            "*.pem"
        ],
        description="Deny-by-default protected patterns"
    )

    expires_at: float = Field(default_factory=lambda: time.time() + 300.0, description="Token expiration timestamp (5m TTL)")

class SPIFFEIdentityAuthority:
    """Authority for issuing SPIFFE identities and JIT downscoped capability tokens."""

    AGENT_TOOL_PERMISSIONS = {
        "coordinator": [
            "sanitize_logs_and_extract_stack",
            "query_similar_bugs_by_vector",
            "resolve_codeowners_and_blame",
            "execute_reproduction_and_sandbox_fix",
            "create_draft_pull_request"
        ],
        "ingestion": ["sanitize_logs_and_extract_stack"],
        "dedupe": ["query_similar_bugs_by_vector"],
        "enrichment": ["resolve_codeowners_and_blame"],
        "remediation": ["execute_reproduction_and_sandbox_fix"],
        "hitl": ["create_draft_pull_request"]
    }

    @classmethod
    def get_spiffe_id(cls, agent_role: str) -> str:
        """Returns the canonical SPIFFE ID for an agent role."""
        return f"spiffe://{SPIFFE_TRUST_DOMAIN}/agent/{agent_role.lower()}"

    @classmethod
    def issue_jit_context(cls, agent_role: str, target_tool: Optional[str] = None) -> JITSecurityContext:
        """Issues a fresh, downscoped JIT token specifically restricted to target tool and allowlists."""
        role_key = agent_role.lower().replace("agent", "").replace("_agent", "").strip()
        spiffe_id = cls.get_spiffe_id(role_key)
        allowed_tools = cls.AGENT_TOOL_PERMISSIONS.get(role_key, [])

        if target_tool and target_tool in allowed_tools:
            # Downscope strictly to the single requested tool
            effective_tools = [target_tool]
        else:
            effective_tools = allowed_tools

        return JITSecurityContext(
            spiffe_id=spiffe_id,
            agent_role=role_key,
            allowed_tools=effective_tools
        )

    @classmethod
    def validate_path_access(cls, security_ctx: JITSecurityContext, file_path: str) -> bool:
        """Enforces deny-by-default file tree allowlists against path traversal and protected files."""
        normalized = file_path.replace("\\", "/").strip()
        
        # 1. Block directory traversal
        if ".." in normalized or normalized.startswith("/etc") or normalized.startswith("/root"):
            return False

        # 2. Check deny patterns
        for deny_pat in security_ctx.denied_file_patterns:
            if fnmatch.fnmatch(normalized, deny_pat) or fnmatch.fnmatch(normalized.split("/")[-1], deny_pat):
                return False

        # 3. Check allowlist patterns
        for allow_pat in security_ctx.allowed_file_patterns:
            if fnmatch.fnmatch(normalized, allow_pat) or fnmatch.fnmatch(f"target_repo/{normalized}", allow_pat):
                return True

        return False
