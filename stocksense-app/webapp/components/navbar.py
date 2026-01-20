import reflex as rx


def _brand() -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.image(
                src="/favicon.ico",
                width="1.75rem",
                height="1.75rem",
                border_radius="0.5rem",
            ),
            rx.heading("Stocksense", size="5", weight="bold"),
            align="center",
            spacing="3",
        ),
        href="/",
        style={"textDecoration": "none"},
    )


def _navbar_center_item(label: str, icon: str, href: str) -> rx.Component:
    active = rx.State.router.page.path == href
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label, size="3", weight="medium"),
            spacing="2",
            align="center",
        ),
        href=href,
        padding="0.5em 1em",
        border_radius="999px",
        background_color=rx.cond(active, rx.color("accent", 3), "transparent"),
        color=rx.cond(active, rx.color("accent", 11), rx.color("gray", 11)),
        _hover={
            "background_color": rx.cond(
                active, rx.color("accent", 4), rx.color("gray", 3)
            ),
            "text_decoration": "none",
        },
        style={"textDecoration": "none", "transition": "all 150ms ease"},
    )


def navbar() -> rx.Component:
    """Modern top navbar.

    - Brand (logo + name) on the left
    - Primary pages centered
    - Utility actions on the right
    """
    center_nav = rx.hstack(
        _navbar_center_item("Home", "home", "/"),
        _navbar_center_item("Playground", "joystick", "/playground"),
        _navbar_center_item("AI", "brain", "/ai"),
        _navbar_center_item("Management", "settings_2", "/management"),
        spacing="1",
        align="center",
        display={"base": "none", "md": "flex"},
    )

    return rx.box(
        rx.hstack(
            _brand(),
            # Spacer pushes content to center/right
            rx.spacer(),
            center_nav,
            # Spacer pushes content to right
            rx.spacer(),
            rx.hstack(
                rx.color_mode.button(),
                spacing="4",
                align="center",
            ),
            align="center",
            width="100%",
            max_width="1400px",
            margin_x="auto",
            padding_x="1.5em",
        ),
        bg=rx.color("gray", 2),
        border_bottom=f"1px solid {rx.color('gray', 4)}",
        position="sticky",
        top="0px",
        z_index="50",
        width="100%",
        padding_y="0.75em",
    )
