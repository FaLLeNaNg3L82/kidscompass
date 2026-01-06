from datetime import date
from kidscompass.models import VisitPattern
from kidscompass.data import Database


def test_split_pattern_creates_labeled_new_pattern(tmp_path):
    dbf = tmp_path / 'db.db'
    db = Database(str(dbf))
    # original pattern from 2024-01-01 open-ended
    p = VisitPattern([0,6], 1, date(2024,1,1), None)
    p.label = 'OriginalLabel'
    db.save_pattern(p)
    pid = p.id
    # split at 2025-01-01
    res = db.split_pattern(pid, date(2025,1,1), [1,2], new_interval_weeks=1, end_prev=True)
    assert res['new_pattern_id'] is not None
    # load patterns and find new one
    pats = db.load_patterns()
    new = [x for x in pats if x.id == res['new_pattern_id']]
    assert len(new) == 1
    assert new[0].label is not None
    assert 'ab 2025-01-01' in new[0].label
    db.close()


def test_split_replace_updates_label(tmp_path):
    dbf = tmp_path / 'db2.db'
    db = Database(str(dbf))
    p = VisitPattern([0], 1, date(2025,1,10), None)
    p.label = 'ToBeReplaced'
    db.save_pattern(p)
    pid = p.id
    # split_date before start -> replace behaviour
    res = db.split_pattern(pid, date(2025,1,1), [1], new_interval_weeks=1, end_prev=True)
    assert res['old_updated'] is True
    pats = db.load_patterns()
    updated = [x for x in pats if x.id == pid][0]
    assert updated.label is not None
    assert 'ab 2025-01-01' in updated.label
    db.close()
