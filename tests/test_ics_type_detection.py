from datetime import date
import tempfile
import os

from kidscompass.data import Database


def write_ics(path, summary, start, end):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('BEGIN:VCALENDAR\n')
        f.write('BEGIN:VEVENT\n')
        f.write(f'DTSTART;VALUE=DATE:{start.strftime("%Y%m%d")}\n')
        f.write(f'DTEND;VALUE=DATE:{end.strftime("%Y%m%d")}\n')
        f.write(f'SUMMARY:{summary}\n')
        f.write('END:VEVENT\n')
        f.write('END:VCALENDAR\n')


def test_ics_detection_all_types(tmp_path):
    dbfile = tmp_path / 'db.db'
    db = Database(str(dbfile))
    cases = [
        ('Weihnachtsferien', 'weihnachten'),
        ('Osterferien', 'oster'),
        ('Sommerferien', 'sommer'),
        ('Herbstferien', 'herbst'),
    ]
    for i, (label, expected) in enumerate(cases):
        ics = tmp_path / f'ev{i}.ics'
        write_ics(ics, label, date(2025,12,20), date(2026,1,5))
        created = db.import_vacations_from_ics(str(ics))
        assert created, 'no overrides created'
        # ensure vac_type set on created overrides
        for ov in created:
            assert getattr(ov, 'vac_type', None) == expected
