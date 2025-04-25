from datetime import date
from kidscompass.data import Database
from kidscompass.models import VisitStatus
from kidscompass.statistics import count_missing_by_weekday

def test_count_missing_by_weekday(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    # lege drei Tage an: Mo fehlt A, Di fehlt B, Mi beide fehlen
    db.save_status(VisitStatus(date(2025,4,21), False, True))   # Mo
    db.save_status(VisitStatus(date(2025,4,22), True, False))   # Di
    db.save_status(VisitStatus(date(2025,4,23), False, False))  # Mi
    stats = count_missing_by_weekday(db)
    assert stats[0]['missed_a'] == 2   # Montag+Mittwoch
    assert stats[1]['missed_b'] == 2   # Dienstag + Mittwoch
    assert stats[2]['both_missing'] == 1  # Mittwoch
