"""Reflex app entrypoint for StockSense (migrating from Streamlit).

Pages live under the `webapp.pages` package.
"""

import reflex_enterprise as rx

from webapp.pages import home
from webapp.pages.ai import ai
from webapp.pages.ai import chat as ai_chat
from webapp.pages.ai import research as ai_research
from webapp.pages.management import configuration as management_configuration
from webapp.pages.management import (
    management,
)
from webapp.pages.playground import (
    data as playground_data,
)
from webapp.pages.playground import (
    playground,
)
from webapp.pages.playground import (
    strategy as playground_strategy,
)

app = rx.App()
app.add_page(home, route="/", title="StockSense")
app.add_page(playground, route="/playground", title="Playground")
app.add_page(playground_data, route="/playground/data", title="Playground: Data")
app.add_page(
    playground_strategy, route="/playground/strategy", title="Playground: Strategy"
)
app.add_page(ai, route="/ai", title="AI")
app.add_page(ai_chat, route="/ai/chat", title="AI Chat")
app.add_page(ai_research, route="/ai/research", title="AI Research")
app.add_page(management, route="/management", title="Management")
app.add_page(
    management_configuration,
    route="/management/configuration",
    title="Management: Configuration",
)
