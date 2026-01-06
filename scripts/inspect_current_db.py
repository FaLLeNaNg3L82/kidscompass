#!/usr/bin/env python3
import os, sqlite3, json
from pathlib import Path

home = os.path.expanduser('~')
db_path = os.path.join(home, '.kidscompass', 'kidscompass.db')
reports_dir = Path('scripts') / 'reports'

print('DB path:', db_path)
print('Exists:', os.path.exists(db_path))

print('\nBackups in scripts/reports:')
if reports_dir.exists():
    for p in sorted(reports_dir.glob('*')):
        print('-', p.name)
else:
    print(' (no reports directory)')

if not os.path.exists(db_path):
    print('\nNo DB found, nothing to inspect.')
    raise SystemExit(0)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','index') ORDER BY type, name")
rows = cur.fetchall()
print('\nSQLite schema objects:')
for r in rows:
    print(' -', r[1], r[0])

print('\nTable row counts (if table exists):')
for t in ['patterns','overrides','visit_status','sqlite_sequence']:
    try:
        cur.execute(f"SELECT COUNT(1) FROM {t}")
        c = cur.fetchone()[0]
        print(f" {t}: {c}")
    except Exception as e:
        print(f" {t}: ERROR ({e})")

# If patterns table missing, try to dump first 200 lines of SQL backup files for inspection
if 'patterns' not in [r[0] for r in rows]:
    print('\npatterns table not present in current DB. Showing top of SQL dumps (if any) for evidence:')
    if reports_dir.exists():
        for p in sorted(reports_dir.glob('*.sql')):
            print('\n---', p.name, '---')
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i>199:
                        break
                    print(line.rstrip())
    else:
        print(' No SQL dumps found.')

conn.close()
print('\nDone.')
