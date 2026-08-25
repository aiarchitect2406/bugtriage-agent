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

import contextlib
import os
from collections.abc import AsyncIterator
from typing import Dict, Any

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from google.adk.cli.fast_api import get_fast_api_app

from google.adk.runners import Runner

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.models.hitl import WebhookSignalInput

load_dotenv()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=os.getenv("OTEL_TO_CLOUD", "false").lower() == "true",
    lifespan=lifespan,
)
app.title = "adk-bugtriage"
app.description = "API for interacting with the Agent adk-bugtriage"


@app.post("/webhooks/github/issues")
async def handle_github_issue_webhook(request: Request) -> Dict[str, Any]:
    """Ingests GitHub issue creation webhooks and triggers autonomous triage pipeline."""
    from app.models.bug_report import BugReport
    from app.agents.coordinator import TriageCoordinator

    payload = await request.json()
    action = payload.get("action", "opened")
    issue = payload.get("issue", {})
    
    issue_num = issue.get("number", "101")
    title = issue.get("title", "Runtime Exception in payment gateway")
    body = issue.get("body", "")
    
    is_blocker = any(k in title.lower() for k in ["critical", "blocker", "npe", "null"])
    severity_val = "Blocker" if is_blocker else "Major"

    report = BugReport(
        issue_id=f"GH-{issue_num}",
        title=title,
        description=body,
        raw_logs=body,
        stack_trace=body,
        source_system="GitHub",
        metadata={"severity": severity_val}
    )
    
    result = TriageCoordinator.run_triage_pipeline(report)
    return {
        "status": "PROCESSED",
        "action": action,
        "issue_id": report.issue_id,
        "triage_result": result
    }


@app.post("/webhooks/hitl/action")
async def handle_hitl_action_webhook(signal: WebhookSignalInput) -> Dict[str, Any]:
    """Handles HMAC-authenticated approval or rejection signals from Human Reviewers."""
    from app.hitl.webhook_listener import process_hitl_webhook_signal
    return process_hitl_webhook_signal(signal)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

