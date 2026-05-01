"""
Finnhub client integration for earnings retrieval.
"""

import contextlib
from datetime import date

import finnhub
from finnhub.exceptions import FinnhubAPIException, FinnhubRequestException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tech_calendar.earnings.models import EarningsEvent
from tech_calendar.logging import get_logger

logger = get_logger(__name__)


class FinnhubEarningsItem(BaseModel):
    symbol: str
    date: date
    quarter: int
    hour: str | None = None
    year: int

    eps_estimate: float | None = Field(default=None, alias="epsEstimate")
    eps_actual: float | None = Field(default=None, alias="epsActual")
    revenue_estimate: float | None = Field(default=None, alias="revenueEstimate")
    revenue_actual: float | None = Field(default=None, alias="revenueActual")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @field_validator("eps_estimate", "eps_actual", "revenue_estimate", "revenue_actual", mode="before")
    @classmethod
    def _empty_str_to_none_numeric(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("hour", mode="before")
    @classmethod
    def _empty_str_to_none_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    def into(self) -> EarningsEvent:
        return EarningsEvent(
            ticker=self.symbol.strip().upper(),
            date=self.date,
            quarter=self.quarter,
            fiscal_year=self.year,
            eps_estimate=self.eps_estimate,
            revenue_estimate=self.revenue_estimate,
            source="Finnhub",
        )


class FinnhubResponse(BaseModel):
    earnings_calendar: list[FinnhubEarningsItem] = Field(default_factory=list, alias="earningsCalendar")
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


def _retry_on_status_error(exc: BaseException) -> bool:
    """
    Retry only on rate limiting and 5xx server errors raised by the official SDK.
    """
    return isinstance(exc, FinnhubAPIException) and getattr(exc, "status", None) in (429, 500, 502, 503, 504)


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=1, max=20),
    retry=retry_if_exception_type(FinnhubRequestException) | retry_if_exception(_retry_on_status_error),
)
def _get_validated_response(client: finnhub.Client, start: date, end: date, *, symbol: str = "") -> FinnhubResponse:
    """
    Call the official SDK and strictly validate the response with Pydantic.
    """
    payload = client.earnings_calendar(
        _from=start.isoformat(),
        to=end.isoformat(),
        symbol=symbol,
        international=False,
    )
    return FinnhubResponse.model_validate(payload)


def fetch_finnhub_earnings(
    start: date,
    end: date,
    api_key: str,
    tickers: list[str] | None = None,
) -> list[EarningsEvent]:
    """
    Fetch earnings across the date window from Finnhub via the official SDK.

    When ``tickers`` is provided, fetches each ticker individually to guarantee
    complete coverage (the global calendar endpoint may omit entries on the
    free tier).  Otherwise falls back to a single global-calendar request.
    """
    normalised: list[str] = (
        [t.strip().upper() for t in tickers if t and t.strip()]
        if tickers
        else []
    )
    targets: list[str] = normalised if normalised else [""]

    client = finnhub.Client(api_key=api_key)
    try:
        all_events: list[EarningsEvent] = []
        for symbol in targets:
            try:
                parsed = _get_validated_response(client, start, end, symbol=symbol)
            except ValidationError as exc:
                logger.error(
                    "finnhub_response_validation_error",
                    extra={"error": str(exc), "symbol": symbol},
                )
                raise SystemExit(2) from exc
            except Exception as exc:
                logger.error(
                    "finnhub_fetch_failed",
                    extra={"error": str(exc), "symbol": symbol},
                )
                raise SystemExit(2) from exc

            all_events.extend(item.into() for item in parsed.earnings_calendar)

        return all_events
    finally:
        close_func = getattr(client, "close", None)
        if callable(close_func):
            with contextlib.suppress(Exception):
                close_func()
