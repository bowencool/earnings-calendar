"""
SQLite-backed repository for earnings events.
"""

import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime

from earnings_calendar.earnings.models import EarningsEvent
from earnings_calendar.exceptions import StorageError
from earnings_calendar.logging import get_logger

logger = get_logger(__name__)


class EarningsRepository:
    """
    SQLite-backed repository for earnings events.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_events(self, events: Iterable[EarningsEvent]) -> None:
        """
        Upsert earnings events by ticker, fiscal year, and quarter.
        """
        materialized = list(events)
        if not materialized:
            return

        now = datetime.now(UTC).isoformat()
        payload = []
        for event in materialized:
            payload.append(
                (
                    event.ticker.strip().upper(),
                    event.event_year(),
                    event.quarter,
                    event.date.isoformat(),
                    event.eps_estimate,
                    event.revenue_estimate,
                    event.source,
                    event.source_ticker,
                    event.hour,
                    now,
                    now,
                )
            )

        try:
            self.conn.executemany(
                """
                INSERT INTO earnings (
                    ticker,
                    fiscal_year,
                    quarter,
                    event_date,
                    eps_estimate,
                    revenue_estimate,
                    source,
                    source_ticker,
                    event_hour,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, fiscal_year, quarter) DO UPDATE SET
                    event_date=excluded.event_date,
                    eps_estimate=excluded.eps_estimate,
                    revenue_estimate=excluded.revenue_estimate,
                    source=excluded.source,
                    source_ticker=excluded.source_ticker,
                    event_hour=excluded.event_hour,
                    updated_at=excluded.updated_at
                """,
                payload,
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            raise StorageError("failed to persist earnings events") from exc

    def sync_snapshot(
        self,
        events: Iterable[EarningsEvent],
        *,
        configured_tickers: Iterable[str],
        start_date: date,
        end_date: date,
    ) -> None:
        """
        Persist a complete snapshot and remove stale events from its scope.

        The scope contains configured tickers whose event dates fall within the
        inclusive date range. Events outside that scope are left untouched.
        """
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        materialized = list(events)
        active_tickers = {ticker.strip().upper() for ticker in configured_tickers if ticker.strip()}
        snapshot_identities = {
            (event.ticker.strip().upper(), event.event_year(), event.quarter) for event in materialized
        }

        try:
            with self.conn:
                self._upsert_events(materialized)

                if not active_tickers:
                    return

                cursor = self.conn.execute(
                    """
                    SELECT ticker, fiscal_year, quarter
                    FROM earnings
                    WHERE event_date >= ?
                      AND event_date <= ?
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                )
                stale_identities = [
                    (ticker, fiscal_year, quarter)
                    for ticker, fiscal_year, quarter in cursor.fetchall()
                    if ticker in active_tickers and (ticker, fiscal_year, quarter) not in snapshot_identities
                ]
                self.conn.executemany(
                    """
                    DELETE FROM earnings
                    WHERE ticker = ? AND fiscal_year = ? AND quarter = ?
                    """,
                    stale_identities,
                )
        except sqlite3.Error as exc:
            raise StorageError("failed to synchronize earnings snapshot") from exc

    def _upsert_events(self, events: Iterable[EarningsEvent]) -> None:
        """Upsert earnings events without managing the transaction."""
        materialized = list(events)
        if not materialized:
            return

        now = datetime.now(UTC).isoformat()
        payload = [
            (
                event.ticker.strip().upper(),
                event.event_year(),
                event.quarter,
                event.date.isoformat(),
                event.eps_estimate,
                event.revenue_estimate,
                event.source,
                event.source_ticker,
                event.hour,
                now,
                now,
            )
            for event in materialized
        ]
        self.conn.executemany(
            """
            INSERT INTO earnings (
                ticker,
                fiscal_year,
                quarter,
                event_date,
                eps_estimate,
                revenue_estimate,
                source,
                source_ticker,
                event_hour,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, fiscal_year, quarter) DO UPDATE SET
                event_date=excluded.event_date,
                eps_estimate=excluded.eps_estimate,
                revenue_estimate=excluded.revenue_estimate,
                source=excluded.source,
                source_ticker=excluded.source_ticker,
                event_hour=excluded.event_hour,
                updated_at=excluded.updated_at
            """,
            payload,
        )

    def list_for_calendar(self, *, current_year: int, retention_years: int) -> list[EarningsEvent]:
        """
        Return earnings events eligible for calendar generation.
        """
        threshold_year = current_year - retention_years
        try:
            cursor = self.conn.execute(
                """
                SELECT
                    ticker,
                    fiscal_year,
                    quarter,
                    event_date,
                    eps_estimate,
                    revenue_estimate,
                    source,
                    source_ticker,
                    event_hour
                FROM earnings
                WHERE fiscal_year >= ?
                """,
                (threshold_year,),
            )
            rows = cursor.fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"failed to load earnings events for calendar: {exc}") from exc

        events: list[EarningsEvent] = []
        for row in rows:
            event_date = _parse_date(row[3])
            if event_date is None:
                continue
            events.append(
                EarningsEvent(
                    ticker=row[0],
                    date=event_date,
                    quarter=int(row[2]),
                    fiscal_year=int(row[1]),
                    eps_estimate=row[4],
                    revenue_estimate=row[5],
                    source=row[6],
                    source_ticker=row[7],
                    hour=row[8],
                )
            )

        return sorted(events, key=lambda ev: (ev.date, ev.ticker, ev.quarter))


def _parse_date(value: str | None) -> date | None:
    """
    Parse an ISO date string into a date object.
    """
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
