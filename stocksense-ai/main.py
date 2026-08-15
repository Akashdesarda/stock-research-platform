from pathlib import Path

from agno.client.os import AgentOSClient, SessionType
from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings
from agno.run import RunStatus
from app.agents import AGENTS_BY_ID, ALL_AGENTS
from app.utils import async_sqlite_db
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from scalar_fastapi import get_scalar_api_reference
from stocksense.config import get_settings

settings = get_settings()
STATIC_DIR = Path(__file__).parent / "static"


class SessionRenameRequest(BaseModel):
    """Request to rename a session"""

    session_type: SessionType = Field(
        ..., description="The type of the session to rename"
    )
    component_id: str = Field(
        ..., description="The ID of the component that created the session"
    )
    session_id: str = Field(..., description="The ID of the session to rename")
    content: list[str] = Field(
        ...,
        description="The content based on which the session name is to be generated",
    )


agent_os = AgentOS(
    name="StockSense AI API",
    version="0.1.1",
    agents=ALL_AGENTS,
    db=async_sqlite_db,
    tracing=True,
    settings=AgnoAPISettings(docs_enabled=False),
)

app = agent_os.get_app()
# Adding website icon
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# making the openapi spec available so that scalar docs can read it
@app.get("/openapi.json", include_in_schema=False)
async def _openapi():
    return app.openapi()


@app.get("/docs", include_in_schema=False)
async def _internal_scalar_html():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title=app.title,
        scalar_favicon_url="/static/chart-growth-invest.svg",
    )


@app.patch("/debug/session/rename", tags=["Debug"])
async def rename_session(request: SessionRenameRequest) -> dict[str, str]:
    """Rename a session"""
    client = AgentOSClient(f"{settings.ai.ai_url}:{settings.ai.port}")
    # generating the session title
    response = await client.run_agent(
        agent_id="session-title",
        message=f"Generate a title for the session based on the following user prompt: {', '.join(request.content)}",
        session_type=SessionType.AGENT,
        component_id=request.component_id,
        session_id=request.session_id,
    )
    if response.status != RunStatus.completed:
        return {"message": "Failed to generate session title"}
    await client.rename_session(
        session_id=request.session_id,
        session_name=response.content["title"],
        session_type=request.session_type,
    )
    return {"message": f"session renamed successfully as: {response.content['title']}"}


@app.get("/debug/headroom-savings", tags=["Debug"])
def headroom_savings() -> dict:
    """Return Headroom token-savings metrics for each agent (process lifetime)."""
    out: dict[str, dict] = {}
    for name, agent in AGENTS_BY_ID.items():
        model = agent.model
        if model is None or not hasattr(model, "get_savings_summary"):
            out[name] = {"error": "model is not Headroom-wrapped"}
            continue
        metrics_history = getattr(model, "metrics_history", [])
        out[name] = {
            "summary": model.get_savings_summary(),
            "history": [
                {
                    "request_id": m.request_id,
                    "timestamp": m.timestamp.isoformat(),
                    "tokens_before": m.tokens_before,
                    "tokens_after": m.tokens_after,
                    "tokens_saved": m.tokens_saved,
                    "savings_percent": m.savings_percent,
                    "transforms_applied": m.transforms_applied,
                    "model": m.model,
                }
                for m in metrics_history
            ],
        }
    return out


if __name__ == "__main__":
    agent_os.serve(app=app, host="0.0.0.0", port=settings.ai.port, access_log=True)
