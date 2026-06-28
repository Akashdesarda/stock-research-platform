from pathlib import Path

from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings
from app.agents import (
    company_summary,
    dataset_description,
    strategy_selector,
    text_to_sql,
)
from app.utils import async_sqlite_db
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import get_scalar_api_reference
from stocksense.config import get_settings

settings = get_settings()
STATIC_DIR = Path(__file__).parent / "static"

agent_os = AgentOS(
    name="StockSense AI API",
    agents=[text_to_sql, strategy_selector, company_summary, dataset_description],
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


if __name__ == "__main__":
    agent_os.serve(app=app, host="0.0.0.0", port=settings.ai.port, access_log=True)
