---
name: agent-architecture-design
description: Enterprise architecture patterns for Google ADK 2.0 and GEAP multi-agent orchestration, system constitutions, strategic model routing, guardrails, and HITL review gates.
---

# Agent Architecture & Multi-Agent Orchestration

This skill provides architectural patterns for building Google ADK 2.0 and GEAP multi-agent systems.

---

## 1. Multi-Agent Design Patterns
- Structure complex workflows using proven multi-agent patterns (Coordinator-Worker DAG, Sequential Pipelines) rather than monolithic agents.
- **Lead Coordinator**: A central orchestrator (`TriageCoordinator`) manages state transitions, invokes specialized subagents, and applies policy guardrails.
- **Specialized Worker Agents**: Subagents encapsulate single-responsibility domain functions (intake sanitization, vector deduplication, ownership routing, and code remediation).
- **Native ADK 2.0 Agent Hierarchy**:
  ```python
  from google.adk.agents import Agent

  coordinator_agent = Agent(
      model="gemini-3.7-flash",
      name="TriageCoordinator",
      instruction=COORDINATOR_CONSTITUTION,
      sub_agents=[ingestion_agent, dedupe_agent, enrichment_agent, remediation_agent]
  )
  ```

---

## 2. Strategic Model Routing Policy
- **Fast / High-Throughput Routing (`gemini-3.7-flash`)**: Used for real-time log ingestion, PII redaction, vector similarity search, and initial triage routing.
- **Deep Reasoning / Planning (`gemini-3.1-pro-preview`)**: Used for root-cause analysis, stack frame parsing, pytest reproduction test synthesis, and patch generation.

---

## 3. Policy Plugins & Safety Guardrails
- Validate triage and routing decisions using deterministic policy plugins (`GuardrailPolicyPlugin`) before state commitment.
- Automatically verify business SLA mappings (e.g. `Blocker` $\rightarrow$ `P0` with 2h SLA target).
- Catch and reject contradictory assignments or unsupported escalation paths before invoking external tools.

---

## 4. Human-in-the-Loop (HITL) Checkpoints
- Enforce explicit execution pauses in state `AWAITING_HUMAN_REVIEW` prior to high-stakes operations (e.g., Pull Request creation, Git commits).
- Render declarative A2UI review cards displaying "The Vibe Diff" (plain-English intent summary side-by-side with code diffs).
- Resume execution only upon receiving an HMAC-authenticated webhook signoff (`APPROVE`, `MODIFY`, `REJECT`).
