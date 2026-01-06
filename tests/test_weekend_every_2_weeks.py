from datetime import date, timedelta
from kidscompass.models import VisitPattern
from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days


def test_weekend_every_2_weeks(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    # Pattern: Fr(4), Sa(5), So(6), Mo(0) every 2 weeks starting 2024-11-22
    pat = VisitPattern([4,5,6,0], interval_weeks=2, start_date=date(2024,11,22), end_date=None)
    db.save_pattern(pat)
    # Generate for 2024 and 2025
    days_2024 = generate_standard_days(pat, 2024)
    days_2025 = generate_standard_days(pat, 2025)

    # First weekend should include 2024-11-22..2024-11-25
    expected_first = {date(2024,11,22), date(2024,11,23), date(2024,11,24), date(2024,11,25)}
    assert expected_first.issubset(set(days_2024))

    # Next occurrence should be +14 days -> 2024-12-06..2024-12-09
    expected_second = {date(2024,12,6), date(2024,12,7), date(2024,12,8), date(2024,12,9)}
    assert expected_second.issubset(set(days_2024))

    # Check some dates in 2025 follow the 14-day spacing: pick 2025-01-03 (which is 6 weeks after 2024-11-22)
    # Compute that 2024-11-22 + 42 days = 2025-01-03
    assert date(2025,1,3) in days_2025
