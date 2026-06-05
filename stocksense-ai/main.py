from agno.db.postgres import PostgresDb, AsyncPostgresDb
from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings
from app.agents import text_to_sql, strategy_selector
from scalar_fastapi import get_scalar_api_reference
from stocksense.config import get_settings


settings = get_settings()
db = PostgresDb(
    db_url=f"postgresql+psycopg://stocksense:{settings.common.postgres_passwd}@{settings.common.postgres_url}:5432/agno",
    id="traces",
)

agent_os = AgentOS(
    name="StockSense",
    agents=[text_to_sql, strategy_selector],
    db=db,
    tracing=True,
    # settings=AgnoAPISettings(docs_enabled=False),
)
app = agent_os.get_app()


# Scalar interactive docs
# @app.get("/docs", include_in_schema=False)
# async def _internal_scalar_html():
#     return get_scalar_api_reference(
#         openapi_url=app.openapi_url,
#         title=app.title,
#         # scalar_favicon_url="/static/chart-growth-invest.svg",
#     )
