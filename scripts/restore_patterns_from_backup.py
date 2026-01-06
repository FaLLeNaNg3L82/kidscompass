"""
Tool: restore_patterns_from_backup.py
- Lädt die `patterns`-Inserts aus einer SQL-Backup-Datei
- Zeigt die gefundenen Pattern mit Beispiel-Daten an
- Erlaubt interaktives Auswählen und Wiederherstellen (als neue Patterns) in die aktuelle DB
- Option --preserve um IDs original zu erhalten (vorsichtig, kann vorhandene IDs überschreiben)

Usage:
    python restore_patterns_from_backup.py [backup_file]

Wenn kein backup_file angegeben wird, versucht das Skript bekannte Backup-Pfade in ~/.kidscompass.
"""
import sys
import os
import re
import sqlite3
import argparse
import datetime
import ast

sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.models import VisitPattern
from kidscompass.calendar_logic import generate_standard_days
from kidscompass.data import Database

# Known backup dir
HOME = os.path.expanduser('~')
DEFAULT_BACKUP_DIR = os.path.join(HOME, '.kidscompass')
DEFAULT_BACKUPS = [
    os.path.join(DEFAULT_BACKUP_DIR, fn) for fn in os.listdir(DEFAULT_BACKUP_DIR) if fn.startswith('backup_before')
] if os.path.isdir(DEFAULT_BACKUP_DIR) else []

parser = argparse.ArgumentParser()
parser.add_argument('backup_file', nargs='?', help='Pfad zur SQL-Backup-Datei')
parser.add_argument('--preserve', action='store_true', help='Versuche, die originale Pattern-ID beizubehalten (vorsichtig)')
args = parser.parse_args()

backup_fn = args.backup_file
if not backup_fn:
    if not DEFAULT_BACKUPS:
        print('Kein Backup gefunden in', DEFAULT_BACKUP_DIR)
        sys.exit(1)
    # pick the newest backup
    DEFAULT_BACKUPS.sort(key=os.path.getmtime, reverse=True)
    backup_fn = DEFAULT_BACKUPS[0]

backup_fn = os.path.normpath(backup_fn)
if not os.path.exists(backup_fn):
    print('Backup-Datei nicht gefunden:', backup_fn)
    sys.exit(1)

print('Using backup file:', backup_fn)
sql = open(backup_fn, 'r', encoding='utf-8').read()

# Extract CREATE TABLE patterns ... ; block
m = re.search(r'CREATE TABLE patterns\s*\((.*?)\);', sql, re.S)
create_stmt = None
if m:
    create_stmt = 'CREATE TABLE patterns (' + m.group(1) + ');'
else:
    print('CREATE TABLE patterns not found in backup')

# Extract INSERT INTO "patterns" VALUES(...);
inserts = re.findall(r"INSERT INTO \"patterns\" VALUES\((.*?)\);", sql)
if not inserts:
    print('No patterns INSERTs found in backup')
    sys.exit(1)

# Build in-memory DB and populate patterns
mem = sqlite3.connect(':memory:')
mem.row_factory = sqlite3.Row
cur = mem.cursor()
if create_stmt:
    cur.execute(create_stmt)
for ins in inserts:
    # ins is the part inside parentheses; reconstruct statement
    stmt = 'INSERT INTO patterns VALUES(' + ins + ');'
    cur.execute(stmt)
mem.commit()

rows = list(cur.execute('SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns'))
if not rows:
    print('No pattern rows parsed')
    sys.exit(1)

print('\nFound patterns in backup:')
for i, r in enumerate(rows):
    wd = r['weekdays']
    sd = r['start_date']
    ed = r['end_date']
    interval = r['interval_weeks']
    # sample dates
    try:
        wd_list = [int(x) for x in wd.split(',') if x]
        sd_date = datetime.date.fromisoformat(sd)
        ed_date = datetime.date.fromisoformat(ed) if ed else None
        pat = VisitPattern(wd_list, interval, sd_date, ed_date)
        sample = generate_standard_days(pat, sd_date.year)
        sample_show = ', '.join(d.isoformat() for d in sample[:5]) + (f', ... total {len(sample)}' if sample else '')
    except Exception:
        sample_show = 'n/a'
    print(f"[{i}] id={r['id']} weekdays={wd} interval={interval} start={sd} end={ed} | sample: {sample_show}")

# Interactive selection
sel = input('\nGib die Indices der zu restaurierenden Patterns ein (z.B. 0,2,5) oder "all": ').strip()
if not sel:
    print('Nothing selected, exiting.')
    sys.exit(0)
if sel.lower() == 'all':
    chosen = list(range(len(rows)))
else:
    try:
        chosen = [int(x.strip()) for x in sel.split(',') if x.strip()]
    except Exception:
        print('Invalid input')
        sys.exit(1)

# Open current DB
db = Database()
# Backup current DB to be safe
bk = os.path.join(os.path.dirname(db.db_path), f'backup_before_partial_restore_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.sql')
print('Creating DB backup:', bk)
db.export_to_sql(bk)

for idx in chosen:
    r = rows[idx]
    wd = r['weekdays']
    interval = r['interval_weeks']
    sd = datetime.date.fromisoformat(r['start_date'])
    ed = datetime.date.fromisoformat(r['end_date']) if r['end_date'] else None
    wd_list = [int(x) for x in wd.split(',') if x]
    pat = VisitPattern(wd_list, interval, sd, ed)
    if args.preserve:
        # attempt to insert with original id
        try:
            with db.conn:
                db.conn.execute('INSERT INTO patterns (id, weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?,?)',
                                (r['id'], r['weekdays'], r['interval_weeks'], r['start_date'], r['end_date']))
                # update sqlite_sequence if needed
                cur2 = db.conn.cursor()
                cur2.execute("SELECT seq FROM sqlite_sequence WHERE name='patterns'")
                rr = cur2.fetchone()
                if rr is None or rr[0] < r['id']:
                    cur2.execute("DELETE FROM sqlite_sequence WHERE name='patterns'")
                    cur2.execute("INSERT INTO sqlite_sequence(name,seq) VALUES('patterns',?)", (r['id'],))
                print(f"Inserted pattern (preserve id) original id={r['id']}")
        except Exception as e:
            print('Failed to preserve id insertion for pattern', r['id'], 'error:', e)
            print('Falling back to normal save...')
            db.save_pattern(pat)
    else:
        db.save_pattern(pat)
        print(f'Restored pattern as new id={getattr(pat, "id", None)}')

print('Done. Reload your app to see changes.')
db.close()
