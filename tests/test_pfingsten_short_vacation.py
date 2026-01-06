from datetime import date
import json
from kidscompass.data import Database


def write_ics(path, summary, start, end):
    path.write_text(f"BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:{start.strftime('%Y%m%d')}\nDTEND:{end.strftime('%Y%m%d')}\nSUMMARY:{summary}\nEND:VEVENT\nEND:VCALENDAR\n")


def test_pfingsten_single_day_import(tmp_path):
    db = Database(str(tmp_path / 'vac.db'))
    # Pfingsten single day (1 day)
    ics = tmp_path / 'pfing1.ics'
    write_ics(ics, 'Pfingstferien', date(2025,5,20), date(2025,5,20))
    created = db.import_vacations_from_ics(str(ics), anchor_year=2025)
    assert len(created) == 1
    ov = created[0]
    assert getattr(ov, 'vac_type', None) == 'pfingsten'
    meta = json.loads(getattr(ov, 'meta'))
    # For a single-day vacation we import that day; assigned must be 'first' or 'second' depending on split
    assert meta['year'] == 2025
    assert getattr(ov, 'holder', None) == 'father'
    assert ov.from_date == date(2025,5,20)
    assert ov.to_date == date(2025,5,20)
    db.close()
