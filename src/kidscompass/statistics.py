from datetime import date
from typing import List, Dict
from kidscompass.data import Database
from kidscompass.models import VisitStatus


def count_missing_by_weekday(db: Database) -> dict[int, dict[str, int]]:
    """
    0 -> {'missed_a': Anzahl Tage, an denen A fehlt (inkl. beide fehlen)}
    1 -> {'missed_b': Anzahl Tage, an denen B fehlt (inkl. beide fehlen)}
    2 -> {'both_missing': Anzahl Tage, an denen beide fehlen}
    """
    status = db.load_all_status()
    missed_a     = sum(1 for vs in status.values() if not vs.present_child_a)
    missed_b     = sum(1 for vs in status.values() if not vs.present_child_b)
    both_missing = sum(1 for vs in status.values()
                       if not vs.present_child_a and not vs.present_child_b)

    return {
        0: {'missed_a': missed_a},
        1: {'missed_b': missed_b},
        2: {'both_missing': both_missing},
    }


def summarize_visits(planned: List[date], visit_status: Dict[date, VisitStatus]) -> Dict[str, int]:
    """
    Gesamt-Zusammenfassung für gegebene Liste geplanter Termine:
      total         : Gesamtzahl der Termine
      missed_a      : Anzahl Termine, an denen Kind A nicht da war
      missed_b      : Anzahl Termine, an denen Kind B nicht da war
      both_present  : Anzahl Termine, an denen beide Kinder da waren
      both_missing  : Anzahl Termine, an denen beide Kinder fehlten
    """
    total = len(planned)
    missed_a = sum(1 for d in planned
                   if d in visit_status and not visit_status[d].present_child_a)
    missed_b = sum(1 for d in planned
                   if d in visit_status and not visit_status[d].present_child_b)
    both_missing = sum(1 for d in planned
                       if d in visit_status and not visit_status[d].present_child_a and not visit_status[d].present_child_b)
    both_present = sum(1 for d in planned
                       if d not in visit_status or (visit_status[d].present_child_a and visit_status[d].present_child_b))

    return {
        'total': total,
        'missed_a': missed_a,
        'missed_b': missed_b,
        'both_missing': both_missing,
        'both_present': both_present,
    }


def calculate_trends(filtered_visits: List[Dict], period: str = 'weekly') -> Dict[str, List[int]]:
    """Berechnet Trends basierend auf gefilterten Besuchsdaten."""
    from collections import defaultdict
    from datetime import timedelta

    trends = defaultdict(int)

    for visit in filtered_visits:
        day = visit['day']
        if period == 'weekly':
            key = day.isocalendar()[1]  # Kalenderwoche
        elif period == 'monthly':
            key = day.month
        else:
            key = day.year

        trends[key] += 1

    sorted_keys = sorted(trends.keys())
    return {"periods": sorted_keys, "counts": [trends[k] for k in sorted_keys]}
