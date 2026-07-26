import reflex as rx
from stocksense.strategy.catalog import AnalysisDomainIndex

from webapp.components.layout import page_layout, responsive_grid, section_header
from webapp.state.playground import StrategyDiscoveryState


def _bullet_list(items: list[str]) -> rx.Component:
    return rx.list.unordered(
        rx.foreach(
            items,
            lambda item: rx.list.item(item),
        )
    )


def _category_card(name: str, data: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(name, font_weight="bold"),
            rx.data_list.root(
                rx.data_list.item(
                    rx.data_list.label("Summary"), rx.data_list.value(data["summary"])
                ),
                rx.data_list.item(
                    rx.data_list.label("Use If"),
                    rx.data_list.value(_bullet_list(data["use_if"])),
                ),
                rx.data_list.item(
                    rx.data_list.label("Example Queries"),
                    rx.data_list.value(_bullet_list(data["example_queries"])),
                ),
            ),
        )
    )


def _unit_domain_card(data: AnalysisDomainIndex, domain_key: str) -> rx.Component:
    domain = data.domains[domain_key]
    # root --> domain info --> categories --> category info
    return rx.vstack(
        section_header(title=domain.id, subtitle=domain.summary),
        rx.hstack(
            # used if & avoid when info
            rx.vstack(
                rx.text("Use If", font_weight="bold", color_scheme="green"),
                _bullet_list(domain.use_if),
            ),
            rx.vstack(
                rx.text("Avoid When", font_weight="bold", color_scheme="red"),
                _bullet_list(domain.avoid_when),
            ),
        ),
        rx.separator(),
        rx.text("Categories", font_weight="bold"),
        rx.foreach(
            domain.categories.keys(),
            lambda key: _category_card(name=key, data=domain.categories[key]),
        ),
    )


def strategy() -> rx.Component:
    return page_layout(
        responsive_grid(
            rx.scroll_area(
                rx.card(
                    _unit_domain_card(
                        StrategyDiscoveryState.analysis_domain, "technical_analysis"
                    ),  # Replace "example_domain_key" with the actual domain key you want to display
                ),
                spacing="4",
            )
        )
    )
