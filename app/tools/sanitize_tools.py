"""ADK Tool for Bug Intake, PII Redaction, and Stack Frame Extraction."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.models.bug_report import BugReport, SanitizedBugReport, StackFrame
from app.observability.pii_scrubber import EnterprisePIIRedactor

class SanitizeLogsInput(BaseModel):
    """Input payload for log sanitization and stack extraction."""
    issue_id: str = Field(..., description="Unique issue identifier")
    title: str = Field(..., description="Bug report title")
    description: str = Field(..., description="Bug report description")
    raw_logs: str = Field(..., description="Raw logs or crash output")
    stack_trace: Optional[str] = Field(None, description="Raw stack trace string")
    source_system: str = Field("Sentry", description="Origin source system")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")

class SanitizeLogsOutput(BaseModel):
    """Output payload from log sanitization."""
    status: str = Field(..., description="'SUCCESS' or 'ERROR'")
    sanitized_report: Optional[SanitizedBugReport] = Field(None, description="Sanitized bug report")
    message: str = Field(..., description="Human-readable status summary")
    recovery_hint: Optional[str] = Field(None, description="Corrective guidance on failure")

def sanitize_logs_and_extract_stack(
    issue_id: str,
    title: str,
    description: str,
    raw_logs: str,
    stack_trace: Optional[str] = None,
    source_system: str = "Sentry",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Sanitizes sensitive PII from incoming bug logs and extracts structured stack frames.

    Args:
        issue_id: Unique issue identifier (e.g. 'BUG-2026-001').
        title: Bug report title summary.
        description: Bug report description text.
        raw_logs: Raw console logs, HTTP dumps, or Sentry payload.
        stack_trace: Optional raw stack trace string.
        source_system: Source origin channel ('Sentry', 'GitHub', 'Jira', 'Cloud Logging').
        metadata: Optional dictionary of alert metadata.

    Returns:
        Dict[str, Any]: A dictionary serialized from SanitizeLogsOutput containing
            status ('SUCCESS' or 'ERROR'), sanitized_report, message, and recovery_hint.

    Raises:
        None: All internal exceptions are caught and returned in the dictionary.
    """
    try:
        if not raw_logs and not stack_trace:
            return SanitizeLogsOutput(
                status="ERROR",
                message="Both raw_logs and stack_trace are empty.",
                recovery_hint="Provide either raw_logs or a stack_trace string in the intake payload."
            ).model_dump()

        # 1. Redact PII from description and logs
        cleaned_desc, pii_desc = EnterprisePIIRedactor.redact_text(description or "")
        sanitized_logs, pii_logs = EnterprisePIIRedactor.redact_text(raw_logs or "")
        total_pii = pii_desc + pii_logs

        target_trace = stack_trace or raw_logs or ""

        # 2. Extract Stack Frames via Regex
        stack_frames: List[StackFrame] = []
        py_frame_regex = re.compile(
            r'File\s+"(?P<path>[^"]+)",\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\n\r]+))?'
        )
        for match in py_frame_regex.finditer(target_trace):
            file_path = match.group("path")
            line_no = int(match.group("line"))
            func_name = match.group("func") or "unknown"
            stack_frames.append(
                StackFrame(
                    file_path=file_path,
                    line_number=line_no,
                    function_name=func_name.strip(),
                    code_context=None
                )
            )

        # 3. Detect Exception Type
        exc_match = re.search(r'([A-Za-z0-9_.]*(?:Exception|Error|Fault|NullPointer|TypeError|ValueError|KeyError))(?::|\s|$)', target_trace)
        detected_exc = exc_match.group(1).split(".")[-1] if exc_match else "UnknownException"

        sanitized_report = SanitizedBugReport(
            issue_id=issue_id,
            title=title,
            cleaned_description=cleaned_desc,
            sanitized_logs=sanitized_logs,
            stack_frames=stack_frames,
            detected_exception_type=detected_exc,
            pii_redacted_count=total_pii
        )

        return SanitizeLogsOutput(
            status="SUCCESS",
            sanitized_report=sanitized_report,
            message=f"Successfully sanitized bug report {issue_id}. Redacted {total_pii} PII tokens and extracted {len(stack_frames)} stack frames."
        ).model_dump()

    except Exception as e:
        return SanitizeLogsOutput(
            status="ERROR",
            message=f"Failed to sanitize bug report: {str(e)}",
            recovery_hint="Check that raw_logs and description are valid UTF-8 strings."
        ).model_dump()
