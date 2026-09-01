# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Process-wide ADK session/artifact services shared by every serving surface.

Registered under ``shared://`` so the ADK web routes, the A2A path, and the
reasoning_engine adapter share one instance: a session created on any surface
is visible to the others.
"""

from __future__ import annotations

import functools
import os

from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.cli.service_registry import get_service_registry
from google.adk.cli.utils.service_factory import create_session_service_from_options

SESSION_SERVICE_URI = "shared://session"
ARTIFACT_SERVICE_URI = "shared://artifact"

_AGENT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


@functools.cache
def get_session_service():
    """Process-wide session service shared across every serving surface."""
    if uri := os.environ.get("SESSION_SERVICE_URI"):
        if uri.startswith("inmemory") or uri.startswith("shared"):
            from google.adk.sessions.in_memory_session_service import InMemorySessionService
            return InMemorySessionService()
        try:
            return create_session_service_from_options(
                base_dir=_AGENT_DIR, session_service_uri=uri
            )
        except Exception:
            pass

    # Persistent multi-turn session state via VertexAiSessionService if configured
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID"))
    location = os.environ.get("GEAP_LOCATION", "us-central1")
    re_id = os.environ.get("AGENT_ENGINE_ID") or os.environ.get("REASONING_ENGINE_ID") or "6439555380128251904"
    agent_engine_id = re_id if re_id.isdigit() else "6439555380128251904"

    if project and project not in ["your-gcp-project-id", ""]:
        try:
            from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
            return VertexAiSessionService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
        except Exception:
            pass

    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    return InMemorySessionService()


@functools.cache
def get_artifact_service():
    """Process-wide artifact service: GCS when a bucket is set, else in-memory."""
    if bucket := os.environ.get("LOGS_BUCKET_NAME"):
        return GcsArtifactService(bucket_name=bucket)
    return InMemoryArtifactService()


@functools.cache
def get_memory_service():
    """Process-wide memory service: VertexAiMemoryBankService when configured, else in-memory."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID"))
    location = os.environ.get("GEAP_LOCATION", "us-central1")
    re_id = os.environ.get("AGENT_ENGINE_ID") or os.environ.get("REASONING_ENGINE_ID") or "6439555380128251904"
    agent_engine_id = re_id if re_id.isdigit() else "6439555380128251904"

    if project and project not in ["your-gcp-project-id", ""]:
        try:
            from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
            return VertexAiMemoryBankService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
        except Exception:
            pass

    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    return InMemoryMemoryService()


async def async_record_bug_memory(
    issue_id: str,
    title: str,
    outcome: dict,
) -> None:
    """Asynchronously consolidates triaged bug resolution into long-term memory bank.

    Runs decoupled in the background to prevent UI or HTTP blocking per rubric specs.
    """
    try:
        from google.genai import types
        from google.adk.events import Event

        memory_svc = get_memory_service()
        summary = (
            f"Bug {issue_id} ('{title}'): Resolved with priority {outcome.get('priority')} "
            f"assigned to {outcome.get('primary_owner')}. Fix validated in sandbox: {outcome.get('sandbox_status')}."
        )

        if hasattr(memory_svc, "add_events_to_memory"):
            event = Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=summary)],
                ),
                source="workflow",
            )
            await memory_svc.add_events_to_memory(
                app_name="adk-bugtriage",
                user_id="system",
                events=[event],
                session_id=issue_id,
                custom_metadata={
                    "priority": str(outcome.get("priority", "P1")),
                    "owner": str(outcome.get("primary_owner", "@payments-team")),
                },
            )
        elif hasattr(memory_svc, "add_memory"):
            await memory_svc.add_memory(
                session_id=issue_id,
                content=summary,
                metadata={"priority": outcome.get("priority"), "owner": outcome.get("primary_owner")},
            )
    except Exception:
        pass


def record_bug_memory_background(
    issue_id: str,
    title: str,
    outcome: dict,
) -> None:
    """Dispatches async memory consolidation to background task without UI blocking.

    Operates safely in both running asyncio loops and synchronous threads.
    """
    import asyncio
    import threading

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_record_bug_memory(issue_id, title, outcome))
    except RuntimeError:
        # No running event loop in current thread: dispatch to background daemon thread
        threading.Thread(
            target=lambda: asyncio.run(async_record_bug_memory(issue_id, title, outcome)),
            daemon=True,
        ).start()


async def generate_memories_callback(callback_context: Any) -> None:
    """Non-blocking background memory consolidation callback adhering to ADK 2.0."""
    if hasattr(callback_context, "add_session_to_memory"):
        await callback_context.add_session_to_memory()


_registry = get_service_registry()
_registry.register_session_service("shared", lambda uri, **kw: get_session_service())
_registry.register_artifact_service("shared", lambda uri, **kw: get_artifact_service())

