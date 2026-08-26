---
name: adk-geap-best-practices
description: Comprehensive Google Agent Development Kit (ADK 2.0) and Gemini Enterprise Agent Platform (GEAP) technical best practices covering Pydantic tools, Google docstrings, ToolContext, VertexAiMemoryBankService callbacks, sliding window compaction, structured Cloud Logging, OpenTelemetry tracing, Secret Manager, DLP PII scrubbing, HITL A2UI cards, and Agent CLI usage.
---

# Skill: Google ADK 2.0 & Gemini Enterprise Agent Platform (GEAP) Best Practices

This skill defines the technical standards, architectural patterns, and implementation rules for building enterprise-grade agents with **Google ADK 2.0** and **GEAP**.

---

## 1. Tool & Interface Design Best Practices

### 1.1 Action-Verb Function Naming
- Tool functions must begin with descriptive action verbs indicating what operation they perform (e.g., `query_similar_bugs_by_vector`, `create_draft_pull_request`, `resolve_codeowners_and_blame`).
- Never use generic noun-only names (`ticket`, `bug_data`) or vague helper names (`process_item`, `do_work`).

### 1.2 Comprehensive Google-Style Docstrings
- Every tool function must define complete Google-style docstrings that are parsed by the ADK schema generator and sent to the LLM.
- Clearly document:
  - `Args`: Explicit parameter types, default values, and semantic meaning.
  - `Returns`: Structure of the returned Python dictionary.
  - `Raises`: State `Raises: None - All exceptions are caught and returned in the dictionary.`

### 1.3 Strict Pydantic Type Schemas & `.model_dump()` Returns
- Input arguments must be constrained by Pydantic `BaseModel` schemas with clear `Field(..., description="...")` annotations.
- Function outputs must return Python dictionaries generated via `.model_dump()` from an explicit output `BaseModel`.

### 1.4 Guided Error Handling & Zero Unhandled Exceptions
- Tool functions MUST wrap execution in a `try...except` block and catch all exceptions.
- Never allow unhandled exceptions to crash the agent runtime.
- On error, return a dictionary with:
  - `"status": "ERROR"`
  - `"message"`: Human-readable error explanation.
  - `"recovery_hint"`: Clear instructions for the LLM on how to correct arguments and retry.

### 1.5 ToolContext Context Injection
- When a tool requires access to session state, event actions, or artifact services, add a parameter typed as `ToolContext` (`from google.adk.tools import ToolContext`).
- ADK automatically injects `ToolContext` at runtime by checking the type annotation.
- **Do not** document `ToolContext` in the docstring to avoid confusing the LLM.

---

## 2. Context, Session & Memory Best Practices

### 2.1 Multi-Turn Session Persistence (`VertexAiSessionService`)
- Short-term conversational turns must be managed via `google.adk.sessions.VertexAiSessionService` (or `InMemorySessionService` fallback) to persist state across invocations.

### 2.2 GEAP Memory Bank (`VertexAiMemoryBankService`)
- Store long-term cross-session knowledge using `google.adk.memory.VertexAiMemoryBankService` (`BaseMemoryService`).
- Equip agents with `PreloadMemoryTool` to automatically retrieve relevant memories at the beginning of each turn, or `LoadMemoryTool` for on-demand LLM retrieval.

### 2.3 Non-Blocking Async Background Callbacks
- Consolidate session events into long-term memory via after-agent callbacks (`from google.adk.agents.callback_context import CallbackContext`).
- Invoke `await callback_context.add_session_to_memory()` or `await callback_context.add_events_to_memory(events=...)` in background callbacks to avoid blocking UI or main execution threads.

### 2.4 Token-Based Sliding Window Context Compaction
- Implement token-based sliding window compaction (`compact_session_history(session_id, max_tokens)`) to prune or summarize older turns when approaching context window limits while preserving critical triage state.

---

## 3. Orchestration & Multi-Agent Logic

### 3.1 Coordinator-Worker DAG Pattern
- Structure complex workflows using a coordinator agent (`TriageCoordinator`) that delegates subtasks to domain-specific worker agents (`IngestionAgent`, `DedupeAgent`, `EnrichmentAgent`, `CodeRemediationAgent`).
- Ensure clear task boundaries and structured input/output schemas between agents.

### 3.2 Strategic Model Routing
- Use **`gemini-3.7-flash`** for high-throughput, low-latency classification, intake, vector similarity deduplication, and CODEOWNERS routing.
- Use **`gemini-3.1-pro`** for deep reasoning tasks such as multi-file stack trace analysis, unit test synthesis, and git diff patch generation.

### 3.3 Guardrail Policy Plugins
- Equip coordinator pipelines with self-evaluation guardrail plugins (`GuardrailPolicyPlugin`) that validate severity-to-priority SLA rules (e.g., auto-correcting Blocker severity to P0/P1 priority).

---

## 4. Observability, Distributed Tracing & Evaluation

### 4.1 Structured JSON Logging
- Emit structured logs compatible with Google Cloud Logging JSON format containing `timestamp`, `phase`, `request_id`, `agent_name`, and `tool_name`.

### 4.2 Intent vs. Outcome Phase Capture
- **INTENT Phase**: Log pre-invocation arguments before executing a tool or agent step.
- **OUTCOME Phase**: Log post-invocation results and execution duration (`duration_ms`) immediately upon step completion.

### 4.3 OpenTelemetry Distributed Tracing
- Wrap tool and agent execution steps in OpenTelemetry spans (`@tracer.start_as_current_span("AgentName:ToolName")`) with trace and span attributes (`request_id`, `agent.name`, `tool.name`).

### 4.4 Automated CI/CD Golden Dataset Evaluation
- Validate agent trajectory accuracy in CI/CD (`.github/workflows/eval.yml`) using an automated evaluation harness (`eval_harness.py`) against Golden Datasets (`golden_dataset.json`).

---

## 5. Enterprise Governance, Security & Agent CLI Operations

### 5.1 Zero Hardcoded Secrets
- Fetch secrets dynamically at runtime from Google Cloud Secret Manager (`google.cloud.secretmanager`) with environment variable fallbacks.

### 5.2 PII & Sensitive Data Redaction
- Scrub passwords, tokens, emails, and PII from raw bug reports using Google Cloud Sensitive Data Protection (`dlp_v2.DlpServiceClient`) with regex fallback before logging or storing data.

### 5.3 Human-in-the-Loop (HITL) A2UI Cards & HMAC Signoff
- Pause high-stakes actions in session state `'AWAITING_HUMAN_REVIEW'`.
- Render declarative A2UI review cards for Slack/Jira interactive signoff.
- Require HMAC-verified webhook signoff (`APPROVE`, `MODIFY`, `REJECT`) before resuming execution.

### 5.4 Agent CLI (`agentapi` & `adk` CLI) Operations
- Use standard `agentapi` commands (`new-conversation`, `get-conversation-metadata`, `send-message`) and `adk` CLI (`adk web`, `adk run`) for lifecycle control and testing.

---

## 6. Spec-Driven Engineering, Role-Based Execution, Zero-Trust Security & Circuit Breakers

### 6.1 BDD / EDD Inversion Workflow
- **Behavior-Driven Development (BDD)**: All technical specifications must be written in executable Gherkin syntax (`Scenario` / `Given` / `When` / `Then`) to eliminate ambiguity.
- **Evaluation-Driven Development (EDD)**: Before writing code or drafting new skills, define at least three (3) concrete JSON evaluation cases upfront (in `golden_dataset.json`).

### 6.2 Role-Based Execution Modes & Constraints
- **The Architect (Project Generation)**: Enforce explicit library and model version pinning; never run in YOLO mode without structure confirmation.
- **The Builder (Feature Generation)**: Match existing codebase style and naming conventions; perform surgical line edits; isolate variable renaming to separate, dedicated git commits.
- **The Forensic Specialist (Bug Fixing)**: Demand trace evidence and structured logs; write a reproducing, failing unit test before attempting code repairs; repair only the root cause.
- **The Author (Documentation Writing)**: Maintain concurrent code-doc synchronization (`README.md`, `CHANGELOG.md`, docstrings).

### 6.3 Tool Output Management & Memory ETL Lifecycle
- **External State Passing**: Never return large tables or datasets directly in tool outputs. Store payloads in external state or ADK Artifact Services and return only pointer/reference URIs to preserve token budgets.
- **Memory ETL Lifecycle**: Long-term memory must follow the full ETL pipeline:
  - **Ingestion & Extraction**: Parse dialogue for user-specific facts.
  - **Consolidation**: Merge new details, update existing records, or delete invalid/contradictory memories (active forgetting).
  - **Storage & Provenance**: Persist records with age and origin metadata via non-blocking async background callbacks.

### 6.4 LLM-as-a-Judge & Trajectory Evaluation
- **Outside-In Evaluation**: Evaluate both Black Box end-to-end task success and Glass Box trajectory adherence (`EXACT`, `IN_ORDER`, `ANY_ORDER` modes) using the $pass^k$ reliability metric.
- **Pairwise Comparison**: Neutralize ordering bias in qualitative evaluation by running prompt evaluations twice with swapped positions (Run 1: A vs B; Run 2: B vs A) and requiring structured JSON rubrics.

### 6.5 Zero-Trust Security, Hybrid Policy Gating & The Vibe Diff
- **Sandbox & Supply Chain Defense**: Run all dynamically generated code, forensic scripts, and tests strictly inside native **GEAP Agent Sandboxes** (`Code Execution` / `BuiltInCodeExecutor`). Protect against slopsquatting by enforcing vetted package allowlists, SBOM scanning, and version pinning.
- **Zero Ambient Authority**: Assign unique SPIFFE Agent Identities, enforce Just-In-Time (JIT) downscoping, and use deny-by-default file-tree allowlists.
- **Hybrid Policy Server**: Gate tool executions via Layer 1 Structural Gating (deterministic role/env checks) and Layer 2 Semantic Gating (secondary LLM PII/safety scan).
- **The Vibe Diff**: For high-stakes HITL review checkpoints, render a plain-English intent summary side-by-side with original user instructions so reviewers can assess operational impact without approval fatigue.

### 6.6 The Security Response Playbook (Circuit Breakers)
- On detecting intent drift or anomalous reasoning loop volume:
  1. **Trip the Circuit Breaker**: Instantly revoke the compromised agent's tool credentials.
  2. **Stateful Quarantine**: Pause container execution, freeze short-term memory intact for forensic debugging, and route session trace to review queue.
  3. **Rollback**: Automatically trigger a git rollback to the last known safe version control checkpoint.

---

## 7. Native GEAP Skill Registry & Agent Gateway Integration

### 7.1 GEAP Skill Registry
- Maintain cloud-ready skill definitions in `skills/<skill-name>/SKILL.md`.
- Register and synchronize all skills with Google Cloud GEAP Skill Registry via `scripts/sync_skills_to_geap.py` (`projects/{project}/locations/{location}/skills`).
- At runtime, query dynamic skill prompts and schemas via `app.skills.registry_client.SkillRegistryClient`.

### 7.2 Agent Gateway Ingress
- Define declarative ingress routing in `agent-gateway-ingress.yaml` (`access_type: CLIENT_TO_AGENT`, `protocol: A2A`).
- Deploy with Gateway binding:
  `agents-cli deploy --deployment-target agent_runtime --service-name adk-bugtriage-gw --agent-identity --agent-gateway-ingress projects/{PROJECT}/locations/{REGION}/agentGateways/{GATEWAY} --region {REGION} --no-confirm-project`.
- Verify Agent Card JSON via the reasoning engine's `.well-known/agent-card.json` endpoint.

