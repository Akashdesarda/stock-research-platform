from agno.os import AgentOS
from app.agents import company_summary, strategy_selector, text_to_sql
from app.utils import postgres_db
from stocksense.config import get_settings

settings = get_settings()

agent_os = AgentOS(
    name="StockSense",
    agents=[text_to_sql, strategy_selector, company_summary],
    db=postgres_db,
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
if __name__ == "__main__":
    agent_os.serve(
        app=app,
        host="0.0.0.0",
        port=settings.ai.port,
    )
