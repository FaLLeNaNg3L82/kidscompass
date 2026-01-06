#!/usr/bin/env python3
"""Repair SQL dump ordering (ensure patterns table exists before inserts) and import into a temp DB.
Usage: repair_and_restore_sql.py <sql_dump> [--target-db <path>] [--apply]
If --apply is given and import into temp DB succeeds, it will replace target DB after backing it up.
"""
import sys, os, shutil, argparse, datetime, sqlite3
from pathlib import Path

def make_patterns_create():
    return (
        "CREATE TABLE IF NOT EXISTS patterns (\n"
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "  weekdays TEXT NOT NULL,\n"
        "  interval_weeks INTEGER NOT NULL,\n"
        "  start_date TEXT NOT NULL,\n"
        "  end_date TEXT\n"
        ");\n"
    )


def repair_sql(content: str) -> str:
    # Remove markdown fences if present
    content = content.replace('```sql', '').replace('```', '')

    import re
    lower = content.lower()
    pos_insert_overrides = lower.find("insert into \"overrides\"")
    # Find existing CREATE TABLE patterns block (if any)
    m = re.search(r"create\s+table\s+patterns\b.*?\);", content, flags=re.IGNORECASE | re.DOTALL)
    if m:
        create_block = m.group(0)
        pos_create_patterns = m.start()
    else:
        create_block = None
        pos_create_patterns = -1

    # If inserts to overrides appear before the CREATE TABLE patterns, move the existing
    # CREATE TABLE block to the top to ensure references exist before inserts.
    if create_block and pos_insert_overrides != -1 and pos_create_patterns > pos_insert_overrides:
        # remove the existing block and prepend it
        content = content[:pos_create_patterns] + content[pos_create_patterns + len(create_block):]
        header = '-- Moved CREATE TABLE patterns to top to repair ordering\n' + create_block + '\n'
        content = header + content
    else:
        # If no create block exists at all, ensure a safe CREATE is prepended
        if not create_block:
            header = '-- Auto-inserted CREATE TABLE patterns to repair dump\n' + make_patterns_create()
            content = header + '\n' + content
    return content


def import_to_temp_db(sql_text: str, tmpdb_path: str):
    if os.path.exists(tmpdb_path):
        os.remove(tmpdb_path)
    conn = sqlite3.connect(tmpdb_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(sql_text)
        conn.commit()
    finally:
        conn.close()


def verify_db(tmpdb_path: str) -> bool:
    conn = sqlite3.connect(tmpdb_path)
    conn.row_factory = sqlite3.Row
    ok = False
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        print('Tables found in temp DB:', tables)
        if 'patterns' in tables:
            cur.execute('SELECT COUNT(1) as c FROM patterns')
            c = cur.fetchone()['c']
            print('patterns rows:', c)
            ok = True
    except Exception as e:
        print('Verification failed:', e)
    finally:
        conn.close()
    return ok


def backup_and_replace(target_db: str, tmpdb_path: str):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = target_db + f'.bak_before_restore_{ts}'
    if os.path.exists(target_db):
        shutil.copy2(target_db, bak)
        print('Backed up current DB to', bak)
    shutil.copy2(tmpdb_path, target_db)
    print('Replaced target DB with repaired temp DB')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('sql_dump')
    p.add_argument('--target-db', dest='target_db', help='Target DB path', default=os.path.join(os.path.expanduser('~'), '.kidscompass', 'kidscompass.db'))
    p.add_argument('--apply', action='store_true', help='Replace target DB on success')
    args = p.parse_args()

    sql_path = Path(args.sql_dump)
    if not sql_path.exists():
        print('SQL dump not found:', sql_path)
        sys.exit(1)

    with open(sql_path, 'r', encoding='utf-8') as f:
        content = f.read()

    repaired = repair_sql(content)
    tmpdb = str(sql_path.with_suffix('.tmp.db'))
    print('Importing repaired SQL into temp DB', tmpdb)
    try:
        import_to_temp_db(repaired, tmpdb)
    except Exception as e:
        print('Import into temp DB failed:', e)
        if os.path.exists(tmpdb):
            os.remove(tmpdb)
        sys.exit(2)

    if not verify_db(tmpdb):
        print('Verification failed; will not replace target DB')
        if os.path.exists(tmpdb):
            os.remove(tmpdb)
        sys.exit(3)

    print('Temp DB import OK.')

    if args.apply:
        print('Applying: backing up and replacing target DB', args.target_db)
        backup_and_replace(args.target_db, tmpdb)
    else:
        print('Dry run complete. Use --apply to replace target DB.')

if __name__ == '__main__':
    main()
