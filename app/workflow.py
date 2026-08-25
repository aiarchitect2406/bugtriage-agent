"""ADK 2.0 Graph-Based Workflow Engine for Bug Triage & Remediation."""

import uuid
import logging
from typing import Dict, Any, Optional, List
from google.adk.workflow import Workflow, node
from google.adk.events import Event
from google.adk.agents.context import Context

from app.models.bug_report import BugReport, SanitizedBugReport, EnrichmentContext
from app.models.hitl import HITLGateState
from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.tools.git_tools import create_draft_pull_request
from app.plugins.guardrails import GuardrailPolicyPlugin
from app.hitl.state_store import HITLStateStore
from app.hitl.card_renderer import render_a2ui_review_card

guardrail_plugin = GuardrailPolicyPlugin()

@node
def ingest_node(ctx: Context, node_input: Any) -> Event:
    """Ingestion Node: Sanitizes raw logs, extracts stack frames, and redacts PII."""
    payload = node_input if isinstance(node_input, dict) else (node_input.model_dump() if hasattr(node_input, "model_dump") else {})
    
    res = sanitize_logs_and_extract_stack(
        issue_id=payload.get("issue_id", "BUG-2026-UNKNOWN"),
        title=payload.get("title", ""),
        description=payload.get("description", ""),
        raw_logs=payload.get("raw_logs", ""),
        stack_trace=payload.get("stack_trace"),
        source_system=payload.get("source_system", "Sentry"),
        metadata=payload.get("metadata", {})
    )
    
    if res.get("status") == "ERROR":
        return Event(output={"status": "ERROR", "step": "INGESTION", "message": res.get("message")})
    
    sanitized_report = res.get("sanitized_report", {})
    ctx.state["sanitized_report"] = sanitized_report
    ctx.state["metadata"] = payload.get("metadata", {})
    return Event(output=sanitized_report)

@node
def dedupe_node(ctx: Context, node_input: Any) -> Event:
    """Dedupe Node: Performs vector similarity check and branches routes."""
    sanitized = ctx.state.get("sanitized_report") or (node_input if isinstance(node_input, dict) else {})
    issue_id = sanitized.get("issue_id", "")
    title = sanitized.get("title", "")
    desc = f"{sanitized.get('cleaned_description', '')} {sanitized.get('sanitized_logs', '')}"
    
    candidates = ctx.state.get("historical_candidates")
    res = query_similar_bugs_by_vector(
        issue_id=issue_id,
        bug_title=title,
        bug_description=desc,
        candidate_historical_bugs=candidates
    )
    
    dedupe_info = res.get("dedupe_result", {})
    is_duplicate = dedupe_info.get("is_duplicate", False)
    
    if is_duplicate:
        ctx.state["dedupe_result"] = dedupe_info
        return Event(
            output={
                "status": "DUPLICATE_LINKED",
                "issue_id": issue_id,
                "parent_issue_id": dedupe_info.get("matching_parent_issue_id"),
                "similarity_score": dedupe_info.get("similarity_score"),
                "explanation": dedupe_info.get("explanation")
            },
            route="duplicate"
        )
    
    return Event(output=sanitized, route="new_bug")

@node
def handle_duplicate_node(ctx: Context, node_input: Any) -> Dict[str, Any]:
    """Duplicate Handler Node: Concludes flow with linked master parent ticket."""
    return node_input if isinstance(node_input, dict) else ctx.state.get("dedupe_result", {})

@node
def enrich_node(ctx: Context, node_input: Any) -> Event:
    """Enrichment Node: Resolves CODEOWNERS, git blame authors, and SLA priority assignments."""
    sanitized = ctx.state.get("sanitized_report", {})
    issue_id = sanitized.get("issue_id", "")
    frames = sanitized.get("stack_frames", [])
    metadata = ctx.state.get("metadata", {})
    severity_hint = metadata.get("severity", "Major")
    
    res = resolve_codeowners_and_blame(
        issue_id=issue_id,
        stack_frames=frames,
        severity_input=severity_hint
    )
    
    enrichment_context = res.get("enrichment_context", {})
    ctx.state["enrichment_context"] = enrichment_context
    
    # Guardrail Check
    guard_check = guardrail_plugin.validate_triage_decision(
        severity=enrichment_context.get("severity", "Major"),
        priority=enrichment_context.get("priority", "P1"),
        primary_owner=enrichment_context.get("primary_owner", "@core-triage-team")
    )
    if not guard_check.get("is_valid"):
        return Event(
            output={
                "status": "REJECTED_BY_GUARDRAIL",
                "violations": guard_check.get("violations"),
                "issue_id": issue_id
            }
        )
    
    return Event(output=enrichment_context)

from app.tools.review_tools import review_code_patch_with_claude

@node
def remediate_node(ctx: Context, node_input: Any) -> Event:
    """Remediation Node: Synthesizes failing pytest and unified diff patch in sandbox."""
    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    affected_files = enrichment.get("affected_files", [])
    target_file = affected_files[0] if affected_files else "app/services/payment_checkout.py"
    
    res = execute_reproduction_and_sandbox_fix(
        issue_id=sanitized.get("issue_id", ""),
        stack_trace=sanitized.get("sanitized_logs", ""),
        source_file_path=target_file,
        existing_source_code=None
    )
    
    ctx.state["remediation_result"] = res
    return Event(output=res)

@node
def review_node(ctx: Context, node_input: Any) -> Event:
    """Peer Review Node: Maker-Checker audit using Claude Sonnet 4.6 on Vertex AI."""
    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    remediation = ctx.state.get("remediation_result", {})
    
    repro = remediation.get("reproduction_test", {})
    fix = remediation.get("fix_patch", {})
    affected_files = enrichment.get("affected_files", ["services/payment_gateway.py"])
    target_file = affected_files[0] if affected_files else "services/payment_gateway.py"

    review_res = review_code_patch_with_claude(
        issue_id=sanitized.get("issue_id", ""),
        target_file_path=target_file,
        diff_patch=fix.get("diff_patch", ""),
        patch_explanation=fix.get("explanation", ""),
        reproduction_test_code=repro.get("test_code", ""),
        source_context=None
    )
    
    ctx.state["review_result"] = review_res
    return Event(output=review_res)

@node
def hitl_gate_node(ctx: Context, node_input: Any) -> Event:
    """HITL Gateway Node: Pauses execution in state AWAITING_HUMAN_REVIEW and renders A2UI Card."""
    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    remediation = ctx.state.get("remediation_result", {})
    review_res = ctx.state.get("review_result", {})
    
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    issue_id = sanitized.get("issue_id", "BUG-UNKNOWN")
    repro = remediation.get("reproduction_test", {})
    fix = remediation.get("fix_patch", {})
    sandbox = remediation.get("sandbox_result", {})
    
    gate_state = HITLGateState(
        session_id=session_id,
        issue_id=issue_id,
        status="AWAITING_HUMAN_REVIEW",
        severity=enrichment.get("severity", "Major"),
        priority=enrichment.get("priority", "P1"),
        primary_owner=enrichment.get("primary_owner", "@core-triage-team"),
        failing_test_code=repro.get("test_code", ""),
        proposed_diff_patch=fix.get("diff_patch", ""),
        patch_explanation=fix.get("explanation", ""),
        claude_review=review_res
    )
    
    HITLStateStore.save_paused_state(gate_state)
    a2ui_card = render_a2ui_review_card(gate_state)
    HITLStateStore.compact_session_history(session_id)
    HITLStateStore.async_consolidate_memory(session_id)
    
    output = {
        "status": "AWAITING_HUMAN_REVIEW",
        "session_id": session_id,
        "issue_id": issue_id,
        "primary_owner": enrichment.get("primary_owner"),
        "severity": enrichment.get("severity"),
        "priority": enrichment.get("priority"),
        "sla_target_hours": enrichment.get("sla_target_hours"),
        "sandbox_status": sandbox.get("status"),
        "proposed_diff_patch": fix.get("diff_patch"),
        "failing_test_code": repro.get("test_code"),
        "claude_review": review_res,
        "a2ui_card": a2ui_card,
    }
    
    return Event(output=output)

@node
def create_pr_node(ctx: Context, node_input: Any) -> Dict[str, Any]:
    """Draft PR Node: Publishes draft PR upon approval."""
    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    remediation = ctx.state.get("remediation_result", {})
    review_res = ctx.state.get("review_result", {})
    fix = remediation.get("fix_patch", {})
    repro = remediation.get("reproduction_test", {})
    
    return create_draft_pull_request(
        issue_id=sanitized.get("issue_id", ""),
        diff_patch=fix.get("diff_patch"),
        test_code=repro.get("test_code"),
        reviewer_handle=enrichment.get("primary_owner"),
        claude_review=review_res
    )

# Deterministic Graph Edges
workflow_edges = [
    ("START", ingest_node),
    (ingest_node, dedupe_node),
    (dedupe_node, {
        "duplicate": handle_duplicate_node,
        "new_bug": enrich_node
    }),
    (enrich_node, remediate_node),
    (remediate_node, review_node),
    (review_node, hitl_gate_node),
    (hitl_gate_node, {
        "approved": create_pr_node
    }),
]

bug_triage_workflow = Workflow(
    name="bug_triage_workflow",
    edges=workflow_edges,
    description="End-to-end Autonomous Bug Triage & Peer Review Workflow",
)
