from datetime import date

import pytest

from earnings_calendar.earnings.models import EarningsEvent


@pytest.mark.parametrize(
    ("hour", "label"),
    [
        ("bmo", "Before Market Open"),
        ("amc", "After Market Close"),
    ],
)
def test_earnings_event_displays_recognized_report_time(hour, label):
    event = EarningsEvent("AAPL", date(2026, 7, 20), 3, hour=hour)

    assert event.name() == f"AAPL Q3 Earnings ({label})"
    assert f"Report Time: {label}" in event.description().splitlines()


@pytest.mark.parametrize("hour", [None, "dmh"])
def test_earnings_event_name_is_unchanged_for_unknown_report_time(hour):
    event = EarningsEvent("AAPL", date(2026, 7, 20), 3, hour=hour)

    assert event.name() == "AAPL Q3 Earnings"
