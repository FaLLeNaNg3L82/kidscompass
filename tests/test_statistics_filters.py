import pytest
from datetime import date
from kidscompass.data import Database
from kidscompass.statistics import calculate_trends
import os
import tempfile

def setup_test_db():
    # Temporäre Datenbank für Tests
    tmp = tempfile.NamedTemporaryFile(delete=False)
    db = Database(tmp.name)
    # Füge Testdaten hinzu
    db.conn.execute("INSERT INTO visit_status (day, present_child_a, present_child_b) VALUES (?, ?, ?)", ("2024-06-01", 1, 1))
    db.conn.execute("INSERT INTO visit_status (day, present_child_a, present_child_b) VALUES (?, ?, ?)", ("2024-06-02", 0, 1))
    db.conn.execute("INSERT INTO visit_status (day, present_child_a, present_child_b) VALUES (?, ?, ?)", ("2024-06-03", 1, 0))
    db.conn.execute("INSERT INTO visit_status (day, present_child_a, present_child_b) VALUES (?, ?, ?)", ("2024-06-04", 0, 0))
    db.conn.commit()
    return db, tmp.name

def test_query_visits_filters():
    db, dbfile = setup_test_db()
    # Filter: nur Sonntage (weekday=6)
    res = db.query_visits(date(2024,6,1), date(2024,6,4), [6], {})
    assert any(v['day'].weekday() == 6 for v in res)
    # Filter: beide da
    res = db.query_visits(date(2024,6,1), date(2024,6,4), [], {'both_present': True})
    assert all(v['present_child_a'] and v['present_child_b'] for v in res)
    # Filter: beide fehlen
    res = db.query_visits(date(2024,6,1), date(2024,6,4), [], {'both_absent': True})
    assert all(not v['present_child_a'] and not v['present_child_b'] for v in res)
    db.conn.close()
    os.unlink(dbfile)

def test_trend_calculation():
    db, dbfile = setup_test_db()
    visits = db.query_visits(date(2024,6,1), date(2024,6,4), [], {})
    trends = calculate_trends(visits, period='weekly')
    assert 'periods' in trends and 'counts' in trends
    db.conn.close()
    os.unlink(dbfile)

def test_statistics_export(tmp_path):
    db, dbfile = setup_test_db()
    visits = db.query_visits(date(2024,6,1), date(2024,6,4), [], {})
    # --- CSV Export ---
    import csv
    csv_file = tmp_path / "stats_export.csv"
    # Simulate CSV export (header + rows)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["day", "present_child_a", "present_child_b"])
        writer.writeheader()
        for v in visits:
            writer.writerow({
                "day": v["day"].isoformat() if hasattr(v["day"], "isoformat") else v["day"],
                "present_child_a": int(v["present_child_a"]),
                "present_child_b": int(v["present_child_b"]),
            })
    assert csv_file.exists()
    with open(csv_file, encoding="utf-8") as f:
        lines = f.readlines()
    assert lines[0].startswith("day,present_child_a,present_child_b")
    assert len(lines) == len(visits) + 1
    # --- PDF Export (mocked) ---
    try:
        from reportlab.pdfgen import canvas
        pdf_file = tmp_path / "stats_export.pdf"
        c = canvas.Canvas(str(pdf_file))
        c.drawString(100, 750, "Test PDF Export")
        c.save()
        assert pdf_file.exists() and pdf_file.stat().st_size > 0
        # --- Detaillierte PDF-Inhaltsprüfung ---
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_file))
            text = "".join(page.extract_text() or "" for page in reader.pages)
            assert "Test PDF Export" in text
        except ImportError:
            pytest.skip("pypdf not installed for PDF content check")
    except ImportError:
        pytest.skip("reportlab not installed")
    db.conn.close()
    os.unlink(dbfile)
