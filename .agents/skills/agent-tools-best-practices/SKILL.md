---
name: agent-tools-best-practices
description: Tool design and implementation patterns for Google ADK 2.0 covering action-verb naming, Pydantic type schemas, Google-style docstrings, ToolContext injection, external state passing, and guided error handling.
---

# Agent Tools & Engineering Best Practices

This skill provides tool design and implementation patterns for building Google ADK 2.0 and GEAP tools.

---

## 1. Descriptive Action-Verb Naming
- Tool functions must begin with an explicit action verb indicating the specific operation performed (e.g., `query_similar_bugs_by_vector`, `create_draft_pull_request`, `resolve_codeowners_and_blame`).
- Never use generic noun-only names (`ticket`, `bug_data`) or vague helper names (`do_work`, `process_item`).
- Clear naming ensures logged agent trajectories are completely auditable.

---

## 2. Comprehensive Google-Style Docstrings
- Every tool function must have a complete Google-style docstring parsed by the ADK schema generator and sent to the LLM:
  - `Args:` Explicit parameter types, descriptions, and constraints.
  - `Returns:` Precise dictionary schema and return types.
  - `Raises:` State `Raises: None - All exceptions are caught and returned in the dictionary.`
- **Example Pattern**:
  ```python
  def query_similar_bugs_by_vector(input_data: QuerySimilarBugsInput) -> Dict[str, Any]:
      """Searches vector store for existing duplicate tickets using cosine similarity.

      Args:
          input_data (QuerySimilarBugsInput): Input payload containing issue ID and title.

      Returns:
          Dict[str, Any]: Structured dictionary with similarity score, parent ID, and status.

      Raises:
          None - All exceptions are caught and returned in the dictionary.
      """
  ```

---

## 3. Strict Pydantic Type Schemas & `.model_dump()` Returns
- Input arguments must be constrained by Pydantic `BaseModel` schemas with clear `Field(..., description="...")` annotations.
- Function outputs must return Python dictionaries generated via `.model_dump()` from an explicit output `BaseModel`.
- **External State Passing**: Never return massive tables or raw files in tool outputs. Write large outputs to external state or ADK Artifact Services and return only the reference URI to preserve token budgets.

---

## 4. Guided Error Handling & Zero Unhandled Exceptions
- Tool functions MUST catch all internal exceptions and never allow crashes.
- On error, return a dictionary with:
  - `"status": "ERROR"`
  - `"message"`: Human-readable error explanation.
  - `"recovery_hint"`: Clear instructions for the LLM on how to correct arguments and retry.
- **Example Pattern**:
  ```python
  try:
      # Execute tool logic
      return {"status": "SUCCESS", "data": result}
  except Exception as exc:
      return {
          "status": "ERROR",
          "message": f"Operation failed: {str(exc)}",
          "recovery_hint": "Verify argument format and ensure dependent services are running."
      }
  ```
