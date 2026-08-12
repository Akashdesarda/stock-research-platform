import reflex as rx
from stocksense.strategy.catalog import AnalysisDomainIndex, StrategyDescriptor

from webapp.components.inputs import dropdown_select
from webapp.components.layout import (
    accordion_item,
    badge_row,
    bullet_list,
    data_list,
    data_list_item,
    detail_section,
    dict_table,
    empty_state_card,
    form_field,
    labeled_bullet_columns,
    optional_bullet_list,
    responsive_grid,
    scrollable_card,
    section_header,
    subsection_header,
)
from webapp.state.playground import StrategyDiscoveryState

_DOMAIN_SCROLL_HEIGHT = 500

_PARAMETER_COLUMNS = (
    ("name", "Name"),
    ("type", "Type"),
    ("default", "Default"),
    ("range", "Range"),
    ("description", "Description"),
)


def _category_accordion_item(name: str, data: dict) -> rx.Component:
    return accordion_item(
        name,
        data_list(
            data_list_item("Summary", data["summary"]),
            data_list_item("Use If", bullet_list(data["use_if"])),
            data_list_item(
                "Example Queries",
                optional_bullet_list(data["example_queries"]),
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
        labeled_bullet_columns(
            ("Use If", domain.use_if, "green"),
            ("Avoid When", domain.avoid_when, "red"),
        ),
        rx.separator(),
        subsection_header("Categories", size="3"),
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
        spacing="6",
        width="100%",
        align_items="stretch",
    )


def _placeholder_domain_card(title: str) -> rx.Component:
    return section_header(title=title, subtitle="Coming soon")


def _strategy_card(data: StrategyDescriptor) -> rx.Component:
    return rx.card(
        rx.vstack(
            detail_section(
                "Identity",
                data_list(
                    data_list_item("Name", data.name),
                    data_list_item("ID", rx.code(data.id)),
                    data_list_item(
                        "Category",
                        rx.code(StrategyDiscoveryState.strategy_category_label),
                    ),
                    data_list_item("Tags", badge_row(data.tags, color_scheme="violet")),
                    data_list_item("Summary", data.summary),
                ),
                separator=True,
            ),
            detail_section(
                "When to use",
                data_list(
                    data_list_item("Purpose", bullet_list(data.purpose)),
                    data_list_item("Best For", bullet_list(data.best_for)),
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
                        "Combine With",
                        badge_row(
                            data.decision_guidance.combine_with,
                            color_scheme="violet",
                        ),
                    ),
                ),
                labeled_bullet_columns(
                    ("Use If", data.decision_guidance.use_if, "green"),
                    ("Avoid When", data.avoid_when, "red"),
                ),
                separator=True,
            ),
            detail_section(
                "Implementation",
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
                    dict_table(
                        _PARAMETER_COLUMNS,
                        StrategyDiscoveryState.strategy_parameter_rows,
                        empty="No parameters",
                        code_keys=("name",),
                    ),
                    width="100%",
                    spacing="2",
                    align_items="start",
                ),
                separator=True,
            ),
            detail_section(
                "Guidance",
                data_list(
                    data_list_item("Interpretation", data.interpretation),
                    data_list_item("Limitations", bullet_list(data.limitations)),
                    data_list_item("LLM Hint", data.llm_hint),
                ),
            ),
            spacing="4",
            width="100%",
            align_items="stretch",
        ),
        width="100%",
        padding="4",
    )


def _strategy_filters() -> rx.Component:
    return responsive_grid(
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
    )


def _domain_overview_section() -> rx.Component:
    # return bordered_container(
    return responsive_grid(
        scrollable_card(
            _unit_domain_card(
                StrategyDiscoveryState.analysis_domain,
                "technical_analysis",
            ),
            height=_DOMAIN_SCROLL_HEIGHT,
        ),
        scrollable_card(
            _placeholder_domain_card("Fundamental Analysis"),
            height=_DOMAIN_SCROLL_HEIGHT,
        ),
        scrollable_card(
            _placeholder_domain_card("Back Testing"),
            height=_DOMAIN_SCROLL_HEIGHT,
        ),
        columns=[1, 3, 3],
    )
    # )


def _strategy_detail_section() -> rx.Component:
    return rx.vstack(
        subsection_header("Strategy Detail View"),
        _strategy_filters(),
        rx.cond(
            StrategyDiscoveryState.strategy,
            _strategy_card(StrategyDiscoveryState.strategy),
            empty_state_card("Select a strategy to view details"),
        ),
        spacing="4",
        width="100%",
    )


def discovery_panel() -> rx.Component:
    return rx.vstack(
        _domain_overview_section(),
        _strategy_detail_section(),
        spacing="8",
        width="100%",
    )
