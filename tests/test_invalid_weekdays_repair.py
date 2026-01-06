from datetime import date
import sqlite3
from kidscompass.data import Database
from pathlib import Path


def test_invalid_weekdays_repair(tmp_path):
    dbf = tmp_path / 'bad.db'
    # create DB and insert bad pattern row
    db = Database(str(dbf))
    cur = db.conn.cursor()
    # Insert a bad row directly (weekdays='remove') using explicit columns
    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date, label) VALUES (?,?,?,?,?)", ('remove', 1, '2024-01-01', None, 'BadRow'))
    db.conn.commit()
    # load_patterns should not crash and should skip bad row
    pats = db.load_patterns()
    assert all(getattr(p, 'weekdays', None) for p in pats) or len(pats) == 0
    # find_bad_patterns should detect the row
    bad = db.find_bad_patterns()
    assert len(bad) == 1
    # repair (quarantine)
    report = db.repair_patterns_weekdays()
    assert report['count'] == 1
    # after repair, no bad patterns
    bad2 = db.find_bad_patterns()
    assert len(bad2) == 0
    # load_patterns ok
    pats2 = db.load_patterns()
    assert isinstance(pats2, list)
    db.close()
