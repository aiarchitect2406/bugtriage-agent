# AGENTS.md: Production-Grade Agentic Engineering & Governance Specification

> **System Directive for Coding Agents**: This document defines the absolute engineering, security, context, observability, and quality standards for all development, refactoring, and integration within this repository. As a Coding Agent (e.g., Antigravity, Claude Code, Gemini CLI), you must strictly parse, adhere to, and execute the policies laid out below. Every change is evaluated against the 95-point AgentOps Code Review Matrix and strictly grounded in the **Gemini Enterprise Agent Platform (GEAP)**.

---

# Gemini Enterprise Agent Platform (GEAP) Core Directives

The **Gemini Enterprise Agent Platform (GEAP)** is the unified, authoritative platform for the entire agent lifecycle. All agent architectures, infrastructure components, runtime services, security guardrails, and observability tools must strictly leverage GEAP components across the four foundational pillars: **Build**, **Scale**, **Govern**, and **Optimize**.

```
+---------------------------------------------------------------------------------------------------+
|                            GEMINI ENTERPRISE AGENT PLATFORM (GEAP)                                |
+---------------------------------+---------------------------------+-------------------------------+
|             BUILD               |              SCALE              |            GOVERN             |
| - Google ADK 2.0+               | - GEAP Agent Runtime            | - GEAP Agent Registry         |
| - Agent Studio & Agent Garden   | - Agent Platform Sessions       | - Agent Identity & Auth Mgr   |
| - Model Garden (Gemini 3.7/3.1) | - Agent Platform Memory Bank    | - Agent Gateway & Model Armor |
| - RAG Engine & Vector Search    | - Code Execution Sandbox        | - Governance Policies (Content|
| - Managed Agents API            | - Dynamic Graph Workflows       |   Protection & Semantic Gov)  |
| - Colab Enterprise Notebooks    |                                 | - AI Threat & Vuln Scanning   |
|                                 |                                 | - AI Content Detection API    |
|                                 |                                 | - HITL A2UI Review Gates      |
+---------------------------------+---------------------------------+-------------------------------+
|                                    OPTIMIZE & OBSERVABILITY                                       |
| - GEAP Agent Observability (Overview, Models, Tools, Usage, Logs, Unified Trace Viewer, Topology)  |
| - OpenTelemetry GenAI Semantic Conventions & Cloud Trace Spans                                    |
| - Structured Cloud Logging (INTENT / OUTCOME Phase Tracking & Latency Profiling)                 |
| - Sensitive Data Protection (Google Cloud DLP API PII & Credential Masking)                       |
| - GenAI Evaluation Service (Offline Golden Eval, Multi-Turn AutoRaters, Continuous Online Monitors)|
| - Simulate & Evaluate Agent Behavior (Synthetic Scenario Generation & User Simulation)          |
| - Optimize Agent Prompts (Automated Prompt Refinement & Quality Flywheel)                         |
+---------------------------------------------------------------------------------------------------+
```

## 1. GEAP Component Standards Across Lifecycle Pillars

### Pillar 1: Build
- **Framework Standard (Google ADK 2.0+)**: All agent code must target **Google ADK v2.0+** (`google-adk>=2.0.0`). Build modular, model-agnostic agents using `Agent`, `WorkflowAgent`, typed functional tools, and native callbacks. Do not use deprecated ADK 1.x APIs.
- **Visual Canvas & Templates (Agent Studio & Agent Garden)**: Utilize Agent Studio for visual canvas prototyping and reasoning loop design; leverage Agent Garden for vetted prebuilt agent patterns.
- **Model Garden & Strategic Model Routing**: Ground agent reasoning strictly in frontier models via Model Garden:
  - `gemini-3.7-flash`: High-throughput, low-latency intake, bug classification, vector deduplication, and routing.
  - `gemini-3.1-pro-preview`: Deep multi-step reasoning, root-cause forensic analysis, unit test synthesis, and patch generation.
  - *Deprecated Models Prohibited*: Never use `gemini-2.0-flash`, `gemini-2.5-flash`, or older legacy endpoints.
- **Enterprise Data Grounding (RAG Engine & Vector Search)**: Ground agent context against enterprise documentation, code repositories, and historical issue trackers using GEAP RAG Engine and Vector Search.
- **Managed Agents API on Agent Platform**: Support config-driven, REST-first agent execution using the **Agents API** (to manage configurations, sandboxes, skills, and artifacts) and the runtime **Interactions API** within managed cloud sandboxes.
- **Colab Enterprise Notebooks**: Support code-based model exploration, data analysis, and experimentation.

### Pillar 2: Scale & Deploy
- **Scale Agents with Agent Runtime**: Deploy agents to GEAP Agent Runtime for managed, high-concurrency execution with sub-second cold starts, long-running agent workloads, and stateful runtime isolation.
- **Agent Platform Sessions (`VertexAiSessionService`)**: Persist short-term conversational turns, intermediate tool states, and shared scratchpads across invocations with native session management.
- **Agent Platform Memory Bank (`VertexAiMemoryBankService`)**: Store and recall long-term cross-session knowledge and agent heuristics via GEAP Memory Bank using non-blocking async background callbacks (`add_session_to_memory`).
- **Code Execution Sandbox**: Execute untrusted, dynamically synthesized code and automated test scripts exclusively in ephemeral, kernel-isolated execution sandboxes (gVisor).

### Pillar 3: Govern & Secure
- **Agent Registry**: Central enterprise catalog for discovering, tracking, versioning, and managing all approved enterprise agents, tools, and Model Context Protocol (MCP) servers across the organization.
- **Agent Identity & Auth Manager**: Issue unique, cryptographically verifiable Agent Identities (SPIFFE standard) with Context-Aware Access (mTLS and DPoP) and Just-In-Time (JIT) credential downscoping.
- **Agent Gateway**: Central policy enforcement point and network proxy governing all connectivity (user-to-agent, agent-to-tool, agent-to-agent) with protocol mediation for MCP, A2A, REST, and gRPC.
- **Governance Policies & Model Armor**: Enforce Content Protection, Semantic Governance, and real-time Model Armor sanitization to block MCP prompt injection, jailbreaks, data leakage, and unauthorized tool invocation.
- **AI Threat and Vulnerability Scanning**: Continuous real-time threat detection and vulnerability scanning specific to agentic systems.
- **AI Content Detection API**: Support responsible media governance by detecting and verifying AI-generated artifacts.
- **Human-in-the-Loop (HITL) Review Gates**: High-stakes operations (e.g., Pull Request creation, automated code patching, production deployment) MUST pause execution in `"AWAITING_HUMAN_REVIEW"` and render declarative A2UI review cards.

### Pillar 4: Optimize & Observability
- **GEAP Agent Observability**: Unified fleet observability providing dedicated dashboards for Overview metrics, Foundation Models, Tool latency/error rates, Infrastructure Usage, Logs, Unified Trace Viewer, and Multi-Agent Topology Graphs.
- **OpenTelemetry GenAI Semantic Conventions**: Standardize all execution spans with official GenAI semantic attributes (`gen_ai.agent.name`, `gen_ai.conversation.id`, `gen_ai.tool.definitions`, inference events) exported to Cloud Trace.
- **Structured Google Cloud Logging**: Emit structured JSON logs capturing pre-execution `INTENT` and post-execution `OUTCOME` phases with execution duration (`duration_ms`).
- **Sensitive Data Protection (Cloud DLP)**: Scrub PII, API tokens, passwords, and private keys dynamically before logging or storing session payloads.
- **Agent Evaluation & Continuous Online Monitors**: Systematically assess agent quality using offline Golden Dataset evaluations (`run_eval.py` / `agents-cli eval`), Multi-Turn AutoRaters, and live traffic Online Monitors.
- **Simulate and Evaluate Agent Behavior**: Generate synthetic test scenarios and simulate multi-turn user interactions with configurable personas to stress-test agent logic.
- **Optimize Agent Prompts**: Programmatically refine agent system instructions and tool descriptions by analyzing failure patterns, clustering loss modes, and auto-tuning prompts (`agents-cli eval optimize`).

---

## 2. Development Workflow & Tooling Standard

1. **Scaffold:** Use `agents-cli scaffold` or the `google-agents-cli-scaffold` skill when setting up new agents.
2. **Code Patterns:** Follow ADK architecture patterns (typed functional tools, `Agent`, `WorkflowAgent`, session management) via `google-agents-cli-adk-code`.
3. **Quality & Eval:** Validate workflows with `google-agents-cli-eval` and `run_eval.py` before deployment.
4. **Deploy to Runtime:** Deploy to GEAP Agent Runtime via `agents-cli deploy`.
5. **Publish to Registry:** Register deployed agents and tools with `agents-cli publish gemini-enterprise`.

---

## Production Architectural Standards & Implementation Matrix (95 / 95 Points Target)

| GEAP Pillar & Area | Rubric Standard | Technical Implementation Standard |
| :--- | :--- | :--- |
| **1. Build: Tool & Interface Design** | **Comprehensive Tool Docstrings** | Google-style docstrings with explicit `Args`, `Returns`, and `Raises: None`. |
| | **Descriptive Naming** | Action-verb function names (`query_similar_bugs_by_vector`, `create_draft_pull_request`). |
| | **Explicit JSON Schemas** | Pydantic `BaseModel` input and output schemas constraining all arguments. |
| | **Guided Error Handling** | All tools return `.model_dump()` dictionaries with `"status": "ERROR"` and `"recovery_hint"`. |
| **2. Scale: Context, Sessions & Memory** | **Persistent Session State** | GEAP Agent Platform Sessions (`VertexAiSessionService`) for multi-turn state persistence across turns. |
| | **History Compaction** | Token-based sliding window compaction (`compact_session_history`) and recursive summarization. |
| | **Cross-Session Memory Bank** | GEAP Memory Bank (`VertexAiMemoryBankService`) with background async callbacks (`add_session_to_memory`). |
| | **Sandboxed Code Execution** | Ephemeral kernel-level isolated sandboxes (gVisor) for executing dynamic code safely. |
| **3. Build: Orchestration & Logic** | **Multi-Agent Coordination** | Coordinator-Worker DAG pattern implemented via Google ADK 2.0 `Agent` / `WorkflowAgent`. |
| | **Strategic Model Routing** | Model Garden routing: `gemini-3.7-flash` for high-throughput intake; `gemini-3.1-pro-preview` for deep planning. |
| | **Data Grounding** | GEAP RAG Engine & Vector Search for enterprise codebase and bug history grounding. |
| | **Guardrails & Policy Plugins** | Self-evaluation `GuardrailPolicyPlugin` validating SLA severity-to-priority rules. |
| **4. Govern: Security & HITL** | **Central Catalog** | GEAP Agent Registry for fleet discovery of agents, tools, and MCP servers. |
| | **Agent Identity & Auth** | SPIFFE Agent Identities, Context-Aware Access (mTLS/DPoP), and JIT least-privilege downscoping. |
| | **Agent Gateway & Model Armor** | Traffic proxying, MCP/A2A protocol mediation, and prompt injection defense via Model Armor. |
| | **Human-in-the-Loop Review** | Explicit code stops at `"AWAITING_HUMAN_REVIEW"` with declarative A2UI review cards and HMAC signoff. |
| **5. Monitor & Observability** | **Agent Observability Dashboards** | GEAP Observability dashboards for fleet health, model/tool latency, and system topology graphs. |
| | **Structured JSON Logging** | Google Cloud Logging structured JSON format with `INTENT` and `OUTCOME` phase capture. |
| | **Distributed OpenTelemetry Tracing** | OpenTelemetry GenAI Semantic Conventions (`@tracer.start_as_current_span`) across agent hops. |
| | **PII Redaction** | Active scrubbing of credentials and PII via Google Cloud Sensitive Data Protection (DLP API). |
| **6. Optimize & CI/CD** | **Automated Evaluation Suites** | GenAI Evaluation Service (`run_eval.py` / `agents-cli eval`) asserting 100% accuracy on Golden Datasets. |
| | **Infrastructure as Code** | Declarative Terraform (`main.tf`) provisioning GEAP services with full IAM bindings. |
| | **Secure Secret Management** | Google Cloud Secret Manager runtime injection with zero hardcoded API keys. |

---

## Section 1: Spec-Driven Development (SDD) & Behavior-Driven Engineering

### 1.1 The Inversion Workflow (BDD & EDD)
Traditional "code-first" development is prohibited in this repository. All changes must follow a spec-first methodology:
1. **Behavior-Driven Development (BDD)**: Technical designs must be formulated as executable Gherkin specifications (`Scenario` / `Given` / `When` / `Then`) to structure natural-language intent into deterministic states, actions, and outcomes.
2. **Evaluation-Driven Development (EDD)**: Before writing implementation code or drafting a skill (`SKILL.md`), you must write three (3) concrete JSON evaluation cases representing the functional spec upfront for the GEAP GenAI Evaluation Service:
   ```json
   {
     "case_id": "eval_case_001",
     "input": "User reports crash with invalid session token",
     "expected_agent": "IngestionAgent",
     "expected_tool_calls": [
       {"tool": "sanitize_logs_and_extract_stack", "args": {"issue_id": "ISSUE-001"}}
     ],
     "expected_output_format": "sanitized_report",
     "rubric": ["redacts auth tokens", "extracts clean stack trace"]
   }
   ```

### 1.2 Role-Based Execution Modes & Constraints
Transition to the appropriate role-based execution pattern based on task context:
1. **Project Generation (The Architect)**: Propose folder structure and dependency pinning before writing code; enforce explicit version pinning; no unverified generation.
2. **Feature Generation (The Builder)**: Match existing style; execute surgical line changes; isolate variable renaming to separate, dedicated commits.
3. **Bug Fixing (The Forensic Specialist)**: Reject symptom prompting; analyze logs and trace evidence; write a reproducing failing unit test before attempting a fix; isolate root-cause repairs.
4. **Documentation Writing (The Author)**: Maintain concurrent code-doc synchronization (`README.md`, docstrings); use Google-style docstrings for Python.

---

## Section 2: Robust Tool Design & Engineering (Google ADK 2.0+)

### 2.1 Tool Documentation & Schemas
1. **Action-Verb Naming**: Tool functions must begin with descriptive action verbs indicating what operation they perform (e.g., `query_similar_bugs_by_vector`, `create_draft_pull_request`, `resolve_codeowners_and_blame`).
2. **Comprehensive Google-Style Docstrings**: Clearly document `Args:`, `Returns:`, and `Raises: None - All exceptions are caught and returned in the dictionary`.
3. **Publish Tasks, Not API Wrappers**: Encapsulate high-level human-centric tasks rather than thin API calls.
4. **Enforce Single Responsibility**: Keep tools granular and limited to a single function.

### 2.2 Input & Output Schemas & External State Passing
1. **Strict Pydantic Type Schemas**: Input arguments must be constrained by Pydantic `BaseModel` schemas with `Field(..., description="...")` annotations. Function outputs must return dictionaries generated via `.model_dump()`.
2. **External State Passing**: Never return large tables or massive payloads directly in tool outputs. Store payloads in external state or ADK Artifact Services and return only pointer/reference URIs to preserve token budgets.
3. **ToolContext Injection**: When a tool requires session metadata or artifact handles, accept `ToolContext` (`from google.adk.tools import ToolContext`). ADK injects this context automatically at runtime.

### 2.3 Guided Error Handling & Recovery Hints
- Tool functions MUST catch all internal exceptions and return a structured dictionary containing `"status": "ERROR"`, human-readable `"message"`, and a `"recovery_hint"` guiding the LLM on how to self-correct.

---

## Section 3: Context Engineering, Sessions & Memory (GEAP Scale Pillar)

### 3.1 Context Window Budget & Progressive Disclosure
- Treat context as a finite resource. Do not pre-load all tool definitions and system instructions into the prompt at startup. Dynamically index and load specific tool schemas and skill instructions only when their activation cues are triggered.

### 3.2 Multi-Turn Session Persistence (`VertexAiSessionService`)
- Maintain active conversational turns and intermediate tool states using native GEAP Agent Platform Sessions (`google.adk.sessions.VertexAiSessionService`, with `InMemorySessionService` fallback for testing).
- Use a structured `{key: value}` session state (`session.state`) as a temporary scratchpad to share data across subagents and tools.

### 3.3 Token-Based Sliding Window Context Compaction
- Implement token-based sliding window context compaction (`compact_session_history(session_id, max_tokens)`) and periodic background summarization to prune older dialogue turns while preserving critical state.

### 3.4 GEAP Long-Term Memory Bank & Async Callbacks (`VertexAiMemoryBankService`)
- Persist cross-session knowledge using `google.adk.memory.VertexAiMemoryBankService`.
- **Memory ETL Lifecycle**: Follow the full ETL pipeline:
  - *Ingestion*: Dialogue fed into the pipeline.
  - *Extraction*: Extract key facts and signatures.
  - *Consolidation*: Merge new details, update existing records, or delete invalid memories (active forgetting).
  - *Storage & Provenance*: Persist records with age and origin metadata.
- **Non-Blocking Execution**: Consolidate session events via after-agent callbacks (`after_agent_callback`) executing `await callback_context.add_session_to_memory()` in the background without blocking the response loop.

---

## Section 4: Continuous Evaluation, Observability & AgentOps (GEAP Optimize Pillar)

### 4.1 Trajectory Evaluation & Outside-In Hierarchy
- **The Trajectory is the Truth**: Evaluating only final outputs is insufficient; evaluate the entire sequence of tool calls.
- **Outside-In Evaluation Hierarchy**:
  1. *Black Box (End-to-End)*: Task Success Rate and output validity.
  2. *Glass Box (Trajectory)*: Tool selection accuracy, argument parameterization, and step ordering.
- **Trajectory Validation Modes**:
  - `EXACT`: Verifies exact tool call sequence.
  - `IN_ORDER`: Verifies expected tool sequence ignoring helper calls.
  - `ANY_ORDER`: Verifies tool presence without ordering restrictions (read-only tasks).
  - Measure success using the $pass^k$ reliability metric (requiring 100% success across $k$ runs).

### 4.2 LLM-as-a-Judge & Pairwise Position Swapping
- When evaluating qualitative candidate responses with LLM judges, eliminate model selection bias by running evaluations twice with swapped positions (Run 1: A vs B; Run 2: B vs A) with structured JSON rubrics.

### 4.3 Structured JSON Logging & Phase Capture
- Emit structured logs compatible with Google Cloud Logging JSON format containing `timestamp`, `phase`, `request_id`, `agent_name`, and `tool_name`.
- **`INTENT` Phase**: Log pre-invocation parameters before invoking a tool or subagent.
- **`OUTCOME` Phase**: Log post-invocation results and execution duration (`duration_ms`) upon step completion.

### 4.4 Distributed Tracing & PII Redaction
- **OpenTelemetry Distributed Tracing**: Wrap tool and agent execution steps in OpenTelemetry spans (`@tracer.start_as_current_span`) adhering to OpenTelemetry GenAI Semantic Conventions (`gen_ai.agent.name`, `gen_ai.conversation.id`, `gen_ai.tool.definitions`).
- **Sensitive Data Protection**: Scrub passwords, tokens, emails, and PII from raw payloads using Google Cloud Sensitive Data Protection (`dlp_v2.DlpServiceClient`) with regex fallback before logging or storing data.

---

## Section 5: Zero-Trust Security, Governance & Human-in-the-Loop (GEAP Govern Pillar)

### 5.1 Sandbox Isolation & Supply Chain Defense
- **Ephemeral Kernel-Level Isolation**: Run all dynamically generated code and test executions in isolated, ephemeral sandboxes (gVisor) with deny-by-default network policies.
- **Supply Chain Defense**: Prevent slopsquatting by enforcing pre-approved package allowlists, strict version pinning, and SBOM scanning.

### 5.2 Zero Ambient Authority & Identity Propagation
- Enforce unique cryptographic Agent Identities (SPIFFE standard) managed through GEAP Agent Identity and Auth Manager.
- Apply Context-Aware Access (mTLS and DPoP) and Just-In-Time (JIT) credential downscoping.

### 5.3 Agent Gateway, Model Armor & Hybrid Policy Gating
- Route all agent traffic through **GEAP Agent Gateway** for protocol mediation (MCP, A2A, REST, gRPC) and centralized policy enforcement.
- Protect against MCP prompt injection attacks, jailbreaks, and unsafe tool payloads using **Model Armor**.
- Gate tool executions via a two-layer Policy Server:
  1. *Layer 1 (Structural Gating)*: Deterministic, fast role/environment checks.
  2. *Layer 2 (Semantic Gating)*: Secondary LLM safety scan checking arguments against natural-language guidelines.

### 5.4 Human-in-the-Loop (HITL) Checkpoints & "The Vibe Diff"
- High-stakes actions (such as Pull Request creation or production deployment) MUST pause execution in state `"AWAITING_HUMAN_REVIEW"`.
- Render declarative A2UI review cards containing "The Vibe Diff" (plain-English intent summary side-by-side with original instructions and code diffs) to prevent review fatigue.
- Resume execution only upon receiving an HMAC-authenticated webhook signoff (`APPROVE`, `MODIFY`, `REJECT`).

---

## Section 6: Actionable Implementation Cheatsheet & Circuit Breakers

### 6.1 Agent CLI & Platform Operations
All agent systems must be fully operable via the Google ADK CLI, Agent API CLI, and GEAP publishing commands:
```bash
# 1. Interactive testing and local playground
agents-cli playground
adk web --port=8080
adk run app.agents.coordinator:root_agent

# 2. Run CI/CD Evaluation and Quality Flywheel
agents-cli eval run
agents-cli eval optimize

# 3. Deploy to GEAP Agent Runtime
agents-cli deploy

# 4. Publish agent to GEAP Agent Registry
agents-cli publish gemini-enterprise

# 5. Agent API operations and HITL resume
agentapi new-conversation --model=flash --title="Incident Triage" "Triage incoming alert payload"
agentapi get-conversation-metadata <conversation-id>
agentapi send-message --title="HITL Approval" "<conversation-id>" "APPROVE: Patch verified."
```

### 6.2 The Security Response Playbook (Circuit Breakers)
If monitoring detects intent drift, Model Armor security findings, or anomalous reasoning loops:
1. **Trip the Circuit Breaker**: Instantly revoke the compromised agent's tool credentials in Agent Gateway.
2. **Stateful Quarantine**: Pause container execution in Agent Runtime, freeze short-term memory intact for forensic debugging, and route session trace to review queue.
3. **Rollback**: Automatically trigger a git rollback to the last known safe version control checkpoint.

---

# Models Directive

Strictly adhere to the following foundation model requirements:
- **Fast / Routing Tier**: `gemini-3.7-flash` (High-throughput intake, deduplication, triage classification, CODEOWNERS routing).
- **Reasoning / Deep Planning Tier**: `gemini-3.1-pro-preview` (Multi-file code analysis, unit test generation, complex patch synthesis, HITL diff preparation).
- **Prohibited Legacy Models**: Do NOT use `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-1.5-pro`, or any deprecated models.