import streamlit as st

from app.core.utils import rest_request_sync


# Adding service status check in sidebar
def check_service_status(service_name: str, service_url: str) -> bool:
    """Simple service status check using existing utilities"""
    try:
        response = rest_request_sync(service_url, method="GET", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


with st.sidebar:
    st.markdown("## Service Status")
    services = {
        # NOTE - add other services as needed
        "StockDB API": "http://localhost:8000",
    }
    for service_name, service_url in services.items():
        status = check_service_status(service_name, service_url)

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
                st.badge("", icon=":material/error:", color="red")
