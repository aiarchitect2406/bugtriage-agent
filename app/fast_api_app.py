"""FastAPI server for Google ADK 2.0 Bug Triage Agent with A2A and Reasoning Engine support."""

import contextlib
import os
import logging
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.config import Config

load_dotenv()
logger = logging.getLogger("FastApiServer")

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
app.description = "API for interacting with the Google ADK Bug Triage Agent"



@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "HEALTHY",
        "service": "bugtriage-agent",
        "project": Config.PROJECT_ID,
        "location": Config.LOCATION,
    }


from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    issue_id: str = Field(..., description="Target issue ID, e.g. GH-101")
    title: str = Field(..., description="Bug report title")
    description: Optional[str] = Field("", description="Detailed bug report description")
    raw_logs: Optional[str] = Field("", description="Stack trace or execution logs")
    source_system: Optional[str] = Field("GitHub", description="Source alert system")


@app.post("/triage")
def triage_issue(req: TriageRequest) -> Dict[str, Any]:
    """Autonomous Bug Triage Endpoint executing the full ADK pipeline."""
    from app.models.bug_report import BugReport
    from app.workflow import TriageCoordinator

    coordinator = TriageCoordinator()
    report = BugReport(
        issue_id=req.issue_id,
        title=req.title,
        description=req.description or "",
        raw_logs=req.raw_logs or req.description or "",
        source_system=req.source_system or "GitHub",
    )
    return coordinator.execute_triage_pipeline(report)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)


