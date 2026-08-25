---
name: ownership-routing
description: Resolves microservice and file ownership via .github/CODEOWNERS and git blame history; assigns SLA severity and priority targets.
activation_cues:
  - "resolve_owner"
  - "match_codeowners"
  - "git_blame"
  - "calculate_sla"
tools:
  - "resolve_codeowners_and_blame"
---

# Skill: Ownership Resolution & SLA Priority Mapping

## Purpose
Parses the top non-library stack frames against `.github/CODEOWNERS` glob rules and inspects recent `git blame` author contributions to ensure single-hop triage routing. Enforces SLA priority mapping (`Blocker` $\rightarrow$ `P0`/`P1`).

## Activation Protocol
Triggered when an issue is confirmed to be a unique, non-duplicate incident.

## Tool Binding
Dynamically attaches and executes `resolve_codeowners_and_blame`.
