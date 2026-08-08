import reflex as rx
from stocksense.strategy.catalog import AnalysisDomainIndex, StrategyDescriptor

from webapp.components.inputs import dropdown_select
from webapp.components.layout import (
    badge_row,
    bordered_container,
    bullet_list,
    data_list,
    data_list_item,
    form_field,
    optional_bullet_list,
    page_layout,
    responsive_grid,
    section_header,
    subsection_header,
)
from webapp.state.playground import StrategyDiscoveryState

_DOMAIN_SCROLL_HEIGHT = 500


def _category_accordion_item(name: str, data: dict) -> rx.Component:
    return rx.accordion.item(
        rx.accordion.header(
            rx.accordion.trigger(
                rx.hstack(
                    rx.text(name, weight="medium"),
                    rx.accordion.icon(),
                    width="100%",
                    justify="between",
                    align="center",
                ),
            ),
        ),
        rx.accordion.content(
            data_list(
                data_list_item("Summary", data["summary"]),
                data_list_item("Use If", bullet_list(data["use_if"])),
                data_list_item(
                    "Example Queries",
                    optional_bullet_list(data["example_queries"]),
                ),
            ),
        ),
        value=name,
    )


def _unit_domain_card(data: AnalysisDomainIndex, domain_key: str) -> rx.Component:
    domain = data.domains[domain_key]
    return rx.vstack(
        section_header(
            title=StrategyDiscoveryState.domain_id_labels[domain_key],
            subtitle=domain.summary,
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Use If", font_weight="bold", color_scheme="green"),
                bullet_list(domain.use_if),
            ),
            rx.vstack(
                rx.text("Avoid When", font_weight="bold", color_scheme="red"),
                bullet_list(domain.avoid_when),
            ),
        ),
        rx.separator(),
        subsection_header("Categories"),
        rx.accordion.root(
            rx.foreach(
                domain.categories.keys(),
                lambda key: _category_accordion_item(
                    name=key,
                    data=domain.categories[key],
                ),
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align_items="stretch",
    )


def _placeholder_domain_card(title: str) -> rx.Component:
    return section_header(title=title, subtitle="Coming soon")


def _strategy_parameters_table() -> rx.Component:
    return rx.cond(
        StrategyDiscoveryState.strategy_parameter_rows.length() > 0,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Name"),
                    rx.table.column_header_cell("Type"),
                    rx.table.column_header_cell("Default"),
                    rx.table.column_header_cell("Range"),
                    rx.table.column_header_cell("Description"),
                )
            ),
            rx.table.body(
                rx.foreach(
                    StrategyDiscoveryState.strategy_parameter_rows,
                    lambda row: rx.table.row(
                        rx.table.row_header_cell(rx.code(row["name"])),
                        rx.table.cell(row["type"]),
                        rx.table.cell(row["default"]),
                        rx.table.cell(row["range"]),
                        rx.table.cell(row["description"]),
                    ),
                )
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        rx.text("No parameters", color_scheme="gray"),
    )


def _strategy_card(data: StrategyDescriptor) -> rx.Component:
    return rx.card(
        rx.vstack(
            # Identity
            subsection_header("Identity"),
            data_list(
                data_list_item("Name", data.name),
                data_list_item("ID", rx.code(data.id)),
                data_list_item(
                    "Category",
                    rx.badge(
                        StrategyDiscoveryState.strategy_category_label,
                        variant="soft",
                        color_scheme="blue",
                    ),
                ),
                data_list_item("Tags", badge_row(data.tags, color_scheme="violet")),
                data_list_item("Summary", data.summary),
            ),
            rx.separator(),
            # When to use
            subsection_header("When to use"),
            data_list(
                data_list_item("Purpose", bullet_list(data.purpose)),
                data_list_item("Best For", bullet_list(data.best_for)),
                data_list_item("Avoid When", bullet_list(data.avoid_when)),
                data_list_item(
                    "Market Regimes",
                    badge_row(
                        StrategyDiscoveryState.strategy_market_regimes,
                        color_scheme="orange",
                    ),
                ),
                data_list_item(
                    "Time Horizons",
                    badge_row(
                        StrategyDiscoveryState.strategy_time_horizons,
                        color_scheme="cyan",
                    ),
                ),
                data_list_item(
                    "Use If",
                    optional_bullet_list(data.decision_guidance.use_if),
                ),
                data_list_item(
                    "Combine With",
                    optional_bullet_list(data.decision_guidance.combine_with),
                ),
            ),
            rx.separator(),
            # Implementation
            subsection_header("Implementation"),
            data_list(
                data_list_item(
                    "Required Columns",
                    badge_row(data.required_columns, color_scheme="gray"),
                ),
                data_list_item(
                    "Output Columns",
                    badge_row(data.output_columns, color_scheme="green"),
                ),
            ),
            rx.vstack(
                rx.text("Parameters", size="2", weight="medium"),
                _strategy_parameters_table(),
                width="100%",
                spacing="2",
                align_items="start",
            ),
            rx.separator(),
            # Guidance
            subsection_header("Guidance"),
            data_list(
                data_list_item("Interpretation", data.interpretation),
                data_list_item("Limitations", bullet_list(data.limitations)),
                data_list_item("LLM Hint", data.llm_hint),
            ),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
    )


def _strategy_empty_state() -> rx.Component:
    return rx.card(
        rx.text(
            "Select a strategy to view details",
            color_scheme="gray",
            size="2",
        ),
        width="100%",
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
                        style={"height": _DOMAIN_SCROLL_HEIGHT},
                    ),
                    rx.scroll_area(
                        rx.card(
                            _placeholder_domain_card("fundamental analysis"),
                        ),
                        type="auto",
                        scrollbars="vertical",
                        style={"height": _DOMAIN_SCROLL_HEIGHT},
                    ),
                    rx.scroll_area(
                        rx.card(
                            _placeholder_domain_card("back testing"),
                        ),
                        type="auto",
                        scrollbars="vertical",
                        style={"height": _DOMAIN_SCROLL_HEIGHT},
                    ),
                    columns=[1, 3, 3],
                )
            ),
            rx.spacer(),
            bordered_container(
                subsection_header("Strategy Detail View"),
                responsive_grid(
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
                            width="100%",
                        ),
                        help_text="Available strategies for the selected category",
                    ),
                    columns=[1, 3, 3],
                ),
                rx.cond(
                    StrategyDiscoveryState.strategy,
                    _strategy_card(StrategyDiscoveryState.strategy),
                    _strategy_empty_state(),
                ),
            ),
        ),
    )
