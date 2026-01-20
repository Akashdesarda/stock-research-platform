from dataclasses import dataclass

import reflex as rx


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
            NavLink(
                "New Configuration",
                "/management/task/new-configuration",
                "plus",
            ),
        ],
    ),
]


def _sidebar_link(link: NavLink) -> rx.Component:
    icon = rx.icon(link.icon, size=18) if link.icon else rx.fragment()

    return rx.link(
        rx.button(
            rx.hstack(
                icon,
                rx.text(link.label, size="3", weight="medium"),
                spacing="2",
                align="center",
                width="100%",
            ),
            variant="ghost",
            width="100%",
            justify_content="flex-start",
            style={"padding": "var(--space-2) var(--space-4)", "lineHeight": "1"},
        ),
        href=link.href,
        width="100%",
    )


def nav_sidebar(
    *,
    default_open_group: str | None = None,
    groups: list[NavGroup] | None = None,
) -> rx.Component:
    """Grouped, collapsible sidebar navigation.

    - Groups map to top navbar items (Playground/AI/Management)
    - Each group expands/collapses
    - Links are styled like vertical tabs
    """

    groups = groups or APP_NAV

    open_key = default_open_group or "playground"

    accordion_items: list[rx.Component] = [
        rx.accordion.item(
            rx.accordion.trigger(
                rx.hstack(
                    rx.icon(group.icon, size=18),
                    rx.text(group.label, weight="medium"),
                    align="center",
                    spacing="2",
                ),
                rx.accordion.icon(size=18),
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
        for group in groups
    ]

    return rx.card(
        rx.vstack(
            rx.link(
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.icon("home", size=18),
                            rx.text("Home", weight="medium"),
                            align="center",
                            spacing="2",
                        ),
                        # Placeholder to match the chevron space in accordion triggers.
                        rx.box(width="18px", height="18px"),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    width="100%",
                    style={
                        # Match AccordionTrigger default spacing
                        "padding": "var(--space-3) var(--space-4)",
                        "lineHeight": "1",
                    },
                ),
                href="/",
                width="100%",
            ),
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
