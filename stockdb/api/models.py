from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class APITags(Enum):
    root = "Root"
    health = "Health"
    per_security = "Per Security"
    bulk = "Bulk"
    dataset = "Dataset"
    task = "Task"


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


class DBTableName(Enum):
    ticker_history = "factor_investing.ticker_history"


class SuperTrendRecentNDatasetFormat(Enum):
    detail = "detail"
    ticker_only = "tickers-only"


class TickerHistoryDownloadMode(Enum):
    full = "full"
    incremental = "incremental"


class TaskMode(Enum):
    auto = "auto"
    manual = "manual"


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


class TickerIndicatorSuperTrendOutput(BaseModel):
    date: date
    # open: float | None = None
    # high: float | None = None
    # low: float | None = None
    # close: float | None = None
    # volume: float | None = None
    super_trend: float | None = None
    upper: float | None = None
    lower: float | None = None


class ExchangeTickersIndicatorSuperTrend(BaseModel):
    exchange: str
    ticker: str
    indicator: list[dict] | None = None


class TickerHistoryQuery(BaseModel):
    model_config = {"extra": "forbid"}

    interval: Interval = Field(
        Interval.ONE_DAY, description="Day interval between historical data points"
    )
    period: Period = Field(
        Period.ONE_DAY,
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
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Start date must be less than end date")
        return self


class SuperTrendIndicatorQuery(TickerHistoryQuery):
    lookback_periods: int = Field(
        10,
        description="Number of periods (N) for the ATR evaluation. Must be greater than 1 and is "
        "usually set between 7 and 14.",
    )
    multiplier: float = Field(
        3,
        description="Multiplier sets the ATR band width. Must be greater than 0 and is usually set "
        "around 2 to 3.",
    )
    retain_source_column: list[str] | None = Field(
        default=None,
        description="List of column to retain from source ticker history data into indicator result",
        examples=[["close"], ["open", "high"]],
    )


class SuperTrendRecentNDatasetQuery(SuperTrendIndicatorQuery):
    recent_n: int = Field(
        5,
        description="Number of recent N days to evaluate Lower band v/s SuperTrend. Must be greater than 0.",
        ge=0,
        examples=[[5], [10]],
    )
    result_format: SuperTrendRecentNDatasetFormat = Field(
        SuperTrendRecentNDatasetFormat.detail,
        description="Format of the output dataset. `detail` format includes complete table data. `ticker_only` format only includes ticker symbol.",
    )


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
        StockExchange.nse, description="Stock Exchange to download ticker history for"
    )
    task_mode: TaskMode = Field(TaskMode.auto, description="Mode of task execution")
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
                raise ValueError("start_date and end_date are required in manual mode")
            if self.start_date > self.end_date:
                raise ValueError("start_date must be less than end_date")
        return self

    def get_yahoo_aware_ticker(self) -> list[YahooTickerIdentifier]:
        """Get Ticker wrt to yahoo aware exchange."""
        if self.ticker is None:
            from polars import scan_delta

            from api.config import Settings

            settings = Settings()

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
                exch_id=getattr(StockExchangeYahooIdentifier, self.exchange.name),
            )
            for t in self.ticker
        ]
