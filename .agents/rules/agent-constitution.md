# Production-Grade Agent Engineering Constitution & Workspace Rules

This constitution establishes mandatory engineering, security, context, and quality standards for building agents with Google ADK 2.0 and GEAP.

1. **Pydantic Type Safety & Tool Design**:
   - All tool functions MUST accept Pydantic input models (`BaseModel`) with field descriptions and return typed dictionaries generated via `.model_dump()`.
   - Tool functions MUST use descriptive action-verb naming (e.g., `query_similar_bugs_by_vector`, `create_draft_pull_request`).
   - Tool functions MUST include comprehensive Google-style docstrings documenting `Args`, `Returns`, and `Raises: None`.
   - Tool functions MUST handle all exceptions internally with zero unhandled crashes, returning structured dictionaries with `"status": "ERROR"` and guided LLM `"recovery_hint"`.

2. **Context & Memory Persistence**:
   - System prompts ("Constitutions") MUST be explicitly defined for every agent, stating persona, operational boundaries, and rules.
   - Short-term conversational state MUST be persisted using native `google.adk.sessions.VertexAiSessionService` (with `InMemorySessionService` fallback for testing).
   - Long-term cross-session knowledge MUST be managed via `google.adk.memory.VertexAiMemoryBankService`.
   - Memory consolidation MUST be executed via non-blocking async background callbacks (`add_session_to_memory` / `add_events_to_memory` via `CallbackContext`) to avoid blocking UI or main execution threads.
   - Context bloat MUST be prevented via token-based sliding window context compaction (`compact_session_history`) and background summarization.

3. **Multi-Agent Orchestration & Governance**:
   - Multi-agent architectures MUST use proven patterns (e.g., Coordinator-Worker DAG) rather than monolithic agent designs.
   - Strategic Model Routing MUST route low-latency/intake tasks to Flash models and deep planning/code analysis tasks to Pro models.
   - Guardrail Policy Plugins (`GuardrailPolicyPlugin`) MUST self-evaluate and validate business/SLA compliance before committing state.
   - High-stakes actions MUST pause in state `"AWAITING_HUMAN_REVIEW"` and render declarative A2UI review cards for human authorization.

4. **Observability, Tracing & PII Scrubbing**:
   - All logs MUST be emitted in Google Cloud Logging structured JSON format with timestamps, request IDs, agent names, and tool names.
   - Execution logs MUST capture pre-execution `INTENT` (arguments) and post-execution `OUTCOME` (results and `duration_ms`).
   - Distributed execution spans across agents MUST be traced using OpenTelemetry (`opentelemetry.trace`).
   - Sensitive data (passwords, tokens, emails, PII) MUST be scrubbed via Google Cloud Sensitive Data Protection (`dlp_v2.DlpServiceClient`) with regex fallback before logging or storing.

5. **Infrastructure, CI/CD & Secret Management**:
   - All changes MUST be validated against Golden Datasets in an automated CI evaluation harness (`eval_harness.py` via GitHub Actions).
   - Google Cloud infrastructure MUST be declared using Terraform (`main.tf`) with proper IAM role bindings (`roles/aiplatform.user`, `roles/secretmanager.secretAccessor`, `roles/dlp.user`).
   - Secrets MUST be retrieved dynamically at runtime via Google Cloud Secret Manager with zero hardcoded API keys.
   - System MUST support official Google ADK CLI (`adk run`, `adk web`) and Agent API CLI (`agentapi`).

6. **Spec-Driven & Behavior-Driven Development (SDD/BDD)**:
   - All feature development MUST follow BDD specifications (`Scenario`/`Given`/`When`/`Then`) and define at least three (3) concrete JSON evaluation cases upfront before code implementation.
   - Follow role-based execution modes (The Architect, The Builder, The Forensic Specialist, The Author).
   - Execute untrusted code in ephemeral kernel-level sandboxes (gVisor) with zero ambient authority and circuit breaker fail-safes.
