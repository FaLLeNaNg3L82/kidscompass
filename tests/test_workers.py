import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QThread, QCoreApplication
from kidscompass.ui import StatisticsWorker, BackupWorker, RestoreWorker, ExportWorker
from datetime import date

class DummyDB:
    def export_to_sql(self, fn):
        self.exported = fn
    def import_from_sql(self, fn):
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

# --- StatisticsWorker ---
def test_statistics_worker_success(qapp):
    db = MagicMock()
    db.return_value = [
        {'missed_a': 1},
        {'missed_b': 2},
        {'both_missing': 3}
    ]
    with patch('kidscompass.ui.count_missing_by_weekday', return_value=db.return_value):
        worker = StatisticsWorker(db)
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        assert results[0] == db.return_value
        assert not errors

def test_statistics_worker_error(qapp):
    db = MagicMock()
    with patch('kidscompass.ui.count_missing_by_weekday', side_effect=Exception("fail")):
        worker = StatisticsWorker(db)
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        assert not results
        assert errors and "fail" in errors[0]

# --- BackupWorker ---
def test_backup_worker_success(qapp):
    db = DummyDB()
    worker = BackupWorker(db, "test.sql")
    results = []
    errors = []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)
    worker.run()
    assert results[0] == "test.sql"
    assert not errors

def test_backup_worker_oserror(qapp):
    db = MagicMock()
    db.export_to_sql.side_effect = OSError("disk full")
    worker = BackupWorker(db, "fail.sql")
    results = []
    errors = []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)
    worker.run()
    assert not results
    assert errors and "disk full" in errors[0]

# --- RestoreWorker ---
def test_restore_worker_success(qapp):
    db = DummyDB()
    parent = DummyParent()
    worker = RestoreWorker(db, "test.sql", parent)
    results = []
    errors = []
    worker.finished.connect(lambda: results.append("done"))
    worker.error.connect(errors.append)
    worker.run()
    assert results and results[0] == "done"
    assert not errors
    assert hasattr(parent, "visit_status")
    assert hasattr(parent, "patterns")
    assert hasattr(parent, "overrides")
    assert hasattr(parent, "refresh_calendar")

# --- ExportWorker ---
def test_export_worker_image_missing(qapp):
    parent = DummyParent()
    with patch('os.path.exists', return_value=False):
        worker = ExportWorker(parent, None, None, [], [], {})
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        assert not results
        assert errors and "Start- und Enddatum" in errors[0]

def test_export_worker_success(qapp):
    parent = DummyParent()
    # Provide a minimal planned date and visit_status so charts are generated
    planned_date = date(2025, 6, 1)
    parent.patterns = [MagicMock()]  # Not used directly, but required for signature
    parent.overrides = []
    parent.visit_status = {planned_date: MagicMock(present_child_a=False, present_child_b=False)}
    # Patch generate_standard_days and apply_overrides to return our planned_date
    with patch('os.path.exists', return_value=True), \
         patch('kidscompass.ui.create_pie_chart') as mock_chart, \
         patch('reportlab.pdfgen.canvas.Canvas') as mock_canvas, \
         patch('kidscompass.ui.generate_standard_days', return_value=[planned_date]), \
         patch('kidscompass.ui.apply_overrides', return_value=[planned_date]), \
         patch('kidscompass.ui.summarize_visits', return_value={
             'total': 1, 'missed_a': 1, 'missed_b': 1, 'both_present': 0, 'both_missing': 1
         }):
        mock_canvas.return_value.drawString = MagicMock()
        mock_canvas.return_value.setFont = MagicMock()
        mock_canvas.return_value.drawImage = MagicMock()
        mock_canvas.return_value.showPage = MagicMock()
        mock_canvas.return_value.save = MagicMock()
        worker = ExportWorker(parent, date(2025,1,1), date(2025,12,31), parent.patterns, parent.overrides, parent.visit_status)
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        assert results and 'PDF erstellt' in results[0]
        assert not errors
        assert mock_chart.call_count == 3
        assert mock_canvas.return_value.save.called

def test_export_worker_pdf_error(qapp):
    parent = DummyParent()
    with patch('os.path.exists', return_value=True), \
         patch('kidscompass.charts.create_pie_chart'), \
         patch('reportlab.pdfgen.canvas.Canvas', side_effect=Exception('PDF fail')):
        worker = ExportWorker(parent, date(2025,1,1), date(2025,12,31), [], [], {})
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        assert not results
        assert errors and 'PDF fail' in errors[0]
