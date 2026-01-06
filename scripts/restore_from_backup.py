import os
import sys
import sqlite3
import datetime

backup_fn = r"C:\Users\oneaboveall\\.kidscompass\\backup_before_cleanup_20250826_075441.sql"
# target DB path must match Database() default
db_dir = os.path.join(os.path.expanduser('~'), '.kidscompass')
db_fn = os.path.join(db_dir, 'kidscompass.db')

print('Backup file:', backup_fn)
print('Target DB file:', db_fn)

if not os.path.exists(backup_fn):
    print('ERROR: Backup file not found. Exiting.')
    sys.exit(1)

# Ensure target directory exists
os.makedirs(db_dir, exist_ok=True)

# If DB exists, move it to a timestamped backup
if os.path.exists(db_fn):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    old = db_fn + f'.broken_before_restore_{ts}'
    print('Renaming existing DB to:', old)
    os.replace(db_fn, old)

# Create new DB and execute SQL
print('Restoring...')
conn = sqlite3.connect(db_fn)
try:
    cur = conn.cursor()
    with open(backup_fn, 'r', encoding='utf-8') as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    print('Restore completed successfully.')
except Exception as e:
    print('Restore failed:', e)
    # Cleanup: remove possibly partially created DB
    try:
        conn.close()
    except Exception:
        pass
    if os.path.exists(db_fn):
        try:
            os.remove(db_fn)
        except Exception:
            pass
    sys.exit(2)
finally:
    conn.close()

print('Done.')
