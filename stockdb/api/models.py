from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from stocksense.types import DataInterval, DataPeriod

from api.dependency import stable_hash


class APITags(Enum):
    root = "Root"
    health = "Health"
    per_security = "Per Security"
    bulk = "Bulk"
    dataset = "Dataset"
    task = "Task"
    ops = "Operation"
    agent = "Agents"
    strategy = "Strategy"


class Period(Enum):
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    YEAR_TO_DATE = "ytd"
    MAX = "max"


class Interval(Enum):
    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    SIXTY_MINUTES = "60m"
    NINETY_MINUTES = "90m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"


class StockExchange(Enum):
    nse = "nse"
    bse = "bse"
    nasdaq = "nasdaq"
    nyse = "nyse"
    tse = "tse"
    lse = "lse"
    hkse = "hkse"
    xetra = "xetra"
    sse = "sse"
    asx = "asx"
    bmv = "bmv"
    tsx = "tsx"
    euronext = "euronext"


class StockExchangeYahooIdentifier(Enum):
    nse = ".NS"
    bse = ".BO"
    nasdaq = ""
    nyse = ""
    lse = ".L"
    tse = ".T"
    hkse = ".HK"
    xetra = ".X"
    sse = ".S"
    asx = ".A"
    bmv = ".M"
    tsx = ".C"
    euronext = ".F"


class StockExchangeFullName(Enum):
    nse = "National Stock Exchange of India"
    bse = "Bombay Stock Exchange"
    tse = "Tokyo Stock Exchange"
    lse = "London Stock Exchange"
    hkse = "Hong Kong Stock Exchange"
    xetra = "Frankfurt Stock Exchange"
    sse = "Shanghai Stock Exchange"
    asx = "Australian Securities Exchange"
    nasdaq = "nasdaq Stock Exchange"
    nyse = "New York Stock Exchange"
    bmv = "Mexico Stock Exchange"
    tsx = "Toronto Stock Exchange"
    euronext = "euronext"


class TickerHistoryDownloadMode(Enum):
    full = "full"
    incremental = "incremental"


class TaskMode(Enum):
    auto = "auto"
    manual = "manual"


class PromptCacheTier(Enum):
    auto = "auto"  # Auto select tier based on data size
    tier1 = "tier1"  # Delta Lake Storage
    tier2 = "tier2"  # Vector DB Storage


class YahooTickerIdentifier(BaseModel):
    symbol: str
    exchange: str
    exch_id: str


class ExchangeTickerInfo(BaseModel):
    ticker: str | None = None
    company: str | None = None


class ExchangeTickersInfo(BaseModel):
    exchange: str
    ticker: str
    info: dict


class TickerHistoryOutput(BaseModel):
    date: datetime | None = None
    ticker: str | None = None
    company: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    # REVIEW - maybe required in future
    # dividends: float | None = None
    # stock_splits: float | None = Field(None, alias="Stock Splits")


class ExchangeTickersHistory(BaseModel):
    exchange: str
    ticker: str
    history: list[TickerHistoryOutput] | None = None


class TickerHistoryQuery(BaseModel):
    model_config = {"extra": "forbid"}

    interval: DataInterval = Field(
        DataInterval.ONE_DAY,
        description="Day interval between historical data points",
    )
    period: DataPeriod = Field(
        DataPeriod.ONE_DAY,
        description="Day period between historical data points. This is mutually exclusive with `start_date` and `end_date`",
    )
    start_date: date | None = Field(
        None,
        description="Start date for historical data points. This is mutually exclusive with `period`",
        examples=["2024-01-01", "2020-12-31"],
    )
    end_date: date | None = Field(
        None,
        description="End date for historical data points. This is mutually exclusive with `period`",
        examples=["2024-02-01", "2021-01-31"],
    )

    @model_validator(mode="after")
    def check_start_end_date(self):
        if (self.start_date is not None) and (self.end_date is None):
            raise ValueError("end_date is required when start_date is set")
        if (
            self.start_date
            and self.end_date
            and self.start_date > self.end_date
        ):
            raise ValueError("Start date must be less than end date")
        return self


class TickerInput(BaseModel):
    ticker: list[str] = Field(
        description="Desired company's `Ticker` symbol",
        examples=[
            ["infy", "tcs", "AKASH"],
            ["AAPL", "msft"],
        ],
    )

    def get_yahoo_aware_ticker(
        self, exchange: StockExchange
    ) -> list[YahooTickerIdentifier]:
        """Get Ticker wrt to yahoo aware exchange."""
        self.ticker = [
            t.upper() for t in self.ticker
        ]  # making sure that ticker symbol are always Upper case
        return [
            YahooTickerIdentifier(
                symbol=t,
                exchange=exchange.name,
                exch_id=getattr(StockExchangeYahooIdentifier, exchange.name),
            )
            for t in self.ticker
        ]


class TaskTickerHistoryDownloadInput(BaseModel):
    exchange: StockExchange = Field(
        StockExchange.nse,
        description="Stock Exchange to download ticker history for",
    )
    task_mode: TaskMode = Field(
        TaskMode.auto, description="Mode of task execution"
    )
    download_mode: TickerHistoryDownloadMode = Field(
        TickerHistoryDownloadMode.incremental,
        description="Download mode. `full` mode downloads complete history. `incremental` mode downloads only latest/missing data.",
    )
    ticker: list[str] | None = Field(
        None,
        description="Desired company's `Ticker` symbol. If not provided, all tickers in the exchange will be processed.",
        examples=[
            ["infy", "tcs", "AKASH"],
            ["AAPL", "msft"],
        ],
    )
    start_date: date | None = Field(
        None,
        description="Start date for historical data points. Only used in `manual` mode.",
        examples=["2024-01-01", "2021-01-01"],
    )
    end_date: date | None = Field(
        None,
        description="End date for historical data points. Only used in `manual` mode.",
        examples=["2024-02-01", "2021-01-31"],
    )

    @model_validator(mode="after")
    def validate_manual_mode_dates(self):
        # In auto mode, start_date and end_date should not be provided
        if self.task_mode == TaskMode.auto and (
            self.start_date is not None or self.end_date is not None
        ):
            raise ValueError(
                "start_date and end_date should not be provided in auto mode"
            )
        if self.task_mode == TaskMode.manual:
            if self.start_date is None or self.end_date is None:
                raise ValueError(
                    "start_date and end_date are required in manual mode"
                )
            if self.start_date > self.end_date:
                raise ValueError("start_date must be less than end_date")
        return self

    def get_yahoo_aware_ticker(self) -> list[YahooTickerIdentifier]:
        """Get Ticker wrt to yahoo aware exchange."""
        if self.ticker is None:
            from polars import scan_delta
            from stocksense.config import get_settings

            settings = get_settings()

            self.ticker = (
                scan_delta(settings.stockdb.data_base_path / "common/security")
                .select(self.exchange.value)
                .explode(self.exchange.value)
                .collect()
                .to_series()
                .to_list()
            )

        self.ticker = [
            t.upper() for t in self.ticker
        ]  # making sure that ticker symbol are always Upper case
        return [
            YahooTickerIdentifier(
                symbol=t,
                exchange=self.exchange.name,
                exch_id=getattr(
                    StockExchangeYahooIdentifier, self.exchange.name
                ),
            )
            for t in self.ticker
        ]


class TickerQueryInput(BaseModel):
    exchange: StockExchange = Field(
        ...,
        description="Stock Exchange of the ticker",
        examples=[StockExchange.nse.value, StockExchange.nyse.value],
    )
    sql_query: str = Field(
        ...,
        description="""SQL query to get ticker(s) history data.

        NOTE: Always use `stockdb` as table name in the sql query.""",
        examples=[
            "SELECT * FROM stockdb WHERE ticker = 'TCS' AND date >= '2025-01-01'",
            "SELECT date, ticker, close FROM stockdb WHERE ticker IN ('INFY', '3MINDIA') AND date BETWEEN '2022-01-01' AND '2022-12-31' ORDER BY date DESC",
        ],
    )


class BulkTickerHistoryInput(BaseModel):
    model_config = {"extra": "forbid"}

    exchange: StockExchange = Field(
        ...,
        description="Stock Exchange of the ticker",
        examples=[StockExchange.nse.value, StockExchange.nyse.value],
    )
    ticker: list[str] = Field(
        description="Desired company's `Ticker` symbol",
        examples=[
            ["infy", "tcs", "AKASH"],
            ["AAPL", "msft"],
        ],
    )

    interval: DataInterval = Field(
        DataInterval.ONE_DAY,
        description="Day interval between historical data points",
    )
    period: DataPeriod = Field(
        DataPeriod.ONE_DAY,
        description="Day period between historical data points. This is mutually exclusive with `start_date` and `end_date`",
    )
    start_date: date | None = Field(
        None,
        description="Start date for historical data points. This is mutually exclusive with `period`",
        examples=["2024-01-01", "2020-12-31"],
    )
    end_date: date | None = Field(
        None,
        description="End date for historical data points. This is mutually exclusive with `period`",
        examples=["2024-02-01", "2021-01-31"],
    )

    @model_validator(mode="after")
    def check_start_end_date(self):
        if (self.start_date is not None) and (self.end_date is None):
            raise ValueError("end_date is required when start_date is set")
        if (
            self.start_date
            and self.end_date
            and self.start_date > self.end_date
        ):
            raise ValueError("Start date must be less than end date")
        return self

    def get_yahoo_aware_ticker(self) -> list[YahooTickerIdentifier]:
        """Get Ticker wrt to yahoo aware exchange."""
        return [
            YahooTickerIdentifier(
                symbol=t.upper(),  # ticker symbol must be always Upper case
                exchange=self.exchange.name,
                exch_id=getattr(
                    StockExchangeYahooIdentifier, self.exchange.name
                ),
            )
            for t in self.ticker
        ]


class PromptCacheInput(BaseModel):
    prompt: str = Field(
        ...,
        description="The prompt string to be cached",
        examples=[
            "What is the stock price of AAPL?",
            "Give me the latest news on TSLA.",
        ],
    )
    agent: str = Field(
        ...,
        description="The agent string associated with the prompt",
        examples=[
            "Agent1",
            "text-to-sql",
        ],
    )
    model: str | None = Field(
        None,
        description="The model string associated with the prompt",
        examples=[
            "gpt-5",
            "gemini-3-pro",
        ],
    )
    response: str | None = Field(
        None,
        description="The LLM response string corresponding to the prompt",
        examples=[
            "The stock price of AAPL is $150.",
            "The latest news on TSLA is that they are launching a new model.",
        ],
    )
    thinking: str | None = Field(
        None,
        description="The LLM thinking string corresponding to the prompt",
        examples=[
            "Analyzing stock price trends for AAPL.",
            "Gathering latest news on TSLA.",
        ],
    )
    ttl: int = Field(
        30_000,
        description="Time-to-live (TTL) in days for the cached prompt-response pair",
        examples=[7, 30, 90],
    )

    def get_cache_key(self) -> str:
        """
        Create a cache key as a forever-stable hash from structured input.
        """

        return stable_hash(self.prompt, self.agent)


class PromptSearchInput(BaseModel):
    prompt: str = Field(
        ...,
        description="The prompt string to be searched in cache to get its cached response",
        examples=[
            "What is the stock price of AAPL?",
            "Give me the latest news on TSLA.",
        ],
    )
    agent: str = Field(
        ...,
        description="The agent string associated with the prompt",
        examples=[
            "Agent1",
            "text-to-sql",
        ],
    )
    cache_tier: PromptCacheTier = Field(
        PromptCacheTier.auto,
        description="The cache tier to be used for storing or retrieving the prompt cache",
        examples=[
            PromptCacheTier.auto,
            PromptCacheTier.tier1,
            PromptCacheTier.tier2,
        ],
    )

    def get_cache_key(self) -> str:
        """
        Create a cache key as a forever-stable hash from structured input.
        """

        return stable_hash(self.prompt, self.agent)


class PromptCacheOutput(BaseModel):
    response: str
    thinking: str | None = None


class LogicalPlan(BaseModel):
    exchange: StockExchange
    ticker: list[str] | None = None
    interval: DataInterval | None = None
    period: DataPeriod | None = None
    start_date: date | None = None
    end_date: date | None = None
    sql_query: str | None = None

    @model_validator(mode="after")
    def check_start_end_date(self):
        if (self.start_date is not None) and (self.end_date is None):
            raise ValueError("end_date is required when start_date is set")
        if (
            self.start_date
            and self.end_date
            and self.start_date > self.end_date
        ):
            raise ValueError("Start date must be less than end date")
        return self

    @model_validator(mode="after")
    def check_sql_or_query_params(self):
        # When sql_query is provided, other query parameters should not be provided and vice versa.
        if self.sql_query is not None and any(
            [
                self.ticker,
                self.interval,
                self.period,
                self.start_date,
                self.end_date,
            ]
        ):
            raise ValueError(
                "sql_query cannot be provided with other query parameters"
            )

        # When sql_query is not provided, ticker and interval are required. Also, either period or
        # start_date & end_date should be provided.
        if self.sql_query is None and not all([self.ticker, self.interval]):
            raise ValueError(
                "ticker and interval are required when sql_query is not provided"
            )
        if self.sql_query is None:
            if not self.period and not (self.start_date and self.end_date):
                raise ValueError(
                    "Either period or both start_date and end_date must be provided when sql_query is not provided"
                )
            if self.period and (self.start_date or self.end_date):
                raise ValueError(
                    "period is mutually exclusive with start_date and end_date"
                )
        return self


class DataRegistrationInput(BaseModel):
    dataset_id: str | None = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the dataset. If not provided, a UUID will be generated.",
    )
    name: str | None = Field(
        None, description="Name of the dataset to be registered"
    )
    description: str | None = Field(
        None, description="Description of the dataset to be registered"
    )
    logical_plan: LogicalPlan = Field(
        ...,
        description="Logical plan for the dataset to be rebuild dynamically based on user query",
    )
    tags: list[str] = Field(
        ...,
        description="List of tags associated with the dataset for better discoverability",
    )


class RegisteredDataOutput(BaseModel):
    dataset_id: str
    name: str
    description: str | None = None
    logical_plan: LogicalPlan
    tags: list[str] | None = None
    last_modified: datetime


# SECTION - Agents related models
class TextChunk(BaseModel):
    type: Literal["text"] = "text"
    content: str


class ThinkingChunk(BaseModel):
    type: Literal["thinking"] = "thinking"
    content: str


class ToolCallChunk(BaseModel):
    tool_name: str
    args: dict | None = None


class ResultChunk(BaseModel):
    type: Literal["result"] = "result"
    content: Any


class AgentStructuredResponse(BaseModel):
    content: dict[str, Any]
    thinking: str | None = None
    tool_calls: list[dict[str, Any]] | None


class TextToSQLAgent(BaseModel):
    model: str = Field(
        ...,
        description="LLM model name to be used for the agent",
        examples=[
            "groq:openai/gpt-oss-120b",
            "google-gla:gemini-2.5-flash",
        ],
    )
    prompt: str = Field(
        ...,
        description="The user's natural language request for which SQL query needs to be generated",
        examples=[
            "Get me the historical stock price data for TCS from 1st Jan 2025",
            "What was the closing price of INFY on 15th Aug 2022?",
        ],
    )
    exchange: StockExchange = Field(
        StockExchange.nse,
        description="Stock Exchange for which the SQL query needs to be generated",
        examples=[StockExchange.nse.value, StockExchange.nyse.value],
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session ID for the agent run",
    )


class CompanySummaryAgent(BaseModel):
    model: str = Field(
        ...,
        description="LLM model name to be used for the agent",
        examples=[
            "groq:openai/gpt-oss-120b",
            "google-gla:gemini-2.5-flash",
        ],
    )
    exchange: StockExchange = Field(
        StockExchange.nse,
        description="Stock Exchange for which the company summary needs to be generated",
        examples=[StockExchange.nse.value, StockExchange.nyse.value],
    )
    ticker: str = Field(
        ...,
        description="The ticker symbol of the company for which summary needs to be generated",
        examples=["TCS", "INFY"],
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session ID for the agent run",
    )


class CompanySummaryAgentQA(BaseModel):
    prompt: str = Field(
        ...,
        description="The user's natural language question for which answer needs to be generated based on company summary",
        examples=[
            "What are the key financial metrics of TCS based on key financial data points?",
            "For summary of recent news about INFY use company summary.",
        ],
    )
    model: str = Field(
        ...,
        description="LLM model name to be used for the agent",
        examples=[
            "groq:openai/gpt-oss-120b",
            "google-gla:gemini-2.5-flash",
        ],
    )
    exchange: StockExchange = Field(
        StockExchange.nse,
        description="Stock Exchange for which the company summary needs to be generated",
        examples=[StockExchange.nse.value, StockExchange.nyse.value],
    )
    ticker: str = Field(
        ...,
        description="The ticker symbol of the company for which summary needs to be generated",
        examples=["TCS", "INFY"],
    )
    instruction: str | None = Field(
        None,
        description="The instruction wrt to current user prompt. Its optional & can be use to give specific instruction to agent for current prompt. ",
        examples=[
            "What are the key financial metrics of TCS based on key financial data points?",
            "For summary of recent news about INFY use company summary.",
        ],
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session ID for the agent run",
    )


# SECTION - Strategy related models
class ApplyStrategyInput(BaseModel):
    strategy_id: str = Field(
        ...,
        description="Unique identifier of the strategy to be applied.",
        examples=["momentum.rsi", "trend.macd"],
    )
    registered_dataset_id: str = Field(
        ...,
        description="Unique identifier of the registered dataset on which the strategy needs to be applied.",
    )
    parameters: dict = Field(
        ...,
        description="Dictionary of parameters to be passed to the strategy. The required parameters depend on the specific strategy being applied.",
        examples=[
            {"period": 14},
            {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ],
    )
