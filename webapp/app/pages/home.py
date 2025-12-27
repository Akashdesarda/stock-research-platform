import os

import streamlit as st
from stocksense.config import get_settings

from app.core.utils import rest_request_sync

settings = get_settings(os.getenv("CONFIG_FILE"))


# Adding service status check in sidebar
def check_service_status(service_url: str) -> bool:
    """Simple service status check using existing utilities"""
    try:
        response = rest_request_sync(service_url, method="GET", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# SECTION - Sidebar for various service status checks
with st.sidebar:
    st.markdown("## Service Status")
    services = {
        # NOTE - add other services as needed
        "StockDB API": f"{settings.common.base_url}:{settings.stockdb.port}/health/api",
    }
    for service_name, service_url in services.items():
        status = check_service_status(service_url)

        # Display service name and status badge
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(service_name)

        with col2:
            if status:
                # Available - Green badge with OK text
                st.badge("OK", color="green")
            else:
                # Not available - Red badge with ERROR text
                st.badge("Not Available", icon=":material/error:", color="red")

    st.markdown("## Data Status")
    # Display service name and status badge
    col1, col2 = st.columns([1.5, 1], vertical_alignment="center")
    with col1:
        status = rest_request_sync(
            f"{settings.common.base_url}:{settings.stockdb.port}/health/data/"
        ).json()
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=status.keys(),
            label_visibility="collapsed",
        )
    with col2:
        if status[selected_exchange] == "OK":
            # Available - Green badge with OK text
            st.badge("OK", color="green")
        elif status[selected_exchange] == "OUTDATED":
            # Outdated - orange badge with Outdated text
            st.badge("Outdated", icon=":material/warning:", color="orange")
        else:
            # Not available - Red badge with ERROR text
            st.badge("No Data", icon=":material/error:", color="red")

# TODO - Add home page description content and useful links
