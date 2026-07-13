import sqlite3
from collections.abc import Iterator
from datetime import date

import pytest

from earnings_calendar.earnings.models import EarningsEvent
from earnings_calendar.storage.earnings_repository import EarningsRepository


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE earnings (
            ticker TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            eps_estimate REAL,
            revenue_estimate REAL,
            source TEXT,
            source_ticker TEXT,
            event_hour TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, fiscal_year, quarter)
        )
        """
    )
    yield conn
    conn.close()


def event(ticker: str, event_date: date, quarter: int = 1) -> EarningsEvent:
    return EarningsEvent(
        ticker=ticker,
        date=event_date,
        fiscal_year=event_date.year,
        quarter=quarter,
        source="test",
    )


def identities(conn: sqlite3.Connection) -> set[tuple[str, int, int, str]]:
    return set(conn.execute("SELECT ticker, fiscal_year, quarter, event_date FROM earnings").fetchall())


def test_sync_snapshot_upserts_and_deletes_only_stale_events_in_scope(
    connection: sqlite3.Connection,
) -> None:
    repository = EarningsRepository(connection)
    repository.save_events(
        [
            event("AAPL", date(2026, 7, 20)),
            event("MSFT", date(2026, 7, 21)),
            event("AAPL", date(2026, 9, 1), quarter=2),
            event("NVDA", date(2026, 7, 22)),
        ]
    )

    repository.sync_snapshot(
        [event(" aapl ", date(2026, 7, 25))],
        configured_tickers=["aapl", " MSFT "],
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    assert identities(connection) == {
        ("AAPL", 2026, 1, "2026-07-25"),
        ("AAPL", 2026, 2, "2026-09-01"),
        ("NVDA", 2026, 1, "2026-07-22"),
    }


def test_sync_snapshot_empty_snapshot_clears_inclusive_scope(
    connection: sqlite3.Connection,
) -> None:
    repository = EarningsRepository(connection)
    repository.save_events(
        [
            event("AAPL", date(2026, 7, 1)),
            event("AAPL", date(2026, 7, 31), quarter=2),
            event("AAPL", date(2026, 8, 1), quarter=3),
        ]
    )

    repository.sync_snapshot(
        [],
        configured_tickers=["AAPL"],
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    assert identities(connection) == {("AAPL", 2026, 3, "2026-08-01")}


def test_sync_snapshot_rejects_reversed_date_range(connection: sqlite3.Connection) -> None:
    repository = EarningsRepository(connection)

    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        repository.sync_snapshot(
            [],
            configured_tickers=["AAPL"],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 31),
        )
