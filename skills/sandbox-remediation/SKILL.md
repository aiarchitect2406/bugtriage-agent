---
name: sandbox-remediation
description: Synthesizes standalone pytest reproduction unit tests and unified diff patches using deep reasoning; executes in an isolated subprocess sandbox verifying clean fixes.
activation_cues:
  - "synthesize_reproduction"
  - "generate_patch"
  - "run_sandbox_pytest"
  - "verify_remediation"
tools:
  - "execute_reproduction_and_sandbox_fix"
---

# Skill: Sandbox Reproduction & Automated Patch Synthesis

## Purpose
Invokes deep planning models (`gemini-3.1-pro-preview`) to generate executable reproduction tests and source patches. Executes in an ephemeral subprocess sandbox enforcing test-first verification (fails on baseline, passes on patch).

## Activation Protocol
Triggered after ownership routing when code changes are required to remediate the defect.

## Tool Binding
Dynamically attaches and executes `execute_reproduction_and_sandbox_fix`.
