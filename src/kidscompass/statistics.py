from datetime import date
from typing import List, Dict
from kidscompass.data import Database
from kidscompass.models import VisitStatus


def count_missing_by_weekday(db: Database) -> Dict[int, Dict[str, int]]:
    """
    Aggregierte Statistik für Besuchsausfälle pro Wochentag:
      0    -> {'missed_a': Anzahl Tage, an denen Kind A fehlt (inkl. Tage, an denen beide fehlen),
               'missed_b': Anzahl Tage, an denen Kind B fehlt (inkl. Tage, an denen beide fehlen),
               'both_missing': Anzahl Tage, an denen beide Kinder fehlen,
               'both_present': Anzahl Tage, an denen beide anwesend waren}
      1..6 analog für Di..So
    """
    status = db.load_all_status()
    # Initialisiere Zähler
    counter = {i: {'missed_a': 0, 'missed_b': 0, 'both_missing': 0, 'both_present': 0}
               for i in range(7)}

    for vs in status.values():
        wd = vs.day.weekday()
        a_missing = not vs.present_child_a
        b_missing = not vs.present_child_b

        if a_missing:
            counter[wd]['missed_a'] += 1
        if b_missing:
            counter[wd]['missed_b'] += 1
        if a_missing and b_missing:
            counter[wd]['both_missing'] += 1
        if vs.present_child_a and vs.present_child_b:
            counter[wd]['both_present'] += 1

    return counter


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
