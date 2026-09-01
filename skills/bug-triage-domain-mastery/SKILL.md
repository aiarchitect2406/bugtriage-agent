---
name: bug-triage-domain-mastery
description: Comprehensive enterprise software engineering bug triage domain mastery guide covering real-world triage pain points, SLA matrices, vector duplicate clustering, git blame/CODEOWNERS routing, sandbox reproduction testing, and dual-model review gates.
---

# Skill: Software Engineering Bug Triage Domain Mastery

## 1. The Real-World Enterprise Bug Triage Challenge

In a typical enterprise engineering organization, bug triage is one of the most expensive and error-prone bottlenecks in the software development lifecycle. Real-world engineering teams face five critical failure modes:

| Enterprise Pain Point | Real-World Impact | Traditional Manual Process | Autonomous Agent Solution |
| :--- | :--- | :--- | :--- |
| **1. Inbound Noise & Incomplete Reports** | High engineering time wasted deciphering poorly formatted reports, missing stack traces, or customer PII leaks in tickets. | L1 support or triage managers spend 15–30 minutes manually asking reporters for logs or scrubbing passwords/tokens. | **`IngestionAgent`**: Automatically parses raw alert payloads, normalizes stack traces, and scrubs PII/secrets via Google Cloud DLP / regex fallback before saving to the database. |
| **2. Duplicate Ticket Flood (40–60% Duplicates)** | During outages or regressions, dozens of duplicate Jira/GitHub tickets are created by different users and alerts, splitting developer context. | Engineers manually search ticket titles or keywords; duplicates are often missed until multiple engineers work on the same root cause. | **`DedupeAgent`**: Computes semantic vector embeddings and performs cosine similarity matching ($\ge 0.85$ threshold) against historical and active issues to link duplicates to a master ticket. |
| **3. Severity Inflation & SLA Misalignment** | Reporters tag trivial bugs as "P0/Blocker" to get attention, causing alert fatigue, while real silent regressions sit in "P2/P3" backlogs. | Triage leads argue over subjective priority ratings during weekly triage meetings. | **`EnrichmentAgent` & Guardrail Policy Plugin**: Maps objective business impact to a strict Priority SLA Matrix. Self-eval guardrail policies auto-correct subjective severity-to-priority mismatches. |
| **4. Team Ping-Pong Routing** | Complex microservice stack traces are assigned to the wrong team ("Is this frontend, API gateway, auth, or DB?"). Tickets bounce 3–4 times over days. | Managers route based on guessing or outdated component labels. | **`RoutingAgent`**: Matches exact stack frame file paths against `.github/CODEOWNERS` and recent `git blame` commit authors to assign the ticket directly to the responsible team on Attempt #1. |
| **5. High Time-to-Reproduce (TTR)** | Developers spend 50%+ of their fix time just trying to write a failing test or reproduce the error locally. | Engineer must read logs, set up a local environment, and manually craft a reproduction script. | **`CodeRemediationAgent` (`gemini-3.1-pro`)**: Synthesizes a standalone, self-contained pytest reproduction unit test and unified diff patch, running them in an isolated container sandbox to verify the fix. |

---

## 2. Enterprise SLA Matrix & Severity vs. Priority Protocol

An enterprise bug triage system must separate **Severity** (objective technical impact) from **Priority** (business SLA timeline).

```
Severity (Technical Impact)   ──┐
                                ├──► Guardrail Policy Validation ──► Priority SLA Assigned
Business Impact / Blast Radius──┘
```

### SLA Matrix Table

| Priority Level | Target Severity | Target Response Time (Ack) | Target Resolution Time (SLA) | Escalation Rule |
| :---: | :--- | :--- | :--- | :--- |
| **P0 - Critical** | **Blocker** (Production outage, data loss, security breach, core user journey broken) | **15 minutes** (24/7 On-Call) | **2 hours** | Automated PagerDuty escalation to engineering directors if unacknowledged within 15m. |
| **P1 - High** | **Major** (Major feature degraded, no workaround, high customer blast radius) | **1 hour** | **24 hours** | Notify engineering manager and primary code owner via Slack/Google Chat. |
| **P2 - Medium** | **Minor** (Non-blocking bug, reasonable workaround exists, moderate blast radius) | **24 hours** | **5 business days** | Standard backlog triage assignment. |
| **P3 - Low** | **Trivial** (Cosmetic UI glitch, typo, minor edge case with low occurrence) | **5 business days** | **Next release cycle** | Candidate for automated good-first-issue marking or backlog grooming. |

### SLA Guardrail Rule
- **Rule**: If `severity == "Blocker"`, `priority` **MUST** be `P0` or `P1`.
- **Enforcement**: If a report arrives with `severity == "Blocker"` and `priority == "P2"`, the `GuardrailPolicyPlugin` automatically corrects `priority` to `P0` and flags an SLA audit log entry.

---

## 3. Vector Duplicate Detection Protocol (`DedupeAgent`)

To prevent duplicate effort during outages:
1. **Embedding Generation**: Convert the sanitized report summary, stack trace signature, and error message into a semantic vector embedding using `gemini-3.6-flash` / text-embeddings.
2. **Cosine Similarity Lookup**: Query the vector database for open tickets with similarity score $S(v_{new}, v_{historical})$.
3. **Threshold Classification**:
   - **$S \ge 0.85$ (Definite Duplicate)**: Link new issue as a child duplicate of `matching_parent_issue_id`, suppress notification spam, and return early with `status = "DUPLICATE_LINKED"`.
   - **$0.70 \le S < 0.85$ (Related Incident)**: Tag ticket as "Related to #ID" in enrichment metadata for reviewer context, but continue full triage.
   - **$S < 0.70$ (Unique Bug)**: Proceed to enrichment and routing.

---

## 4. Code Ownership & Git Blame Attribution Protocol (`RoutingAgent`)

To achieve single-hop assignment accuracy:
1. **Top-of-Stack Frame Extraction**: Identify the first non-library, application-specific file path and line number in the exception stack trace (e.g., `app/services/checkout.py:142`).
2. **`CODEOWNERS` Lookup**: Match the file path against `.github/CODEOWNERS` glob patterns to identify the responsible team alias (e.g., `@engineering/checkout-team`).
3. **`git blame` Author Weighting**: Query git commit history on the affected lines within the last 90 days.
4. **Owner Assignment**: Assign `primary_owner` to the active team or engineer with the highest blame weighting, falling back to `@oncall-sre` if ownership is ambiguous.

---

## 5. Sandbox Reproduction & Remediation Protocol (`CodeRemediationAgent`)

Unlike basic triage systems that stop at assigning tickets, an autonomous enterprise agent accelerates resolution by generating verified code:
1. **Reproduction Unit Test Generation (`pytest`)**:
   - Synthesize a standalone unit test (`test_reproduce_<issue_id>.py`) that exercises the failing code path and asserts that the bug reproduces (fails prior to patching).
2. **Root Cause Patch Synthesis**:
   - Synthesize a unified diff patch (`--- a/... +++ b/...`) targeting the offending source file.
3. **Container Sandbox Verification**:
   - Run the reproduction test in an isolated sandbox before the patch (asserting test failure / bug confirmation).
   - Apply the unified diff patch cleanly.
   - Re-run the test suite in the sandbox (asserting `post_patch_test_passed == True`).

---

## 6. Autonomous Dual-Model Consensus Verification Protocol

Enterprise security policy mandates that autonomous remediation is gated strictly by independent cross-vendor dual-model consensus:
1. **Maker Synthesis**: Gemini 3.1 Pro Preview analyzes the root cause, extracts stack frames, and synthesizes an isolated reproduction test alongside a defensive unified diff patch.
2. **Ephemeral Sandbox Pass**: The patch is applied and validated inside an isolated pytest sandbox (confirming failure on unpatched code and 100% pass on patched code).
3. **Checker Verification**: Claude Sonnet 4.6 on Vertex AI audits the patch for CWE-476, CWE-89, type safety, logic regressions, and prompt injection defense.
4. **Automated PR Publishing**: Upon achieving an approval score >= 90/100, the agent automatically commits the patch to a dedicated branch and opens a Pull Request on GitHub with full audit metadata.

---

## 7. ADK 2.0 & GEAP Tool & Interface Design Best Practices

To ensure reliable LLM reasoning and enterprise-grade robustness, all tools MUST adhere to:
1. **Action-Verb Function Naming**: Function names must begin with descriptive action verbs (`query_similar_bugs_by_vector`, `create_draft_pull_request`, `resolve_codeowners_and_blame`). Avoid generic noun-only or helper naming.
2. **Comprehensive Google-Style Docstrings**: Every tool function MUST define complete Google-style docstrings clearly specifying:
   - `Args`: Parameter types and semantic meanings.
   - `Returns`: Typed dictionary structure and keys.
   - `Raises`: Explicitly state `Raises: None - All exceptions are caught and returned in the dictionary.`
3. **Pydantic Type Schemas & Guided Error Handling**:
   - Constrain all inputs with strict Pydantic `BaseModel` schemas.
   - Return structured Python dictionaries generated via `.model_dump()` containing:
     - `status`: Overall execution state (`"SUCCESS"` or `"ERROR"`).
     - `message`: Descriptive human-readable explanation.
     - `recovery_hint`: Guided self-correction instructions for the LLM when an error occurs.
   - **Zero Unhandled Exceptions**: Catch all runtime exceptions inside the tool function; never let unhandled exceptions propagate to the LLM.
4. **ToolContext Context Injection**:
   - Use `tool_context: ToolContext` (from `google.adk.tools import ToolContext`) when a tool requires access to session state (`tool_context.state`), event actions (`tool_context.actions`), or artifact services (`tool_context.load_artifact`, `save_artifact`, `search_memory`).
   - Do not mention `tool_context` in the docstring, as ADK injects it automatically and mentioning it can confuse the LLM.

---

## 8. ADK 2.0 Session, Memory & Context Compaction Mastery

1. **Short-Term Session Persistence**:
   - Use native `VertexAiSessionService` (with `InMemorySessionService` fallback) to persist multi-turn short-term conversational state across agent invocations.
2. **GEAP Long-Term Memory Bank**:
   - Integrate `VertexAiMemoryBankService` (`BaseMemoryService`) to store and retrieve cross-session long-term memories.
   - Use `PreloadMemoryTool` to automatically retrieve memories at the beginning of each turn, or `LoadMemoryTool` to let the LLM retrieve memories on-demand.
3. **Non-Blocking Async Memory Consolidation Callbacks**:
   - Consolidate session events into long-term memory via after-agent callbacks (`from google.adk.agents.callback_context import CallbackContext`).
   - Invoke `await callback_context.add_session_to_memory()` or `await callback_context.add_events_to_memory(events=...)` in background callbacks to avoid blocking UI or main execution threads.
4. **Token-Based Sliding Window Context Compaction**:
   - Implement `compact_session_history(session_id, max_tokens)` to summarize or prune older conversational turns when approaching context limits while preserving critical triage state.

---

## 9. Observability, Distributed Tracing & Automated Eval Suites

1. **Structured JSON Logging**:
   - All logs must be formatted as JSON objects compatible with Google Cloud Logging containing `timestamp`, `phase`, `request_id`, `agent_name`, and `tool_name`.
2. **Intent vs. Outcome Phase Tracing**:
   - **INTENT Phase**: Log pre-invocation tool arguments before execution.
   - **OUTCOME Phase**: Log post-invocation results and execution duration (`duration_ms`) after execution.
3. **OpenTelemetry Distributed Spans**:
   - Wrap agent and tool executions in OpenTelemetry spans (`@tracer.start_as_current_span("AgentName:ToolName")`) to correlate multi-agent hops and execution latency.
4. **Automated CI/CD Golden Dataset Evaluation**:
   - Validate agent trajectory correctness automatically in CI/CD (`.github/workflows/eval.yml`) using `eval_harness.py` against Golden Datasets (`golden_dataset.json`).
   - Verify 100% compliance across PII redaction, vector duplicate detection, CODEOWNERS routing, sandbox pytest execution, and dual-model review consensus.

---

## 10. Enterprise Governance, Security & Agent CLI Operations

1. **Zero Hardcoded Secrets**:
   - Fetch secrets dynamically at runtime from Google Cloud Secret Manager (`app/config.py`) with environment variable fallbacks. Never hardcode API keys or credentials.
2. **PII & Sensitive Data Protection**:
   - Scrub passwords, API tokens, email addresses, and PII from raw bug reports using Google Cloud Sensitive Data Protection (`dlp_v2.DlpServiceClient`) with regex fallback (`EnterprisePIIRedactor`) before logging or storage.
3. **Consensus Gated Security**:
   - High-stakes actions require Maker-Checker consensus (Gemini 3.1 Pro synthesis + Claude Sonnet 4.6 security audit >= 90/100) before pull request creation.
4. **Agent CLI (`agentapi` & `adk` CLI) Operations**:
   - Use `agentapi new-conversation --model=flash`, `agentapi get-conversation-metadata <id>`, and `agentapi send-message <id>` to inspect and control conversations programmatically.
   - Execute local ADK runtimes using `adk web` (web UI server) or `adk run` (terminal runner).
