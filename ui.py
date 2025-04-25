import os
import json
import sys
from datetime import date

import matplotlib.pyplot as plt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QCalendarWidget, QCheckBox, QPushButton, QLabel,
    QSpinBox, QListWidget, QListWidgetItem, QMessageBox, QDateEdit,
    QComboBox, QGroupBox, QRadioButton, QGridLayout
)
from PySide6.QtGui import QTextCharFormat, QBrush, QColor
from PySide6.QtCore import Qt, QDate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from kidscompass.calendar_logic import generate_standard_days, apply_overrides

CONFIG_FILE = "kidscompass_config.json"

# Statistik-Funktion: Zusammenfassung der Besuchsdaten
def summarize_visits(planned: list[date], visit_status: dict) -> dict:
    total = len(planned)
    missed_a = sum(1 for d in planned if d in visit_status and not visit_status[d].present_child_a)
    missed_b = sum(1 for d in planned if d in visit_status and not visit_status[d].present_child_b)
    # Wie oft beide präsent
    both_present = sum(1 for d in planned if d not in visit_status or (visit_status[d].present_child_a and visit_status[d].present_child_b))
    return {
        'total': total,
        'missed_a': missed_a,
        'missed_b': missed_b,
        'both_present': both_present,
    }

# Tortendiagramm-Funktion
def create_pie_chart(values: list, labels: list, filename: str):
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
        wd = QHBoxLayout()
        self.weekday_checks = []
        for i, w in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(w)
            wd.addWidget(cb)
            self.weekday_checks.append((i, cb))
        layout.addLayout(wd)
        # Interval und Startdatum
        hp = QHBoxLayout()
        hp.addWidget(QLabel("Intervall (Wo):"))
        self.interval = QSpinBox(); self.interval.setRange(1,52); self.interval.setValue(1)
        hp.addWidget(self.interval)
        hp.addWidget(QLabel("Ab Datum:"))
        self.start_date = QDateEdit(QDate(date.today().year,1,1)); self.start_date.setCalendarPopup(True)
        hp.addWidget(self.start_date)
        self.btn_pattern = QPushButton("Pattern hinzufügen")
        hp.addWidget(self.btn_pattern)
        layout.addLayout(hp)
        # Override
        layout.addWidget(QLabel("🔄 Override:"))
        ovg = QHBoxLayout()
        self.ov_add = QRadioButton("Urlaubs-Add"); self.ov_add.setChecked(True)
        self.ov_remove = QRadioButton("Urlaubs-Remove")
        ovg.addWidget(self.ov_add); ovg.addWidget(self.ov_remove)
        ov_from = QHBoxLayout()
        ov_from.addWidget(QLabel("Von:")); self.ov_from = QDateEdit(QDate.currentDate()); self.ov_from.setCalendarPopup(True)
        ov_from.addWidget(self.ov_from); ov_from.addWidget(QLabel("Bis:")); self.ov_to = QDateEdit(QDate.currentDate()); self.ov_to.setCalendarPopup(True)
        ov_from.addWidget(self.ov_to); ovg.addLayout(ov_from)
        self.btn_override = QPushButton("Override hinzufügen")
        ovg.addWidget(self.btn_override)
        layout.addLayout(ovg)
        # Einträge
        layout.addWidget(QLabel("Einträge:"))
        self.entry_list = QListWidget(); layout.addWidget(self.entry_list)
        btns = QHBoxLayout()
        self.btn_delete = QPushButton("Eintrag löschen"); self.btn_delete.setToolTip("Muster oder Override löschen")
        self.btn_save = QPushButton("Speichern")
        btns.addWidget(self.btn_delete); btns.addWidget(self.btn_save)
        layout.addLayout(btns)
        # Signale
        self.btn_pattern.clicked.connect(self.parent.on_add_pattern)
        self.btn_override.clicked.connect(self.parent.on_add_override)
        self.btn_delete.clicked.connect(self.parent.on_delete_entry)
        self.btn_save.clicked.connect(self.parent.on_save_config)

class StatusTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)
        # Kinderanzahl
        top = QHBoxLayout(); top.addWidget(QLabel("Kinder:"))
        self.child_count = QComboBox(); self.child_count.addItems([str(i) for i in range(1,6)])
        top.addWidget(self.child_count); layout.addLayout(top)
        # Abwesenheits Check
        self.child_checks = []
        self.grid = QGridLayout(); layout.addLayout(self.grid)
        self.btn_reset = QPushButton("Alle Abw. zurücksetzen")
        layout.addWidget(self.btn_reset)
        # Kalender
        self.calendar = QCalendarWidget(); self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        # Signale
        self.child_count.currentIndexChanged.connect(self.parent.on_child_count_changed)
        self.btn_reset.clicked.connect(self.parent.on_reset_status)
        self.calendar.selectionChanged.connect(self.parent.on_calendar_click)

class ExportTab(QWidget):
    def __init__(self, parent):
        super().__init__(); self.parent = parent
        layout = QVBoxLayout(self)
        # Zeitraum
        hl = QHBoxLayout(); hl.addWidget(QLabel("Zeitraum von:"))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        hl.addWidget(self.date_from); hl.addWidget(QLabel("bis:"))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        hl.addWidget(self.date_to)
        layout.addLayout(hl)
        # Einziger Export-Button
        self.btn_export = QPushButton("Export: Abweichungen + Diagramme")
        layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.parent.on_export)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("KidsCompass"); self.resize(900,600)
        self.patterns = []; self.overrides = []; self.visit_status = {}
        tabs = QTabWidget(); self.setCentralWidget(tabs)
        self.tab1 = SettingsTab(self); self.tab2 = StatusTab(self); self.tab3 = ExportTab(self)
        tabs.addTab(self.tab1, "Einstellungen"); tabs.addTab(self.tab2, "Status"); tabs.addTab(self.tab3, "Export")
        self.load_config(); self.refresh_calendar(); self.on_child_count_changed(0)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try: data = json.load(open(CONFIG_FILE, encoding='utf-8'))
        except: return
        self.patterns.clear(); self.overrides.clear(); self.visit_status.clear(); self.tab1.entry_list.clear()
        for p in data.get('patterns', []):
            pat = VisitPattern(p['weekdays'], p['interval_weeks'], date.fromisoformat(p['start_date']))
            self.patterns.append(pat)
            item = QListWidgetItem(str(pat)); item.setData(Qt.UserRole, pat)
            self.tab1.entry_list.addItem(item)
        for o in data.get('overrides', []):
            if o['type'] == 'add': pat_o = VisitPattern(o['pattern']['weekdays'], o['pattern']['interval_weeks'], date.fromisoformat(o['pattern']['start_date'])); ov = OverridePeriod(date.fromisoformat(o['from_date']), date.fromisoformat(o['to_date']), pat_o)
            else: ov = RemoveOverride(date.fromisoformat(o['from_date']), date.fromisoformat(o['to_date']))
            self.overrides.append(ov)
            item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov)
            self.tab1.entry_list.addItem(item)
        for vs in data.get('visit_status', []):
            d0 = date.fromisoformat(vs['day']); st = VisitStatus(day=d0, present_child_a=vs['present_child_a'], present_child_b=vs['present_child_b'])
            self.visit_status[d0] = st

    def save_config(self):
        data={'patterns':[], 'overrides':[], 'visit_status':[]}
        for p in self.patterns: data['patterns'].append({'weekdays':p.weekdays,'interval_weeks':p.interval_weeks,'start_date':p.start_date.isoformat()})
        for o in self.overrides:
            e = {'type':'add' if isinstance(o,OverridePeriod) else 'remove','from_date':o.from_date.isoformat(),'to_date':o.to_date.isoformat()}
            if isinstance(o,OverridePeriod): e['pattern'] = {'weekdays':o.pattern.weekdays,'interval_weeks':o.pattern.interval_weeks,'start_date':o.pattern.start_date.isoformat()}
            data['overrides'].append(e)
        for vs in self.visit_status.values(): data['visit_status'].append({'day':vs.day.isoformat(),'present_child_a':vs.present_child_a,'present_child_b':vs.present_child_b})
        json.dump(data, open(CONFIG_FILE,'w',encoding='utf-8'), indent=2)
    on_save_config = save_config

    def refresh_calendar(self):
        cal = self.tab2.calendar; cal.setDateTextFormat(QDate(), QTextCharFormat())
        today = date.today()
        planned = apply_overrides(sum((generate_standard_days(p, today.year) for p in self.patterns), []), self.overrides)
        for d in planned:
            if d <= today: fmt = QTextCharFormat(); fmt.setBackground(QBrush(QColor('#A0C4FF'))); cal.setDateTextFormat(QDate(d.year,d.month,d.day), fmt)
        for d,vs in self.visit_status.items():
            if d <= today: qd=QDate(d.year,d.month,d.day); fmt=QTextCharFormat()
            if not vs.present_child_a and not vs.present_child_b: fmt.setBackground(QBrush(QColor('#FFADAD')))
            elif not vs.present_child_a: fmt.setBackground(QBrush(QColor('#FFD97D')))
            elif not vs.present_child_b: fmt.setBackground(QBrush(QColor('#A0FFA0')))
            cal.setDateTextFormat(qd, fmt)

    def on_add_pattern(self):
        days=[i for i,cb in self.tab1.weekday_checks if cb.isChecked()]; iv=self.tab1.interval.value(); sd=self.tab1.start_date.date().toPython()
        pat=VisitPattern(days,iv,sd); self.patterns.append(pat)
        item=QListWidgetItem(str(pat)); item.setData(Qt.UserRole,pat); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_add_override(self):
        f=self.tab1.ov_from.date().toPython(); t=self.tab1.ov_to.date().toPython()
        pat_o = VisitPattern(list(range(7)), 1, f) if self.tab1.ov_add.isChecked() else None
        ov = OverridePeriod(f, t, pat_o) if self.tab1.ov_add.isChecked() else RemoveOverride(f, t)
        self.overrides.append(ov); item=QListWidgetItem(str(ov)); item.setData(Qt.UserRole,ov); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_delete_entry(self):
        item=self.tab1.entry_list.currentItem();
        if not item: return
        obj=item.data(Qt.UserRole)
        if obj in self.patterns: self.patterns.remove(obj)
        if obj in self.overrides: self.overrides.remove(obj)
        self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        self.refresh_calendar(); self.save_config()

    def on_child_count_changed(self, index):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(index+1): cb=QCheckBox(f"Kind {i+1} nicht da"); self.tab2.grid.addWidget(cb, i//2, i%2); self.tab2.child_checks.append((i, cb))

    def on_calendar_click(self):
        today=date.today(); planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]), self.overrides)
        d=self.tab2.calendar.selectedDate().toPython();
        if d not in planned: return
        idxs=[i for i,cb in self.tab2.child_checks if cb.isChecked()];
        if not idxs: return
        vs=self.visit_status.get(d, VisitStatus(day=d))
        for i in idxs:
            if i==0: vs.present_child_a=not vs.present_child_a
            elif i==1: vs.present_child_b=not vs.present_child_b
        if vs.present_child_a and vs.present_child_b: self.visit_status.pop(d,None)
        else: self.visit_status[d]=vs
        self.refresh_calendar(); self.save_config()

    def on_reset_status(self):
        self.visit_status.clear(); self.refresh_calendar(); self.save_config()

    def on_export(self):
        # Zeitraum ermitteln
        df=self.tab3.date_from.date().toPython(); dt=self.tab3.date_to.date().toPython(); today=date.today()
        all_planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]), self.overrides)
        planned=[d for d in all_planned if df<=d<=dt]
        # Abweichungstage
        deviations=[]
        for d in planned:
            vs=self.visit_status.get(d, VisitStatus(day=d))
            if not (vs.present_child_a and vs.present_child_b):
                status=(
                    "Beide fehlen" if not vs.present_child_a and not vs.present_child_b else
                    "Kind A fehlt" if not vs.present_child_a else
                    "Kind B fehlt"
                )
                deviations.append((d, status))
        # Statistik
        stats=summarize_visits(planned, self.visit_status)
        # Grafiken
        png_a="kind_a.png"; png_b="kind_b.png"; png_both="both.png"
        create_pie_chart([stats['total']-stats['missed_a'], stats['missed_a']], ["Anwesend","Fehlend"], png_a)
        create_pie_chart([stats['total']-stats['missed_b'], stats['missed_b']], ["Anwesend","Fehlend"], png_b)
        create_pie_chart([stats['both_present'], stats['total']-stats['both_present']], ["Beide da","Mindestens ein Kind fehlt"], png_both)
        # PDF-Erzeugung
        pdf_fn='kidscompass_report.pdf'; c=canvas.Canvas(pdf_fn, pagesize=letter); w,h=letter; y=h-50
        c.setFont('Helvetica-Bold',16); c.drawString(50,y,'KidsCompass Report'); y-=30
        c.setFont('Helvetica',10); c.drawString(50,y, f"Zeitraum: {df.isoformat()} bis {dt.isoformat()}"); y-=20
        c.drawString(50,y, f"Abweichungstage: {len(deviations)}"); y-=20
        c.setFont('Helvetica',10)
        for d,st in deviations:
            if y<100: c.showPage(); y=h-50
            c.drawString(60,y,f"{d.isoformat()}: {st}"); y-=15
        if y<250: c.showPage(); y=h-50
        size=200
        c.drawImage(png_a,50,y-size,width=size,height=size); c.drawImage(png_b,260,y-size,width=size,height=size); c.drawImage(png_both,470,y-size,width=size,height=size)
        c.save()
        QMessageBox.information(self,'Export', f'PDF erstellt: {pdf_fn}')

if __name__=='__main__':
    app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec())
