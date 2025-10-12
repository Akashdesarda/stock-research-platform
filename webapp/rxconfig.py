import reflex as rx

config = rx.Config(
    app_name="app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    frontend_packages=["react@^19.2.0", "react-dom@^19.2.0"],
    frontend_port=4000,
)
