import json
from datetime import datetime, timezone

import httpx
import reflex as rx

from .model import ExchangeChoice


class State(rx.State):
    """Central app state.

    This is intentionally simple "dummy" logic so you can expand it into
    page-scoped or feature-scoped state as you migrate from Streamlit.
    """

    # Demo data
    counter: int = 0
    name: str = "Investor"
    selected_exchange: str = ExchangeChoice.nse.value

    exchanges: list[str] = [e.value for e in ExchangeChoice]

    # Async demo (httpbin)
    httpbin_is_loading: bool = False
    httpbin_error: str = ""
    httpbin_status_code: int = 0
    httpbin_url: str = ""
    httpbin_origin: str = ""
    httpbin_user_agent: str = ""
    httpbin_response_json: str = ""
    httpbin_last_fetched_utc: str = ""

    # Events
    def increment(self):
        self.counter += 1

    def decrement(self):
        self.counter -= 1

    def reset_counter(self):
        self.counter = 0

    def set_selected_exchange(self, value: str):
        self.selected_exchange = value

    def set_name(self, value: str):
        self.name = value

    @rx.event
    async def fetch_httpbin(self):
        """Async demo: call httpbin using httpx.

        This showcases Reflex async event handlers and server-side IO.
        """

        self.httpbin_is_loading = True
        self.httpbin_error = ""
        self.httpbin_status_code = 0

        try:
            params = {
                "exchange": self.selected_exchange,
                "name": self.name,
                "counter": str(self.counter),
            }
            headers = {"X-StockSense-Demo": "reflex-async-httpx"}

            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(
                    "https://httpbin.org/delay/1",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()

            payload = resp.json() if resp.content else {}
            self.httpbin_status_code = int(resp.status_code)
            self.httpbin_url = str(payload.get("url", ""))
            self.httpbin_origin = str(payload.get("origin", ""))

            payload_headers = payload.get("headers") or {}
            if isinstance(payload_headers, dict):
                self.httpbin_user_agent = str(payload_headers.get("User-Agent", ""))
            else:
                self.httpbin_user_agent = ""

            self.httpbin_response_json = json.dumps(payload, indent=2, sort_keys=True)
            self.httpbin_last_fetched_utc = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # pragma: no cover
            self.httpbin_error = str(exc)
            self.httpbin_response_json = ""
        finally:
            self.httpbin_is_loading = False

    # Derived state
    @rx.var
    def greeting(self) -> str:
        name = (self.name or "Investor").strip() or "Investor"
        return f"Hi {name}. Selected exchange: {self.selected_exchange}. Counter: {self.counter}"  # noqa: E501

    @rx.var
    def has_httpbin_response(self) -> bool:
        return bool(self.httpbin_response_json.strip())
