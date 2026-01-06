import json
from datetime import date
from kidscompass.export_utils import format_visit_window
from kidscompass.models import OverridePeriod, VisitPattern


def test_format_visit_window_christmas():
    # create override covering date with christmas meta
    pat = VisitPattern(list(range(7)), 1, date(2025,12,20), date(2026,1,5))
    meta = json.dumps({'end_type':'jan1','end_time':'17:00','anchor_year':2025})
    ov = OverridePeriod(date(2025,12,20), date(2026,1,5), pat, holder='mother', vac_type='weihnachten', meta=meta)
    txt = format_visit_window(date(2025,12,26), [ov], {'handover_rules': {}})
    assert 'Weihnachtsferien' in txt and '01.01' in txt or '17:00' in txt

def test_format_visit_window_generic_rule():
    pat = VisitPattern(list(range(7)), 1, date(2025,6,1), date(2025,6,10))
    meta = json.dumps({'rule':'after_school'})
    ov = OverridePeriod(date(2025,6,1), date(2025,6,10), pat, holder='father', vac_type='sommer', meta=meta)
    cfg = {'handover_rules': {'after_school': 'nach Schulende'}}
    txt = format_visit_window(date(2025,6,2), [ov], cfg)
    assert 'nach Schulende' in txt

def test_pattern_label_persistence(tmp_path):
    # quick check: save a pattern with label via Database
    from kidscompass.data import Database
    dbf = tmp_path / 'db.db'
    db = Database(str(dbf))
    p = VisitPattern([1], 1, date(2025,1,1), None)
    p.label = 'TestLabel'
    db.save_pattern(p)
    pats = db.load_patterns()
    assert any((getattr(x,'label',None) == 'TestLabel') for x in pats)
