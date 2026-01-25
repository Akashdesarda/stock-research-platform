import reflex as rx
from httpx import AsyncClient
from stocksense.config import get_settings

from .shared import CommonMixin

settings = get_settings()


class HomeState(CommonMixin, rx.State):
    """State for the home page"""

    # UI State
    selected_status_exchange: str = ""

    # Status State (populated by event)
    stockdb_api: bool = False
    stockdb_data_status: dict[str, str] = {}

    @rx.event
    def set_selected_status_exchange(self, value: str):
        self.selected_status_exchange = value

    @rx.event
    async def check_input_status(self):
        """Check the status of services and data availability."""
        try:
            async with AsyncClient() as client:
                # 1. Check API Health
                api_resp = await client.get(
                    f"{settings.common.base_url}:{settings.stockdb.port}/health/api",
                    timeout=5,
                    follow_redirects=True,
                )
                self.stockdb_api = api_resp.status_code == 200

                # 2. Check Data Health
                data_resp = await client.get(
                    f"{settings.common.base_url}:{settings.stockdb.port}/health/data/",
                    timeout=20,  # Increased timeout for data scan
                    follow_redirects=True,
                )

                if data_resp.status_code == 200:
                    self.stockdb_data_status = data_resp.json()
                else:
                    self.stockdb_data_status = {}

        except Exception:
            self.stockdb_api = False
            self.stockdb_data_status = {}

        # 3. Set default selection if needed
        if not self.selected_status_exchange and self.stockdb_data_status:
            # Select the first available exchange key by default
            self.selected_status_exchange = list(self.stockdb_data_status.keys())[0]

    @rx.var
    def data_exchange_options(self) -> list[str]:
        return list(self.stockdb_data_status.keys())

    @rx.var
    def selected_exchange_status(self) -> str:
        return self.stockdb_data_status.get(self.selected_status_exchange, "")
