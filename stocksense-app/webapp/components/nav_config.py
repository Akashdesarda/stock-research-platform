from dataclasses import dataclass


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
            NavLink("Data", "/playground/data", "database"),
            NavLink("Strategy", "/playground/strategy", "candlestick_chart"),
        ],
    ),
    NavGroup(
        key="ai",
        label="AI",
        icon="brain",
        links=[
            NavLink("Chat", "/ai/chat", "message_circle"),
            NavLink("Research", "/ai/research", "search"),
        ],
    ),
    NavGroup(
        key="management",
        label="Management",
        icon="settings_2",
        links=[
            NavLink("Configuration", "/management/configuration", "settings"),
            NavLink("Task", "/management/task", "construction"),
        ],
    ),
]
