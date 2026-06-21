from typing import Any

import polars as pl
from agno.exceptions import RetryAgentRun
from agno.run import RunContext
from agno.tools import Toolkit
from httpx2 import AsyncClient, HTTPStatusError
from stocksense.config import get_settings
from stocksense.strategy.catalog import (
    AnalysisDomainTypes,
    StrategyCategoryTypes,
)
from stocksense.strategy.catalog.registry import (
    filter_strategies,
    get_registry,
)

settings = get_settings()


def _ensure_session_state(run_context: RunContext) -> dict[str, Any]:
    """Ensure session_state is initialized and return it.

    Args:
        run_context: The agent's run context

    Returns:
        The initialized session_state dictionary
    """
    if run_context.session_state is None:
        run_context.session_state = {}
    return run_context.session_state


# required keys for discovery
_ANALYSIS_DOMAIN_DISCOVERY_FIELDS = {
    "domains": {
        "__all__": {  # to include all domains
            # NOTE - below keys are wrt to unit domain
            "id",
            "summary",
            "use_if",
            "avoid_when",
            "categories",
        }
    }
}
_STRATEGY_CATEGORY_DISCOVERY_FIELDS = {
    "strategies": {
        "__all__": {
            "id",
            "name",
            "category",
            "summary",
            "purpose",
        }
    }
}


# setting session_state keys globally
SELECTED_DOMAIN_KEY = "selected_domain"
SELECTED_CATEGORY_KEY = "selected_category"
SELECTED_STRATEGY_KEY = "selected_strategy"

# Session state keys for company context
EXCHANGE_KEY = "exchange"
TICKER_KEY = "ticker"
COMPANY_INFO_KEY = "company_info_cache"


class StrategyDiscoveryTools(Toolkit):
    """
    Toolkit that lets an Agent progressively discover and select:
        1. An Analysis Domain (e.g. --> technical analysis)
        2. A Strategy Category (e.g. --> momentum)
        3. A concrete Strategy (e.g. --> momentum.rsi)
    """

    def __init__(self, **kwargs):
        self._registry = get_registry()

        tools = [
            self.list_analysis_domains,
            self.select_analysis_domain,
            self.list_strategy_categories,
            self.select_strategy_category,
            self.list_strategies_in_selection,
            self.select_strategy,
            self.get_strategy_details,
        ]

        super().__init__(
            name="strategy_discovery_tools",
            tools=tools,
            **kwargs,
        )

    def list_analysis_domains(self) -> dict[str, Any]:
        """List all available analysis domains with their summaries and the
        situations they are best suited for. Call this FIRST when you do
        not yet know which analysis domain fits the user's question.

        Returns:
            A dictionary containing domain descriptors with id, summary, use_if, avoid_when, categories, etc
        """
        return self._registry.domains.model_dump(
            mode="json", include=_ANALYSIS_DOMAIN_DISCOVERY_FIELDS
        )

    def select_analysis_domain(
        self,
        domain: str,
        run_context: RunContext,
    ) -> str:
        """Record which analysis domain you have chosen for this user query.
        You MUST call this after deciding the domain, before exploring strategy categories.

        Args:
            domain (str): The domain id, e.g. "technical analysis".
            run_context (RunContext): The run context containing dependencies (automatically provided)

        Returns:
            A message confirming the selected domain
        """
        normalized = domain.strip().lower().replace("_", " ").replace("-", " ")
        normalized = " ".join(normalized.split())  # collapse repeated spaces

        if not normalized:
            valid = ", ".join(d.value for d in AnalysisDomainTypes)
            raise RetryAgentRun(f"Domain cannot be empty. Valid values: {valid}.")
        try:
            chosen = AnalysisDomainTypes(normalized)
        except ValueError as e:
            valid = ", ".join(d.value for d in AnalysisDomainTypes)
            # Letting the model know about its mistake
            raise RetryAgentRun(
                f"Invalid domain '{domain}'. Valid values: {valid}."
            ) from e

        session_state = _ensure_session_state(run_context)

        current = session_state.get(SELECTED_DOMAIN_KEY)
        if current == chosen.value:
            return f"Analysis domain already set to '{chosen.value}'."

        # Clear downstream selections if the user pivots
        session_state[SELECTED_DOMAIN_KEY] = chosen.value
        session_state.pop(SELECTED_CATEGORY_KEY, None)
        session_state.pop(SELECTED_STRATEGY_KEY, None)
        return f"Analysis domain set to '{chosen.value}'."

    def list_strategy_categories(
        self,
        run_context: RunContext,
    ) -> list[dict[str, Any]] | str:
        """List the strategy categories that belong to the previously selected
        analysis domain. Call select_analysis_domain first.

        Args:
            run_context (RunContext): The run context containing dependencies (automatically provided)

        Returns:
            A list of category descriptors with summary, use_if, example_queries, etc.
        """
        session_state = _ensure_session_state(run_context)

        domain_value = session_state.get(SELECTED_DOMAIN_KEY)
        if domain_value is None:
            raise RetryAgentRun(
                "No analysis domain selected yet. Call select_analysis_domain first."
            )

        return [
            i.model_dump(mode="json", include=_STRATEGY_CATEGORY_DISCOVERY_FIELDS)
            for i in self._registry.strategy_catalogs
            if i.domain == AnalysisDomainTypes(domain_value)
        ]

    def select_strategy_category(
        self,
        category: str,
        run_context: RunContext,
    ) -> str:
        """Record which strategy category you have chosen. Must be called after select_analysis_domain.

        Args:
            category (str): The category id, e.g. "momentum", "trend".
            run_context (RunContext): The run context containing dependencies (automatically provided)

        Returns:
            A message confirming the selected category
        """
        session_state = _ensure_session_state(run_context)

        if SELECTED_DOMAIN_KEY not in session_state:
            raise RetryAgentRun("Select an analysis domain first.")

        try:
            chosen = StrategyCategoryTypes(category.strip().lower())
        except ValueError as e:
            valid = ", ".join(c.value for c in StrategyCategoryTypes)
            # Letting the model know about its mistake
            raise RetryAgentRun(
                f"Invalid category '{category}'. Valid values: {valid}."
            ) from e

        session_state[SELECTED_CATEGORY_KEY] = chosen.value
        session_state.pop(SELECTED_STRATEGY_KEY, None)
        return f"Strategy category set to '{chosen.value}'."

    def list_strategies_in_selection(
        self,
        run_context: RunContext,
    ) -> list[dict[str, Any]] | str:
        """List candidate strategies that match the previously selected analysis domain
        and category. Use this to decide which strategy fits the user's question best.

        Args:
            run_context (RunContext): The run context containing dependencies (automatically provided)

        Returns:
            A list of serialized dictionary representations of filtered
            strategies or a string error message if applicable.
        """
        session_state = _ensure_session_state(run_context)

        domain_value = session_state.get(SELECTED_DOMAIN_KEY)
        category_value = session_state.get(SELECTED_CATEGORY_KEY)

        if domain_value is None or category_value is None:
            # Letting the model know about its mistake
            raise RetryAgentRun(
                "Need both an analysis domain and a strategy category "
                "selected before listing strategies."
            )

        candidates = filter_strategies(
            domain=domain_value,
            category=category_value,
        )

        # Return only the fields the LLM needs to choose. Keep it compact.
        return [i.model_dump(mode="json") for i in candidates]

    def select_strategy(
        self,
        strategy_id: str,
        run_context: RunContext,
    ) -> str:
        """Record the final strategy chosen for the user's question.

        Args:
            strategy_id (str): Full strategy id, e.g. "momentum.rsi".
            run_context (RunContext): The run context containing dependencies (automatically provided)

        Returns:
            A message confirming the selected strategy
        """
        if strategy_id not in self._registry.by_id:
            raise RetryAgentRun(f"Unknown strategy_id '{strategy_id}'.")

        session_state = _ensure_session_state(run_context)

        session_state[SELECTED_STRATEGY_KEY] = strategy_id
        return f"Strategy '{strategy_id}' selected."

    def get_strategy_details(self, strategy_id: str) -> dict[str, Any] | str:
        """Return the full descriptor for a strategy id, including parameters,
        interpretation, decision guidance, and limitations.

        Args:
            strategy_id (str): Full strategy id, e.g. "momentum.rsi".

        Returns:
            A dictionary with strategy details or a string error message if applicable.
        """
        strategy = self._registry.by_id.get(strategy_id)
        if strategy is None:
            raise RetryAgentRun(f"Unknown strategy_id '{strategy_id}'")
        return strategy.model_dump(mode="json")


class StockDBTools(Toolkit):
    """Tools for interacting with the StockDB API."""

    def __init__(self, **kwargs):
        self.stockdb_api_base_url = (
            f"{settings.common.base_url}:{settings.stockdb.port}/api"
        )
        self._aclient = AsyncClient(
            base_url=self.stockdb_api_base_url,
            timeout=None,
        )
        async_tools = [
            (self.get_company_exchange_and_ticker, "get_company_exchange_and_ticker"),
            (self.list_exchange, "list_exchanges"),
            (self.get_company_information, "get_company_information"),
        ]
        tools = [
            self.current_company_context,
            self.set_company_context,
        ]
        super().__init__(
            name="stockdb_tools", tools=tools, async_tools=async_tools, **kwargs
        )

    def current_company_context(self, run_context: RunContext) -> str:
        """Use this tool to get the current company context from the session state.

        Args:
            run_context (RunContext): The run context (automatically provided)

        Returns:
            str: The current company context
        """
        session_state = _ensure_session_state(run_context)
        if run_context.dependencies is None:
            run_context.dependencies = {}

        # 1st check in session state
        exch = session_state.get(EXCHANGE_KEY)
        tkr = session_state.get(TICKER_KEY)

        if exch and tkr:
            return f"Current company context: Exchange={exch}, Ticker={tkr}"

        # 2nd check in dependencies
        exch = run_context.dependencies.get("exchange")
        tkr = run_context.dependencies.get("ticker")
        # Adding in session state if found in dependencies
        if exch and tkr:
            session_state[EXCHANGE_KEY] = exch.lower()
            session_state[TICKER_KEY] = tkr.lower()
            return f"Current company context: Exchange={exch}, Ticker={tkr}"
        else:
            raise RetryAgentRun(
                "Could not find company context in session state or dependencies. Use tool set_company_context to set it."
            )

    def set_company_context(
        self,
        exchange: str,
        ticker: str,
        run_context: RunContext,
    ) -> str:
        """Set the exchange and ticker for the current company analysis session.
        Use this when the user specifies a company in their message.

        Args:
            exchange (str): The exchange (e.g., "nse", "bse")
            ticker (str): The ticker symbol (e.g., "tcs", "reliance")
            run_context (RunContext): The run context (automatically provided)

        Returns:
            str: Confirmation message
        """
        session_state = _ensure_session_state(run_context)

        session_state[EXCHANGE_KEY] = exchange.lower()
        session_state[TICKER_KEY] = ticker.lower()
        return f"Company context set to {ticker.upper()} on {exchange.upper()}"

    async def list_exchange(self) -> list[str]:
        """Use this tool to list all available exchanges

        Returns:
            list[str]: A list of exchanges.
        """
        response = await self._aclient.get("/per-security/")
        return response.json()

    async def get_company_exchange_and_ticker(
        self, company_name: str
    ) -> dict[str, str]:
        """Use this tool to get the respective exchange and ticker for a given company name.

        Args:
            company_name (str): The name of the company.

        Returns:
            dict[str, str]: A dictionary with the exchange and ticker.
        """
        response = await self._aclient.get("/bulk/list-tickers")
        flattened = [
            {
                "exchange": exchange,
                "ticker": item["ticker"],
                "company_name": item["company"],
            }
            for exchange, items in response.json().items()
            for item in items
        ]

        df = pl.DataFrame(flattened)
        words = company_name.lower().split()
        if (
            result := df
            .filter(
                pl.all_horizontal([
                    pl.col("company_name").str.to_lowercase().str.contains(word)
                    for word in words
                ])
            )
            .select(["exchange", "ticker", "company_name"])
            .to_dicts()
        ):
            return result[0]
        else:
            raise RetryAgentRun("Company name not found")

    async def get_company_information(
        self,
        run_context: RunContext,
        exchange: str | None = None,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """Get company data & information.

        - For the CURRENT/main company: call with NO arguments. The exchange and
          ticker are taken from the session context.
        - For ANOTHER company (e.g. during a comparison): pass `exchange` and
          `ticker` explicitly. Resolve them first with
          `get_company_exchange_and_ticker` if you only have the company name.

        If the result contains `"_cached": true`, you already have this company's
        data in context — do NOT call this tool again for it.

        Args:
            exchange (str | None): Optional. Defaults to the session's exchange.
            ticker (str | None): Optional. Defaults to the session's ticker.

        Returns:
            dict[str, Any]: The company data.
        """
        session_state = _ensure_session_state(run_context)

        # Explicit args win; otherwise fall back to session context
        exchange = exchange or session_state.get(EXCHANGE_KEY)
        ticker = ticker or session_state.get(TICKER_KEY)

        if not exchange or not ticker:
            raise RetryAgentRun(
                "Exchange and ticker are required. Pass them explicitly, or set "
                "the current company with set_company_context tool first."
            )

        exchange = exchange.lower()
        ticker = ticker.lower()
        cache_key = f"{exchange}:{ticker}"

        # Short-circuit: return cached data without another API/token round-trip
        cache = session_state.get(COMPANY_INFO_KEY) or {}
        if cache_key in cache:
            # Data already in conversation history — return a pointer, not the payload
            return {
                "_cached": True,
                "message": (
                    f"{ticker.upper()} on {exchange.upper()} was already fetched in this "
                    f"conversation. Reuse the existing data; do not call this tool again."
                ),
            }

        try:
            response = await self._aclient.get(
                f"/per-security/{exchange}/{ticker}/info"
            )
            response.raise_for_status()
            data = response.json()

            # Empty/short response => bad ticker
            if len(data) < 2:
                raise RetryAgentRun(f"Ticker symbol {ticker} is incorrect")

            # Data will remain in history; marking only as cached in session state
            cache[cache_key] = True
            session_state[COMPANY_INFO_KEY] = cache

            return data
        except HTTPStatusError as e:
            try:
                err_detail = response.json()
            except Exception:
                err_detail = response.text or str(e)
            raise RetryAgentRun(
                f"Failed to get company information due to: {err_detail}"
            ) from e
