import reflex as rx

from webapp.components.layout import page_layout


def data() -> rx.Component:
    """Playground → Data page.

    Placeholder while the Streamlit → Reflex migration is in progress.
    """

    return page_layout(
        rx.vstack(
            rx.heading("Data Explorer", size="7"),
            rx.text("This page is being migrated from Streamlit."),
            rx.text("For now, use Home to see central state demo."),
            spacing="3",
            width="100%",
        ),
    )# import os
# import random
# from typing import Any

import reflex as rx

# def _api_base() -> str:
#     # Default matches the VS Code task `stockdb api` (port 8080).
#     return os.getenv("STOCKDB_API_BASE", "http://127.0.0.1:8080").rstrip("/")
# class PlaygroundDataState(rx.State):
#     # Metadata
#     api_base: str = _api_base()
#     is_loading: bool = False
#     error_message: str = ""
#     exchanges: list[dict[str, str]] = []
#     tickers_by_exchange: dict[str, list[dict[str, str]]] = {}
#     # Form state
#     selected_exchange_label: str = ""
#     ticker_choice: str = "Desired"  # Desired | All | Index Based
#     selected_ticker_labels: list[str] = []
#     ticker_picker_label: str = ""
#     interval: str = "1d"
#     period: str = "6mo"
#     sql_query: str = ""
#     # Preview controls
#     preview_enabled: bool = True
#     preview_method: str = "Head"  # Head | Tail | Desired Range | Random
#     preview_n_rows: int = 10
#     preview_start_idx: int = 0
#     preview_end_idx: int = 10
#     # Result data (raw + preview)
#     result_rows: list[dict[str, Any]] = []
#     @rx.var
#     def exchange_options(self) -> list[str]:
#         return [row["dropdown"] for row in self.exchanges]
#     @rx.var
#     def selected_exchange_symbol(self) -> str:
#         return next(
#             (
#                 row["symbol"]
#                 for row in self.exchanges
#                 if row["dropdown"] == self.selected_exchange_label
#             ),
#             "",
#         )
#     @rx.var
#     def ticker_options(self) -> list[str]:
#         if not (exch := self.selected_exchange_symbol):
#             return []
#         return [row["dropdown"] for row in self.tickers_by_exchange.get(exch, [])]
#     @rx.var
#     def resolved_selected_tickers(self) -> list[str]:
#         exch = self.selected_exchange_symbol
#         if not exch:
#             return []
#         all_rows = self.tickers_by_exchange.get(exch, [])
#         if self.ticker_choice == "All":
#             return [row["ticker"] for row in all_rows]
#         if self.ticker_choice == "Index Based":
#             return []
#         selected = set(self.selected_ticker_labels)
#         return [row["ticker"] for row in all_rows if row["dropdown"] in selected]
#     @rx.var
#     def show_ticker_picker(self) -> bool:
#         return self.ticker_choice == "Desired"
#     @rx.var
#     def can_submit(self) -> bool:
#         if not self.selected_exchange_symbol:
#             return False
#         if self.sql_query.strip():
#             return True
#         if self.ticker_choice == "Index Based":
#             return False
#         if self.ticker_choice == "All":
#             return True
#         return len(self.resolved_selected_tickers) > 0
#     @rx.var
#     def has_sql_query(self) -> bool:
#         return bool(self.sql_query.strip())
#     @rx.var
#     def preview_rows(self) -> list[dict[str, Any]]:
#         rows = self.result_rows
#         if not rows:
#             return []
#         if not self.preview_enabled:
#             return rows
#         method = self.preview_method
#         n = max(1, int(self.preview_n_rows))
#         if method == "Head":
#             return rows[:n]
#         if method == "Tail":
#             return rows[-n:]
#         if method == "Desired Range":
#             start = max(0, int(self.preview_start_idx))
#             end = max(start + 1, int(self.preview_end_idx))
#             return rows[start:end]
#         if method == "Random":
#             return rows if len(rows) <= n else random.sample(rows, n)
#         return rows[:n]
#     @rx.var
#     def preview_columns(self) -> list[str]:
#         if not self.preview_rows:
#             return []
#         keys: set[str] = set()
#         for row in self.preview_rows:
#             keys.update(row.keys())
#         return sorted(keys)
#     @rx.event
#     async def load_metadata(self):
#         if self.exchanges and self.tickers_by_exchange:
#             return
#         self.is_loading = True
#         self.error_message = ""
#         try:
#             async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
#                 exch_resp = await client.get(f"{self.api_base}/api/per-security")
#                 exch_resp.raise_for_status()
#                 exch_map: dict[str, str] = exch_resp.json()
#                 self.exchanges = [
#                     {
#                         "symbol": symbol,
#                         "name": name,
#                         "dropdown": f"{name} ({symbol})",
#                     }
#                     for symbol, name in exch_map.items()
#                 ]
#                 self.exchanges.sort(key=lambda r: r["dropdown"].lower())
#                 tick_resp = await client.get(f"{self.api_base}/api/bulk/list-tickers")
#                 tick_resp.raise_for_status()
#                 tick_map: dict[str, list[dict[str, str]] | None] = tick_resp.json()
#                 tickers_by_exchange: dict[str, list[dict[str, str]]] = {}
#                 for exch, rows in tick_map.items():
#                     if not rows:
#                         tickers_by_exchange[exch] = []
#                         continue
#                     tickers_by_exchange[exch] = [
#                         {
#                             "ticker": row.get("ticker", ""),
#                             "company": row.get("company", ""),
#                             "dropdown": f"{row.get('ticker', '')} - {row.get('company', '')}",
#                         }
#                         for row in rows
#                     ]
#                 self.tickers_by_exchange = tickers_by_exchange
#                 if not self.selected_exchange_label and self.exchanges:
#                     self.selected_exchange_label = self.exchanges[0]["dropdown"]
#         except Exception as exc:
#             self.error_message = f"Failed to load StockDB metadata: {exc}"
#         finally:
#             self.is_loading = False
#     @rx.event
#     def on_exchange_change(self, value: str):
#         self.selected_exchange_label = value
#         self.selected_ticker_labels = []
#         self.ticker_picker_label = ""
#         self.result_rows = []
#         self.error_message = ""
#     @rx.event
#     def on_ticker_choice_change(self, value: str):
#         self.ticker_choice = value
#         self.selected_ticker_labels = []
#         self.ticker_picker_label = ""
#         self.result_rows = []
#         self.error_message = ""
#     @rx.event
#     async def set_ticker_picker_label(self, value: str):
#         self.ticker_picker_label = value
#     @rx.event
#     async def add_selected_ticker(self):
#         label = self.ticker_picker_label
#         if not label:
#             return
#         if label not in self.selected_ticker_labels:
#             self.selected_ticker_labels = [*self.selected_ticker_labels, label]
#     @rx.event
#     async def remove_selected_ticker(self, label: str):
#         self.selected_ticker_labels = [
#             t for t in self.selected_ticker_labels if t != label
#         ]
#     @rx.event
#     async def set_interval(self, value: str):
#         self.interval = value
#     @rx.event
#     async def set_period(self, value: str):
#         self.period = value
#     @rx.event
#     async def set_sql_query(self, value: str):
#         self.sql_query = value
#     @rx.event
#     async def set_preview_enabled(self, value: bool):
#         self.preview_enabled = value
#     @rx.event
#     async def set_preview_method(self, value: str):
#         self.preview_method = value
#     @rx.event
#     async def set_preview_n_rows(self, value: str):
#         try:
#             self.preview_n_rows = max(1, int(value))
#         except Exception:
#             self.preview_n_rows = 10
#     @rx.event
#     async def set_preview_start_idx(self, value: str):
#         try:
#             self.preview_start_idx = max(0, int(value))
#         except Exception:
#             self.preview_start_idx = 0
#     @rx.event
#     async def set_preview_end_idx(self, value: str):
#         try:
#             self.preview_end_idx = max(1, int(value))
#         except Exception:
#             self.preview_end_idx = 10
#     @rx.event
#     async def submit(self):
#         self.is_loading = True
#         self.error_message = ""
#         self.result_rows = []
#         exchange = self.selected_exchange_symbol
#         if not exchange:
#             self.error_message = "Please select an exchange."
#             self.is_loading = False
#             return
#         try:
#             async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
#                 if user_sql := self.sql_query.strip():
#                     resp = await client.post(
#                         f"{self.api_base}/api/per-security/{exchange}/query",
#                         json={"sql_query": user_sql},
#                     )
#                     resp.raise_for_status()
#                     rows: list[dict[str, Any]] = resp.json()
#                     self.result_rows = rows
#                     return
#                 if self.ticker_choice == "Index Based":
#                     self.error_message = "Index Based selection is not yet implemented."
#                     return
#                 tickers = self.resolved_selected_tickers
#                 if not tickers:
#                     self.error_message = "Please select at least one ticker."
#                     return
#                 combined: list[dict[str, Any]] = []
#                 for ticker in tickers:
#                     resp = await client.get(
#                         f"{self.api_base}/api/per-security/{exchange}/{ticker}/history",
#                         params={"interval": self.interval, "period": self.period},
#                     )
#                     resp.raise_for_status()
#                     ticker_rows: list[dict[str, Any]] = resp.json()
#                     for row in ticker_rows:
#                         if "ticker" not in row:
#                             row["ticker"] = ticker
#                     combined.extend(ticker_rows)
#                 self.result_rows = combined
#         except httpx.HTTPStatusError as exc:
#             detail = ""
#             try:
#                 detail = f" ({exc.response.json().get('detail')})"
#             except Exception:
#                 detail = ""
#             self.error_message = (
#                 f"StockDB API error: {exc.response.status_code}{detail}"
#             )
#         except Exception as exc:
#             self.error_message = f"Unexpected error: {exc}"
#         finally:
#             self.is_loading = False
# def _sidebar() -> rx.Component:
#     return nav_sidebar(
#         "Playground",
#         [
#             ("Overview", "/playground"),
#             ("Data", "/playground/data"),
#             ("Strategy", "/playground/strategy"),
#         ],
#     )
# def data() -> rx.Component:
#     return rx.box(
#         page_layout_with_sidebar(
#             rx.vstack(
#                 rx.heading("Data Explorer", size="7"),
#                 rx.text("Explore stock data and analytics."),
#                 rx.divider(margin_y="0.75rem"),
#                 rx.heading("Manual Data Query", size="5"),
#                 rx.text("Exchange and Ticker Selection"),
#                 rx.hstack(
#                     rx.vstack(
#                         rx.text("Select Exchange"),
#                         rx.select(
#                             PlaygroundDataState.exchange_options,
#                             value=PlaygroundDataState.selected_exchange_label,
#                             on_change=PlaygroundDataState.on_exchange_change,
#                             placeholder="Select Exchange",
#                             is_disabled=PlaygroundDataState.is_loading,
#                             width="100%",
#                         ),
#                         width="100%",
#                         spacing="2",
#                     ),
#                     rx.vstack(
#                         rx.text("Ticker Selection"),
#                         rx.select(
#                             ["Desired", "All", "Index Based"],
#                             value=PlaygroundDataState.ticker_choice,
#                             on_change=PlaygroundDataState.on_ticker_choice_change,
#                             is_disabled=PlaygroundDataState.is_loading,
#                             width="100%",
#                         ),
#                         width="100%",
#                         spacing="2",
#                     ),
#                     width="100%",
#                     spacing="6",
#                 ),
#                 rx.cond(
#                     PlaygroundDataState.show_ticker_picker,
#                     rx.vstack(
#                         rx.text("Ticker Symbols"),
#                         rx.hstack(
#                             rx.select(
#                                 PlaygroundDataState.ticker_options,
#                                 value=PlaygroundDataState.ticker_picker_label,
#                                 on_change=PlaygroundDataState.set_ticker_picker_label,
#                                 is_disabled=PlaygroundDataState.is_loading,
#                                 width="100%",
#                                 placeholder="Select a ticker to add",
#                             ),
#                             rx.button(
#                                 "Add",
#                                 on_click=PlaygroundDataState.add_selected_ticker,
#                                 is_disabled=PlaygroundDataState.is_loading,
#                                 variant="outline",
#                             ),
#                             width="100%",
#                             spacing="3",
#                             align="end",
#                         ),
#                         rx.cond(
#                             PlaygroundDataState.selected_ticker_labels,
#                             rx.vstack(
#                                 rx.text("Selected:"),
#                                 rx.flex(
#                                     rx.foreach(
#                                         PlaygroundDataState.selected_ticker_labels,
#                                         lambda label: rx.hstack(
#                                             rx.badge(label),
#                                             rx.button(
#                                                 "Remove",
#                                                 size="1",
#                                                 variant="ghost",
#                                                 on_click=PlaygroundDataState.remove_selected_ticker(
#                                                     label
#                                                 ),
#                                             ),
#                                             spacing="2",
#                                             align="center",
#                                         ),
#                                     ),
#                                     wrap="wrap",
#                                     gap="0.5rem",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             rx.callout(
#                                 "Add one or more tickers to run a query.",
#                                 icon="info",
#                                 color_scheme="blue",
#                             ),
#                         ),
#                         spacing="2",
#                         width="100%",
#                     ),
#                     rx.cond(
#                         PlaygroundDataState.ticker_choice == "Index Based",
#                         rx.callout(
#                             "Index Based selection is not yet implemented.",
#                             icon="triangle_alert",
#                             color_scheme="orange",
#                         ),
#                         rx.callout(
#                             "All tickers for the selected exchange will be queried.",
#                             icon="info",
#                             color_scheme="blue",
#                         ),
#                     ),
#                 ),
#                 rx.divider(margin_y="0.75rem"),
#                 rx.heading("Time Range Selection", size="5"),
#                 rx.hstack(
#                     rx.vstack(
#                         rx.text("Data Interval"),
#                         rx.select(
#                             [
#                                 "1d",
#                                 "3d",
#                                 "5d",
#                                 "1wk",
#                                 "3wk",
#                                 "5wk",
#                                 "1mo",
#                                 "3mo",
#                                 "5mo",
#                             ],
#                             value=PlaygroundDataState.interval,
#                             on_change=PlaygroundDataState.set_interval,
#                             is_disabled=PlaygroundDataState.is_loading,
#                             width="100%",
#                         ),
#                         width="100%",
#                         spacing="2",
#                     ),
#                     rx.vstack(
#                         rx.text("Data Period"),
#                         rx.select(
#                             [
#                                 "1mo",
#                                 "3mo",
#                                 "6mo",
#                                 "1y",
#                                 "2y",
#                                 "5y",
#                                 "10y",
#                                 "ytd",
#                                 "max",
#                             ],
#                             value=PlaygroundDataState.period,
#                             on_change=PlaygroundDataState.set_period,
#                             is_disabled=PlaygroundDataState.is_loading,
#                             width="100%",
#                         ),
#                         width="100%",
#                         spacing="2",
#                     ),
#                     width="100%",
#                     spacing="6",
#                 ),
#                 rx.divider(margin_y="0.75rem"),
#                 rx.heading("Custom SQL (Optional)", size="5"),
#                 rx.text(
#                     "If provided, the SQL query is executed directly (overrides the form inputs)."
#                 ),
#                 rx.text_area(
#                     value=PlaygroundDataState.sql_query,
#                     on_change=PlaygroundDataState.set_sql_query,
#                     placeholder="SELECT * FROM ...",
#                     height="10rem",
#                     width="100%",
#                     is_disabled=PlaygroundDataState.is_loading,
#                 ),
#                 rx.hstack(
#                     rx.switch(
#                         PlaygroundDataState.preview_enabled,
#                         on_change=PlaygroundDataState.set_preview_enabled,
#                         is_disabled=PlaygroundDataState.is_loading,
#                     ),
#                     rx.text("Preview Data"),
#                     spacing="2",
#                     align="center",
#                 ),
#                 rx.button(
#                     "Submit",
#                     on_click=PlaygroundDataState.submit,
#                     is_disabled=(~PlaygroundDataState.can_submit)
#                     | PlaygroundDataState.is_loading,
#                 ),
#                 rx.cond(
#                     PlaygroundDataState.error_message != "",
#                     rx.callout(
#                         PlaygroundDataState.error_message,
#                         icon="triangle_alert",
#                         color_scheme="red",
#                     ),
#                     rx.fragment(),
#                 ),
#                 rx.cond(
#                     PlaygroundDataState.is_loading,
#                     rx.text("Loading..."),
#                     rx.fragment(),
#                 ),
#                 rx.cond(
#                     PlaygroundDataState.result_rows,
#                     rx.vstack(
#                         rx.divider(margin_y="0.75rem"),
#                         rx.heading("Query Data Preview", size="5"),
#                         rx.cond(
#                             PlaygroundDataState.has_sql_query,
#                             rx.vstack(
#                                 rx.text("Executed SQL Query:"),
#                                 rx.code_block(
#                                     PlaygroundDataState.sql_query,
#                                     language="sql",
#                                     width="100%",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             rx.fragment(),
#                         ),
#                         rx.hstack(
#                             rx.vstack(
#                                 rx.text("Preview Method"),
#                                 rx.select(
#                                     [
#                                         "Head",
#                                         "Tail",
#                                         "Desired Range",
#                                         "Random",
#                                     ],
#                                     value=PlaygroundDataState.preview_method,
#                                     on_change=PlaygroundDataState.set_preview_method,
#                                     width="100%",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             rx.vstack(
#                                 rx.text("Rows"),
#                                 rx.input(
#                                     value=PlaygroundDataState.preview_n_rows,
#                                     on_change=PlaygroundDataState.set_preview_n_rows,
#                                     type="number",
#                                     min="1",
#                                     max="500",
#                                     width="100%",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             rx.vstack(
#                                 rx.text("Start"),
#                                 rx.input(
#                                     value=PlaygroundDataState.preview_start_idx,
#                                     on_change=PlaygroundDataState.set_preview_start_idx,
#                                     type="number",
#                                     min="0",
#                                     width="100%",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             rx.vstack(
#                                 rx.text("End"),
#                                 rx.input(
#                                     value=PlaygroundDataState.preview_end_idx,
#                                     on_change=PlaygroundDataState.set_preview_end_idx,
#                                     type="number",
#                                     min="1",
#                                     width="100%",
#                                 ),
#                                 width="100%",
#                                 spacing="2",
#                             ),
#                             width="100%",
#                             spacing="6",
#                             align="end",
#                         ),
from webapp.components.layout import page_layout


def data() -> rx.Component:
    """Playground → Data page.

    Placeholder while the Streamlit → Reflex migration is in progress.
    """

    return page_layout(
        rx.vstack(
            rx.heading("Data Explorer", size="7"),
            rx.text("This page is being migrated from Streamlit."),
            rx.text("For now, use Home to see central state demo."),
            spacing="3",
            width="100%",
        ),
    )


#                         rx.cond(
#                             PlaygroundDataState.preview_rows,
#                             rx.data_table(
#                                 data=PlaygroundDataState.preview_rows,
#                                 pagination=True,
#                                 search=True,
#                                 sort=True,
#                                 resizable=True,
#                             ),
#                             rx.text("No preview rows to display."),
#                         ),
#                         width="100%",
#                         spacing="4",
#                     ),
#                     rx.fragment(),
#                 ),
#                 width="100%",
#                 spacing="4",
#             ),
#             sidebar=_sidebar(),
#         ),
#         on_mount=PlaygroundDataState.load_metadata,
#         width="100%",
#     )
