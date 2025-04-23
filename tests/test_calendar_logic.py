# tests/test_calendar_logic.py

from datetime import date, timedelta
import pytest

from kidscompass.models import VisitPattern, OverridePeriod
from kidscompass.calendar_logic import generate_standard_days, apply_overrides

def test_every_monday_2025():
    pat = VisitPattern(weekdays=[0], interval_weeks=1, start_date=date(2025, 1, 1))
    days = generate_standard_days(pat, 2025)
    # Der erste Montag 2025 ist der 6. Januar
    assert days[0] == date(2025, 1, 6)
    # Die drei ersten Montage
    assert days[:3] == [
        date(2025, 1, 6),
        date(2025, 1, 13),
        date(2025, 1, 20),
    ]
    # Und alle liegen im Jahr 2025
    assert all(d.year == 2025 for d in days)

def test_every_second_wednesday_2025():
    pat = VisitPattern(weekdays=[2], interval_weeks=2, start_date=date(2025, 1, 1))
    days = generate_standard_days(pat, 2025)
    # Erster Mittwoch 2025 ist der 1. Januar
    assert days[0] == date(2025, 1, 1)
    # Dann jeweils im Zwei-Wochen-Rhythmus
    assert days[1] == date(2025, 1, 15)
    assert days[2] == date(2025, 1, 29)
    # Prüfe den 14-Tage-Abstand
    diffs = [(days[i+1] - days[i]).days for i in range(2)]
    assert all(diff == 14 for diff in diffs)

def test_apply_overrides_replaces_standard_with_override():
    # Standard: jeden Montag
    std_pat = VisitPattern(weekdays=[0], interval_weeks=1, start_date=date(2025, 1, 1))
    standard_days = generate_standard_days(std_pat, 2025)

    # Override-Period: 6.–20. Jan, mit pattern: jeden Dienstag
    ov_pat = VisitPattern(weekdays=[1], interval_weeks=1, start_date=date(2025, 1, 1))
    override = OverridePeriod(
        from_date=date(2025, 1, 6),
        to_date=date(2025, 1, 20),
        pattern=ov_pat
    )
    result = apply_overrides(standard_days, [override])

    # Die Montags-Termine 6., 13., 20. Jan sollten weg sein
    for d in (date(2025, 1, 6), date(2025, 1, 13), date(2025, 1, 20)):
        assert d not in result

    # Stattdessen sollten die Dienstage 7. und 14. Jan drin sein
    assert date(2025, 1, 7) in result
    assert date(2025, 1, 14) in result

    # Und alle anderen Standard-Montage außerhalb des Overrides bleiben drin
    assert date(2025, 1, 27) in result

@pytest.mark.parametrize("wd,interval", [
    (4, 3),  # jeden dritten Freitag
    (6, 4),  # jeden vierten Sonntag
])
def test_various_patterns(wd, interval):
    pat = VisitPattern(weekdays=[wd], interval_weeks=interval, start_date=date(2025, 1, 1))
    days = generate_standard_days(pat, 2025)
    # Mindestens ein Termin im Jahr ist OK, und alle haben den korrekten Wochentag
    assert days, "Keine Termine generiert"
    assert all(d.weekday() == wd for d in days)
