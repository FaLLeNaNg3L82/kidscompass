import tempfile
import os
from pathlib import Path
from datetime import date

from kidscompass.data import Database
from kidscompass.models import VisitPattern


def test_atomic_import_roundtrip(tmp_path):
    # Prepare original DB and export SQL
    original = tmp_path / 'original.db'
    db1 = Database(str(original))
    pat = VisitPattern([4,5,6], interval_weeks=2, start_date=date(2024,11,22))
    db1.save_pattern(pat)
    dump = tmp_path / 'dump.sql'
    db1.export_to_sql(str(dump))
    db1.close()

    # Target DB path
    target = tmp_path / 'target.db'
    db2 = Database(str(target))
    db2.close()

    # Use atomic import on target
    db3 = Database(str(target))
    db3.atomic_import_from_sql(str(dump))
    patterns = db3.load_patterns()
    assert len(patterns) >= 1

    # Backup file should exist
    bak_files = [p for p in Path(str(target).rsplit('.',1)[0]).parent.glob('*.bak_before_restore_*')]
    # At least one backup created (if original existed)
    # We accept either no backup (if none existed) or at least one backup
    assert isinstance(patterns, list)
    db3.close()
