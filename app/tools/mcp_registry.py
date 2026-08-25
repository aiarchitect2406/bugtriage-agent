"""Native Google ADK 2.0 McpToolset integration for GEAP and external MCP servers."""

import os
import logging
from typing import Optional, List
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

logger = logging.getLogger("McpRegistry")


def get_github_mcp_toolset(
    github_token: Optional[str] = None,
    tool_filter: Optional[List[str]] = None
) -> McpToolset:
    """Creates a native ADK McpToolset connecting to the GitHub MCP Server via stdio."""
    token = github_token or os.getenv("GITHUB_TOKEN", "")
    tool_filter = tool_filter or [
        "create_pull_request",
        "create_issue_comment",
        "get_file_contents",
        "list_commits",
    ]
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token} if token else {}
            )
        ),
        tool_filter=tool_filter
    )


def get_remote_mcp_toolset(
    sse_endpoint_url: str,
    tool_filter: Optional[List[str]] = None
) -> McpToolset:
    """Creates a native ADK McpToolset connecting to a remote GEAP Agent Gateway / Cloud Run MCP endpoint."""
    return McpToolset(
        connection_params=SseConnectionParams(url=sse_endpoint_url),
        tool_filter=tool_filter
    )
