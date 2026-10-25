from datetime import date, datetime
from zoneinfo import ZoneInfo

from analytics.services.metrics import Categories, Punctuality, range_weeks, week_starts

TZ = ZoneInfo("America/Chicago")


def test_range_weeks_accepts_only_4_12_26():
    """Helper check: ?weeks= values (D-74)."""
    assert [range_weeks(v) for v in ("4", "12", "26", 26)] == [4, 12, 26, 26]
    assert [range_weeks(v) for v in (None, "", "5", "abc", "-4", "100")] == [12] * 6


def test_week_starts_end_with_the_current_week():
    """Helper check: Sundays oldest first, the last one is this week (company time)."""
    saturday_night = datetime(2026, 10, 24, 23, 30, tzinfo=TZ)  # already Sunday in UTC
    assert week_starts(saturday_night, 3) == [
        date(2026, 10, 4),
        date(2026, 10, 11),
        date(2026, 10, 18),
    ]


def test_rate_and_totals():
    """Helper check: on-time rate rounds to a whole percent; Break never in a category total."""
    assert Punctuality().rate is None
    assert Punctuality(on_time=2, late=1).rate == 67
    assert Punctuality(on_time=1, late=1, missed=1).counted == 3
    assert Categories(rows=[("Project work", 120), ("PTO", 60)], break_minutes=45).total == 180
