# AGENTS.md: GEAP & ADK Engineering Standards

> **System Directive**: Strictly use native **Google ADK 2.0+** (`google-adk>=2.0.0`) and **Gemini Enterprise Agent Platform (GEAP)** features. No custom boilerplate.

## 1. Models Directive
- **Routing/Fast Tier**: `gemini-3.7-flash` (intake, deduplication, triage, routing).
- **Reasoning/Planning Tier**: `gemini-3.1-pro-preview` (forensics, multi-file analysis, patch synthesis).
- **Prohibited**: `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-1.5-pro`, and legacy endpoints.

## 2. Tool Design & Engineering
- **Naming & Docstrings**: Action verbs (e.g. `query_similar_bugs_by_vector`). Google-style docstrings (`Args:`, `Returns:`, `Raises: None`).
- **Schemas**: Constrain inputs with Pydantic `BaseModel` (`Field(description=...)`). Outputs return `.model_dump()` with `{"status": "OK"|"ERROR", "recovery_hint": "..."}`.
- **Context & State**: Inject `ToolContext` for session/artifact access. Never return massive payloads directly; return artifact/storage reference URIs.

## 3. Scale, Sessions & Memory
- **Sessions**: Persist state with `VertexAiSessionService` (`InMemorySessionService` for tests); use token sliding window (`compact_session_history`).
- **Memory Bank**: Persist long-term facts using `VertexAiMemoryBankService` via async `after_agent_callback` (`await callback_context.add_session_to_memory()`).
- **Execution**: Run dynamic code/scripts strictly in ephemeral kernel-isolated sandboxes (gVisor).

## 4. Governance, Security & HITL
- **Zero-Trust**: SPIFFE Agent Identity, Agent Gateway proxying, and Model Armor prompt injection sanitization.
- **Human-in-the-Loop (HITL)**: High-stakes operations (PR creation, code patching, deployment) MUST pause in `"AWAITING_HUMAN_REVIEW"` and render declarative A2UI cards ("The Vibe Diff"). Resume only upon HMAC signoff.

## 5. Observability & Evaluation
- **Logging**: Structured JSON Google Cloud Logging capturing `INTENT` (pre-call) and `OUTCOME` (post-call with `duration_ms`).
- **Tracing & DLP**: Wrap executions in OpenTelemetry GenAI semantic spans (`@tracer.start_as_current_span`). Scrub PII/credentials via Cloud DLP.
- **Evaluation**: Spec/Evaluation-Driven Development (EDD) — write 3 JSON eval cases before code. Validate 100% pass on Golden Datasets via `agents-cli eval run`.

## 6. CLI & Workflow
- Use `agents-cli` for scaffolding (`scaffold`), testing (`playground`), evaluation (`eval run/optimize`), deployment (`deploy`), and registry publishing (`publish gemini-enterprise`).
