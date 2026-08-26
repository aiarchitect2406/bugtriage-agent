"""ADK 2.0 Graph-Based Workflow Engine for Bug Triage & Remediation."""

import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from google.genai import types
from google.adk.workflow import Workflow, node
from google.adk.events import Event
from google.adk.agents.context import Context

from app.config import Config
from app.models.bug_report import BugReport, SanitizedBugReport, EnrichmentContext
from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.tools.review_tools import review_code_patch_with_claude
from app.tools.git_tools import create_draft_pull_request

logger = logging.getLogger(__name__)


def _parse_node_input(node_input: Any) -> Dict[str, Any]:
    """Extracts a dictionary payload from various input representations (Content, str, dict, Pydantic)."""
    if hasattr(node_input, "parts"):
        raw_text = "".join(getattr(p, "text", "") for p in node_input.parts if getattr(p, "text", None))
        try:
            return json.loads(raw_text)
        except Exception:
            return {"raw_logs": raw_text, "title": raw_text[:80]}
    elif isinstance(node_input, str):
        try:
            return json.loads(node_input)
        except Exception:
            return {"raw_logs": node_input, "title": node_input[:80]}
    elif isinstance(node_input, dict):
        return node_input
    elif hasattr(node_input, "model_dump"):
        return node_input.model_dump()
    return {}


@node
def ingest_node(ctx: Context, node_input: Any) -> Event:
    """Ingestion Node: Sanitizes raw logs, extracts stack frames, and redacts PII."""
    payload = _parse_node_input(node_input)

    res = sanitize_logs_and_extract_stack(
        issue_id=payload.get("issue_id", "BUG-2026-UNKNOWN"),
        title=payload.get("title", ""),
        description=payload.get("description", ""),
        raw_logs=payload.get("raw_logs", ""),
        stack_trace=payload.get("stack_trace"),
        source_system=payload.get("source_system", "Sentry"),
        metadata=payload.get("metadata", {}),
    )

    if res.get("status") == "ERROR":
        err_out = {"status": "ERROR", "step": "INGESTION", "message": res.get("message")}
        return Event(
            content=types.Content(role="model", parts=[types.Part.from_text(text=f"Ingestion error: {res.get('message')}")]),
            output=err_out,
        )

    sanitized_report = res.get("sanitized_report", {})
    ctx.state["sanitized_report"] = sanitized_report
    ctx.state["metadata"] = payload.get("metadata", {})
    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"Ingested and sanitized {sanitized_report.get('issue_id')}: '{sanitized_report.get('title')}'")],
        ),
        output=sanitized_report,
    )


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
        candidate_historical_bugs=candidates,
    )

    dedupe_info = res.get("dedupe_result", {})
    is_duplicate = dedupe_info.get("is_duplicate", False)

    if is_duplicate:
        ctx.state["dedupe_result"] = dedupe_info
        dup_output = {
            "status": "DUPLICATE_LINKED",
            "issue_id": issue_id,
            "parent_issue_id": dedupe_info.get("matching_parent_issue_id"),
            "similarity_score": dedupe_info.get("similarity_score"),
            "explanation": dedupe_info.get("explanation"),
        }
        return Event(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"Duplicate bug identified: Linked to parent issue {dedupe_info.get('matching_parent_issue_id')} (similarity {dedupe_info.get('similarity_score'):.2f}). {dedupe_info.get('explanation')}")],
            ),
            output=dup_output,
            route="duplicate",
        )

    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"Confirmed novel bug ({issue_id}): Proceeding with team assignment and automated root-cause remediation.")],
        ),
        output=sanitized,
        route="new_bug",
    )


@node
def handle_duplicate_node(ctx: Context, node_input: Any) -> Event:
    """Duplicate Handler Node: Concludes flow with linked master parent ticket."""
    res = node_input if isinstance(node_input, dict) else ctx.state.get("dedupe_result", {})
    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"Concluded duplicate triage: Linked {res.get('issue_id')} to parent issue {res.get('parent_issue_id')}.")],
        ),
        output=res,
    )


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
        severity_input=severity_hint,
    )

    enrichment_context = res.get("enrichment_context", {})
    ctx.state["enrichment_context"] = enrichment_context
    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"Enriched issue {issue_id}: assigned to {enrichment_context.get('primary_owner')} with Priority {enrichment_context.get('priority')} (SLA target: {enrichment_context.get('sla_target_hours')}h).")],
        ),
        output=enrichment_context,
    )


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
        existing_source_code=None,
    )

    ctx.state["remediation_result"] = res
    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"Remediation synthesized: {res.get('remediation_summary')} [Sandbox: {res.get('sandbox_result', {}).get('status')}].")],
        ),
        output=res,
    )


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
        source_context=None,
    )

    ctx.state["review_result"] = review_res
    summary_text = review_res.get("summary", f"Claude Sonnet Peer Review: Verdict {review_res.get('verdict')} (Score {review_res.get('score')}/100)")

    if review_res.get("verdict") == "APPROVED":
        return Event(
            content=types.Content(role="model", parts=[types.Part.from_text(text=summary_text)]),
            output=review_res,
            route="approved",
        )
    return Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=summary_text)]),
        output=review_res,
        route="needs_attention",
    )


@node
def create_pr_node(ctx: Context, node_input: Any) -> Event:
    """Draft PR Node: Publishes verified PR upon approval."""
    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    remediation = ctx.state.get("remediation_result", {})
    review_res = ctx.state.get("review_result", {})
    fix = remediation.get("fix_patch", {})
    repro = remediation.get("reproduction_test", {})

    pr_res = create_draft_pull_request(
        issue_id=sanitized.get("issue_id", ""),
        repository_name=Config.GITHUB_REPO,
        diff_patch=fix.get("diff_patch", ""),
        test_code=repro.get("test_code", ""),
        reviewer_handle=enrichment.get("primary_owner", "@lead-reviewer"),
        review_verdict=review_res.get("verdict", "APPROVED"),
        review_score=review_res.get("score", 95),
        reviewer_model=review_res.get("reviewer_model", "claude-sonnet-4-6"),
        commit_message=f"fix({sanitized.get('issue_id')}): automated remediation verified by Claude Sonnet",
    )
    ctx.state["pr_result"] = pr_res
    pr_msg = pr_res.get("message") or f"Created Pull Request: {pr_res.get('pull_request_url')}"
    return Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=pr_msg)]),
        output=pr_res,
    )


@node
def flag_attention_node(ctx: Context, node_input: Any) -> Event:
    """Attention Node: Concludes flow when review requires manual engineer inspection."""
    res = {
        "status": "NEEDS_MANUAL_REVIEW",
        "review_result": ctx.state.get("review_result", {}),
        "sanitized_report": ctx.state.get("sanitized_report", {}),
    }
    msg_text = f"Bug triage concluded: Manual review required. Claude Sonnet review verdict: {res.get('review_result', {}).get('verdict', 'NEEDS_ATTENTION')}."
    return Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=msg_text)]),
        output=res,
    )


# Deterministic Graph Edges
workflow_edges = [
    ("START", ingest_node),
    (ingest_node, dedupe_node),
    (dedupe_node, {
        "duplicate": handle_duplicate_node,
        "new_bug": enrich_node,
    }),
    (enrich_node, remediate_node),
    (remediate_node, review_node),
    (review_node, {
        "approved": create_pr_node,
        "needs_attention": flag_attention_node,
    }),
]

bug_triage_workflow = Workflow(
    name="bug_triage_workflow",
    edges=workflow_edges,
    description="End-to-end Autonomous Bug Triage & Peer Review Workflow",
)


class WorkflowContext:
    """Lightweight runtime context for synchronous graph node execution."""
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self.state: Dict[str, Any] = initial_state or {}


def run_triage_workflow(
    bug_report: BugReport,
    historical_candidates: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes the Bug Triage Workflow and returns structured execution outcomes."""
    req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
    logger.info(f"[{req_id}] Executing ADK Bug Triage Workflow for {bug_report.issue_id}: '{bug_report.title}'")

    # Construct execution context
    ctx = WorkflowContext()
    ctx.state["historical_candidates"] = historical_candidates or []

    # 1. Ingest
    ingest_event = ingest_node._func(ctx, bug_report)
    if isinstance(ingest_event.output, dict) and ingest_event.output.get("status") == "ERROR":
        return ingest_event.output

    # 2. Dedupe
    dedupe_event = dedupe_node._func(ctx, ingest_event.output)
    dedupe_route = getattr(dedupe_event.actions, "route", None) if dedupe_event.actions else None
    if dedupe_route == "duplicate":
        dup_info = ctx.state.get("dedupe_result", {})
        return {
            "status": "DUPLICATE_LINKED",
            "issue_id": bug_report.issue_id,
            "parent_issue_id": dup_info.get("matching_parent_issue_id"),
            "similarity_score": dup_info.get("similarity_score"),
            "explanation": dup_info.get("explanation"),
        }

    # 3. Enrich
    enrich_node._func(ctx, dedupe_event.output)

    # 4. Remediate (Maker: Gemini 3.1 Pro + Sandbox)
    remediate_node._func(ctx, ctx.state.get("enrichment_context"))

    # 5. Peer Review (Checker: Claude Sonnet 4.6 on Vertex AI)
    review_event = review_node._func(ctx, ctx.state.get("remediation_result"))

    # 6. Pull Request
    review_route = getattr(review_event.actions, "route", None) if review_event.actions else None
    if review_route == "approved":
        pr_event = create_pr_node._func(ctx, review_event.output)
        pr_res = pr_event.output if isinstance(pr_event, Event) else (pr_event or {})
    else:
        pr_event = flag_attention_node._func(ctx, review_event.output)
        pr_res = pr_event.output if isinstance(pr_event, Event) else (pr_event or {})

    sanitized = ctx.state.get("sanitized_report", {})
    enrichment = ctx.state.get("enrichment_context", {})
    remediation = ctx.state.get("remediation_result", {})
    review_res = ctx.state.get("review_result", {})

    return {
        "status": "PR_CREATED" if review_route == "approved" else "NEEDS_MANUAL_REVIEW",
        "issue_id": bug_report.issue_id,
        "title": bug_report.title,
        "sanitized_logs": sanitized.get("sanitized_logs", ""),
        "primary_owner": enrichment.get("primary_owner", "@payments-team"),
        "secondary_owners": enrichment.get("secondary_owners", []),
        "priority": enrichment.get("priority", "P1"),
        "sla_target_hours": enrichment.get("sla_target_hours", 24),
        "failing_test_code": remediation.get("reproduction_test", {}).get("test_code", ""),
        "proposed_diff_patch": remediation.get("fix_patch", {}).get("diff_patch", ""),
        "sandbox_status": remediation.get("sandbox_result", {}).get("status", "PASSED"),
        "code_review": review_res,
        "pull_request_url": pr_res.get("pull_request_url"),
        "pull_request_number": pr_res.get("pull_request_number"),
        "branch_name": pr_res.get("branch_name"),
    }


class TriageCoordinator:
    """Coordinator Engine delegating execution to the ADK 2.0 Bug Triage Workflow."""

    def __init__(self, log: Optional[logging.Logger] = None):
        self.logger = log or logger
        self.workflow = bug_triage_workflow
        self.historical_issues: List[Dict[str, Any]] = []

    def execute_triage_pipeline(
        self,
        bug_report: BugReport,
        historical_candidates: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes full bug triage lifecycle via ADK Workflow Engine."""
        candidates = historical_candidates if historical_candidates is not None else list(self.historical_issues)
        result = run_triage_workflow(
            bug_report=bug_report,
            historical_candidates=candidates,
            request_id=request_id,
        )

        if result.get("status") == "PR_CREATED":
            self.historical_issues.append({
                "issue_id": bug_report.issue_id,
                "title": bug_report.title,
                "description": bug_report.description,
                "stack_trace": bug_report.stack_trace or bug_report.raw_logs,
            })

        return result


