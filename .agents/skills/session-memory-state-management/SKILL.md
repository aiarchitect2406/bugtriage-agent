---
name: session-memory-state-management
description: State and memory management patterns for Google ADK 2.0 covering short-term session persistence, GEAP Memory Bank consolidation, after-agent callbacks, sliding-window compaction, and state pause/resume.
---

# Session, Memory & State Management

This skill provides state and memory management patterns for building Google ADK 2.0 and GEAP agents.

---

## 1. Robust System Instructions & Agent Constitutions
- Define exhaustive, authoritative system instructions ("Constitutions") for each agent specifying persona, role boundaries, SLA rules, and exact output expectations.

---

## 2. History Compaction & Context Management
- Treat the LLM context window as a finite budget.
- Implement token-based sliding window context compaction (`compact_session_history(session_id, max_tokens)`) and periodic background summarization to prune older turns while preserving critical state:
  ```python
  def compact_session_history(session_id: str, max_tokens: int = 4096) -> Dict[str, Any]:
      """Applies token-based sliding window compaction to session history."""
      # Prune older turns to remain within max_tokens budget
  ```

---

## 3. Persistent Multi-Turn Session State
- Maintain active conversational turns and intermediate tool states using native ADK 2.0 `google.adk.sessions.VertexAiSessionService` (with `InMemorySessionService` fallback for tests).
- Use a structured `{key: value}` session state (`session.state`) as a mutable scratchpad to share variables across subagents and tools without bloating message history.

---

## 4. Asynchronous Memory Operations
- Consolidate cross-session facts and long-term knowledge using `google.adk.memory.VertexAiMemoryBankService`.
- **Memory ETL Lifecycle**:
  1. *Ingestion*: Dialogue fed into the pipeline.
  2. *Extraction*: LLM extracts structured facts and issue signatures.
  3. *Consolidation*: LLM merges new details, updates evolved facts, and actively deletes contradictory memories.
  4. *Storage & Provenance*: Persist records with age and origin metadata.
- **Non-Blocking Background Callbacks**: Execute memory extraction and consolidation in after-agent callbacks (`after_agent_callback`) without blocking UI or user response threads:
  ```python
  from google.adk.agents.callback_context import CallbackContext

  async def generate_memories_callback(callback_context: CallbackContext) -> None:
      """Non-blocking background memory consolidation."""
      if hasattr(callback_context, "add_session_to_memory"):
          await callback_context.add_session_to_memory()
      return None
  ```
