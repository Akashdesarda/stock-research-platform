import reflex as rx

from webapp.components.layout import page_layout

from ._company_summary import company_summary_component


def research() -> rx.Component:
    return page_layout(company_summary_component())
