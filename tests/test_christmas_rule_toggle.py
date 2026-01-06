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
    created = db.import_vacations_from_ics(str(ics), anchor_year=2025)
    # mine_only default True -> should import only father's phase
    assert len(created) == 1
    ov = created[0]
    assert getattr(ov, 'holder', None) == 'father'
    assert getattr(ov, 'vac_type', None) == 'weihnachten'
    # For 2025 parity -> father has the second phase; meta must contain neutral dates (25.12 and 01.01)
    assert ov.meta
    assert '2025-12-25' in ov.meta or '2026-01-01' in ov.meta or 'neutral_dates' in ov.meta


def test_christmas_2026_first_half_father(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    ics = tmp_path / 'xmas26.ics'
    make_ics(ics, date(2026,12,20), date(2027,1,5))
    created = db.import_vacations_from_ics(str(ics), anchor_year=2025)
    # mine_only => only father's phase
    assert len(created) == 1
    ov = created[0]
    # For 2026 parity flips => father has the first phase; meta must contain neutral dates
    assert getattr(ov, 'holder', None) == 'father'
    assert getattr(ov, 'vac_type', None) == 'weihnachten'
    assert ov.meta
    assert 'neutral_dates' in ov.meta


def test_christmas_special_2024_2025_two_father_blocks(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    ics = tmp_path / 'xmas_special.ics'
    # Special judge case covering 2024-12-20 .. 2025-01-07
    make_ics(ics, date(2024,12,20), date(2025,1,7))
    created = db.import_vacations_from_ics(str(ics), anchor_year=2025)
    # Should produce two father blocks
    assert len(created) == 2
    b1, b2 = created[0], created[1]
    assert getattr(b1, 'holder', None) == 'father'
    assert getattr(b2, 'holder', None) == 'father'
    assert 'special_2024_2025_block_1' in b1.meta
    assert 'special_2024_2025_block_2' in b2.meta
