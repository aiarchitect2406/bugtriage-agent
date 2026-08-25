---
name: spec-driven-development
description: Mandatory Spec-Driven Development (SDD), Behavior-Driven Development (BDD), Evaluation-Driven Development (EDD), and role-based execution patterns for building production-grade agents.
---

# Spec-Driven Development & Behavior-Driven Engineering

This skill defines the mandatory specification and development methodology for coding agents building production-grade Google ADK 2.0 and GEAP multi-agent systems.

---

## 1. The Inversion Workflow (BDD & EDD)

Traditional "code-first" development is prohibited. All development must follow a spec-first methodology:

1. **Behavior-Driven Development (BDD)**:
   - Technical designs must be formulated as executable Gherkin specifications (`Scenario` / `Given` / `When` / `Then`) to structure natural-language intent into deterministic states, actions, and outcomes.
   - Example:
     ```gherkin
     Scenario: Ingest alert with PII tokens
       Given an incoming crash report with an embedded bearer token
       When the IngestionAgent executes sanitize_logs_and_extract_stack
       Then all bearer tokens must be scrubbed from the output
       And the cleaned stack frames must be extracted
     ```

2. **Evaluation-Driven Development (EDD)**:
   - Before writing implementation code or drafting a skill (`SKILL.md`), you must write at least three (3) concrete JSON evaluation cases upfront representing the functional spec in `golden_dataset.json`:
     ```json
     {
       "case_id": "eval_case_001",
       "input": "User reported crash with invalid session token",
       "expected_agent": "IngestionAgent",
       "expected_tool_calls": [
         {"tool": "sanitize_logs_and_extract_stack", "args": {"issue_id": "ISSUE-001"}}
       ],
       "expected_output_format": "sanitized_report",
       "rubric": ["redacts auth tokens", "extracts clean stack trace"]
     }
     ```

---

## 2. Role-Based Execution Modes & Constraints

Transition to the appropriate role-based execution pattern based on task context:

1. **Project Generation (The Architect)**:
   - **No YOLO Mode**: Propose folder structure, technical stack, and library version pinning for confirmation before writing code.
   - **Explicit Version Pinning**: Pin all library and model dependencies in prompts and configuration files.

2. **Feature Generation (The Builder)**:
   - **Match Style**: Match existing style, naming patterns, and error handling perfectly.
   - **Surgical Changes**: Restrict changes strictly to the lines necessary to implement the feature.
   - **Renaming Boundary**: Variable renaming is disruptive; isolate to separate, dedicated commits.

3. **Bug Fixing (The Forensic Specialist)**:
   - **Evidence Prompting**: Reject vague symptom prompting; analyze logs, stack traces, and trace evidence.
   - **Test-First Debugging**: Write a reproducing, failing unit test before attempting code repairs.
   - **Root-Cause Isolation**: Repair only the root cause; avoid random refactoring in adjacent modules.

4. **Documentation Writing (The Author)**:
   - **Code-Doc Sync**: Ensure `README.md`, `AGENTS.md`, and specifications are updated concurrently with code changes.
   - **Strict Google-Style Docstrings**: Use Google Style Docstrings for Python to enable downstream agents to parse function signatures seamlessly.
