---
name: log-sanitization-dlp
description: Sanitizes raw crash logs, extracts structured stack frames, and redacts PII, tokens, and secrets via Google Cloud Sensitive Data Protection (DLP API) with regex fallback.
activation_cues:
  - "sanitize_logs"
  - "parse_stack"
  - "redact_pii"
  - "raw_crash_report"
tools:
  - "sanitize_logs_and_extract_stack"
---

# Skill: Log Sanitization & Sensitive Data Redaction

## Purpose
Parses noisy inbound alert payloads from Sentry, GitHub Issues, Jira, and Cloud Logging. Normalizes multi-language stack traces and scrubs bearer tokens, API keys, passwords, and customer emails.

## Activation Protocol
Triggered during the intake phase when raw logs contain unscrubbed telemetry or unstructured error text.

## Tool Binding
Dynamically attaches and executes `sanitize_logs_and_extract_stack`.
