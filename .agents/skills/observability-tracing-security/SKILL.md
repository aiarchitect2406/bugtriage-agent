---
name: observability-tracing-security
description: Production observability, structured Google Cloud Logging, INTENT/OUTCOME phase capture, OpenTelemetry tracing, and Cloud DLP PII redaction for Google ADK 2.0.
---

# Observability, Distributed Tracing & Security

This skill provides observability, tracing, and security patterns for building Google ADK 2.0 and GEAP agents.

---

## 1. Structured JSON Logging for Google Cloud Logging
- Emit all application and agent logs in structured JSON format compatible with Google Cloud Logging.
- Mandatory top-level fields: `timestamp` (ISO 8601 UTC), `phase`, `request_id`, `agent_name`, `tool_name`, and metadata payloads:
  ```python
  payload = {
      "timestamp": "2026-08-04T23:59:00Z",
      "phase": "INTENT",
      "request_id": "req-12345",
      "agent_name": "EnrichmentAgent",
      "tool_name": "resolve_codeowners_and_blame",
      "intended_args": {"issue_id": "BUG-101"}
  }
  ```

---

## 2. Intent vs. Outcome Phase Capture
- **`INTENT` Phase**: Log pre-invocation arguments immediately before invoking a tool or worker agent.
- **`OUTCOME` Phase**: Log post-invocation results and execution duration (`duration_ms`) immediately upon completion:
  ```python
  # Log INTENT
  StructuredLogger.log_phase(phase="INTENT", request_id=req_id, agent_name="ToolName", intended_args=args)

  # Execute operation & measure duration
  start_time = time.perf_counter()
  result = execute_tool(...)
  duration = (time.perf_counter() - start_time) * 1000

  # Log OUTCOME
  StructuredLogger.log_phase(phase="OUTCOME", request_id=req_id, agent_name="ToolName", duration_ms=duration, actual_outcome=result)
  ```

---

## 3. Distributed OpenTelemetry Tracing
- Link agent execution hops and tool invocations across distributed execution chains using OpenTelemetry spans (`@tracer.start_as_current_span` or `with tracer.start_as_current_span(...)`).
- Attach span attributes (`request_id`, `agent.name`, `tool.name`).

---

## 4. PII Redaction & Sensitive Data Protection
- Scrub all user payloads, log messages, and error traces before storing in logs or memory.
- **Primary Engine**: Google Cloud Sensitive Data Protection (`dlp_v2.DlpServiceClient`) targeting `EMAIL_ADDRESS`, `IP_ADDRESS`, `AUTH_TOKEN`, `CREDIT_CARD_NUMBER`, and `API_KEY`.
- **Fallback Engine**: Regex Scrubber (`EMAIL_REGEX`, `API_KEY_REGEX`, `IPV4_REGEX`, `CREDIT_CARD_REGEX`).
