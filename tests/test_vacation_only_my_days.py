from datetime import date
import json
from kidscompass.data import Database


def write_ics(path, summary, start, end):
    path.write_text(f"BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:{start.strftime('%Y%m%d')}\nDTEND:{end.strftime('%Y%m%d')}\nSUMMARY:{summary}\nEND:VEVENT\nEND:VCALENDAR\n")


def test_vacation_only_my_days_oster_and_sommer(tmp_path):
    db = Database(str(tmp_path / 'vac.db'))

    # Ostern 2025 -> I have the SECOND half
    ics1 = tmp_path / 'oster25.ics'
    write_ics(ics1, 'Osterferien', date(2025,4,1), date(2025,4,14))
    created1 = db.import_vacations_from_ics(str(ics1), anchor_year=2025)
    assert len(created1) == 1
    ov = created1[0]
    assert getattr(ov, 'vac_type', None) == 'oster'
    meta = json.loads(getattr(ov, 'meta'))
    assert meta['assigned'] == 'second'
    assert getattr(ov, 'holder', None) == 'father'

    # Ostern 2026 -> I have the FIRST half
    ics2 = tmp_path / 'oster26.ics'
    write_ics(ics2, 'Osterferien', date(2026,4,1), date(2026,4,14))
    created2 = db.import_vacations_from_ics(str(ics2), anchor_year=2025)
    assert len(created2) == 1
    ov2 = created2[0]
    meta2 = json.loads(getattr(ov2, 'meta'))
    assert meta2['assigned'] == 'first'

    # Sommer 2025 -> I have the LAST 14 days
    ics3 = tmp_path / 'sommer25.ics'
    write_ics(ics3, 'Sommerferien', date(2025,7,1), date(2025,8,20))
    created3 = db.import_vacations_from_ics(str(ics3), anchor_year=2025)
    assert len(created3) == 1
    ov3 = created3[0]
    meta3 = json.loads(getattr(ov3, 'meta'))
    assert meta3['assigned'] == 'last_14'
    # check dates: last 14 days -> end -13
    assert ov3.from_date == date(2025,8,7)
    assert ov3.to_date == date(2025,8,20)

    # Sommer 2026 -> I have the FIRST 14 days
    ics4 = tmp_path / 'sommer26.ics'
    write_ics(ics4, 'Sommerferien', date(2026,7,1), date(2026,8,20))
    created4 = db.import_vacations_from_ics(str(ics4), anchor_year=2025)
    assert len(created4) == 1
    ov4 = created4[0]
    meta4 = json.loads(getattr(ov4, 'meta'))
    assert meta4['assigned'] == 'first_14'
    assert ov4.from_date == date(2026,7,1)
    assert ov4.to_date == date(2026,7,14)

    db.close()
