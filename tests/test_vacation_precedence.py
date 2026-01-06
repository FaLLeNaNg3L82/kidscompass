from datetime import date
from kidscompass.data import Database
from kidscompass.calendar_logic import apply_overrides, generate_standard_days


def test_vacation_overrides_remove(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    # Create a standard pattern that includes 2025-12-25 (Friday) — choose weekday 4 (Fri) and start early
    from kidscompass.models import VisitPattern
    pat = VisitPattern([4], interval_weeks=1, start_date=date(2025,1,1), end_date=date(2026,12,31))
    db.save_pattern(pat)

    # Create a RemoveOverride covering the Christmas date (should remove standard day)
    from kidscompass.models import RemoveOverride
    rem = RemoveOverride(date(2025,12,24), date(2025,12,26))
    db.save_override(rem)

    # Now import Christmas add which should re-add days (vacation adds)
    ics = tmp_path / 'x.ics'
    with open(ics, 'w', encoding='utf-8') as f:
        f.write('BEGIN:VCALENDAR\n')
        f.write('BEGIN:VEVENT\n')
        f.write('DTSTART;VALUE=DATE:20251220\n')
        f.write('DTEND;VALUE=DATE:20260105\n')
        f.write('SUMMARY:Weihnachtsferien\n')
        f.write('END:VEVENT\n')
        f.write('END:VCALENDAR\n')

    created = db.import_vacations_from_ics(str(ics))
    # Build standard days and apply overrides
    std = []
    for p in db.load_patterns():
        std.extend(generate_standard_days(p, 2025))
    ov = db.load_overrides()
    planned = apply_overrides(std, ov)
    # 2025-12-25 should be present because vacation add overrides the removal
    assert date(2025,12,25) in planned
