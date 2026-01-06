import os
import sqlite3
import sys
import datetime

backup_fn = r'C:\Users\oneaboveall\\.kidscompass\\backup_before_cleanup_20250826_075441.sql'
backup_fn = os.path.normpath(backup_fn)
print('Restoring from:', backup_fn)
# Determine DB path (same default as Database)
home = os.path.expanduser('~')
db_dir = os.path.join(home, '.kidscompass')
db_path = os.path.join(db_dir, 'kidscompass.db')
print('Target DB:', db_path)
if not os.path.exists(backup_fn):
    print('Backup file not found:', backup_fn)
    sys.exit(1)

# Create backup of current DB file
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
if os.path.exists(db_path):
    backup_current = os.path.join(db_dir, f'pre_restore_backup_{now}.sql')
    print('Creating SQL dump of current DB to:', backup_current)
    conn = sqlite3.connect(db_path)
    with open(backup_current, 'w', encoding='utf-8') as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    conn.close()

# Execute the backup SQL into the DB, disabling foreign keys first
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = OFF;')
    with open(backup_fn, 'r', encoding='utf-8') as f:
        script = f.read()
    print('Executing script (this may take a moment)...')
    cur.executescript(script)
    conn.commit()
    cur.execute('PRAGMA foreign_keys = ON;')
    conn.close()
    print('Restore finished successfully.')
    print('Backup of pre-restore state:', backup_current if os.path.exists(db_path) else 'none')
except Exception as e:
    print('Restore failed:', e)
    try:
        conn.close()
    except Exception:
        pass
    sys.exit(1)
