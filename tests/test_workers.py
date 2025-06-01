import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QThread, QCoreApplication, QEventLoop
from kidscompass.ui import BackupWorker, RestoreWorker, ExportWorker
from datetime import date
from kidscompass.data import Database
import os

class DummyDB:
    def __init__(self):
        self.conn = MagicMock()
        self.conn.execute = MagicMock()
        self.conn.commit = MagicMock()
        self.conn.close = MagicMock()

    def export_to_sql(self, fn):
        if '/invalid/' in fn or not fn:
            raise IOError(f"Cannot write to invalid path: {fn}")
        self.exported = fn
        
    def import_from_sql(self, fn):
        if '/invalid/' in fn or not fn or not fn.endswith('.sql'):
            raise IOError(f"Cannot read from invalid path: {fn}")
        self.imported = fn
        
    def load_all_status(self):
        return {}
        
    def load_patterns(self):
        return []
        
    def load_overrides(self):
        return []
    def close(self):
        pass
    def save_pattern(self, pat):
        pass
    def save_override(self, ov):
        pass
    def delete_pattern(self, id):
        pass
    def delete_override(self, id):
        pass
    def save_status(self, vs):
        pass
    def delete_status(self, d):
        pass
    def clear_status(self):
        pass

class DummyParent:
    def __init__(self):
        self.db = DummyDB()
        self.visit_status = {}
        self.patterns = []
        self.overrides = []
    def refresh_calendar(self):
        self.refreshed = True

@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app

# --- BackupWorker ---
def test_backup_worker_success(qapp, tmp_path):
    db = DummyDB()
    db_path = str(tmp_path / "backup.sql")
    worker = BackupWorker(db_path, db_path)
    results = []
    errors = []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()

    assert results
    assert not errors


def test_backup_worker_failure(qapp, tmp_path):
    db_path = "/invalid/path/backup.sql"
    worker = BackupWorker(db_path, db_path)
    results = []
    errors = []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()

    assert not results
    assert errors

# --- RestoreWorker ---
def test_restore_worker_success(qapp, tmp_path):
    # Erzeuge eine echte SQLite-DB und exportiere sie mit BackupWorker
    dbfile = tmp_path / "test_restore.db"
    db = Database(str(dbfile))
    db.conn.execute("CREATE TABLE IF NOT EXISTS visit_status (day TEXT, present_child_a INTEGER, present_child_b INTEGER)")
    db.conn.commit()
    db.conn.close()
    backup_file = tmp_path / "backup.sql"
    backup_worker = BackupWorker(str(dbfile), str(backup_file))
    backup_results = []
    backup_errors = []
    backup_worker.finished.connect(backup_results.append)
    backup_worker.error.connect(backup_errors.append)
    thread_b = QThread()
    backup_worker.moveToThread(thread_b)
    thread_b.started.connect(backup_worker.run)
    thread_b.start()
    thread_b.quit()
    thread_b.wait()
    assert backup_results
    # Jetzt RestoreWorker auf die exportierte Datei anwenden
    worker = RestoreWorker(str(dbfile), str(backup_file), DummyParent())
    results = []
    errors = []
    worker.finished.connect(lambda: results.append("done"))
    worker.error.connect(errors.append)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()
    assert results
    assert not errors
    # assert db.imported == db.exported  # DummyDB check entfällt

def test_restore_worker_failure(qapp, tmp_path):
    db_path = "/invalid/path/backup.sql"
    worker = RestoreWorker(db_path, db_path, DummyParent())
    results = []
    errors = []
    worker.finished.connect(lambda: results.append("done"))
    worker.error.connect(errors.append)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()

    assert not results
    assert errors

# --- ExportWorker ---
def test_export_worker_success(qapp, tmp_path):
    dbfile = tmp_path / "test_export.db"
    db = Database(str(dbfile))
    db.conn.execute("INSERT INTO visit_status (day, present_child_a, present_child_b) VALUES (?, ?, ?)", ("2023-01-01", 1, 1))
    db.conn.commit()
    db.conn.close()

    visit_status = {date(2023, 1, 1): {'present_child_a': 1, 'present_child_b': 1}}

    df = date(2023, 1, 1)
    dt = date(2023, 1, 2)
    report_file = tmp_path / "kidscompass_report.pdf"
    worker = ExportWorker(qapp, df, dt, [], [], visit_status, out_fn=str(report_file))
    results = []
    errors = []
    worker.finished.connect(lambda: results.append("done"))
    worker.error.connect(errors.append)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()

    assert results
    assert not errors

    # Check for report file in tmp_path
    assert report_file.exists()

    # Clean up
    report_file.unlink()


def test_export_worker_failure(qapp, tmp_path):
    db = DummyDB()
    worker = ExportWorker(db, "/invalid/path/export.sql", [], [], {}, {})
    results = []
    errors = []
    worker.finished.connect(lambda: results.append("done"))
    worker.error.connect(errors.append)

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()
    thread.quit()
    thread.wait()

    assert not results
    assert errors
