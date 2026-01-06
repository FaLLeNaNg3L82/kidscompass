from datetime import date
from kidscompass.models import VisitPattern
from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days


def test_midweek_transition(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))

    # Midweek until end of 2024: Wednesdays only
    mid_2024 = VisitPattern([2], interval_weeks=1, start_date=date(2024,11,22), end_date=date(2024,12,31))
    db.save_pattern(mid_2024)
    days_2024 = generate_standard_days(mid_2024, 2024)
    # First generated Wednesday should be 2024-11-27
    assert date(2024,11,27) in days_2024
    # Last Wednesday in 2024 should be 2024-12-25
    assert date(2024,12,25) in days_2024
    assert date(2025,1,1) not in days_2024

    # Midweek from 2025: Tuesday+Wednesday starting 2025-01-01
    mid_2025 = VisitPattern([1,2], interval_weeks=1, start_date=date(2025,1,1), end_date=None)
    db.save_pattern(mid_2025)
    days_2025 = generate_standard_days(mid_2025, 2025)
    # 2025-01-01 is a Wednesday and should be present
    assert date(2025,1,1) in days_2025
    # 2025-01-07 (Tuesday) should be present
    assert date(2025,1,7) in days_2025
