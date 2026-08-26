---
name: pull-request-publishing
description: Opens GitHub Pull Requests with Maker-Checker audit badges and automated verification results.
activation_cues:
  - "create_pull_request"
  - "pull_request"
tools:
  - "create_draft_pull_request"
---

# Skill: Automated Pull Request Publishing

## Purpose
Creates verified pull requests on the target repository following multi-agent Maker-Checker code review approval.

## Tool Binding
Dynamically attaches and executes `create_draft_pull_request`.

