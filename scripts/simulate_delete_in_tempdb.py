#!/usr/bin/env python3
"""Simulate deleting an override or pattern in a temp DB and show diffs of planned days.
Usage: simulate_delete_in_tempdb.py <type> <id> [start_date end_date]
Type: override|pattern
"""
import os, sys, shutil, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days, apply_overrides


def load_db_copy():
    default_db = os.path.join(os.path.expanduser('~'), '.kidscompass', 'kidscompass.db')
    if not os.path.exists(default_db):
        print('Default DB not found:', default_db)
        sys.exit(1)
    tmp = default_db + '.tmp_sim.db'
    shutil.copy(default_db, tmp)
    return tmp


def analyze_window(db_path, start_date, end_date):
    db = Database(db_path=db_path)
    patterns = db.load_patterns()
    overrides = db.load_overrides()
    # build base
    years = range(start_date.year-1, end_date.year+1)
    base_days = set()
    for p in patterns:
        for y in years:
            base_days.update(generate_standard_days(p, y))
    planned = [d for d in apply_overrides(sorted(base_days), overrides) if start_date<=d<=end_date]
    db.close()
    return set(planned)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: simulate_delete_in_tempdb.py <override|pattern> <id> [start end]')
        sys.exit(1)
    typ = sys.argv[1]
    oid = int(sys.argv[2])
    s = sys.argv[3] if len(sys.argv)>3 else '2025-08-09'
    e = sys.argv[4] if len(sys.argv)>4 else '2025-08-26'
    ws = datetime.date.fromisoformat(s)
    we = datetime.date.fromisoformat(e)

    tmp = load_db_copy()
    try:
        before = analyze_window(tmp, ws, we)
        db = Database(db_path=tmp)
        if typ == 'override':
            print('Deleting override id=', oid)
            db.delete_override(oid)
        else:
            print('Deleting pattern id=', oid)
            db.delete_pattern(oid)
        after = analyze_window(tmp, ws, we)
        removed = sorted(before - after)
        added = sorted(after - before)
        print('Removed days:', removed)
        print('Added days:', added)
    finally:
        db.close()
        try:
            os.remove(tmp)
        except Exception:
            pass
