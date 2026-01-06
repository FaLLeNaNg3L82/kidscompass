import sys
import os
import datetime
sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days
from kidscompass.models import VisitPattern

# Config
YEAR = 2025
AUG_START = datetime.date(YEAR, 8, 1)
AUG_END = datetime.date(YEAR, 8, 31)

print('Opening DB...')
db = Database()
cur = db.conn.cursor()

# Backup whole DB to SQL file
backup_fn = os.path.join(os.path.dirname(db.db_path), f'backup_before_cleanup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.sql')
print('Creating SQL backup:', backup_fn)
db.export_to_sql(backup_fn)

# Load overrides and patterns
cur.execute("SELECT id, type, from_date, to_date, pattern_id FROM overrides")
overrides = cur.fetchall()
referenced = {r['pattern_id'] for r in overrides if r['pattern_id'] is not None}

cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns")
patterns = cur.fetchall()

candidates = []
for row in patterns:
    pid = row['id']
    if pid in referenced:
        continue
    # build pattern
    wd = [int(x) for x in row['weekdays'].split(',') if x]
    sd = datetime.date.fromisoformat(row['start_date'])
    ed = datetime.date.fromisoformat(row['end_date']) if row['end_date'] else None
    pat = VisitPattern(wd, row['interval_weeks'], sd, ed)
    # generate dates for years covering AUG
    dates = []
    for y in range(sd.year, (ed.year if ed else YEAR) + 1):
        dates.extend(generate_standard_days(pat, y))
    in_aug = [d for d in dates if AUG_START <= d <= AUG_END]
    if in_aug:
        candidates.append((pid, in_aug))

if not candidates:
    print('No unreferenced patterns with dates in August found. Nothing to do.')
    db.close()
    sys.exit(0)

print('Unreferenced patterns that create dates in August:')
for pid, dates in candidates:
    print(' - pattern id=', pid, ' -> sample dates:', dates[:5], ' total:', len(dates))

# Ask user? This script runs non-interactively; proceed to delete these patterns.
print('\nDeleting candidate patterns...')
for pid, _ in candidates:
    try:
        cur.execute('DELETE FROM patterns WHERE id=?', (pid,))
        print('Deleted pattern id=', pid)
    except Exception as e:
        print('Failed to delete pattern id=', pid, 'error:', e)

db.conn.commit()
print('Deletion complete. Current patterns:')
cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns")
for row in cur.fetchall():
    print(dict(row))

print('\nDone. If you run the app now, the calendar should no longer show those August days from deleted patterns.')
db.close()
