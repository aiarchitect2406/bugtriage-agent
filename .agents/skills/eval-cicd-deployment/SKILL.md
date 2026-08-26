---
name: eval-cicd-deployment
description: Continuous evaluation, CI/CD pipelines, Terraform IaC, Secret Manager integration, Agent CLI operations, and A2A/A2UI protocols for Google ADK 2.0.
---

# Continuous Evaluation, CI/CD, IaC & Protocols

This skill provides testing, CI/CD, infrastructure, and agent protocol patterns for building Google ADK 2.0 and GEAP agents.

---

## 1. Automated Golden Dataset Evaluation Harness
- Implement an automated evaluation harness (`tests/eval/run_eval.py`) that tests end-to-end agent trajectories against a curated Golden Dataset (`bugtriage_golden_dataset.json`).
- Verify critical quality assertions on every test run:
  1. **PII Redaction Accuracy**: Confirm sensitive tokens are scrubbed.
  2. **Deduplication / Routing Accuracy**: Confirm duplicates are linked and CODEOWNERS match target teams.
  3. **Sandbox Remediation Success**: Confirm reproduction tests fail first, patches apply cleanly, and post-patch test suites pass.
  4. **A2UI Card Generation**: Confirm review payloads conform to A2UI declarative schema.
- Require **100% trajectory accuracy** before promotion.

---

## 2. Infrastructure as Code & Agent CLI Documentation
- Manage Google Cloud infrastructure declaratively using Terraform (`main.tf` with `google` provider >= 5.0).
- Provision mandatory resources with full IAM bindings:
  - Managed Service Account (`google_service_account`) for GEAP Agent Identity with `roles/aiplatform.user`, `roles/secretmanager.secretAccessor`, and `roles/dlp.user`.
  - Google Cloud Secret Manager secrets (`google_secret_manager_secret`).
  - Google Cloud Run v2 service (`google_cloud_run_v2_service`) deploying the containerized ADK runtime.
- **Agent CLI Operations**: Ensure and document full operational compatibility with Google ADK CLI and Agent API CLI:
  ```bash
  # Start a new conversation
  agentapi new-conversation --model=flash --title="Incident #101" "Triage incoming alert"

  # Run local ADK Web UI or CLI chat
  adk web --port 8085 app
  adk run app.agent:root_agent
  ```

---

## 3. Secure Secret Management
- **Zero Hardcoded Secrets**: Fetch all API keys, GitHub tokens, and HMAC signing keys dynamically at runtime from Google Cloud Secret Manager (`google.cloud.secretmanager`) with environment variable fallbacks.

---

## 4. Agent-to-Agent (A2A) & Agent-to-User (A2UI) Protocols
- **A2A Agent Card**: Expose an A2A discovery card at `/.well-known/agent-card.json` detailing agent name, description, and available skills.
- **A2UI Declarative Cards**: Generate interactive review cards for Slack/Jira containing failing unit test code blocks, unified diff patches, and single-click approval/modification action buttons.
