# Autonomous Enterprise Bug Triage & Auto-Remediation Agent

[![Framework](https://img.shields.io/badge/Google%20ADK-2.0-4285F4?style=for-the-badge&logo=google)](https://google.github.io/adk-docs/)
[![Models](https://img.shields.io/badge/Gemini-3.7%20Flash%20%7C%203.1%20Pro-8A2BE2?style=for-the-badge&logo=googleai)](https://ai.google.dev/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-Passing-00E676?style=for-the-badge&logo=githubactions)](.github/workflows/eval.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)

An enterprise-grade autonomous software engineering bug triage and remediation agent built on **Google Agent Development Kit (ADK 2.0)** and the **Gemini Enterprise Agent Platform (GEAP)**. It transforms raw, noisy crash reports into sanitized, deduplicated, single-hop routed, sandbox-verified pull requests with an interactive Human-in-the-Loop review gate.

---

## 1. Problem Framing & Scoped Boundaries

In high-velocity engineering organizations and shared microservice platforms, software maintenance is severely bottlenecked by four systemic failure modes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                SYSTEMIC TRIAGE FAILURE MODES                           │
├───────────────────────────────┬────────────────────────────────────────────────────────┤
│ 1. Inbound Noise & Fatigue    │ 40–60% of tickets during incidents are duplicates.     │
│ 2. Security & PII Leakage     │ Raw crash logs leak API keys, tokens, and user emails. │
│ 3. Routing Ping-Pong & SLA    │ Unclear ownership causes tickets to bounce for days.   │
│ 4. High Time-to-Reproduce     │ Developers spend 50%+ of fix time writing test repros. │
└───────────────────────────────┴────────────────────────────────────────────────────────┘
```

### What This Agent Solves (Core Capabilities)
- **Multi-Source Ingestion & PII Redaction**: Ingests raw alerts from Sentry, GitHub Issues, Jira, and Cloud Logging; scrubs secrets and user PII via Google Cloud Sensitive Data Protection (DLP API) with dual regex fallback.
- **Semantic Vector Deduplication**: Encodes error signatures into vector embeddings and clusters duplicates using cosine similarity ($\ge 0.85$ threshold) to link child issues to active parent tickets and suppress noise.
- **Dynamic Ownership Resolution & SLA Guardrails**: Matches failing stack frames against `.github/CODEOWNERS` and recent `git blame` history; enforces strict business SLA policies (`Blocker` $\rightarrow$ `P0`/`P1`).
- **Automated Sandbox Reproduction & Patch Synthesis**: Deep reasoning via `gemini-3.1-pro` to synthesize standalone `pytest` reproduction test cases and unified git diff patches, executing in an isolated sandbox subprocess to verify that the test fails before the patch and passes cleanly after.
- **Human-in-the-Loop (HITL) Gateway**: Enforces a strict pause in state `AWAITING_HUMAN_REVIEW` with declarative A2UI review cards, requiring HMAC-signed developer signoff before creating GitHub Draft Pull Requests.

### Engineering Safety Guardrails
- ❌ **No Unchecked Auto-Merging**: The agent *never* merges code into production directly; all actions are gated via Draft PRs and HMAC-signed review cards.
- ❌ **No Monolithic Prompts**: Tasks are decomposed into a DAG of specialized subagents, eliminating prompt hallucination and token waste.

---

## 2. Multi-Agent Architecture & Pipeline DAG

The system implements a **Coordinator-Worker DAG** pattern using Google ADK 2.0:

```
                               ┌────────────────────────────────────────────────┐
                               │   TriageCoordinator (gemini-3.7-flash)         │
                               │   - Orchestrates multi-agent execution DAG     │
                               │   - Enforces GuardrailPolicyPlugin SLA rules   │
                               │   - Manages persistent session state           │
                               └───────┬──────────────┬──────────────┬──────────┘
                                       │              │              │
                    ┌──────────────────┘              │              └──────────────────┐
                    ▼                                 ▼                                 ▼
       ┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
       │     IngestionAgent      │       │       DedupeAgent       │       │     EnrichmentAgent     │
       │   (gemini-3.7-flash)    │       │   (gemini-3.7-flash)    │       │   (gemini-3.7-flash)    │
       ├─────────────────────────┤       ├─────────────────────────┤       ├─────────────────────────┤
       │ • Scrub PII via DLP API │       │ • Generate embeddings   │       │ • Match .github/        │
       │ • Parse stack frames    │       │ • Cosine similarity     │       │   CODEOWNERS            │
       │ • Extract error type    │       │ • Link duplicate parent │       │ • Git blame lines       │
       └─────────────────────────┘       └─────────────────────────┘       │ • Calculate SLA (P0-P3) │
                                                                           └────────────┬────────────┘
                                                                                        │
                                                                                        ▼
                                                                           ┌─────────────────────────┐
                                                                           │  CodeRemediationAgent   │
                                                                           │    (gemini-3.1-pro)     │
                                                                           ├─────────────────────────┤
                                                                           │ • Deep stack reasoning  │
                                                                           │ • Synthesize repro test │
                                                                           │ • Generate diff patch   │
                                                                           │ • Verify in sandbox     │
                                                                           └────────────┬────────────┘
                                                                                        │
                                                                                        ▼
                                                                           ┌─────────────────────────┐
                                                                           │  HITL Gateway & A2UI    │
                                                                           ├─────────────────────────┤
                                                                           │ • Pause session state   │
                                                                           │ • Render review cards   │
                                                                           │ • Verify HMAC signoff   │
                                                                           │ • Open Draft GitHub PR  │
                                                                           └─────────────────────────┘
```

---

## 3. Dynamic Tooling & Capabilities

The agent equips modular, typed functional tools adhering to Google ADK 2.0 specifications:

| Tool Component | Description & Operational Behavior |
| :--- | :--- |
| **`sanitize_logs_and_extract_stack`** | Normalizes multi-language stack traces and scrubs bearer tokens, API keys, passwords, and emails using Cloud DLP API with regex fallback. |
| **`query_similar_bugs_by_vector`** | Computes vector cosine similarity against historical open issues. Suppresses duplicate notification spam when similarity exceeds $0.85$. |
| **`resolve_codeowners_and_blame`** | Parses `.github/CODEOWNERS` and `git blame` history from disk to route the ticket to the responsible engineering team on Attempt #1. |
| **`execute_reproduction_and_sandbox_fix`** | Invokes `gemini-3.1-pro` to synthesize a self-contained `pytest` test and unified diff patch; executes in an isolated sandbox verifying clean application. |
| **`render_a2ui_review_card`** | Generates declarative A2UI review cards displaying the diff patch, reproduction code, and one-click action buttons (`APPROVE`, `MODIFY`, `REJECT`). |
| **`create_draft_pull_request`** | Pushes a verified branch and opens a Draft Pull Request on GitHub using the GEAP Managed Agent Identity. |

---

## 4. Developer Experience & Workflow Integration

The agent integrates into engineering workflows across three interaction surfaces:

### 4.1 Automated Webhook & ChatOps Workflow (Slack / Jira / GitHub)
```
  [Production Alert] ──► [Agent DAG] ──► [A2UI Review Card in Slack] ──► [Developer Clicks "APPROVE"] ──► [GitHub Draft PR]
```
1. An incoming crash webhook triggers `/webhook/alert-intake`.
2. The agent sanitizes logs, checks duplicates, routes ownership, and verifies a fix in the sandbox.
3. The session pauses in `AWAITING_HUMAN_REVIEW` and posts an interactive A2UI card into Slack/Jira.
4. The engineer reviews "The Vibe Diff" and clicks **APPROVE**.
5. The Cloud Run webhook listener ([`app/hitl/webhook_listener.py`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/app/hitl/webhook_listener.py)) validates the HMAC signature and opens a GitHub Draft PR.

### 4.2 Interactive Developer CLI (`agentapi` & Google `adk` CLI)
Developers can inspect triage state, resume paused sessions, or chat directly with the agent from their terminal:

```bash
# Start an interactive triage session with Gemini 3.7 Flash
agentapi new-conversation --model=flash --title="Checkout Crash" "Triage NPE in payment_checkout.py"

# Inspect conversation metadata and check paused HITL state
agentapi get-conversation-metadata <conversation-id>

# Resume a paused session with developer approval
agentapi send-message --title="HITL Approval" "<conversation-id>" "APPROVE: Patch verified locally."

# Run local ADK Web Server UI on port 8080
adk web --port=8080

# Execute interactive CLI chat against the TriageCoordinator
adk run app.agents.coordinator:root_agent
```

### 4.3 Visual Test Console (`/ui`)
Start the FastAPI server and open [http://localhost:8080/ui](http://localhost:8080/ui) to select sample alerts, watch the live multi-agent execution trajectory, and inspect generated A2UI cards in real time.

---

## 5. Live Grounded Verification against Target Codebase (`target_repo/`)

The repository includes an active target service workspace ([`target_repo/`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/target_repo)) with realistic microservices, CODEOWNERS rules, and unit test suites:
- [`target_repo/services/payment_gateway.py`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/target_repo/services/payment_gateway.py) $\rightarrow$ Handled by `@payments-team` (from [`target_repo/.github/CODEOWNERS`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/target_repo/.github/CODEOWNERS))
- [`target_repo/services/auth_service.py`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/target_repo/services/auth_service.py) $\rightarrow$ Handled by `@security-team`

---

## 6. Verification & Quickstart

### 6.1 Run Automated Pytest Suite
```bash
pytest tests/unit/ tests/eval/ -v
```

### 6.2 Run Automated Golden Dataset Evaluation Harness
```bash
python3 tests/eval/run_eval.py
```
*Validates 100% trajectory accuracy across PII scrubbing, vector deduplication, CODEOWNERS routing, sandbox status, and HITL card generation.*

### 6.3 Run Interactive Real Triage CLI Demo
```bash
python3 scripts/interactive_real_triage.py
```

### 6.4 Launch Local ADK Web Server UI
```bash
adk web --port 8085 app
```
Navigate to [http://127.0.0.1:8085/dev-ui/?app=app](http://127.0.0.1:8085/dev-ui/?app=app).

---

## 7. Infrastructure as Code (Terraform Deployment)

Declarative GCP infrastructure is defined in [`main.tf`](file:///Users/nrcheruku/sourcecode/work/bugtriage-agent/main.tf):
- **Cloud Run v2 Service** (`bug-triage-agent-service`) with auto-scaling container runtime.
- **GEAP Agent Identity Service Account** (`bug-triage-agent-sa`) with least-privilege IAM bindings (`roles/aiplatform.user`, `roles/secretmanager.secretAccessor`, `roles/dlp.user`).
- **Google Cloud Secret Manager** (`github-api-token`, `slack-hmac-signing-key`) injected securely at runtime with zero hardcoded keys.

```bash
# Validate Terraform configuration
terraform init -backend=false
terraform validate
```

---

## 8. System Capabilities & Architecture Overview

| Pillar | Architectural Focus | Implementation Details |
| :--- | :--- | :--- |
| **Tool & Interface Design** | Strict Schemas & Guided Recovery | Comprehensive Google-style docstrings, action-verb naming, Pydantic `BaseModel` input/output validation, and `.model_dump()` returns with `"recovery_hint"`. |
| **Context & Memory** | Multi-Turn Persistence & Compaction | Per-agent constitutions, token sliding-window context compaction (`compact_session_history`), `VertexAiSessionService`, and async callbacks to GEAP Memory Bank. |
| **Orchestration & Logic** | Deterministic DAG Routing & Guardrails | Google ADK 2.0 multi-agent coordinator routing `gemini-3.7-flash` (Global) & `gemini-3.1-pro-preview` (Global), SLA policy plugins, and declarative A2UI review cards. |
| **Observability & Tracing** | Enterprise Tracing & PII Defense | Google Cloud Logging structured JSON format, `INTENT`/`OUTCOME` phase logs with timers, OpenTelemetry spans, and Cloud DLP PII redaction. |
| **CI/CD & Infrastructure** | Declarative IaC & Secret Governance | Automated Golden Dataset evaluation harness, declarative Terraform (`main.tf`), and Secret Manager runtime injection. |

---

## 9. License

Apache License 2.0. See [LICENSE](LICENSE) for details.
