from datetime import date
from kidscompass.data import Database


def make_ics(path, start, end, summary='Weihnachtsferien'):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('BEGIN:VCALENDAR\n')
        f.write('BEGIN:VEVENT\n')
        f.write(f'DTSTART;VALUE=DATE:{start.strftime("%Y%m%d")}\n')
        f.write(f'DTEND;VALUE=DATE:{end.strftime("%Y%m%d")}\n')
        f.write(f'SUMMARY:{summary}\n')
        f.write('END:VEVENT\n')
        f.write('END:VCALENDAR\n')


def test_christmas_2025_first_half_mother(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    ics = tmp_path / 'xmas25.ics'
    make_ics(ics, date(2025,12,20), date(2026,1,5))
    created = db.import_vacations_from_ics(str(ics))
    # Should produce two halves
    assert len(created) == 2
    first, second = created[0], created[1]
    # Anchor year 2025 => first half holder should be 'mother'
    assert getattr(first, 'holder', None) == 'mother'
    assert getattr(first, 'vac_type', None) == 'weihnachten'
    # meta should indicate first_holiday end_time
    assert first.meta and 'first_holiday' in first.meta


def test_christmas_2026_first_half_father(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    ics = tmp_path / 'xmas26.ics'
    make_ics(ics, date(2026,12,20), date(2027,1,5))
    created = db.import_vacations_from_ics(str(ics))
    assert len(created) == 2
    first = created[0]
    # For 2026 parity flips => first half holder should be 'father'
    assert getattr(first, 'holder', None) == 'father'
    assert getattr(first, 'vac_type', None) == 'weihnachten'
