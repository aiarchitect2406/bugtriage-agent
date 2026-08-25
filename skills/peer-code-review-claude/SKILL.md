---
name: peer-code-review-claude
description: Conducts unbiased, independent peer code review on proposed patches and pytest suites using Claude Sonnet 4.6 via Google Cloud Vertex AI (Maker-Checker dual-model verification).
activation_cues:
  - "review_code_patch"
  - "claude_code_review"
  - "audit_patch_security"
  - "verify_peer_review"
tools:
  - "review_code_patch_with_claude"
---

# Skill: Independent Peer Code Review (Claude Sonnet 4.6 on Vertex AI)

## Purpose
Implements the Maker-Checker (Generator-Critic) multi-model verification architecture. While `gemini-3.1-pro` synthesizes the patch and reproduction test, this skill invokes `claude-sonnet-4-6` via Google Cloud Vertex AI (`AnthropicVertex` in `global` region using the shared GCP project) to perform an independent, cross-model audit of security (CWE-476, CWE-89), type safety, edge cases, and API invariants before pull request creation.

## Activation Protocol
Triggered immediately after `sandbox-remediation` succeeds with a 100% test pass in the ephemeral sandbox.

## Tool Binding
Dynamically attaches and executes `review_code_patch_with_claude`.
