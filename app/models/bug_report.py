"""Pydantic Schemas for Bug Intake, Sanitization, Vector Deduplication & Context Enrichment."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class StackFrame(BaseModel):
    """Structured Frame in an Exception Stack Trace."""
    file_path: str = Field(..., description="Relative or absolute path to the source file")
    line_number: int = Field(..., description="Failing line number in source file")
    function_name: str = Field(..., description="Function or method name where error occurred")
    code_context: Optional[str] = Field(None, description="Source code snippet surrounding failing line")

class BugReport(BaseModel):
    """Raw Incoming Alert or Bug Report Payload."""
    issue_id: str = Field(..., description="Unique issue identifier, e.g. BUG-2026-101")
    title: str = Field(..., description="Summary title of the bug report or alert")
    description: str = Field(..., description="Detailed description and steps to reproduce")
    raw_logs: str = Field(..., description="Raw console logs, HTTP dumps, or Sentry payload")
    stack_trace: Optional[str] = Field(None, description="Raw stack trace string")
    source_system: str = Field("Sentry", description="Origin channel: 'Sentry', 'GitHub', 'Jira', 'Cloud Logging'")
    reporter: Optional[str] = Field(None, description="User or webhook reporter email/ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional alert metadata")

class SanitizedBugReport(BaseModel):
    """Log-Sanitized Bug Report with Structured Stack Frames."""
    issue_id: str
    title: str
    cleaned_description: str
    sanitized_logs: str
    stack_frames: List[StackFrame] = Field(default_factory=list)
    detected_exception_type: Optional[str] = Field(None, description="Parsed Exception class name (e.g. NullPointerException)")
    pii_redacted_count: int = Field(0, description="Total number of PII tokens redacted")

class DedupeSearchResult(BaseModel):
    """Result of Vector Similarity Duplicate Search."""
    is_duplicate: bool = Field(..., description="True if semantic similarity exceeds duplicate threshold")
    matching_parent_issue_id: Optional[str] = Field(None, description="Master ticket ID if duplicate found")
    similarity_score: float = Field(..., description="Cosine similarity score between 0.0 and 1.0")
    explanation: str = Field(..., description="Human-readable justification for duplicate classification")

class EnrichmentContext(BaseModel):
    """Enriched Context including CODEOWNERS and Git Blame Info."""
    affected_files: List[str] = Field(default_factory=list, description="List of source file paths extracted from stack frames")
    codeowners: List[str] = Field(default_factory=list, description="Matching CODEOWNERS team or user handles")
    primary_owner: str = Field(..., description="Assigned primary component owner handle")
    recent_commit_authors: List[str] = Field(default_factory=list, description="Recent commit author handles on failing line ranges")
    severity: str = Field("Major", description="Technical severity: 'Blocker', 'Major', 'Minor', 'Trivial'")
    priority: str = Field("P1", description="Business priority: 'P0', 'P1', 'P2', 'P3'")
    sla_target_hours: int = Field(24, description="Standard SLA resolution target in hours")
