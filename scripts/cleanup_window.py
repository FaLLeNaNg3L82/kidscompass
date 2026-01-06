import sys
import os
import datetime
sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.data import Database

START = datetime.date(2025,8,9)
END = datetime.date(2025,8,26)

print('Opening DB...')
db = Database()
cur = db.conn.cursor()
# Backup
backup_fn = os.path.join(os.path.dirname(db.db_path), f'backup_before_window_cleanup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.sql')
print('Creating SQL backup:', backup_fn)
db.export_to_sql(backup_fn)

candidates = db.find_unreferenced_patterns(START, END)
if not candidates:
    print('No unreferenced patterns found in window.')
    db.close()
    sys.exit(0)

print('Candidates to delete:')
for row in candidates:
    print(row)

# Delete them
for row in candidates:
    pid = row['id']
    try:
        db.delete_pattern(pid)
        print('Deleted pattern id=', pid)
    except Exception as e:
        print('Failed to delete pattern id=', pid, 'error:', e)

print('Remaining patterns:')
for r in db.conn.execute("SELECT id, weekdays, start_date, end_date FROM patterns"):
    print(dict(r))

print('Done')
db.close()
