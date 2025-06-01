import sys
import datetime
from typing import List
import os
import logging

import matplotlib
matplotlib.use("Agg")

from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from kidscompass.charts import create_pie_chart
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QCalendarWidget, QCheckBox, QPushButton, QLabel,
    QSpinBox, QListWidget, QListWidgetItem, QMessageBox, QDateEdit,
    QComboBox, QGroupBox, QRadioButton, QGridLayout, QTextEdit, QFileDialog
)
from PySide6.QtGui import QTextCharFormat, QBrush, QColor
from PySide6.QtCore import Qt, QDate, QThread, Signal, QObject, QMutex
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.data import Database
from kidscompass.statistics import count_missing_by_weekday, summarize_visits, calculate_trends
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
import tempfile



# === Constants ===
SQL_FILE_FILTER = "SQL-Datei (*.sql)"
BACKUP_TITLE = "Backup speichern als"
RESTORE_TITLE = "Backup wiederherstellen"
RESTORE_CONFIRM_TITLE = "Restore bestätigen"
RESTORE_CONFIRM_TEXT = "Achtung: Alle aktuellen Einträge werden überschrieben.\nWeiter?"
BACKUP_SUCCESS_TITLE = "Backup"
BACKUP_SUCCESS_TEXT = "Datenbank erfolgreich exportiert nach:\n{fn}"
BACKUP_ERROR_TITLE = "Backup-Fehler"
RESTORE_SUCCESS_TITLE = "Restore"
RESTORE_SUCCESS_TEXT = "Datenbank erfolgreich wiederhergestellt."
RESTORE_ERROR_TITLE = "Restore-Fehler"

# Farbkonstanten
COLOR_PLANNED = '#A0C4FF'
COLOR_BOTH_ABSENT = '#FFADAD'
COLOR_A_ABSENT = '#FFD97D'
COLOR_B_ABSENT = '#A0FFA0'
COLOR_BOTH_PRESENT = COLOR_B_ABSENT  # Für Konsistenz, beide da = grün
COLOR_AT_LEAST_ONE_ABSENT = COLOR_A_ABSENT  # Mindestens ein Kind fehlt = gelb
COLOR_BOTH_MISSING = '#FF0000'  # Beide fehlen = rot


def qdate_to_date(qdate):
    """Hilfsfunktion: QDate -> datetime.date"""
    return qdate.toPython() if hasattr(qdate, 'toPython') else datetime.date(qdate.year(), qdate.month(), qdate.day())

# === UI Text Constants ===
BACKUP_BTN_TEXT = "DB Backup"
RESTORE_BTN_TEXT = "DB Restore"
EXPORT_BTN_TEXT = "Export starten"
PATTERN_BTN_TEXT = "Pattern hinzufügen"
OVERRIDE_BTN_TEXT = "Override hinzufügen"
DELETE_BTN_TEXT = "Eintrag löschen"
RESET_BTN_TEXT = "Alle zurücksetzen"
CALENDAR_LABEL = "📅 Besuchsmuster:"
CHILD_LABEL = "Kinder:"
INTERVAL_LABEL = "Intervall (Wochen):"
FROM_LABEL = "Von:"
TO_LABEL = "Bis:"
INFINITE_LABEL = "Bis unendlich"
STATISTICS_BTN_TEXT = "Statistik berechnen"

# Hilfsfunktion für Kalender-Formatierung
from PySide6.QtGui import QTextCharFormat, QBrush, QColor

def set_date_format(calendar, date_obj, color_hex):
    qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
    fmt = QTextCharFormat()
    fmt.setBackground(QBrush(QColor(color_hex)))
    calendar.setDateTextFormat(qdate, fmt)

class SettingsTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        # Besuchsmuster
        layout.addWidget(QLabel(CALENDAR_LABEL))
        wd_layout = QHBoxLayout()
        self.weekday_checks = []
        for i, day in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(day)
            wd_layout.addWidget(cb)
            self.weekday_checks.append((i, cb))
        layout.addLayout(wd_layout)

        # Intervall, Start- und Enddatum
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel(INTERVAL_LABEL))
        self.interval = QSpinBox(); self.interval.setRange(1, 52); self.interval.setValue(1)
        param_layout.addWidget(self.interval)
        param_layout.addWidget(QLabel(FROM_LABEL))
        self.start_date = QDateEdit(QDate(datetime.date.today().year, 1, 1)); self.start_date.setCalendarPopup(True)
        param_layout.addWidget(self.start_date)
        param_layout.addWidget(QLabel(TO_LABEL))
        self.end_date = QDateEdit(QDate(datetime.date.today().year, 12, 31)); self.end_date.setCalendarPopup(True)
        param_layout.addWidget(self.end_date)
        self.chk_infinite = QCheckBox(INFINITE_LABEL)
        param_layout.addWidget(self.chk_infinite)
        self.btn_pattern = QPushButton(PATTERN_BTN_TEXT)
        param_layout.addWidget(self.btn_pattern)
        layout.addLayout(param_layout)

        # Override
        layout.addWidget(QLabel("🔄 Override:"))
        ov_group = QGroupBox()
        ov_layout = QHBoxLayout(ov_group)
        self.ov_add = QRadioButton("Urlaubs-Add"); self.ov_add.setChecked(True)
        self.ov_remove = QRadioButton("Urlaubs-Remove")
        ov_layout.addWidget(self.ov_add); ov_layout.addWidget(self.ov_remove)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel(FROM_LABEL))
        self.ov_from = QDateEdit(QDate.currentDate()); self.ov_from.setCalendarPopup(True)
        date_layout.addWidget(self.ov_from)
        date_layout.addWidget(QLabel(TO_LABEL))
        self.ov_to = QDateEdit(QDate.currentDate()); self.ov_to.setCalendarPopup(True)
        date_layout.addWidget(self.ov_to)
        ov_layout.addLayout(date_layout)
        self.btn_override = QPushButton(OVERRIDE_BTN_TEXT)
        ov_layout.addWidget(self.btn_override)
        layout.addWidget(ov_group)

        # Einträge
        layout.addWidget(QLabel("Einträge:"))
        self.entry_list = QListWidget()
        layout.addWidget(self.entry_list)
        btns = QHBoxLayout()
        self.btn_delete = QPushButton(DELETE_BTN_TEXT)
        btns.addWidget(self.btn_delete)
        layout.addLayout(btns)

        # Signale
        self.btn_pattern.clicked.connect(self.parent.on_add_pattern)
        self.btn_override.clicked.connect(self.parent.on_add_override)
        self.btn_delete.clicked.connect(self.parent.on_delete_entry)

class StatusTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        hl = QHBoxLayout(); hl.addWidget(QLabel(CHILD_LABEL))
        self.child_count = QComboBox(); self.child_count.addItems([str(i) for i in range(1,6)])
        hl.addWidget(self.child_count); layout.addLayout(hl)

        self.child_checks = []
        self.grid = QGridLayout(); layout.addLayout(self.grid)
        self.btn_reset = QPushButton(RESET_BTN_TEXT)
        layout.addWidget(self.btn_reset)

        self.calendar = QCalendarWidget(); self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        self.child_count.currentIndexChanged.connect(self.parent.on_child_count_changed)
        self.btn_reset.clicked.connect(self.parent.on_reset_status)
        self.calendar.selectionChanged.connect(self.parent.on_calendar_click)

class ExportTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        btn_backup  = QPushButton(BACKUP_BTN_TEXT)
        btn_restore = QPushButton(RESTORE_BTN_TEXT)
        hl.addWidget(btn_backup)
        hl.addWidget(btn_restore)
        layout.addLayout(hl)

        hl2 = QHBoxLayout()
        hl2.addWidget(QLabel(FROM_LABEL))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        hl2.addWidget(self.date_from)
        hl2.addWidget(QLabel(TO_LABEL))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        hl2.addWidget(self.date_to)
        layout.addLayout(hl2)

        layout.addWidget(QLabel(""))
        self.btn_export = QPushButton(EXPORT_BTN_TEXT)
        layout.addWidget(self.btn_export)

        btn_backup.clicked.connect(self.on_backup)
        btn_restore.clicked.connect(self.on_restore)
        self.btn_export.clicked.connect(self.parent.on_export)

    def on_backup(self):
        if hasattr(self.parent, 'backup_thread') and self.parent.backup_thread and self.parent.backup_thread.isRunning():
            return
        fn, _ = QFileDialog.getSaveFileName(self, BACKUP_TITLE, filter=SQL_FILE_FILTER)
        if not fn:
            return
        self.backup_thread = QThread()
        db_path = self.parent.db.db_path if hasattr(self.parent.db, 'db_path') else self.parent.db.filename
        self.backup_worker = BackupWorker(db_path, fn)
        self.backup_worker.moveToThread(self.backup_thread)
        self.backup_thread.started.connect(self.backup_worker.run)
        self.backup_worker.finished.connect(self.on_backup_finished)
        self.backup_worker.error.connect(self.on_backup_error)
        self.backup_worker.finished.connect(self.backup_thread.quit)
        self.backup_worker.finished.connect(self.backup_worker.deleteLater)
        self.backup_thread.finished.connect(self.backup_thread.deleteLater)
        self.backup_thread.start()

    def on_backup_finished(self, fn):
        QMessageBox.information(self, BACKUP_SUCCESS_TITLE, BACKUP_SUCCESS_TEXT.format(fn=fn))

    def on_backup_error(self, msg):
        logging.error(f"Backup error: {msg}")
        QMessageBox.critical(self, BACKUP_ERROR_TITLE, msg)

    def on_restore(self):
        if hasattr(self.parent, 'restore_thread') and self.parent.restore_thread and self.parent.restore_thread.isRunning():
            return

        fn, _ = QFileDialog.getOpenFileName(self, RESTORE_TITLE, filter=SQL_FILE_FILTER)
        if not fn:
            return
        confirm = QMessageBox.question(
            self, RESTORE_CONFIRM_TITLE,
            RESTORE_CONFIRM_TEXT)
        if confirm != QMessageBox.Yes:
            return
        self.restore_thread = QThread()
        db_path = self.parent.db.db_path if hasattr(self.parent.db, 'db_path') else self.parent.db.filename
        self.restore_worker = RestoreWorker(db_path, fn, self.parent)
        self.restore_worker.moveToThread(self.restore_thread)
        self.restore_thread.started.connect(self.restore_worker.run)
        self.restore_worker.finished.connect(self.on_restore_finished)
        self.restore_worker.error.connect(self.on_restore_error)
        self.restore_worker.finished.connect(self.restore_thread.quit)
        self.restore_worker.finished.connect(self.restore_worker.deleteLater)
        self.restore_thread.finished.connect(self.restore_thread.deleteLater)
        self.restore_thread.start()

    def on_restore_finished(self):
        QMessageBox.information(self, RESTORE_SUCCESS_TITLE, RESTORE_SUCCESS_TEXT)

    def on_restore_error(self, msg):
        logging.error(f"Restore error: {msg}")
        QMessageBox.critical(self, RESTORE_ERROR_TITLE, msg)

class StatisticsTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        # — Zeitraum —
        period = QHBoxLayout()
        period.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        period.addWidget(self.date_from)
        period.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        period.addWidget(self.date_to)
        layout.addLayout(period)

        # — Wochentags-Filter —
        wd_group = QGroupBox("Wochentage wählen")
        wd_layout = QHBoxLayout(wd_group)
        self.wd_checks = []
        for i, name in enumerate(["Mo","Di","Mi","Do","Fr","Sa","So"]):
            cb = QCheckBox(name)
            wd_layout.addWidget(cb)
            self.wd_checks.append((i, cb))
        layout.addWidget(wd_group)

        # — Status-Filter als Dropdown —
        status_group = QGroupBox("Statistik für ...")
        status_layout = QHBoxLayout(status_group)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Kind A", "Kind B", "Beide"])
        status_layout.addWidget(QLabel("Auswertung für:"))
        status_layout.addWidget(self.status_combo)
        layout.addWidget(status_group)

        # — Export-Buttons —
        btns = QHBoxLayout()
        self.btn_export_csv = QPushButton("CSV Export")
        self.btn_export_pdf = QPushButton("PDF Export")
        btns.addWidget(self.btn_export_csv)
        btns.addWidget(self.btn_export_pdf)
        layout.addLayout(btns)

        # — Ausgabe-Feld —
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result)
        # Trend-Chart
        self.chart_label = QLabel()
        self.chart_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.chart_label)

        # Signals: Filteränderungen triggern Statistik
        self.date_from.dateChanged.connect(self.on_any_filter_changed)
        self.date_to.dateChanged.connect(self.on_any_filter_changed)
        for _, cb in self.wd_checks:
            cb.stateChanged.connect(self.on_any_filter_changed)
        self.status_combo.currentIndexChanged.connect(self.on_any_filter_changed)
        self.btn_export_csv.clicked.connect(self.on_export_csv)
        self.btn_export_pdf.clicked.connect(self.on_export_pdf)

        # Initiale Berechnung
        self.on_any_filter_changed()

    def get_status_mode(self):
        # Gibt zurück, was im Dropdown gewählt ist
        return self.status_combo.currentText()

    def on_any_filter_changed(self):
        sel_wds = [i for i, cb in self.wd_checks if cb.isChecked()]
        start_d = self.date_from.date().toPython()
        end_d   = self.date_to.date().toPython()
        mode = self.get_status_mode()
        db = self.parent.db
        visits_list = db.query_visits(start_d, end_d, sel_wds, {
            "both_present": False,  # Kein Vorfilter mehr, wir werten alles aus
            "a_absent": False,
            "b_absent": False,
            "both_absent": False
        })
        from collections import defaultdict
        weekday_names = ["Mo","Di","Mi","Do","Fr","Sa","So"]
        total = len(visits_list)
        if mode == "Beide":
            # Für beide Kinder getrennt auswerten
            rel_a = sum(1 for v in visits_list if v["present_child_a"])
            rel_b = sum(1 for v in visits_list if v["present_child_b"])
            miss_a = total - rel_a
            miss_b = total - rel_b
            pct_rel_a = round(rel_a/total*100,1) if total else 0.0
            pct_rel_b = round(rel_b/total*100,1) if total else 0.0
            pct_miss_a = round(miss_a/total*100,1) if total else 0.0
            pct_miss_b = round(miss_b/total*100,1) if total else 0.0
            # Wochentagsauswertung
            weekday_count_a = defaultdict(int)
            weekday_count_b = defaultdict(int)
            for v in visits_list:
                if v["present_child_a"]:
                    weekday_count_a[v["day"].weekday()] += 1
                if v["present_child_b"]:
                    weekday_count_b[v["day"].weekday()] += 1
            weekday_stats = [
                f"{weekday_names[i]}: A {weekday_count_a[i]}x ({round(weekday_count_a[i]/total*100,1) if total else 0.0}%), "
                f"B {weekday_count_b[i]}x ({round(weekday_count_b[i]/total*100,1) if total else 0.0}%)"
                for i in range(7)
            ]
            # Entwicklung der letzten 1, 3, 6 Monate
            today = datetime.date.today()
            def count_in_period(months, key):
                from dateutil.relativedelta import relativedelta
                since = today - relativedelta(months=months)
                return sum(1 for v in visits_list if v["day"] >= since and v[key])
            rel_1m_a = count_in_period(1, "present_child_a")
            rel_3m_a = count_in_period(3, "present_child_a")
            rel_6m_a = count_in_period(6, "present_child_a")
            rel_1m_b = count_in_period(1, "present_child_b")
            rel_3m_b = count_in_period(3, "present_child_b")
            rel_6m_b = count_in_period(6, "present_child_b")
            def pct_change(now, prev):
                return round((now-prev)/prev*100,1) if prev else 0.0
            trend_1m_a = pct_change(rel_1m_a, rel_3m_a-rel_1m_a)
            trend_3m_a = pct_change(rel_3m_a, rel_6m_a-rel_3m_a)
            trend_1m_b = pct_change(rel_1m_b, rel_3m_b-rel_1m_b)
            trend_3m_b = pct_change(rel_3m_b, rel_6m_b-rel_3m_b)
            summary = (
                f"Gefundene Termine: {total}\n"
                f"Kind A anwesend: {rel_a} ({pct_rel_a}%)\nKind A abwesend: {miss_a} ({pct_miss_a}%)\n"
                f"Kind B anwesend: {rel_b} ({pct_rel_b}%)\nKind B abwesend: {miss_b} ({pct_miss_b}%)\n"
                f"\nWochentagsauswertung:\n" + "\n".join(weekday_stats) +
                f"\n\nEntwicklung Umgangsfrequenz:\n"
                f"Kind A letzter Monat: {rel_1m_a} ({trend_1m_a}% Veränderung)\nKind A letzte 3 Monate: {rel_3m_a} ({trend_3m_a}% Veränderung)\nKind A letzte 6 Monate: {rel_6m_a}\n"
                f"Kind B letzter Monat: {rel_1m_b} ({trend_1m_b}% Veränderung)\nKind B letzte 3 Monate: {rel_3m_b} ({trend_3m_b}% Veränderung)\nKind B letzte 6 Monate: {rel_6m_b}"
            )
            self.result.setPlainText(summary)
            self.filtered_visits = visits_list
            self.update_trend_chart(visits_list)  # alle visits für beide Linien
        else:
            # Einzelkind-Modus wie gehabt
            relevant = [v for v in visits_list if v["present_child_a"]] if mode=="Kind A" else [v for v in visits_list if v["present_child_b"]]
            missed = [v for v in visits_list if not v["present_child_a"]] if mode=="Kind A" else [v for v in visits_list if not v["present_child_b"]]
            rel = len(relevant)
            miss = len(missed)
            pct_rel = round(rel/total*100,1) if total else 0.0
            pct_miss = round(miss/total*100,1) if total else 0.0
            weekday_count = defaultdict(int)
            for v in relevant:
                weekday_count[v["day"].weekday()] += 1
            weekday_stats = [f"{weekday_names[i]}: {weekday_count[i]}x ({round(weekday_count[i]/total*100,1) if total else 0.0}%)" for i in range(7)]
            today = datetime.date.today()
            def count_in_period(months):
                from dateutil.relativedelta import relativedelta
                since = today - relativedelta(months=months)
                return len([v for v in relevant if v["day"] >= since])
            rel_1m = count_in_period(1)
            rel_3m = count_in_period(3)
            rel_6m = count_in_period(6)
            def pct_change(now, prev):
                return round((now-prev)/prev*100,1) if prev else 0.0
            trend_1m = pct_change(rel_1m, rel_3m-rel_1m)
            trend_3m = pct_change(rel_3m, rel_6m-rel_3m)
            summary = (
                f"Gefundene Termine: {total}\n"
                f"{mode} anwesend: {rel} ({pct_rel}%)\n"
                f"{mode} abwesend: {miss} ({pct_miss}%)\n"
                f"\nWochentagsauswertung ({mode} anwesend):\n" + "\n".join(weekday_stats) +
                f"\n\nEntwicklung Umgangsfrequenz:\nLetzter Monat: {rel_1m} ({trend_1m}% Veränderung)\nLetzte 3 Monate: {rel_3m} ({trend_3m}% Veränderung)\nLetzte 6 Monate: {rel_6m}"
            )
            self.result.setPlainText(summary)
            self.filtered_visits = visits_list
            self.update_trend_chart(relevant)

    def update_trend_chart(self, relevant):
        mode = self.get_status_mode()
        if not self.filtered_visits:
            self.chart_label.clear()
            return
        from collections import Counter, defaultdict
        import calendar
        # Berechne geplante Umgangstage pro Monat
        all_months = set()
        planned_per_month = defaultdict(int)
        for v in self.filtered_visits:
            m = v['day'].replace(day=1)
            planned_per_month[m] += 1
            all_months.add(m)
        sorted_months = sorted(all_months)
        # Berechne tatsächliche Anwesenheit pro Monat
        if mode == 'Beide':
            present_a = defaultdict(int)
            present_b = defaultdict(int)
            for v in self.filtered_visits:
                m = v['day'].replace(day=1)
                if v['present_child_a']:
                    present_a[m] += 1
                if v['present_child_b']:
                    present_b[m] += 1
            x = [m.strftime('%Y-%m') for m in sorted_months]
            y_a = [round(present_a[m]/planned_per_month[m]*100,1) if planned_per_month[m] else 0 for m in sorted_months]
            y_b = [round(present_b[m]/planned_per_month[m]*100,1) if planned_per_month[m] else 0 for m in sorted_months]
            fig, ax = plt.subplots(figsize=(5,2.5))
            ax.plot(x, y_a, marker='o', color='#1976d2', label='Kind A')
            ax.plot(x, y_b, marker='o', color='#d32f2f', label='Kind B')
            ax.set_title('Anwesenheit pro Monat (%)')
            ax.set_xlabel('Monat')
            ax.set_ylabel('Anwesenheit (%)')
            ax.set_ylim(0, 105)
            ax.legend()
            ax.grid(True, linestyle=':')
            plt.xticks(rotation=30, ha='right')
            fig.tight_layout()
        else:
            present = defaultdict(int)
            for v in self.filtered_visits:
                m = v['day'].replace(day=1)
                if (v['present_child_a'] if mode=='Kind A' else v['present_child_b']):
                    present[m] += 1
            x = [m.strftime('%Y-%m') for m in sorted_months]
            y = [round(present[m]/planned_per_month[m]*100,1) if planned_per_month[m] else 0 for m in sorted_months]
            fig, ax = plt.subplots(figsize=(5,2.5))
            ax.plot(x, y, marker='o', color='#1976d2')
            ax.set_title(f'Anwesenheit {mode} pro Monat (%)')
            ax.set_xlabel('Monat')
            ax.set_ylabel('Anwesenheit (%)')
            ax.set_ylim(0, 105)
            ax.grid(True, linestyle=':')
            plt.xticks(rotation=30, ha='right')
            fig.tight_layout()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            fig.savefig(tmp.name, bbox_inches='tight')
            plt.close(fig)
            self.chart_label.setPixmap(QPixmap(tmp.name))

    def on_export_csv(self):
        import csv
        from PySide6.QtWidgets import QFileDialog
        if not hasattr(self, 'filtered_visits') or not self.filtered_visits:
            QMessageBox.warning(self, "Export", "Bitte zuerst Filter setzen.")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "CSV Export speichern", filter="CSV-Datei (*.csv)")
        if not fn:
            return
        with open(fn, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Datum", "Wochentag", "A anwesend", "B anwesend"])
            weekday_names = ["Mo","Di","Mi","Do","Fr","Sa","So"]
            for v in self.filtered_visits:
                d = v["day"]
                wd = weekday_names[d.weekday()]
                writer.writerow([d.isoformat(), wd, v["present_child_a"], v["present_child_b"]])
        QMessageBox.information(self, "Export", f"CSV erfolgreich gespeichert: {fn}")

    def on_export_pdf(self):
        from PySide6.QtWidgets import QFileDialog
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet
        import tempfile
        if not hasattr(self, 'filtered_visits') or not self.filtered_visits:
            QMessageBox.warning(self, "Export", "Bitte zuerst Filter setzen.")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "PDF Export speichern", filter="PDF-Datei (*.pdf)")
        if not fn:
            return
        # --- Statistische Auswertung vorbereiten ---
        mode = self.get_status_mode()
        summary = self.result.toPlainText()
        # --- Tabelle der Termine ---
        weekday_names = ["Mo","Di","Mi","Do","Fr","Sa","So"]
        table_data = [["Datum", "Wochentag", "A anwesend (1=ja, 0=nein)", "B anwesend (1=ja, 0=nein)"]]
        for v in self.filtered_visits:
            d = v["day"]
            wd = weekday_names[d.weekday()]
            table_data.append([d.isoformat(), wd, int(v["present_child_a"]), int(v["present_child_b"])])
        # --- Trend-Grafik erzeugen (wie im UI) ---
        self.update_trend_chart([v for v in self.filtered_visits if (v['present_child_a'] if mode=='Kind A' else v['present_child_b'] if mode=='Kind B' else v['present_child_a'] and v['present_child_b'])])
        # Hole das zuletzt erzeugte Chart-Bild
        chart_pixmap = self.chart_label.pixmap()
        chart_img_path = None
        if chart_pixmap:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                chart_pixmap.save(tmp.name)
                chart_img_path = tmp.name
        # --- PDF mit ReportLab erzeugen ---
        doc = SimpleDocTemplate(fn, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph("<b>KidsCompass Statistik-Export</b>", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Zeitraum: {self.date_from.date().toString()} bis {self.date_to.date().toString()}", styles['Normal']))
        elements.append(Spacer(1, 12))
        # Statistische Auswertung als Text
        for line in summary.split('\n'):
            elements.append(Paragraph(line, styles['Normal']))
        elements.append(Spacer(1, 12))
        # Trend-Grafik einfügen
        if chart_img_path:
            elements.append(Image(chart_img_path, width=400, height=150))
            elements.append(Spacer(1, 12))
        # Tabelle der Termine
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        elements.append(t)
        doc.build(elements)
        QMessageBox.information(self, "Export", f"PDF erfolgreich gespeichert: {fn}")

class ExportWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, parent, df, dt, patterns, overrides, visit_status, out_fn=None):
        super().__init__()
        self.parent = parent
        self.df = df
        self.dt = dt
        self.patterns = patterns
        self.overrides = overrides
        self.visit_status = visit_status
        self.out_fn = out_fn or 'kidscompass_report.pdf'

    def run(self):
        logging.info("[KidsCompass] ExportWorker.run gestartet.")
        try:
            if self.df is None or self.dt is None:
                self.error.emit("Fehler: Start- und Enddatum müssen gesetzt sein.")
                logging.error("[KidsCompass] Fehler: Start- und Enddatum fehlen im ExportWorker.")
                return
            years = range(self.df.year, self.dt.year + 1)
            all_planned = apply_overrides(
                sum((generate_standard_days(p, year) for p in self.patterns for year in years), []),
                self.overrides
            )
            planned = [d for d in all_planned if self.df <= d <= self.dt]
            deviations = []
            for d in planned:
                vs = self.visit_status.get(d, VisitStatus(day=d))
                if not (vs.present_child_a and vs.present_child_b):
                    status = (
                        "Beide fehlen" if not vs.present_child_a and not vs.present_child_b else
                        "Kind A fehlt" if not vs.present_child_a else
                        "Kind B fehlt"
                    )
                    deviations.append((d, status))
            stats = summarize_visits(planned, self.visit_status)
            png_a, png_b, png_both = 'kind_a.png','kind_b.png','both.png'
            # Prüfe, ob die Bilddateien existieren
            for f in (png_a, png_b, png_both):
                if not os.path.exists(f):
                    self.error.emit(f"Fehler: Bilddatei '{f}' nicht gefunden. Bitte zuerst Statistik berechnen.")
                    return
            try:
                # Farben für alle Diagramme konsistent verwenden
                colors = [COLOR_B_ABSENT, COLOR_A_ABSENT]  # grün, gelb
                create_pie_chart([stats['total']-stats['missed_a'],stats['missed_a']],['Anwesend','Fehlend'],png_a, colors=colors)
                create_pie_chart([stats['total']-stats['missed_b'],stats['missed_b']],['Anwesend','Fehlend'],png_b, colors=colors)
                # Werte für das "both"-Diagramm
                beide_da = stats['both_present']
                mindestens_ein_kind_fehlt = stats['total'] - stats['both_present'] - stats['both_missing']
                beide_fehlen = stats['both_missing']
                # Prozentwert für "mindestens 1 Kind fehlt oder beide fehlen"
                mindestens_einer_oder_beide = mindestens_ein_kind_fehlt + beide_fehlen
                pct_mindestens_einer_oder_beide = round(mindestens_einer_oder_beide / stats['total'] * 100, 1) if stats['total'] else 0.0
                # Farben: grün, gelb, rot
                colors_both = [COLOR_B_ABSENT, COLOR_A_ABSENT, COLOR_BOTH_MISSING]
                wedges, texts, autotexts = create_pie_chart(
                    [beide_da, mindestens_ein_kind_fehlt, beide_fehlen],
                    ['Beide da', f'Mind. 1 fehlt ({pct_mindestens_einer_oder_beide}%)', 'Beide fehlen'],
                    png_both,
                    colors=colors_both,
                    return_handles=True
                    # subtitle="Beide"  # Entfernt, damit das Wort nicht im Kuchendiagramm erscheint
                )
            except Exception as e:
                logging.error(f"Fehler bei create_pie_chart: {e}")
                self.error.emit(f"Fehler bei Diagrammerstellung: {e}")
                return
            # --- ReportLab Flowable-Export statt Canvas ---
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            import tempfile
            doc = SimpleDocTemplate(self.out_fn, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph('<b>KidsCompass Report</b>', styles['Title']))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Zeitraum: {self.df.isoformat()} bis {self.dt.isoformat()}", styles['Normal']))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Geplante Umgänge: {stats['total']}", styles['Normal']))
            elements.append(Paragraph(f"Abweichungstage: {len(deviations)}", styles['Normal']))
            total = stats['total']
            dev = len(deviations)
            pct_dev = round(dev / total * 100, 1) if total else 0.0
            miss_a = stats['missed_a']
            pct_a = round(miss_a / total * 100, 1) if total else 0.0
            miss_b = stats['missed_b']
            pct_b = round(miss_b / total * 100, 1) if total else 0.0
            elements.append(Paragraph(f"Abweichungstage: {dev} ({pct_dev}%)", styles['Normal']))
            elements.append(Paragraph(f"Kind A Abweichungstage: {miss_a} ({pct_a}%)", styles['Normal']))
            elements.append(Paragraph(f"Kind B Abweichungstage: {miss_b} ({pct_b}%)", styles['Normal']))
            elements.append(Spacer(1, 12))
            # Tabelle der Abweichungen
            weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            table_data = [["Datum", "Wochentag", "Status"]]
            for d, st in deviations:
                wd = weekdays[d.weekday()]
                table_data.append([d.isoformat(), wd, st])
            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 24))
            # Kuchendiagramme als Images oben platzieren
            elements.append(Paragraph("<b>Kuchendiagramme</b>", styles['Heading2']))
            elements.append(Spacer(1, 18))
            # Zeile mit Kind A und Kind B, größere Bilder und größere Labels
            img_row = []
            label_row = []
            for img_path, label in zip([png_a, png_b], ["Kind A", "Kind B"]):
                img_row.append(Image(img_path, width=180, height=180))
                label_row.append(Paragraph(f"<b>{label}</b>", styles['BodyText']))
            t_imgs = Table([img_row], colWidths=[200, 200])
            t_imgs.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            t_labels = Table([label_row], colWidths=[200, 200])
            t_labels.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 14),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            elements.append(t_imgs)
            elements.append(t_labels)
            elements.append(Spacer(1, 24))
            # Drittes Diagramm "Beide" zentriert, darunter mittig und groß das Label
            elements.append(Image(png_both, width=220, height=220))
            elements.append(Spacer(1, 8))
            beide_label = Paragraph('<b>Beide</b>', styles['Title'])
            beide_table = Table([[beide_label]], colWidths=[220])
            beide_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 18),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ]))
            elements.append(beide_table)
            doc.build(elements)
            self.finished.emit('PDF erstellt')
            return
        except Exception as e:
            logging.error(f"ExportWorker error: {e}")
            self.error.emit(str(e))

class BackupWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, db_path, fn):
        super().__init__()
        self.db_path = db_path
        self.fn = fn
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        if self._stopped:
            return
        try:
            from kidscompass.data import Database
            db = Database(self.db_path)
            db.export_to_sql(self.fn)
            db.close()
            if not self._stopped:
                self.finished.emit(self.fn)
        except OSError as e:
            logging.error(f"BackupWorker OSError: {e}")
            if not self._stopped:
                self.error.emit(f"Dateifehler: {e}")
        except Exception as e:
            logging.error(f"BackupWorker error: {e}")
            if not self._stopped:
                self.error.emit(str(e))

class RestoreWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, db_path, fn, parent):
        super().__init__()
        self.db_path = db_path
        self.fn = fn
        self.parent = parent
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        if self._stopped:
            return
        try:
            from kidscompass.data import Database
            db = Database(self.db_path)
            db.import_from_sql(self.fn)
            if self._stopped:
                db.close()
                return
            self.parent.visit_status = db.load_all_status()
            self.parent.patterns = db.load_patterns()
            self.parent.overrides = db.load_overrides()
            db.close()
            self.parent.refresh_calendar()
            if not self._stopped:
                self.finished.emit()
        except IOError as e:
            if not self._stopped:
                self.error.emit(f"Dateifehler: {e}")
        except Exception as e:
            if not self._stopped:
                self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, db=None):
        super().__init__()
        self.setWindowTitle("KidsCompass")
        self.resize(900,600)
        self.db = db if db is not None else Database()
        self.patterns = []
        self.overrides = []
        self.visit_status = self.db.load_all_status()

        # Mutex für thread-safe Zugriff
        self._mutex = QMutex()

        # Stelle sicher, dass die DB-Verbindung geschlossen wird
        app = QApplication.instance()
        app.aboutToQuit.connect(self.cleanup)

        tabs = QTabWidget(); self.setCentralWidget(tabs)
        self.tab1 = SettingsTab(self); self.tab2 = StatusTab(self)
        self.tab3 = ExportTab(self); self.tab4 = StatisticsTab(self)
        tabs.addTab(self.tab1, "Einstellungen")
        tabs.addTab(self.tab2, "Status")
        tabs.addTab(self.tab3, "Export")
        tabs.addTab(self.tab4, "Statistiken")

        self.export_thread = None
        self.backup_thread = None
        self.restore_thread = None
        self.worker_thread = None

        self.load_config()
        self.refresh_calendar()
        self.on_child_count_changed(0)

    def load_config(self):
        self._mutex.lock()
        try:
            self.patterns = self.db.load_patterns()
            self.tab1.entry_list.clear()
            for pat in self.patterns:
                item = QListWidgetItem(str(pat)); item.setData(Qt.UserRole, pat)
                self.tab1.entry_list.addItem(item)
            self.overrides = self.db.load_overrides()
            for ov in self.overrides:
                item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov)
                self.tab1.entry_list.addItem(item)
        finally:
            self._mutex.unlock()

    def refresh_calendar(self):
        cal = self.tab2.calendar
        cal.setDateTextFormat(QDate(), QTextCharFormat())
        today = datetime.date.today()

        def apply_format(d, color):
            qd = QDate(d.year, d.month, d.day)
            fmt = QTextCharFormat()
            fmt.setBackground(QBrush(QColor(color)))
            cal.setDateTextFormat(qd, fmt)

        self._mutex.lock()
        try:
            raw: List[datetime.date] = []
            for p in self.patterns:
                start_y = p.start_date.year
                last_y = p.end_date.year if p.end_date else today.year
                for yr in range(start_y, last_y + 1):
                    raw.extend(generate_standard_days(p, yr))

            planned = apply_overrides(raw, self.overrides)

            for d in planned:
                if d <= today:
                    apply_format(d, COLOR_PLANNED)
            for d, vs in self.visit_status.items():
                if d <= today:
                    if not vs.present_child_a and not vs.present_child_b:
                        apply_format(d, COLOR_BOTH_ABSENT)
                    elif not vs.present_child_a:
                        apply_format(d, COLOR_A_ABSENT)
                    elif not vs.present_child_b:
                        apply_format(d, COLOR_B_ABSENT)
        finally:
            self._mutex.unlock()

    def on_add_pattern(self):
        try:
            days = [i for i, cb in self.tab1.weekday_checks if cb.isChecked()]
            iv   = self.tab1.interval.value()
            sd   = qdate_to_date(self.tab1.start_date.date())
            if self.tab1.chk_infinite.isChecked():
                ed = None
            else:
                ed = qdate_to_date(self.tab1.end_date.date())
            pat = VisitPattern(days, iv, sd, ed)

            self.db.save_pattern(pat)
            self.patterns.append(pat)
            item = QListWidgetItem(str(pat))
            item.setData(Qt.UserRole, pat)
            self.tab1.entry_list.addItem(item)
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen des Musters: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Hinzufügen des Musters: {e}")
        self.refresh_calendar()

    def on_add_override(self):
        try:
            f = qdate_to_date(self.tab1.ov_from.date())
            t = qdate_to_date(self.tab1.ov_to.date())
            if self.tab1.ov_add.isChecked():
                pat = VisitPattern(list(range(7)),1,f)
                ov  = OverridePeriod(f,t,pat)
            else:
                ov  = RemoveOverride(f,t)
            self.db.save_override(ov)
            self.overrides.append(ov)
            item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov)
            self.tab1.entry_list.addItem(item)
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen des Overrides: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Hinzufügen des Overrides: {e}")
        self.refresh_calendar()

    def on_delete_entry(self):
        self._mutex.lock()
        try:
            item = self.tab1.entry_list.currentItem()
            if not item: return
            obj  = item.data(Qt.UserRole)
            if isinstance(obj, VisitPattern):
                self.db.delete_pattern(obj.id); self.patterns.remove(obj)
            else:
                self.db.delete_override(obj.id); self.overrides.remove(obj)
            self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        finally:
            self._mutex.unlock()
        self.refresh_calendar()

    def on_child_count_changed(self, index):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(index+1):
            cb = QCheckBox(f"Kind {i+1} nicht da")
            self.tab2.grid.addWidget(cb, i//2, i%2)
            self.tab2.child_checks.append((i, cb))

    def on_calendar_click(self):
        selected_date = qdate_to_date(self.tab2.calendar.selectedDate())

        self._mutex.lock()
        try:
            planned = apply_overrides(
                sum((generate_standard_days(p, selected_date.year) for p in self.patterns), []),
                self.overrides
            )

            if selected_date not in planned:
                return

            checked_children = [i for i, cb in self.tab2.child_checks if cb.isChecked()]
            if not checked_children:
                return

            vs = self.visit_status.get(selected_date, VisitStatus(day=selected_date))

            current_status = (not vs.present_child_a, not vs.present_child_b)
            new_status = (0 in checked_children, 1 in checked_children)

            if selected_date in self.visit_status and current_status == new_status:
                self.visit_status.pop(selected_date)
                self.db.delete_status(selected_date)
            else:
                vs.present_child_a = 0 not in checked_children
                vs.present_child_b = 1 not in checked_children
                self.visit_status[selected_date] = vs
                self.db.save_status(vs)
        finally:
            self._mutex.unlock()

        self.refresh_calendar()

    def on_reset_status(self):
        self._mutex.lock()
        try:
            self.visit_status.clear(); self.db.clear_status()
        finally:
            self._mutex.unlock()
        self.refresh_calendar()

    def on_export(self):
        logging.info("[KidsCompass] Export-Button wurde geklickt.")
        if self.export_thread and self.export_thread.isRunning():
            logging.info("[KidsCompass] Export-Thread läuft bereits.")
            return

        df = qdate_to_date(self.tab3.date_from.date())
        dt = qdate_to_date(self.tab3.date_to.date())
        # Hole den Dateinamen aus dem Dialog
        fn, _ = QFileDialog.getSaveFileName(self, "PDF Export speichern", filter="PDF-Datei (*.pdf)")
        if not fn:
            return
        self.export_thread = QThread()
        self.export_worker = ExportWorker(self, df, dt, self.patterns, self.overrides, self.visit_status, out_fn=fn)
        self.export_worker.moveToThread(self.export_thread)
        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.error.connect(self.on_export_error)
        self.export_worker.finished.connect(self.export_thread.quit)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self.export_thread.deleteLater)
        self.export_thread.start()

    def on_export_finished(self, msg):
        QMessageBox.information(self, 'Export', msg)

    def on_export_error(self, msg):
        logging.error(f"Export error: {msg}")
        QMessageBox.critical(self, 'Export-Fehler', msg)

    def cleanup(self):
        # Stoppe Threads sauber vor dem Schließen
        for thread_attr in ['export_thread', 'backup_thread', 'restore_thread', 'worker_thread']:
            thread = getattr(self, thread_attr, None)
            if thread is not None:
                try:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait()
                except RuntimeError:
                    pass  # Thread-Objekt wurde bereits gelöscht
                setattr(self, thread_attr, None)
        # Schließe die Datenbankverbindung, falls vorhanden
        if hasattr(self, 'db') and self.db:
            self.db.close()

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
