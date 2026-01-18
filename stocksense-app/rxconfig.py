import reflex as rx
import reflex_enterprise as rxe
from stocksense.config import get_settings

settings = get_settings()


config = rxe.Config(
    app_name="webapp",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    backend_port=settings.app.backend_port,
    frontend_port=settings.app.port,
)
