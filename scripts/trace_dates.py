import sys
import os
import datetime
sys.path.insert(0, r'd:\Programmieren\kidscompass\src')
from kidscompass.data import Database
from kidscompass.calendar_logic import generate_standard_days, apply_overrides

START = datetime.date(2025,8,9)
END = datetime.date(2025,8,26)

db = Database()
patterns = db.load_patterns()
overrides = db.load_overrides()
visit_status = db.load_all_status()

print(f'Patterns in DB ({len(patterns)}):')
for p in patterns:
    print(f' - id={getattr(p,"id",None)} weekdays={p.weekdays} interval={p.interval_weeks} start={p.start_date} end={p.end_date}')
print('\nOverrides in DB ({len(overrides)}):')
for o in overrides:
    if hasattr(o, 'pattern'):
        pid = getattr(o.pattern, 'id', None)
    else:
        pid = None
    print(f' - id={getattr(o,"id",None)} type={type(o).__name__} from={o.from_date} to={o.to_date} pattern_id={pid}')

# compute raw standard days from all patterns across relevant years
raw = []
for p in patterns:
    syear = p.start_date.year
    eyear = (p.end_date.year if p.end_date else END.year)
    for y in range(syear, eyear+1):
        raw.extend(generate_standard_days(p, y))
raw = sorted(set(raw))
planned = apply_overrides(raw, overrides)
planned_set = set(planned)

print('\nDates from', START.isoformat(), 'to', END.isoformat())
for d in (START + datetime.timedelta(days=i) for i in range((END-START).days+1)):
    sources = []
    # patterns that would generate d
    for p in patterns:
        for y in range(p.start_date.year, (p.end_date.year if p.end_date else END.year)+1):
            if d in generate_standard_days(p, y):
                sources.append(f'pattern id={getattr(p,"id",None)}')
                break
    # overrides affecting d
    ovsrc = []
    for ov in overrides:
        if ov.from_date <= d <= ov.to_date:
            ovsrc.append(f'{type(ov).__name__}(id={getattr(ov,"id",None)})')
    is_planned = d in planned_set
    vs = visit_status.get(d, None)
    print(f'{d.isoformat()}: planned={is_planned} patterns={sources} overrides={ovsrc} visit_status={vs}')

db.close()
