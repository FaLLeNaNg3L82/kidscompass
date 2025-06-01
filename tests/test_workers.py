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
    worker = BackupWorker(db, str(tmp_path / "backup.sql"))
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
    db = DummyDB()
    worker = BackupWorker(db, "/invalid/path/backup.sql")
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
    db = DummyDB()
    db.exported = str(tmp_path / "backup.sql")  # Simulate existing backup file
    worker = RestoreWorker(db, db.exported, DummyParent())
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
    assert db.imported == db.exported

def test_restore_worker_failure(qapp, tmp_path):
    db = DummyDB()
    # Use invalid path pattern that DummyDB expects
    worker = RestoreWorker(db, "/invalid/path/backup.sql", DummyParent())
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

    worker = ExportWorker(qapp, df, dt, [], [], visit_status)
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

    # Check for report file in current working directory
    report_file = os.path.abspath("kidscompass_report.pdf")
    assert os.path.exists(report_file)

    # Clean up
    os.remove(report_file)


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
