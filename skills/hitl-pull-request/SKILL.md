---
name: hitl-pull-request
description: Renders declarative A2UI review cards displaying 'The Vibe Diff' and opens GitHub Draft Pull Requests following HMAC-signed developer signoff.
activation_cues:
  - "render_review_card"
  - "a2ui_card"
  - "create_pull_request"
  - "developer_approval"
tools:
  - "render_a2ui_review_card"
  - "create_draft_pull_request"
---

# Skill: Human-in-the-Loop Gateway & Pull Request Publishing

## Purpose
Enforces Zero-Trust policy gating by pausing session execution in `AWAITING_HUMAN_REVIEW` with interactive A2UI cards. Upon cryptographic developer signoff, creates draft pull requests on the target repository.

## Activation Protocol
Triggered following sandbox verification or when developer approval is received.

## Tool Binding
Dynamically attaches and executes `render_a2ui_review_card` and `create_draft_pull_request`.
