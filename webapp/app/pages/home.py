import streamlit as st

from app.config import Settings
from app.core.utils import get_available_exchanges, rest_request_sync

settings = Settings()


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
    col1, col2 = st.columns(2)
    with col1:
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=get_available_exchanges().select("symbol").to_series().to_list(),
            label_visibility="collapsed",
        )
        status = check_service_status(
            f"{settings.common.base_url}:{settings.stockdb.port}/health/data/{selected_exchange}"
        )
    with col2:
        if status:
            # Available - Green badge with OK text
            st.badge("OK", color="green")
        else:
            # Not available - Red badge with ERROR text
            st.badge("Outdated", icon=":material/error:", color="red")

# TODO - Add home page description content and useful links
