"""
StockSense Stock Research Platform - Streamlit Web Application
Entry point for the multi-page Streamlit app.
"""

from pathlib import Path

import streamlit as st
from app import setup

setup()
logo = Path(__file__).parent / "static/chart-growth-invest.svg"
title = "StockSense: AI Powered Stock Research Platform"
css = """
body {
    -webkit-font-smoothing: antialiased;
}
"""

st.html(f"<style>{css}</style>")
st.logo(logo)
st.set_page_config(
    page_icon=logo,
    page_title=title,
    layout="wide",
    initial_sidebar_state="expanded",
)
# Title
# st.markdown(f"# {title}")

# Define pages with programmatic navigation
home = st.Page("app/pages/home.py", title="Home", icon=":material/house:")
# Playground Section
data = st.Page(
    "app/pages/playground/data.py",
    title="Data Explore",
    icon=":material/data_exploration:",
)
strategy = st.Page(
    "app/pages/playground/strategy.py",
    title="Strategy",
    icon=":material/candlestick_chart:",
)
# AI Section
chat = st.Page("app/pages/ai/chat.py", title="Chat", icon=":material/chat:")  # "💬")
research = st.Page(
    "app/pages/ai/research.py", title="Research", icon=":material/query_stats:"
)

# Management Section
config_management = st.Page(
    "app/pages/management/configuration.py",
    title="Configuration",
    icon=":material/settings:",
)
task_management = st.Page(
    "app/pages/management/task.py",
    title="Task Management",
    icon=":material/construction:",
)


# Create navigation
pg = st.navigation(
    pages={
        "Home": [home],
        "Playground": [data, strategy],
        "AI": [chat, research],
        "Settings & Management": [config_management, task_management],
    },
    expanded=True,
)

# Run the selected page
pg.run()
