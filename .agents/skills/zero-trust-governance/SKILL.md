---
name: zero-trust-governance
description: Mandatory Zero-Trust Security, Ephemeral Kernel Sandboxing, SPIFFE Agent Identity, Hybrid Policy Gating, The Vibe Diff HITL, and Circuit Breaker Playbooks.
---

# Zero-Trust Security, Governance & Circuit Breakers

This skill defines mandatory enterprise security, governance, and containment standards for autonomous agents built on Google ADK 2.0 and GEAP.

---

## 1. Ephemeral Kernel-Level Sandbox Isolation
- All dynamically generated code, code translation steps, and test executions must run in isolated, ephemeral sandboxes (gVisor).
- Sandboxes must lack access to the host file system or network and must reset state completely between runs.
- **Supply Chain Defense**: Prevent slopsquatting by enforcing pre-approved package allowlists, strict version pinning, and SBOM scanning.

---

## 2. Zero Ambient Authority & Identity Propagation
- **Cryptographic Agent Identity**: Assign a unique cryptographic Agent Identity (SPIFFE standard) to every agent rather than running with broad default administrative credentials.
- **Just-In-Time (JIT) Downscoping**: Ensure containers obtain fresh, hyper-restricted credentials specifically scoped down to required files and endpoints.
- **File-Tree Allowlists**: Enforce restrictive read/write directory allowlists using deny-by-default rules.

---

## 3. Hybrid Policy Server (Structural & Semantic Gating)
- Gate all tool executions via a two-layer Policy Server:
  - **Layer 1 (Structural Gating)**: Deterministic, fast role/environment checks (e.g. read-only roles cannot execute write tools).
  - **Layer 2 (Semantic Gating)**: Secondary LLM safety scan checking arguments against natural-language guidelines to block unmasked secrets or malicious payloads.

---

## 4. Human-in-the-Loop Checkpoints & "The Vibe Diff"
- Sensitive operations (financial transactions, production database writes, PR creation) must pause execution in state `"AWAITING_HUMAN_REVIEW"`.
- **The Vibe Diff**: Render a plain-English intent summary side-by-side with original instructions and code diffs so reviewers can assess operational impact without approval fatigue.
- Require cryptographic or HMAC-verified authentication (`APPROVE`, `MODIFY`, `REJECT`) before resuming execution.

---

## 5. The Security Response Playbook (Circuit Breakers)
On detecting intent drift or an anomalous volume of expensive reasoning loops:
1. **Trip the Circuit Breaker**: Instantly revoke the compromised agent's tool credentials.
2. **Stateful Quarantine**: Pause container execution, freeze short-term memory intact for forensic debugging, and route the trace to the review queue.
3. **Rollback**: Trigger an automatic git rollback to the last known safe version control checkpoint.
