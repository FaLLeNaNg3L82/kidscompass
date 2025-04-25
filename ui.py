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
    attended_a_pct = round((total - missed_a) / total * 100, 1) if total else 0.0
    attended_b_pct = round((total - missed_b) / total * 100, 1) if total else 0.0
    return {
        'total': total,
        'missed_a': missed_a,
        'missed_b': missed_b,
        'attended_a_pct': attended_a_pct,
        'attended_b_pct': attended_b_pct,
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
        wd_layout = QHBoxLayout()
        self.weekday_checks = []
        for i, w in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(w);
            wd_layout.addWidget(cb);
            self.weekday_checks.append((i, cb))
        layout.addLayout(wd_layout)
        # Intervall und Startdatum
        param = QHBoxLayout()
        param.addWidget(QLabel("Intervall (Wochen):"))
        self.interval = QSpinBox(); self.interval.setRange(1,52); self.interval.setValue(1)
        param.addWidget(self.interval)
        param.addWidget(QLabel("Ab Datum:"))
        self.start_date = QDateEdit(QDate(date.today().year,1,1)); self.start_date.setCalendarPopup(True)
        param.addWidget(self.start_date)
        self.btn_pattern = QPushButton("Pattern hinzufügen")
        param.addWidget(self.btn_pattern)
        layout.addLayout(param)
        # Override
        layout.addWidget(QLabel("🔄 Override:"))
        ov_group = QGroupBox(); ov_l = QHBoxLayout(ov_group)
        self.ov_add = QRadioButton("Add-Satz"); self.ov_add.setChecked(True)
        self.ov_remove = QRadioButton("Remove-Satz")
        ov_l.addWidget(self.ov_add); ov_l.addWidget(self.ov_remove)
        dlay = QHBoxLayout()
        dlay.addWidget(QLabel("Von:")); self.ov_from = QDateEdit(QDate.currentDate()); self.ov_from.setCalendarPopup(True)
        dlay.addWidget(self.ov_from); dlay.addWidget(QLabel("Bis:")); self.ov_to = QDateEdit(QDate.currentDate()); self.ov_to.setCalendarPopup(True)
        dlay.addWidget(self.ov_to); ov_l.addLayout(dlay)
        self.btn_override = QPushButton("Override hinzufügen"); ov_l.addWidget(self.btn_override)
        layout.addWidget(ov_group)
        # Eintragsliste
        layout.addWidget(QLabel("Einträge:")); self.entry_list = QListWidget(); layout.addWidget(self.entry_list)
        btns = QHBoxLayout(); self.btn_delete = QPushButton("Eintrag löschen"); self.btn_save = QPushButton("Speichern")
        btns.addWidget(self.btn_delete); btns.addWidget(self.btn_save); layout.addLayout(btns)
        # Signale
        self.btn_pattern.clicked.connect(parent.on_add_pattern)
        self.btn_override.clicked.connect(parent.on_add_override)
        self.btn_delete.clicked.connect(parent.on_delete_entry)
        self.btn_save.clicked.connect(parent.on_save_config)

class StatusTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)
        # Kinderanzahl
        hl = QHBoxLayout(); hl.addWidget(QLabel("Kinder:"))
        self.child_count = QComboBox(); self.child_count.addItems([str(i) for i in range(1,6)])
        hl.addWidget(self.child_count); layout.addLayout(hl)
        # Abwesenheits-Checkboxen
        self.child_checks = []
        self.grid = QGridLayout(); layout.addLayout(self.grid)
        self.btn_reset = QPushButton("Alle zurücksetzen"); layout.addWidget(self.btn_reset)
        # Kalender
        self.calendar = QCalendarWidget(); self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar); layout.addWidget(QLabel("Checkbox wählen → Klick toggelt Abwesenheit."))
        # Signale
        self.child_count.currentIndexChanged.connect(self.parent.on_child_count_changed)
        self.calendar.selectionChanged.connect(self.parent.on_calendar_click)
        self.btn_reset.clicked.connect(self.parent.on_reset_status)

class ExportTab(QWidget):
    def __init__(self, parent):
        super().__init__(); self.parent = parent; layout = QVBoxLayout(self)
        # Zeitraum
        hl = QHBoxLayout(); hl.addWidget(QLabel("Von:")); self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        hl.addWidget(self.date_from); hl.addWidget(QLabel("Bis:")); self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        hl.addWidget(self.date_to); layout.addLayout(hl)
        # Optionen
        self.cb_text = QCheckBox("Nur Textoutput"); self.cb_chart = QCheckBox("Diagramme"); self.cb_stats = QCheckBox("Statistiken")
        self.cb_text.setChecked(True); opt=QHBoxLayout(); opt.addWidget(self.cb_text); opt.addWidget(self.cb_chart); opt.addWidget(self.cb_stats)
        layout.addLayout(opt)
        # Export
        self.btn_export = QPushButton("Export starten"); layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.parent.on_export)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("KidsCompass"); self.resize(900,600)
        self.patterns=[]; self.overrides=[]; self.visit_status={}
        tabs=QTabWidget(); self.setCentralWidget(tabs)
        self.tab1=SettingsTab(self); self.tab2=StatusTab(self); self.tab3=ExportTab(self)
        tabs.addTab(self.tab1,"Einstellungen"); tabs.addTab(self.tab2,"Status"); tabs.addTab(self.tab3,"Export")
        self.load_config(); self.refresh_calendar(); self.on_child_count_changed(0)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try: data = json.load(open(CONFIG_FILE, encoding='utf-8'))
        except: return
        self.patterns.clear(); self.overrides.clear(); self.visit_status.clear(); self.tab1.entry_list.clear()
        for p in data.get('patterns',[]):
            pat=VisitPattern(p['weekdays'],p['interval_weeks'],date.fromisoformat(p['start_date']))
            self.patterns.append(pat); item=QListWidgetItem(str(pat)); item.setData(Qt.UserRole,pat); self.tab1.entry_list.addItem(item)
        for o in data.get('overrides',[]):
            if o['type']=='add': pat_o=VisitPattern(o['pattern']['weekdays'],o['pattern']['interval_weeks'],date.fromisoformat(o['pattern']['start_date'])); ov=OverridePeriod(date.fromisoformat(o['from_date']),date.fromisoformat(o['to_date']),pat_o)
            else: ov=RemoveOverride(date.fromisoformat(o['from_date']),date.fromisoformat(o['to_date']))
            self.overrides.append(ov); item=QListWidgetItem(str(ov)); item.setData(Qt.UserRole,ov); self.tab1.entry_list.addItem(item)
        for vs in data.get('visit_status',[]): d0=date.fromisoformat(vs['day']); st=VisitStatus(day=d0,present_child_a=vs['present_child_a'],present_child_b=vs['present_child_b']); self.visit_status[d0]=st

    def save_config(self):
        data={'patterns':[], 'overrides':[], 'visit_status':[]}
        for p in self.patterns: data['patterns'].append({'weekdays':p.weekdays,'interval_weeks':p.interval_weeks,'start_date':p.start_date.isoformat()})
        for o in self.overrides:
            e={'type':'add' if isinstance(o, OverridePeriod) else 'remove','from_date':o.from_date.isoformat(),'to_date':o.to_date.isoformat()}
            if isinstance(o,OverridePeriod): e['pattern']={'weekdays':o.pattern.weekdays,'interval_weeks':o.pattern.interval_weeks,'start_date':o.pattern.start_date.isoformat()}
            data['overrides'].append(e)
        for vs in self.visit_status.values(): data['visit_status'].append({'day':vs.day.isoformat(),'present_child_a':vs.present_child_a,'present_child_b':vs.present_child_b})
        json.dump(data,open(CONFIG_FILE,'w',encoding='utf-8'),indent=2)
    on_save_config=save_config

    def refresh_calendar(self):
        cal = self.tab2.calendar
        # Reset all formats
        cal.setDateTextFormat(QDate(), QTextCharFormat())
        today = date.today()
        # Geplante Tage berechnen
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year) for p in self.patterns), []),
            self.overrides
        )
        # Blaue Markierung für geplante Umgänge
        for d in planned:
            if d <= today:
                qd = QDate(d.year, d.month, d.day)
                fmt = QTextCharFormat()
                fmt.setBackground(QBrush(QColor('#A0C4FF')))
                cal.setDateTextFormat(qd, fmt)
        # Abwesenheitsstatus färben
        for d, vs in self.visit_status.items():
            if d <= today:
                qd = QDate(d.year, d.month, d.day)
                fmt = QTextCharFormat()
                if not vs.present_child_a and not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#FFADAD')))
                elif not vs.present_child_a:
                    fmt.setBackground(QBrush(QColor('#FFD97D')))
                elif not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#A0FFA0')))
                cal.setDateTextFormat(qd, fmt)

    def on_add_pattern(self):
        days=[i for i,cb in self.tab1.weekday_checks if cb.isChecked()]; iv=self.tab1.interval.value(); sd=self.tab1.start_date.date().toPython()
        pat=VisitPattern(days,iv,sd); self.patterns.append(pat)
        item=QListWidgetItem(str(pat)); item.setData(Qt.UserRole,pat); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_add_override(self):
        f=self.tab1.ov_from.date().toPython(); t=self.tab1.ov_to.date().toPython()
        if self.tab1.ov_add.isChecked(): pat_o=VisitPattern(list(range(7)),1,f); ov=OverridePeriod(f,t,pat_o)
        else: ov=RemoveOverride(f,t)
        self.overrides.append(ov)
        item=QListWidgetItem(str(ov)); item.setData(Qt.UserRole,ov); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_delete_entry(self):
        item=self.tab1.entry_list.currentItem(); 
        if not item: return 
        obj=item.data(Qt.UserRole);
        if obj in self.patterns: self.patterns.remove(obj)
        if obj in self.overrides: self.overrides.remove(obj)
        self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        self.refresh_calendar(); self.save_config()

    def on_child_count_changed(self, index):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(index+1): cb=QCheckBox(f"Kind {i+1} nicht da"); self.tab2.grid.addWidget(cb,i//2,i%2); self.tab2.child_checks.append((i,cb))

    def on_calendar_click(self):
        today=date.today(); planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]),self.overrides)
        d=self.tab2.calendar.selectedDate().toPython();
        if d not in planned: return
        idxs=[i for i,cb in self.tab2.child_checks if cb.isChecked()]
        if not idxs: return
        vs=self.visit_status.get(d,VisitStatus(day=d))
        for i in idxs:
            if i==0: vs.present_child_a=not vs.present_child_a
            elif i==1: vs.present_child_b=not vs.present_child_b
        if vs.present_child_a and vs.present_child_b: self.visit_status.pop(d,None)
        else: self.visit_status[d]=vs
        self.refresh_calendar(); self.save_config()

    def on_reset_status(self):
        self.visit_status.clear(); self.refresh_calendar(); self.save_config()

    def on_export(self):
        df=self.tab3.date_from.date().toPython(); dt=self.tab3.date_to.date().toPython(); today=date.today()
        planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]),self.overrides)
        sel=[d for d in planned if df<=d<=dt]
        stats=summarize_visits(sel,self.visit_status)
        pdf_fn='kidscompass_report.pdf'; c=canvas.Canvas(pdf_fn,pagesize=letter); w,h=letter; y=h-50
        c.setFont('Helvetica-Bold',14); c.drawString(50,y,'KidsCompass Report'); y-=30
        if self.tab3.cb_text.isChecked(): c.setFont('Helvetica',10)
        for d in sel: vs=self.visit_status.get(d,VisitStatus(day=d)); st='Alle da'
        if not vs.present_child_a and not vs.present_child_b: st='Kein Kind'
        elif not vs.present_child_a: st='Kind A fehlt'
        elif not vs.present_child_b: st='Kind B fehlt'
        c.drawString(50,y,f"{d.isoformat()}: {st}"); y-=15; y-=20
        if self.tab3.cb_stats.isChecked(): c.setFont('Helvetica-Bold',12); c.drawString(50,y,'Statistik:'); y-=20
        c.setFont('Helvetica',10); c.drawString(60,y,f"Geplante Termine: {stats['total']}"); y-=15
        c.drawString(60,y,f"Kind A: {stats['attended_a_pct']}% anwesend ({stats['missed_a']} fehlend)"); y-=15
        c.drawString(60,y,f"Kind B: {stats['attended_b_pct']}% anwesend ({stats['missed_b']} fehlend)"); y-=30
        if self.tab3.cb_chart.isChecked(): png_a='child_a_pie.png'; png_b='child_b_pie.png'
        create_pie_chart([stats['total']-stats['missed_a'],stats['missed_a']],['Anwesend','Fehlend'],png_a)
        create_pie_chart([stats['total']-stats['missed_b'],stats['missed_b']],['Anwesend','Fehlend'],png_b)
        img=200; c.drawImage(png_a,50,y-img,width=img,height=img); c.drawImage(png_b,300,y-img,width=img,height=img); y-=img+20
        c.save(); QMessageBox.information(self,'Export',f'PDF erstellt: {pdf_fn}')

if __name__=='__main__':
    app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec())
