import os
import tempfile
from datetime import date
import pytest

from kidscompass.data import Database
from kidscompass.models import VisitStatus

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    db = Database(db_path=path)
    try:
        yield db
    finally:
        # Erst die DB‐Verbindung schließen, dann die Datei löschen
        db.conn.close()
        os.remove(path)

def test_save_and_load_status(temp_db):
    db = temp_db
    vs = VisitStatus(day=date(2025,4,25), present_child_a=False, present_child_b=True)
    db.save_status(vs)
    loaded = db.load_all_status()
    assert date(2025,4,25) in loaded
    assert not loaded[date(2025,4,25)].present_child_a
    assert loaded[date(2025,4,25)].present_child_b

def test_clear_status(temp_db):
    db = temp_db
    db.save_status(VisitStatus(day=date.today(), present_child_a=True, present_child_b=True))
    assert db.load_all_status()
    db.clear_status()
    assert db.load_all_status() == {}
