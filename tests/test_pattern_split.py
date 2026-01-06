import os
import tempfile
import sqlite3
from datetime import date

import pytest

from kidscompass.data import Database
from kidscompass.models import VisitPattern


def make_db(tmp_path):
    dbf = tmp_path / "test_split.db"
    db = Database(str(dbf))
    return db, str(dbf)


def test_normal_split_midway(tmp_path):
    db, dbf = make_db(tmp_path)
    # Create initial pattern starting 2024-11-22, no end
    p = VisitPattern([4,5,6,0], interval_weeks=2, start_date=date(2024,11,22), end_date=None)
    db.save_pattern(p)
    # reload to get id
    pats = db.load_patterns()
    assert len(pats) == 1
    pid = pats[0].id

    split_date = date(2025,9,1)
    res = db.split_pattern(pid, split_date, new_weekdays=[5,6], new_interval_weeks=None, end_prev=True)

    # Check DB state
    pats = {p.id: p for p in db.load_patterns()}
    # Old pattern should have end_date = split_date -1
    old = pats[pid]
    assert old.end_date == date(2025,8,31)
    # New pattern exists with start_date = split_date
    new_id = res['new_pattern_id']
    assert new_id is not None
    newp = pats[new_id]
    assert newp.start_date == split_date
    assert newp.end_date is None
    # interval preserved
    assert newp.interval_weeks == old.interval_weeks


def test_split_preserves_original_enddate(tmp_path):
    db, dbf = make_db(tmp_path)
    # Original has an end_date
    p = VisitPattern([2], interval_weeks=1, start_date=date(2024,11,22), end_date=date(2024,12,31))
    db.save_pattern(p)
    pid = db.load_patterns()[0].id

    split_date = date(2024,12,1)
    res = db.split_pattern(pid, split_date, new_weekdays=[1,2], new_interval_weeks=1, end_prev=True)

    # New pattern should inherit original end_date
    new_id = res['new_pattern_id']
    assert new_id is not None
    newp = [x for x in db.load_patterns() if x.id == new_id][0]
    assert newp.end_date == date(2024,12,31)


def test_split_before_or_equal_start_replaces(tmp_path):
    db, dbf = make_db(tmp_path)
    p = VisitPattern([0,1], interval_weeks=1, start_date=date(2025,1,10), end_date=None)
    db.save_pattern(p)
    pid = db.load_patterns()[0].id

    # split date <= start_date -> replace behavior
    split_date = date(2025,1,1)
    res = db.split_pattern(pid, split_date, new_weekdays=[2,3], new_interval_weeks=2, end_prev=True)
    assert res['new_pattern_id'] == pid
    # verify pattern updated
    updated = [x for x in db.load_patterns() if x.id == pid][0]
    assert updated.start_date == split_date
    assert updated.interval_weeks == 2


def test_split_deduplicates_if_target_exists(tmp_path):
    db, dbf = make_db(tmp_path)
    # Create an existing pattern that will match the new target
    existing = VisitPattern([5,6], interval_weeks=1, start_date=date(2025,9,1), end_date=None)
    db.save_pattern(existing)
    existing_id = db.load_patterns()[0].id

    # Create old pattern to be split
    old = VisitPattern([4,5,6,0], interval_weeks=1, start_date=date(2024,11,22), end_date=None)
    db.save_pattern(old)
    allp = db.load_patterns()
    # find old id (not the existing one)
    pid = [p.id for p in allp if p.id != existing_id][0]

    res = db.split_pattern(pid, date(2025,9,1), new_weekdays=[5,6], new_interval_weeks=1, end_prev=True)
    # new_pattern_id should point to existing
    assert res['new_pattern_id'] == existing_id
    # old pattern end_date updated
    oldp = [p for p in db.load_patterns() if p.id == pid][0]
    assert oldp.end_date == date(2025,8,31)


def test_split_transaction_rollback_on_error(tmp_path):
    db, dbf = make_db(tmp_path)
    # Create a normal pattern
    p = VisitPattern([0], interval_weeks=1, start_date=date(2024,11,22), end_date=None)
    db.save_pattern(p)
    pid = db.load_patterns()[0].id

    # Monkeypatch Database._find_pattern_by_key to raise to force rollback during split
    def bad_find(*args, **kwargs):
        raise sqlite3.OperationalError('simulated failure')

    db._find_pattern_by_key = bad_find
    split_date = date(2025,6,1)
    with pytest.raises(sqlite3.OperationalError):
        db.split_pattern(pid, split_date, new_weekdays=[1], new_interval_weeks=1, end_prev=True)

    # Ensure DB unchanged: old pattern has no end_date
    p_after = db.load_patterns()[0]
    assert p_after.end_date is None
