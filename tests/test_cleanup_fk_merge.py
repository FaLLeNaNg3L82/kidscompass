from datetime import date
import sqlite3

from kidscompass.data import Database
from kidscompass.models import VisitPattern, OverridePeriod


def test_cleanup_merges_fk_refs(tmp_path):
    db_path = tmp_path / 'fk_merge.db'
    db = Database(str(db_path))

    # Insert two identical patterns
    p1 = VisitPattern([0,1], interval_weeks=1, start_date=date(2025,1,1))
    db.save_pattern(p1)
    # Insert a duplicate row directly to simulate legacy duplicate (bypass save_pattern)
    cur = db.conn.cursor()
    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)", ('0,1', 1, '2025-01-01', None))
    db.conn.commit()
    cur.execute("SELECT id FROM patterns WHERE weekdays=? AND start_date=? ORDER BY id DESC", ('0,1', '2025-01-01'))
    dup_id = cur.fetchone()['id']
    assert p1.id != dup_id

    # Create an override referencing the duplicate (dup_id) directly
    cur.execute("INSERT INTO overrides (type, from_date, to_date, pattern_id) VALUES (?,?,?,?)", ('add', '2025-04-01', '2025-04-10', dup_id))
    db.conn.commit()

    # Run dedup (merge)
    res = db.remove_duplicate_patterns()
    # Accept (removed, updated, backup) or (removed, updated)
    if isinstance(res, tuple):
        if len(res) >= 2:
            removed, updated = res[0], res[1]
        else:
            removed = res[0]
            updated = 0
    else:
        removed = res
        updated = 0

    # One pattern should be removed
    assert removed >= 1

    # Load overrides and ensure pattern_id points to canonical p1.id
    cur = db.conn.cursor()
    rows = list(cur.execute('SELECT pattern_id FROM overrides').fetchall())
    assert rows, 'No overrides found'
    for r in rows:
        assert r['pattern_id'] == p1.id

    # PRAGMA foreign_key_check should be empty
    fk_issues = list(db.conn.execute('PRAGMA foreign_key_check').fetchall())
    assert not fk_issues, f'Foreign key issues remain: {fk_issues}'

    db.close()
