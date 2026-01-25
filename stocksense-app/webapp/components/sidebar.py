from dataclasses import dataclass

import reflex as rx

ICON_SIZE = 18
_ROW_LINE_HEIGHT_STYLE = {"lineHeight": "1"}
_TOP_LEVEL_ROW_STYLE = {
    "padding": "var(--space-3) var(--space-4)",
    **_ROW_LINE_HEIGHT_STYLE,
}
_SUB_LINK_BUTTON_STYLE = {
    "padding": "var(--space-2) var(--space-4)",
    **_ROW_LINE_HEIGHT_STYLE,
}


@dataclass(frozen=True)
class NavLink:
    label: str
    href: str
    icon: str | None = None


@dataclass(frozen=True)
class NavGroup:
    key: str
    label: str
    icon: str
    links: list[NavLink]


APP_NAV: list[NavGroup] = [
    NavGroup(
        key="playground",
        label="Playground",
        icon="joystick",
        links=[
            NavLink("Overview", "/playground", "layout_dashboard"),
            NavLink("Data", "/playground/data", "database"),
            NavLink("Strategy", "/playground/strategy", "candlestick_chart"),
        ],
    ),
    NavGroup(
        key="ai",
        label="AI",
        icon="brain",
        links=[
            NavLink("Overview", "/ai", "layout_dashboard"),
            NavLink("Chat", "/ai/chat", "message_circle"),
            NavLink("Research", "/ai/research", "search"),
        ],
    ),
    NavGroup(
        key="management",
        label="Management",
        icon="settings_2",
        links=[
            NavLink("Overview", "/management", "layout_dashboard"),
            NavLink("Configuration", "/management/configuration", "settings"),
            NavLink("Task", "/management/task", "construction"),
        ],
    ),
]


def _sidebar_link(link: NavLink) -> rx.Component:
    return rx.link(
        rx.button(
            rx.hstack(
                rx.text(link.label, size="3", weight="medium"),
                spacing="2",
                align="center",
                width="100%",
            ),
            variant="ghost",
            width="100%",
            justify_content="flex-start",
            style=_SUB_LINK_BUTTON_STYLE,
        ),
        href=link.href,
        width="100%",
    )


def _top_level_link_row(
    *,
    label: str,
    href: str,
    icon: str | None,
    right: rx.Component | None = None,
) -> rx.Component:
    """Non-collapsible (top-level) sidebar row.

    This is intentionally separate from the accordion so we don't force
    non-group links into accordion semantics.

    Styling uses the same padding tokens as the AccordionTrigger so it
    aligns visually with the group rows.
    """

    right_slot = right or rx.box(width=f"{ICON_SIZE}px", height=f"{ICON_SIZE}px")

    return rx.link(
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.text(label, weight="medium"),
                    align="center",
                    spacing="2",
                ),
                # Placeholder matches the chevron space in accordion triggers.
                right_slot,
                justify="between",
                align="center",
                width="100%",
            ),
            width="100%",
            style=_TOP_LEVEL_ROW_STYLE,
        ),
        href=href,
        width="100%",
    )


def _home_row() -> rx.Component:
    return _top_level_link_row(label="Home", href="/", icon="home")


def _group_item(group: NavGroup) -> rx.Component:
    return rx.accordion.item(
        rx.accordion.trigger(
            rx.hstack(
                rx.text(group.label, weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.accordion.icon(size=ICON_SIZE),
        ),
        rx.accordion.content(
            rx.vstack(
                *[_sidebar_link(link) for link in group.links],
                spacing="2",
                width="100%",
                align="stretch",
            ),
        ),
        value=group.key,
    )


def nav_sidebar(
    *,
    default_open_group: str | None = None,
    groups: list[NavGroup] | None = None,
    top_links: list[NavLink] | None = None,
) -> rx.Component:
    """Grouped, collapsible sidebar navigation."""

    groups = APP_NAV if groups is None else groups
    open_key = default_open_group or "playground"

    # Future-proofing: allow other non-group rows above the accordion.
    top_links = [NavLink("Home", "/", "home")] if top_links is None else top_links

    accordion_items: list[rx.Component] = [_group_item(group) for group in groups]

    return rx.card(
        rx.vstack(
            *[
                _top_level_link_row(label=link.label, href=link.href, icon=link.icon)
                for link in top_links
            ],
            rx.accordion.root(
                *accordion_items,
                type="single",
                collapsible=True,
                default_value=open_key,
                variant="ghost",
                show_dividers=True,
                width="100%",
            ),
            width="100%",
            spacing="2",
            align="stretch",
        ),
        width="100%",
        padding="0.75rem",
        position="sticky",
        top="4.5rem",
    )
