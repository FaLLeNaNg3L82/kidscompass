import sys
import os
import datetime
sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days
from kidscompass.models import VisitPattern

db = Database()
cur = db.conn.cursor()
print('Patterns:')
cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns")
for row in cur.fetchall():
    print(dict(row))

print('\nOverrides:')
cur.execute("SELECT id, type, from_date, to_date, pattern_id FROM overrides")
overrides = cur.fetchall()
for row in overrides:
    print(dict(row))

pattern_ids = [r['id'] for r in db.conn.execute("SELECT id FROM patterns")]
referenced = [r['pattern_id'] for r in overrides if r['pattern_id'] is not None]
print('\nUnreferenced pattern ids:', [pid for pid in pattern_ids if pid not in referenced])

aug_start = datetime.date(2025,8,1)
aug_end = datetime.date(2025,8,31)
for row in db.conn.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns"):
    wd = [int(x) for x in row['weekdays'].split(',') if x]
    sd = datetime.date.fromisoformat(row['start_date'])
    ed = datetime.date.fromisoformat(row['end_date']) if row['end_date'] else None
    pat = VisitPattern(wd, row['interval_weeks'], sd, ed)
    dates = generate_standard_days(pat, 2025)
    in_aug = [d for d in dates if aug_start <= d <= aug_end]
    if in_aug:
        print('Pattern', row['id'], 'has dates in Aug:', in_aug[:5], '... total', len(in_aug))

# Also check overrides that might have been deleted but pattern left behind by checking pattern rows with start_date within override-ish ranges

print('\nDone')
db.close()
