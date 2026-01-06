#!/usr/bin/env python3
"""Analyze patterns/overrides and trace which sources generate each day in a given window.
Usage: analyze_db_for_range.py [start_date] [end_date]
Dates in YYYY-MM-DD. Defaults to 2025-08-09 .. 2025-08-26 (problem range).
Produces a human-readable report and a JSON file in scripts/reports/.
"""
import os, sys, shutil, json, datetime
from pathlib import Path

# ensure repo src on path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride


def iso(d):
    return d.isoformat()


def load_db(db_path=None):
    db = Database(db_path=db_path) if db_path else Database()
    return db


def backup_db(db_path):
    t = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    outdir = Path('scripts')/ 'reports'
    outdir.mkdir(parents=True, exist_ok=True)
    backup_fn = outdir / f'kidscompass_db_backup_{t}.db'
    shutil.copy(db_path, backup_fn)
    # also export SQL
    sql_fn = outdir / f'kidscompass_db_backup_{t}.sql'
    db = Database(db_path=db_path)
    db.export_to_sql(str(sql_fn))
    db.close()
    return str(backup_fn), str(sql_fn)


def analyze(window_start, window_end, db_path=None):
    db = load_db(db_path)
    patterns = db.load_patterns()
    overrides = db.load_overrides()
    status = db.load_all_status()

    # Build base standard days union for patterns covering relevant years
    years = range(window_start.year - 1, window_end.year + 1)
    base_days = set()
    pat_map = {}
    for p in patterns:
        pdays = set()
        for y in years:
            pdays.update(generate_standard_days(p, y))
        # Keep only those in window +/- small buffer
        pat_map[p.id] = sorted(pdays)
        base_days.update(pdays)

    # Apply overrides globally using calendar_logic.apply_overrides
    # Note: apply_overrides expects standard_days and list of overrides
    planned_before_overrides = sorted(d for d in base_days if window_start <= d <= window_end)
    planned_after = apply_overrides(sorted(base_days), overrides)
    planned_in_window = [d for d in planned_after if window_start <= d <= window_end]

    # For each day in window, list contributing patterns and overrides
    report = {
        'window_start': iso(window_start),
        'window_end': iso(window_end),
        'patterns': [],
        'overrides': [],
        'days': {}
    }
    for p in patterns:
        report['patterns'].append({
            'id': getattr(p, 'id', None),
            'weekdays': p.weekdays,
            'interval_weeks': p.interval_weeks,
            'start_date': iso(p.start_date),
            'end_date': iso(p.end_date) if p.end_date else None
        })
    for o in overrides:
        if isinstance(o, OverridePeriod):
            report['overrides'].append({'id': o.id, 'type': 'add', 'from': iso(o.from_date), 'to': iso(o.to_date), 'pattern_id': getattr(o.pattern,'id',None)})
        else:
            report['overrides'].append({'id': o.id, 'type': 'remove', 'from': iso(o.from_date), 'to': iso(o.to_date)})

    cur = window_start
    while cur <= window_end:
        sources = []
        # patterns that have cur in their generated days
        for p in patterns:
            pdays = pat_map.get(p.id, [])
            if cur in pdays:
                sources.append({'kind': 'pattern', 'id': p.id})
        # overrides that affect cur
        for o in overrides:
            if o.from_date <= cur <= o.to_date:
                if isinstance(o, OverridePeriod):
                    sources.append({'kind': 'override_add', 'id': o.id, 'pattern_id': getattr(o.pattern, 'id', None)})
                else:
                    sources.append({'kind': 'override_remove', 'id': o.id})
        report['days'][iso(cur)] = {
            'in_base_patterns': any(s['kind']=='pattern' for s in sources),
            'sources': sources,
            'visit_status': None
        }
        if cur in status:
            vs = status[cur]
            report['days'][iso(cur)]['visit_status'] = {'a': bool(vs.present_child_a), 'b': bool(vs.present_child_b)}
        cur += datetime.timedelta(days=1)

    # save report
    t = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    outdir = Path('scripts')/ 'reports'
    outdir.mkdir(parents=True, exist_ok=True)
    out_fn = outdir / f'analysis_{iso(window_start)}_{iso(window_end)}_{t}.json'
    with open(out_fn, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    print('Analysis saved to', out_fn)
    db.close()
    return str(out_fn)


if __name__ == '__main__':
    s = sys.argv[1] if len(sys.argv)>1 else '2025-08-09'
    e = sys.argv[2] if len(sys.argv)>2 else '2025-08-26'
    ws = datetime.date.fromisoformat(s)
    we = datetime.date.fromisoformat(e)
    # Do a backup first
    default_db = os.path.join(os.path.expanduser('~'), '.kidscompass', 'kidscompass.db')
    if os.path.exists(default_db):
        bdb, bsql = backup_db(default_db)
        print('DB backup created:', bdb)
        print('SQL dump created:', bsql)
    else:
        print('Warning: default DB not found at', default_db)

    out = analyze(ws, we, db_path=None)
    print('Report:', out)
