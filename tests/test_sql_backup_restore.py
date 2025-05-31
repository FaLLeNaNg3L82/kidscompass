# tests/test_sql_backup_restore.py

import tempfile
from pathlib import Path
from datetime import date
import os

import pytest

from kidscompass.data import Database
from kidscompass.models import VisitStatus

def test_export_import_roundtrip(tmp_path):
    # 1) Erzeuge "Original-DB" und speichere einen VisitStatus
    db_path = tmp_path / "original.db"
    db1 = Database(str(db_path))
    vs_in = VisitStatus(day=date(2025, 1, 1), present_child_a=False, present_child_b=True)
    db1.save_status(vs_in)

    # 2) Exportiere kompletten SQLite-Dump in eine .sql-Datei
    dump_file = tmp_path / "dump.sql"
    db1.export_to_sql(str(dump_file))
    assert dump_file.exists() and dump_file.stat().st_size > 0

    # 3) Erzeuge neue leere DB und importiere den Dump
    restored_path = tmp_path / "restored.db"
    db2 = Database(str(restored_path))
    db2.import_from_sql(str(dump_file))

    # 4) Lade alle VisitStatus aus der wiederhergestellten DB
    stats = db2.load_all_status()
    #      Der Eintrag vom 2025-01-01 muss vorhanden sein
    assert date(2025, 1, 1) in stats

    # 5) Prüfe, dass die Felder korrekt wiederhergestellt wurden
    vs_out = stats[date(2025, 1, 1)]
    assert vs_out.present_child_a is False
    assert vs_out.present_child_b is True

@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        yield tf.name
    os.remove(tf.name)

@pytest.fixture
def db():
    # Erstelle eine neue temporäre Datenbank
    db = Database(':memory:')
    # Beispiel-Daten einfügen, falls nötig
    yield db
    db.close()


def test_export_import(db, temp_db_path):
    # Exportiere die Datenbank in eine temporäre Datei
    db.export_to_sql(temp_db_path)

    # Erstelle eine neue Datenbankinstanz und importiere die Daten
    db2 = Database(':memory:')
    db2.import_from_sql(temp_db_path)

    # Vergleiche Daten (z.B. Anzahl der Muster und Overrides)
    patterns1 = db.load_patterns()
    patterns2 = db2.load_patterns()
    overrides1 = db.load_overrides()
    overrides2 = db2.load_overrides()

    assert len(patterns1) == len(patterns2)
    assert len(overrides1) == len(overrides2)

    db2.close()
