from typing import Any

from agno.tools import Toolkit
from agno.run import RunContext
from agno.exceptions import RetryAgentRun

from stocksense.strategy.catalog import (
    AnalysisDomainTypes,
    StrategyCategoryTypes,
)
from stocksense.strategy.catalog.registry import (
    StrategyRegistry,
    get_registry,
    filter_strategies,
)

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

    def list_analysis_domains(self) -> list[dict[str, Any]]:
        """List all available analysis domains with their summaries and the
        situations they are best suited for. Call this FIRST when you do
        not yet know which analysis domain fits the user's question.

        Returns:
            A list of domain descriptors with id, summary, use_if, avoid_when, categories, etc
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
            chosen = AnalysisDomainTypes(domain.strip().lower())
        except ValueError:
            valid = ", ".join(d.value for d in AnalysisDomainTypes)
            # Letting the model know about its mistake
            raise RetryAgentRun(f"Invalid domain '{domain}'. Valid values: {valid}.")

        current = run_context.session_state.get(SELECTED_DOMAIN_KEY)
        if current == chosen.value:
            return f"Analysis domain already set to '{chosen.value}'."

        # Clear downstream selections if the user pivots
        run_context.session_state[SELECTED_DOMAIN_KEY] = chosen.value
        run_context.session_state.pop(SELECTED_CATEGORY_KEY, None)
        run_context.session_state.pop(SELECTED_STRATEGY_KEY, None)
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
        domain_value = run_context.session_state.get(SELECTED_DOMAIN_KEY)
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
        if SELECTED_DOMAIN_KEY not in run_context.session_state:
            raise RetryAgentRun("Select an analysis domain first.")

        try:
            chosen = StrategyCategoryTypes(category.strip().lower())
        except ValueError:
            valid = ", ".join(c.value for c in StrategyCategoryTypes)
            # Letting the model know about its mistake
            raise RetryAgentRun(
                f"Invalid category '{category}'. Valid values: {valid}."
            )

        run_context.session_state[SELECTED_CATEGORY_KEY] = chosen.value
        run_context.session_state.pop(SELECTED_STRATEGY_KEY, None)
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
        domain_value = run_context.session_state.get(SELECTED_DOMAIN_KEY)
        category_value = run_context.session_state.get(SELECTED_CATEGORY_KEY)

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

        run_context.session_state[SELECTED_STRATEGY_KEY] = strategy_id
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
