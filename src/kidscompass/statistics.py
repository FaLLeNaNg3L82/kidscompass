from datetime import date
from kidscompass.data import Database

def count_missing_by_weekday(db: Database) -> dict[int, dict[str, int]]:
    """
    Aggregierte Statistik für Besuchsausfälle pro Wochentag:
      0 -> {'missed_a': Anzahl Tage, an denen Kind A fehlt (inkl. Tage, an denen beide fehlen)}
      1 -> {'missed_b': Anzahl Tage, an denen Kind B fehlt (inkl. Tage, an denen beide fehlen)}
      2 -> {'both_missing': Anzahl Tage, an denen beide Kinder fehlen}
    """
    status = db.load_all_status()
    counter = {i: {'missed_a':0, 'missed_b':0, 'both_missing':0, 'both_present':0}
               for i in range(7)}

    for vs in status.values():
        wd = vs.day.weekday()
        a_missing = not vs.present_child_a
        b_missing = not vs.present_child_b

        if a_missing:    counter[wd]['missed_a'] += 1
        if b_missing:    counter[wd]['missed_b'] += 1
        if a_missing and b_missing:
            counter[wd]['both_missing'] += 1
        if vs.present_child_a and vs.present_child_b:
            counter[wd]['both_present'] += 1

    return counter