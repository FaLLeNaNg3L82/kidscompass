import tempfile
import os
import json
from kidscompass.data import Database


def test_oster_herbst_split_ics():
    ics = '''BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20260401
DTEND:20260415
SUMMARY:Ostern
END:VEVENT
END:VCALENDAR
'''
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.ics') as tf:
        tf.write(ics)
        tfname = tf.name
    try:
        db = Database(':memory:')
        created = db.import_vacations_from_ics(tfname, anchor_year=2025, mine_only=True)
        ov = db.load_overrides()
        assert any(getattr(o, 'vac_type', None) == 'oster' for o in ov)
        found = False
        for o in ov:
            if getattr(o, 'vac_type', None) == 'oster':
                m = json.loads(o.meta) if o.meta else {}
                assert 'neutral_dates' in m
                assert o.holder == 'father'
                found = True
        assert found
    finally:
        os.remove(tfname)
