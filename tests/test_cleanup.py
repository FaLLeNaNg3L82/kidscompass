import tempfile
import os
import sqlite3
from pathlib import Path
from datetime import date

from kidscompass.data import Database


def test_find_and_remove_duplicates(tmp_path):
    db_path = tmp_path / 'dup.db'
    db = Database(str(db_path))
    # Insert duplicate rows directly to simulate legacy duplicates
    cur = db.conn.cursor()
    # weekdays stored as text
    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)", ('4,5,6', 2, '2024-11-22', None))
    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)", ('4,5,6', 2, '2024-11-22', None))
    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)", ('1,2', 1, '2025-01-01', None))
    db.conn.commit()

    dups = db.find_duplicate_patterns()
    assert any(len(g) > 1 for g in dups)

    removed = db.remove_duplicate_patterns()
    assert removed >= 1

    # After removal, no duplicate groups
    dups2 = db.find_duplicate_patterns()
    assert all(len(g) == 1 for g in dups2) or not dups2

    db.close()
