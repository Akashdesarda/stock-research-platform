import reflex as rx
from stocksense.strategy.catalog import AnalysisDomainIndex, StrategyDescriptor

from webapp.components.inputs import dropdown_select
from webapp.components.layout import (
    bordered_container,
    form_field,
    page_layout,
    responsive_grid,
    section_header,
)
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


def _strategy_card(data: StrategyDescriptor) -> rx.Component:
    return rx.vstack(
        rx.data_list.root(
            rx.data_list.item(
                rx.data_list.label("Name"), rx.data_list.value(data.name)
            ),
            rx.data_list.item(
                rx.data_list.label("Summary"), rx.data_list.value(data.summary)
            ),
            rx.data_list.item(
                rx.data_list.label("Purpose"),
                rx.data_list.value(_bullet_list(data.purpose)),
            ),
            rx.data_list.item(
                rx.data_list.label("Best For"),
                rx.data_list.value(_bullet_list(data.best_for)),
            ),
            rx.data_list.item(
                rx.data_list.label("Avoid When"),
                rx.data_list.value(_bullet_list(data.avoid_when)),
            ),
            rx.data_list.item(
                rx.data_list.label("Interpretation"),
                rx.data_list.value(data.interpretation),
            ),
            rx.data_list.item(
                rx.data_list.label("Limitations"),
                rx.data_list.value(_bullet_list(data.limitations)),
            ),
            rx.data_list.item(
                rx.data_list.label("LLM Hint"),
                rx.data_list.value(data.llm_hint),
            ),
        ),
    )


def strategy() -> rx.Component:
    return page_layout(
        rx.vstack(
            bordered_container(
                responsive_grid(
                    rx.scroll_area(
                        rx.card(
                            _unit_domain_card(
                                StrategyDiscoveryState.analysis_domain,
                                "technical_analysis",
                            ),
                        ),
                        type="auto",
                        scrollbars="vertical",
                        style={"height": 500},
                    ),
                    rx.scroll_area(
                        rx.card(
                            section_header(
                                title="fundamental analysis", subtitle="placeholder"
                            )
                        ),
                        type="auto",
                        scrollbars="vertical",
                        style={"height": 500},
                    ),
                    rx.scroll_area(
                        rx.card(
                            section_header(title="back testing", subtitle="placeholder")
                        )
                    ),
                    type="auto",
                    scrollbars="vertical",
                    style={"height": 500},
                )
            ),
            rx.spacer(),
            bordered_container(
                rx.text(
                    "Strategy Detail View",
                    size="2",
                    weight="medium",
                    color_scheme="gray",
                ),
                rx.hstack(  # domain + stategy
                    form_field(
                        label="Select Domain",
                        control=dropdown_select(
                            label="Select Domain",
                            options=StrategyDiscoveryState.available_domain,
                            value=StrategyDiscoveryState.selected_domain,
                            on_change=StrategyDiscoveryState.set_domain,
                            width="100%",
                        ),
                        help_text="Available domains for strategy discovery & analysis",
                    ),
                    # rx.spacer(),
                    form_field(
                        label="Select Strategy Category",
                        control=dropdown_select(
                            label="Select Strategy Category",
                            options=StrategyDiscoveryState.available_strategy_category.keys(),
                            value=StrategyDiscoveryState.selected_strategy_category,
                            on_change=StrategyDiscoveryState.set_strategy_category,
                            width="100%",
                        ),
                        help_text="Available strategy categories for the selected domain",
                    ),
                    form_field(
                        label="Select Strategy",
                        control=dropdown_select(
                            label="Select Strategy",
                            options=StrategyDiscoveryState.available_strategy.keys(),
                            value=StrategyDiscoveryState.selected_strategy,
                            on_change=StrategyDiscoveryState.set_strategy,
                        ),
                    ),
                    width="100%",
                    spacing="4",
                ),
                rx.cond(
                    StrategyDiscoveryState.strategy,
                    _strategy_card(StrategyDiscoveryState.strategy),
                    rx.fragment(),
                ),
            ),
        ),
    )
