import sys
from datetime import date

import sys
from datetime import date

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QCalendarWidget, QCheckBox, QPushButton, QLabel,
    QSpinBox, QListWidget, QListWidgetItem, QMessageBox, QDateEdit,
    QComboBox, QGroupBox, QRadioButton, QGridLayout, QTextEdit, QFileDialog
)

from PySide6.QtGui import QTextCharFormat, QBrush, QColor
from PySide6.QtCore import Qt, QDate

from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.data import Database
from kidscompass.statistics import count_missing_by_weekday

from PySide6.QtGui import QTextCharFormat, QBrush, QColor
from PySide6.QtCore import Qt, QDate

from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.data import Database
from kidscompass.statistics import count_missing_by_weekday, summarize_visits



# Hilfsfunktion für Tortendiagramme
def create_pie_chart(values: list, labels: list, filename: str):
    total = sum(values)
    # Wenn keine Daten da sind, lege ein kleines Platzhalter‐Bild an
    if total == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center", fontsize=14)
        ax.axis("off")
        fig.savefig(filename, bbox_inches="tight")
        plt.close(fig)
        return

    # Ansonsten ganz normal zeichnen
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.axis("equal")
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)


class SettingsTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        # Besuchsmuster
        layout.addWidget(QLabel("📅 Besuchsmuster:"))
        wd_layout = QHBoxLayout()
        self.weekday_checks = []
        for i, day in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(day)
            wd_layout.addWidget(cb)
            self.weekday_checks.append((i, cb))
        layout.addLayout(wd_layout)

        # Intervall, Start- und Enddatum
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Intervall (Wochen):"))
        self.interval = QSpinBox(); self.interval.setRange(1, 52); self.interval.setValue(1)
        param_layout.addWidget(self.interval)
        param_layout.addWidget(QLabel("Ab Datum:"))
        self.start_date = QDateEdit(QDate(date.today().year, 1, 1)); self.start_date.setCalendarPopup(True)
        param_layout.addWidget(self.start_date)
        param_layout.addWidget(QLabel("Bis Datum:"))
        self.end_date = QDateEdit(QDate(date.today().year, 12, 31)); self.end_date.setCalendarPopup(True)
        param_layout.addWidget(self.end_date)
        self.chk_infinite = QCheckBox("Bis unendlich")
        param_layout.addWidget(self.chk_infinite)
        self.btn_pattern = QPushButton("Pattern hinzufügen")
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
        date_layout.addWidget(QLabel("Von:"))
        self.ov_from = QDateEdit(QDate.currentDate()); self.ov_from.setCalendarPopup(True)
        date_layout.addWidget(self.ov_from)
        date_layout.addWidget(QLabel("Bis:"))
        self.ov_to = QDateEdit(QDate.currentDate()); self.ov_to.setCalendarPopup(True)
        date_layout.addWidget(self.ov_to)
        ov_layout.addLayout(date_layout)
        self.btn_override = QPushButton("Override hinzufügen")
        ov_layout.addWidget(self.btn_override)
        layout.addWidget(ov_group)

        # Einträge
        layout.addWidget(QLabel("Einträge:"))
        self.entry_list = QListWidget()
        layout.addWidget(self.entry_list)
        btns = QHBoxLayout()
        self.btn_delete = QPushButton("Eintrag löschen")
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

        hl = QHBoxLayout(); hl.addWidget(QLabel("Kinder:"))
        self.child_count = QComboBox(); self.child_count.addItems([str(i) for i in range(1,6)])
        hl.addWidget(self.child_count); layout.addLayout(hl)

        self.child_checks = []
        self.grid = QGridLayout(); layout.addLayout(self.grid)
        self.btn_reset = QPushButton("Alle zurücksetzen")
        layout.addWidget(self.btn_reset)

        self.calendar = QCalendarWidget(); self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        self.child_count.currentIndexChanged.connect(self.parent.on_child_count_changed)
        self.btn_reset.clicked.connect(self.parent.on_reset_status)
        self.calendar.selectionChanged.connect(self.parent.on_calendar_click)

class ExportTab(QWidget):
    def __init__(self, parent):
        super().__init__(); self.parent = parent
        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        hl.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        hl.addWidget(self.date_from)
        hl.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        hl.addWidget(self.date_to)
        layout.addLayout(hl)

        self.btn_export = QPushButton("Export starten")
        layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.parent.on_export)

        # --- Backup / Restore ---
        hl = QHBoxLayout()
        btn_backup  = QPushButton("DB Backup")
        btn_restore = QPushButton("DB Restore")
        hl.addWidget(btn_backup)
        hl.addWidget(btn_restore)
        layout.addLayout(hl)

        btn_backup.clicked.connect(self.on_backup)
        btn_restore.clicked.connect(self.on_restore)        

    def on_backup(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Backup speichern als", filter="SQL-Datei (*.sql)")
        if not fn:
            return
        try:
            self.parent.db.export_to_sql(fn)
            QMessageBox.information(self, "Backup", f"Datenbank erfolgreich exportiert nach:\n{fn}")
        except Exception as e:
            QMessageBox.critical(self, "Backup-Fehler", str(e))

    def on_restore(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Backup wiederherstellen", filter="SQL-Datei (*.sql)")
        if not fn:
            return
        confirm = QMessageBox.question(
            self, "Restore bestätigen",
            "Achtung: Alle aktuellen Einträge werden überschrieben.\nWeiter?")
        if confirm != QMessageBox.Yes:
            return
        try:
            self.parent.db.import_from_sql(fn)
            # Nach dem Restore alle In-Memory-Caches neu laden:
            self.parent.visit_status = self.parent.db.load_all_status()
            self.parent.patterns     = self.parent.db.load_patterns()
            self.parent.overrides    = self.parent.db.load_overrides()
            self.parent.refresh_calendar()
            QMessageBox.information(self, "Restore", "Datenbank erfolgreich wiederhergestellt.")
        except Exception as e:
            QMessageBox.critical(self, "Restore-Fehler", str(e))

class StatisticsTab(QWidget):
    def __init__(self, parent):
        super().__init__(); self.parent = parent
        layout = QVBoxLayout(self)

        period = QHBoxLayout(); period.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        period.addWidget(self.date_from); period.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        period.addWidget(self.date_to); layout.addLayout(period)

        wd_group = QGroupBox("Wochentage")
        wd_l = QHBoxLayout(wd_group)
        self.wd_checks = []
        for i,name in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(name); wd_l.addWidget(cb); self.wd_checks.append((i,cb))
        layout.addWidget(wd_group)

        status_group = QGroupBox("Status-Filter")
        sl = QHBoxLayout(status_group)
        self.cb_a_absent = QCheckBox("A fehlt"); self.cb_b_absent = QCheckBox("B fehlt")
        self.cb_both_absent = QCheckBox("beide fehlen"); self.cb_both_present = QCheckBox("beide da")
        for cb in (self.cb_a_absent,self.cb_b_absent,self.cb_both_absent,self.cb_both_present): sl.addWidget(cb)
        layout.addWidget(status_group)

        self.btn_calc = QPushButton("Statistik berechnen"); layout.addWidget(self.btn_calc)
        self.result   = QTextEdit(); self.result.setReadOnly(True); layout.addWidget(self.result)
        self.btn_calc.clicked.connect(self.on_calculate)

    def on_calculate(self):
        db = self.parent.db
        stats = count_missing_by_weekday(db)
        text = f"A fehlt: {stats[0]['missed_a']}\n"
        text += f"B fehlt: {stats[1]['missed_b']}\n"
        text += f"Beide fehlen: {stats[2]['both_missing']}"
        self.result.setPlainText(text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KidsCompass")
        self.resize(900,600)
        self.db = Database()
        self.patterns = []
        self.overrides = []
        self.visit_status = self.db.load_all_status()

        tabs = QTabWidget(); self.setCentralWidget(tabs)
        self.tab1 = SettingsTab(self); self.tab2 = StatusTab(self)
        self.tab3 = ExportTab(self); self.tab4 = StatisticsTab(self)
        tabs.addTab(self.tab1, "Einstellungen")
        tabs.addTab(self.tab2, "Status")
        tabs.addTab(self.tab3, "Export")
        tabs.addTab(self.tab4, "Statistiken")

        self.load_config()
        self.refresh_calendar()
        self.on_child_count_changed(0)

    def load_config(self):
        self.patterns = self.db.load_patterns()
        self.tab1.entry_list.clear()
        for pat in self.patterns:
            item = QListWidgetItem(str(pat)); item.setData(Qt.UserRole, pat)
            self.tab1.entry_list.addItem(item)
        self.overrides = self.db.load_overrides()
        for ov in self.overrides:
            item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov)
            self.tab1.entry_list.addItem(item)

    def refresh_calendar(self):
        cal = self.tab2.calendar
        cal.setDateTextFormat(QDate(), QTextCharFormat())
        today = date.today()
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year) for p in self.patterns), []),
            self.overrides
        )
        for d in planned:
            if d <= today:
                qd = QDate(d.year,d.month,d.day)
                fmt = QTextCharFormat(); fmt.setBackground(QBrush(QColor('#A0C4FF')))
                cal.setDateTextFormat(qd, fmt)
        for d,vs in self.visit_status.items():
            if d <= today:
                qd = QDate(d.year,d.month,d.day)
                fmt = QTextCharFormat()
                if not vs.present_child_a and not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#FFADAD')))
                elif not vs.present_child_a:
                    fmt.setBackground(QBrush(QColor('#FFD97D')))
                elif not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#A0FFA0')))
                cal.setDateTextFormat(qd, fmt)

    def on_add_pattern(self):
        days = [i for i, cb in self.tab1.weekday_checks if cb.isChecked()]
        iv   = self.tab1.interval.value()
        sd   = self.tab1.start_date.date().toPython()
        # if “bis unendlich” is checked, end_date stays None
        # if “bis unendlich” is checked, end_date stays None
        if self.tab1.chk_infinite.isChecked():
            ed = None
        else:
            ed = self.tab1.end_date.date().toPython()
        pat = VisitPattern(days, iv, sd, ed)      # ← new line

        # 4) Speichere in der DB
        self.db.save_pattern(pat)

        # 5) Füge in-memory und UI hinzu
        self.patterns.append(pat)
        item = QListWidgetItem(str(pat))
        item.setData(Qt.UserRole, pat)
        self.tab1.entry_list.addItem(item)

        # 6) Kalender neu rendern
        self.refresh_calendar()

    def on_add_override(self):
        f = self.tab1.ov_from.date().toPython(); t = self.tab1.ov_to.date().toPython()
        if self.tab1.ov_add.isChecked():
            pat = VisitPattern(list(range(7)),1,f)
            ov  = OverridePeriod(f,t,pat)
        else:
            ov  = RemoveOverride(f,t)
        self.db.save_override(ov)
        self.overrides.append(ov)
        item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov)
        self.tab1.entry_list.addItem(item)
        self.refresh_calendar()

    def on_delete_entry(self):
        item = self.tab1.entry_list.currentItem()
        if not item: return
        obj  = item.data(Qt.UserRole)
        if isinstance(obj, VisitPattern):
            self.db.delete_pattern(obj.id); self.patterns.remove(obj)
        else:
            self.db.delete_override(obj.id); self.overrides.remove(obj)
        self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        self.refresh_calendar()

    def on_child_count_changed(self, index):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(index+1):
            cb = QCheckBox(f"Kind {i+1} nicht da")
            self.tab2.grid.addWidget(cb, i//2, i%2)
            self.tab2.child_checks.append((i, cb))

    def on_calendar_click(self):
        today   = date.today()
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year) for p in self.patterns), []),
            self.overrides
        )
        d       = self.tab2.calendar.selectedDate().toPython()
        if d not in planned: return
        vs      = self.visit_status.get(d, VisitStatus(day=d))
        idxs    = [i for i,cb in self.tab2.child_checks if cb.isChecked()]
        if not idxs: return
        for i in idxs:
            if i==0: vs.present_child_a = not vs.present_child_a
            if i==1: vs.present_child_b = not vs.present_child_b
        if vs.present_child_a and vs.present_child_b:
            self.visit_status.pop(d, None)
            self.db.delete_status(d)
        else:
            self.visit_status[d] = vs
            self.db.save_status(vs)
        self.refresh_calendar()

    def on_reset_status(self):
        self.visit_status.clear(); self.db.clear_status(); self.refresh_calendar()

    def on_export(self):
        df = self.tab3.date_from.date().toPython(); dt = self.tab3.date_to.date().toPython()
        today = date.today()
        all_planned = apply_overrides(
            sum((generate_standard_days(p,today.year) for p in self.patterns),[]),
            self.overrides
        )
        planned = [d for d in all_planned if df<=d<=dt]
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
        create_pie_chart([stats['total']-stats['missed_a'],stats['missed_a']],['Anwesend','Fehlend'],png_a)
        create_pie_chart([stats['total']-stats['missed_b'],stats['missed_b']],['Anwesend','Fehlend'],png_b)
        create_pie_chart([stats['both_present'],stats['total']-stats['both_present']],['Beide da','Mindestens ein Kind fehlt'],png_both)
        c = canvas.Canvas('kidscompass_report.pdf',pagesize=letter)
        w,h = letter; y = h-50
        c.setFont('Helvetica-Bold',14); c.drawString(50,y,'KidsCompass Report'); y-=30
        c.setFont('Helvetica',10)
        c.drawString(50, y,    f"Zeitraum: {df.isoformat()} bis {dt.isoformat()}"); y -= 20
        c.drawString(50, y,    f"Geplante Umgänge: {stats['total']}");             y -= 20
        c.drawString(50, y,    f"Abweichungstage: {len(deviations)}");              y -= 20
        # Prozentzahlen berechnen
        total = stats['total']
        dev = len(deviations)
        pct_dev   = round(dev   / total * 100, 1) if total else 0.0
        miss_a    = stats['missed_a']
        pct_a     = round(miss_a / total * 100, 1) if total else 0.0
        miss_b    = stats['missed_b']
        pct_b     = round(miss_b / total * 100, 1) if total else 0.0

        # Ausgabe
        c.drawString(50, y, f"Abweichungstage: {dev} ({pct_dev}%)"); y -= 20
        c.drawString(50, y, f"Kind A Abweichungstage: {miss_a} ({pct_a}%)"); y -= 15
        c.drawString(50, y, f"Kind B Abweichungstage: {miss_b} ({pct_b}%)"); y -= 20


        # Liste der Abweichungen mit Wochentag
        weekdays = ["Mo","Di","Mi","Do","Fr","Sa","So"]
        for d, st in deviations:
            if y < 100:
                c.showPage()
                y = h - 50
            wd = weekdays[d.weekday()]
            c.drawString(60, y, f"{d.isoformat()} ({wd}): {st}")
            y -= 15

        c.showPage(); size=200
        c.drawImage(png_a,50,y-size,width=size,height=size)
        c.drawImage(png_b,260,y-size,width=size,height=size)
        c.drawImage(png_both,470,y-size,width=size,height=size)
        c.save(); QMessageBox.information(self,'Export','PDF erstellt')

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
