"""US federal holidays for the demo history."""

from datetime import date, timedelta


def us_holidays(year):
    """US federal holidays {date: name} on their calendar dates (weekend ones are skipped)."""

    def nth_weekday(month, weekday, n):
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7, weeks=n - 1)

    last_may_monday = nth_weekday(6, 0, 1) - timedelta(weeks=1)
    return {
        date(year, 1, 1): "New Year's Day",
        nth_weekday(1, 0, 3): "Martin Luther King Jr. Day",
        last_may_monday: "Memorial Day",
        date(year, 6, 19): "Juneteenth",
        date(year, 7, 4): "Independence Day",
        nth_weekday(9, 0, 1): "Labor Day",
        nth_weekday(11, 3, 4): "Thanksgiving",
        date(year, 12, 25): "Christmas Day",
    }
