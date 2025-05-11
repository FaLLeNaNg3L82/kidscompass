# tests/test_sql_backup_restore.py

import tempfile
from pathlib import Path
from datetime import date

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
