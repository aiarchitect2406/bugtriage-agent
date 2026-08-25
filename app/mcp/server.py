"""Model Context Protocol (MCP) Server for Bug Triage Tools.

Exposes the ADK 2.0 Bug Triage tools via standard JSON-RPC MCP protocol for
Gemini Enterprise Agent Platform, Antigravity, Claude, and external MCP clients.
"""

import sys
import json
import logging
from typing import Dict, Any

from app.tools import (
    sanitize_logs_and_extract_stack,
    query_similar_bugs_by_vector,
    resolve_codeowners_and_blame,
    execute_reproduction_and_sandbox_fix,
    create_draft_pull_request,
)

logger = logging.getLogger("BugTriageMCPServer")

TOOLS = {
    "sanitize_logs_and_extract_stack": {
        "description": "Sanitizes crash logs, extracts structured stack frames, and redacts PII/secrets via Cloud DLP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Unique identifier for the bug ticket"},
                "title": {"type": "string", "description": "Bug report title"},
                "description": {"type": "string", "description": "Bug report summary"},
                "raw_logs": {"type": "string", "description": "Raw unstructured error log or crash traceback"}
            },
            "required": ["issue_id", "title", "description"]
        },
        "handler": sanitize_logs_and_extract_stack
    },


    "query_similar_bugs_by_vector": {
        "description": "Queries vector index using cosine similarity to identify duplicate bug reports.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Target issue ID"},
                "bug_title": {"type": "string", "description": "Title of incoming bug"},
                "bug_description": {"type": "string", "description": "Description of incoming bug"},
                "candidate_historical_bugs": {"type": "array", "description": "Optional list of historical bug candidates"}
            },
            "required": ["issue_id", "bug_title", "bug_description"]
        },
        "handler": query_similar_bugs_by_vector
    },
    "resolve_codeowners_and_blame": {
        "description": "Resolves microservice code ownership via .github/CODEOWNERS and git blame; assigns SLA priority.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Unique ticket ID"},
                "stack_frames": {"type": "array", "description": "List of stack frame objects"},
                "severity_input": {"type": "string", "description": "Severity level (Blocker, Major, Minor, Trivial)"}
            },
            "required": ["issue_id", "stack_frames"]
        },
        "handler": resolve_codeowners_and_blame
    },
    "execute_reproduction_and_sandbox_fix": {
        "description": "Synthesizes pytest reproduction unit tests and unified diff patches; verifies in isolated subprocess sandbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Target issue ID"},
                "stack_trace": {"type": "string", "description": "Sanitized stack trace"},
                "source_file_path": {"type": "string", "description": "Path to failing source file"},
                "existing_source_code": {"type": "string", "description": "Current source code"}
            },
            "required": ["issue_id"]
        },
        "handler": execute_reproduction_and_sandbox_fix
    },
    "create_draft_pull_request": {
        "description": "Opens a GitHub Draft Pull Request on the target repository following HMAC developer signoff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Ticket ID"},
                "diff_patch": {"type": "string", "description": "Unified diff patch string"},
                "commit_message": {"type": "string", "description": "Git commit message"},
                "pr_title": {"type": "string", "description": "PR title"}
            },
            "required": ["issue_id", "diff_patch", "commit_message", "pr_title"]
        },
        "handler": create_draft_pull_request
    }
}

def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handles standard JSON-RPC 2.0 MCP requests."""
    method = request.get("method")
    req_id = request.get("id")

    if method == "tools/list":
        tools_list = [
            {
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["inputSchema"]
            }
            for name, meta in TOOLS.items()
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools_list}
        }

    elif method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{name}' not found."}
            }

        try:
            handler = TOOLS[name]["handler"]
            tool_output = handler(**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(tool_output, indent=2)}]
                }
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)}
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not implemented."}
    }

def run_stdio_server():
    """Runs standard IO loop for MCP server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_mcp_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_stdio_server()
