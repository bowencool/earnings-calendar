from datetime import date
from pathlib import Path
from unittest.mock import Mock

from earnings_calendar.config import AppConfig
from earnings_calendar.earnings.models import EarningsEvent
from earnings_calendar.earnings.runner import run_earnings


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "storage": {"db_path": (tmp_path / "earnings.db").as_uri()},
            "earnings": {
                "api_key": "test-key",
                "days_past": 10,
                "days_ahead": 60,
                "tickers": ["AAPL"],
                "calendar": {"ics_path": tmp_path / "earnings.ics"},
            },
        }
    )


def test_run_earnings_syncs_empty_snapshot(monkeypatch, tmp_path):
    config = _config(tmp_path)
    repository = Mock()
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=None)
    database.connection = Mock()

    monkeypatch.setattr("earnings_calendar.earnings.runner.resolve_api_key", Mock(return_value="test-key"))
    monkeypatch.setattr("earnings_calendar.earnings.runner.fetch_finnhub_earnings", Mock(return_value=[]))
    monkeypatch.setattr("earnings_calendar.earnings.runner.Database", Mock(return_value=database))
    monkeypatch.setattr("earnings_calendar.earnings.runner.EarningsRepository", Mock(return_value=repository))
    monkeypatch.setattr(
        "earnings_calendar.earnings.runner.build_and_write_calendar",
        Mock(return_value=str(config.earnings.calendar.ics_path)),
    )
    repository.list_for_calendar.return_value = []

    run_earnings(config, today=date(2026, 7, 13))

    repository.sync_snapshot.assert_called_once_with(
        [],
        configured_tickers=["AAPL"],
        start_date=date(2026, 7, 3),
        end_date=date(2026, 9, 11),
    )


def test_run_earnings_only_writes_events_for_configured_tickers(monkeypatch, tmp_path):
    config = _config(tmp_path)
    active_event = EarningsEvent(ticker="AAPL", date=date(2026, 7, 20), quarter=3, fiscal_year=2026)
    removed_event = EarningsEvent(ticker="MSFT", date=date(2026, 7, 21), quarter=3, fiscal_year=2026)
    repository = Mock()
    repository.list_for_calendar.return_value = [active_event, removed_event]
    database = Mock()
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=None)
    database.connection = Mock()
    writer = Mock(return_value=str(config.earnings.calendar.ics_path))

    monkeypatch.setattr("earnings_calendar.earnings.runner.resolve_api_key", Mock(return_value="test-key"))
    monkeypatch.setattr("earnings_calendar.earnings.runner.fetch_finnhub_earnings", Mock(return_value=[]))
    monkeypatch.setattr("earnings_calendar.earnings.runner.Database", Mock(return_value=database))
    monkeypatch.setattr("earnings_calendar.earnings.runner.EarningsRepository", Mock(return_value=repository))
    monkeypatch.setattr("earnings_calendar.earnings.runner.build_and_write_calendar", writer)

    run_earnings(config, today=date(2026, 7, 13))

    assert writer.call_args.args[0] == [active_event]
