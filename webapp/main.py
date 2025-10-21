"""
StockSense Stock Research Platform - Streamlit Web Application
Entry point for the multi-page Streamlit app.
"""

from pathlib import Path
import streamlit as st

logo = Path(__file__).parent / "static/chart-growth-invest.svg"
title = "StockSense: AI Research Platform"
css = """
body {
    -webkit-font-smoothing: antialiased;
}
"""

st.html(f"<style>{css}</style>")
st.logo(logo)
st.title(title)
st.set_page_config(
    page_title=title,
    page_icon=logo,
    layout="wide",
    initial_sidebar_state="expanded",
)

    # Define pages with programmatic navigation

home = st.Page("app/pages/home.py", title="Home", icon=":material/house:")#"🏠")
# Playground Section
data = st.Page("app/pages/playground/data.py", title="Data Explore", icon=":material/data_exploration:")#"🎯")
strategy = st.Page("app/pages/playground/strategy.py", title="Strategy", icon=":material/candlestick_chart:")#"💼")
chat = st.Page("app/pages/ai/chat.py", title="Chat", icon=":material/chat:")#"💬")
research = st.Page("app/pages/ai/research.py", title="Research", icon=":material/query_stats:")#"🔍"


# Create navigation
pg = st.navigation(
    pages={
        "Home": [home],
        "Playground": [data, strategy],
        "AI": [chat, research],
    },
    expanded=True
)

# Run the selected page
pg.run()
