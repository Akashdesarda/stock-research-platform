import reflex as rx

config = rx.Config(
    app_name="app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    # WARNING - Added these lines to fix react version issues. In future when reflex natively supports react 19, we can remove these lines.
    frontend_packages=["react@^19.2.0", "react-dom@^19.2.0"],
    frontend_port=4000,  # TODO - take from `config.toml`
)
