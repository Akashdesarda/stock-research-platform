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
    StrategyDescriptor,
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


# Strategy descriptor field partitions

# Fields the model needs to CHOOSE between candidates. Kept deliberately small:
# a shortlist can span a whole category, and a category may hold 100+ strategies.
# `llm_hint` is authored precisely as prefer/avoid selection guidance.
_SHORTLIST_FIELDS = {"name", "llm_hint"}

# Carried as dict keys in tool responses, never repeated inside the values.
_KEY_FIELDS = {"id", "category"}

# Everything else. Derived by subtraction so the two views can never overlap and
# new descriptor fields are picked up automatically. To give the model more or
# less to chew on while shortlisting, move a field into or out of
# _SHORTLIST_FIELDS -- it lands in the other view with no further edits.
_DETAIL_FIELDS = set(StrategyDescriptor.model_fields) - _SHORTLIST_FIELDS - _KEY_FIELDS

_PARAMETER_FIELDS = {"name", "parameters", "required_columns"}


def _normalize_enum_input(value: str) -> str:
    """Normalize free-form model input to a catalog enum value.

    Catalog enum values are space separated (e.g. "technical analysis"), so
    underscores and hyphens are folded to spaces.
    """
    normalized = value.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


# Session state keys for company context
EXCHANGE_KEY = "exchange"
TICKER_KEY = "ticker"
COMPANY_INFO_KEY = "company_info_cache"


class StrategyDiscoveryTools(Toolkit):
    """Toolkit for selecting strategies out of the strategy catalog.

    Discovery is a two-hop lookup rather than a progressive funnel:
        1. `list_strategies` shortlists candidates across one or more strategy
           categories, returning only the fields needed to choose between them.
        2. `get_strategy_details` (or `get_strategy_parameters`) returns the
           remaining detail for the few ids actually chosen.

    The two views are disjoint, so no field is ever sent twice. Every tool is
    batched: pass all categories / ids under consideration in a single call.
    """

    def __init__(self, **kwargs):
        self._registry = get_registry()

        tools = [
            self.list_strategies,
            self.get_strategy_details,
            self.get_strategy_parameters,
        ]

        super().__init__(
            name="strategy_discovery_tools",
            tools=tools,
            **kwargs,
        )

    def list_strategies(
        self,
        categories: list[str],
        domain: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """Shortlist the candidate strategies for one or more strategy
        categories, with just enough information to choose between them.

        Pass EVERY category you are considering in a SINGLE call. Do not call
        this tool once per category.

        The response omits full strategy detail on purpose, so that a shortlist
        spanning several categories stays small. Once you have narrowed it down,
        call get_strategy_details with the chosen ids to get the rest.

        Args:
            categories (list[str]): Strategy category ids to shortlist from,
                e.g. ["trend", "momentum", "volatility", "volume", "overlap"].
            domain (str | None): Optional analysis domain id, e.g.
                "technical analysis". Pass it only to disambiguate categories
                that exist in more than one domain.
            tags (list[str] | None): Optional tags to narrow a broad category,
                e.g. ["oscillator"], ["trend-following"], ["mean-reversion"],
                ["volume-confirmation"]. A strategy must carry EVERY tag given
                to be returned, so pass one or two at most. Prefer narrowing
                here over making a second call. Omit this when unsure, since an
                over-narrow tag set can filter out every candidate.

        Returns:
            A mapping of category -> strategy_id -> {name, llm_hint}.
            Categories with no matching strategies are omitted.
        """
        valid_categories = ", ".join(c.value for c in StrategyCategoryTypes)

        if not categories:
            raise RetryAgentRun(
                f"categories cannot be empty. Pass one or more of: {valid_categories}."
            )

        # Collect every invalid value so the model gets one retry, not N.
        chosen: list[StrategyCategoryTypes] = []
        invalid: list[str] = []
        for raw in categories:
            try:
                category = StrategyCategoryTypes(_normalize_enum_input(raw))
            except ValueError:
                invalid.append(raw)
                continue
            if category not in chosen:
                chosen.append(category)

        if invalid:
            raise RetryAgentRun(
                f"Invalid categories: {', '.join(invalid)}. "
                f"Valid values: {valid_categories}."
            )

        domain_value: str | None = None
        normalized_domain = _normalize_enum_input(domain) if domain else ""
        if normalized_domain:
            try:
                domain_value = AnalysisDomainTypes(normalized_domain).value
            except ValueError as e:
                valid_domains = ", ".join(d.value for d in AnalysisDomainTypes)
                raise RetryAgentRun(
                    f"Invalid domain '{domain}'. Valid values: {valid_domains}."
                ) from e

        # Tags are free-form in the catalog, so they are matched as given rather
        # than validated against an enum. Unknown tags simply match nothing,
        # which the empty-result branch below turns into an actionable retry.
        selected_tags = [t.strip().lower() for t in tags if t.strip()] if tags else None

        shortlist: dict[str, dict[str, dict[str, Any]]] = {}
        for category in chosen:
            if candidates := filter_strategies(
                domain=domain_value,
                category=category.value,
                tags=selected_tags,
            ):
                shortlist[category.value] = {
                    s.id: s.model_dump(mode="json", include=_SHORTLIST_FIELDS)
                    for s in candidates
                }

        if not shortlist:
            requested = ", ".join(c.value for c in chosen)
            scope = f" within domain '{domain_value}'" if domain_value else ""
            if selected_tags:
                raise RetryAgentRun(
                    f"No strategies matched categories {requested}{scope} with all "
                    f"of the tags {', '.join(selected_tags)}. Retry with fewer "
                    f"tags, or omit tags entirely to see every candidate."
                )
            raise RetryAgentRun(
                f"No strategies matched categories {requested}{scope}. "
                f"Try different categories. Valid values: {valid_categories}."
            )

        return shortlist

    def get_strategy_details(
        self, strategy_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Return the remaining full detail for strategies you already
        shortlisted with list_strategies.

        Pass ALL the ids you chose in a SINGLE call. Do not call this tool once
        per strategy.

        The response deliberately EXCLUDES the fields list_strategies already
        gave you (name, llm_hint), so nothing is repeated. Combine both
        responses when reasoning about a strategy.

        Args:
            strategy_ids (list[str]): Full strategy ids, exactly as returned by
                list_strategies, e.g. ["momentum.rsi", "trend.adx_dmi"].

        Returns:
            A mapping of strategy_id -> {summary, purpose, best_for,
            avoid_when, tags, required_columns, parameters, output_columns,
            interpretation, market_regimes, time_horizons, decision_guidance,
            limitations}.
        """
        strategies = self._resolve_strategies(strategy_ids, "get_strategy_details")
        return {
            strategy_id: strategy.model_dump(mode="json", include=_DETAIL_FIELDS)
            for strategy_id, strategy in strategies.items()
        }

    def get_strategy_parameters(
        self, strategy_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Return only the parameter specs and required input columns for the
        given strategies. Use this when you need to resolve parameter values
        and not the prose description of a strategy.

        Pass ALL the ids you need in a SINGLE call. Do not call this tool once
        per strategy.

        Args:
            strategy_ids (list[str]): Full strategy ids, e.g.
                ["momentum.rsi", "trend.adx_dmi"].

        Returns:
            A mapping of strategy_id -> {name, parameters, required_columns}.
        """
        strategies = self._resolve_strategies(strategy_ids, "get_strategy_parameters")
        return {
            strategy_id: strategy.model_dump(mode="json", include=_PARAMETER_FIELDS)
            for strategy_id, strategy in strategies.items()
        }

    def _resolve_strategies(
        self,
        strategy_ids: list[str],
        tool_name: str,
    ) -> dict[str, StrategyDescriptor]:
        """Resolve strategy ids to descriptors, de-duplicating and validating.

        Args:
            strategy_ids (list[str]): Raw ids supplied by the model.
            tool_name (str): Calling tool name, used in the retry message.

        Returns:
            A mapping of strategy_id -> descriptor, in first-seen order.
        """
        if not strategy_ids:
            raise RetryAgentRun(
                "strategy_ids cannot be empty. Pass at least one strategy id, "
                "exactly as returned by list_strategies."
            )

        resolved: dict[str, StrategyDescriptor] = {}
        unknown: list[str] = []
        seen: set[str] = set()

        for raw in strategy_ids:
            strategy_id = raw.strip()
            if not strategy_id or strategy_id in seen:
                continue
            seen.add(strategy_id)

            strategy = self._registry.by_id.get(strategy_id)
            if strategy is None:
                unknown.append(strategy_id)
                continue
            resolved[strategy_id] = strategy

        # Aggregate every bad id into ONE retry instead of one retry per id.
        # The valid id list is deliberately not dumped here; it may be 100+ long.
        if unknown:
            raise RetryAgentRun(
                f"Unknown strategy_ids: {', '.join(unknown)}. Use ids exactly as "
                f"returned by list_strategies (for example 'momentum.rsi'), then "
                f"call {tool_name} again with the corrected ids."
            )

        if not resolved:
            raise RetryAgentRun(
                "strategy_ids contained no usable ids. Pass at least one "
                "strategy id, exactly as returned by list_strategies."
            )

        return resolved


class StockDBTools(Toolkit):
    """Tools for interacting with the StockDB API."""

    def __init__(self, **kwargs):
        self._aclient = AsyncClient(
            base_url=f"{settings.stockdb.stockdb_url}:{settings.stockdb.port}/api",
            timeout=None,
        )
        # Async callables whose method name matches the tool name belong in
        # `tools` so include_tools / exclude_tools validation can see them.
        # `async_tools` is only for aliasing (e.g. list_exchange -> list_exchanges).
        tools = [
            self.current_company_context,
            self.set_company_context,
            self.get_company_exchange_and_ticker,
            self.get_company_information,
            self.list_registered_datasets,
        ]
        async_tools = [
            (self.list_exchange, "list_exchanges"),
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
        dependencies = run_context.dependencies or {}

        # NOTE - Dependency state is deliberately kept as 2nd so that during run if LLM updates
        # session state, it is reflected in the tool output.

        # 1st check in session state
        exch = session_state.get(EXCHANGE_KEY)
        tkr = session_state.get(TICKER_KEY)

        if exch and tkr:
            return f"Current company context: Exchange={exch}, Ticker={tkr}"

        # 2nd check in dependencies
        exch = dependencies.get("exchange")
        tkr = dependencies.get("ticker")
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

    async def list_registered_datasets(self) -> list[dict[str, str]]:
        """Use this tool to get available datasets that the user can apply strategies to.

        Returns:
            list[dict[str, str]]: A list of datasets with dataset_id, name, description.
        """

        # response = await self._aclient.get("/api/operation/data")
        # # NOTE - Output is a list of dictionaries with dataset_id, name, description, logical_plan, tags, last_modified
        # data = response.json()
        # return [
        #     {
        #         "dataset_id": item["dataset_id"],
        #         "name": item["name"],
        #         "description": item["description"],
        #     }
        #     for item in data
        # ]
        return [
            {
                "dataset_id": "dataset-1",
                "name": "Nifty50 Daily Prices",
                "description": "Daily NSE Nifty50 OHLCV complete historic data ",
            },
            {
                "dataset_id": "dataset-2",
                "name": "Nifty50 Daily Prices 3M",
                "description": "Daily NSE Nifty50 OHLCV last 3 months data from present day",
            },
            {
                "dataset_id": "dataset-3",
                "name": "Nifty50 Daily Prices 6M",
                "description": "Daily NSE Nifty50 OHLCV last 6 months data from present day",
            },
            {
                "dataset_id": "dataset-4",
                "name": "Nifty Next 50 Daily Prices",
                "description": "Daily NSE Nifty Next 50 OHLCV complete historic data",
            },
        ]
