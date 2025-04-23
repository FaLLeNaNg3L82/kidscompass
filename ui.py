import os
import json
import sys
from datetime import date

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

class SettingsTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("📅 Besuchsmuster:"))
        wd_layout = QHBoxLayout()
        self.weekday_checks = []
        for i, w in enumerate(['Mo','Di','Mi','Do','Fr','Sa','So']):
            cb = QCheckBox(w)
            wd_layout.addWidget(cb)
            self.weekday_checks.append((i, cb))
        layout.addLayout(wd_layout)

        param = QHBoxLayout()
        param.addWidget(QLabel("Intervall (Wochen):"))
        self.interval = QSpinBox()
        self.interval.setRange(1,52)
        self.interval.setValue(1)
        param.addWidget(self.interval)
        param.addWidget(QLabel("Ab Datum:"))
        self.start_date = QDateEdit(QDate(date.today().year, 1, 1))
        self.start_date.setCalendarPopup(True)
        param.addWidget(self.start_date)
        self.btn_pattern = QPushButton("Pattern hinzufügen")
        param.addWidget(self.btn_pattern)
        layout.addLayout(param)

        layout.addWidget(QLabel("🔄 Override:"))
        ov_group = QGroupBox()
        ov_l = QHBoxLayout(ov_group)
        self.ov_add = QRadioButton("Add-Satz")
        self.ov_add.setChecked(True)
        self.ov_remove = QRadioButton("Remove-Satz")
        ov_l.addWidget(self.ov_add)
        ov_l.addWidget(self.ov_remove)
        dlay = QHBoxLayout()
        dlay.addWidget(QLabel("Von:"))
        self.ov_from = QDateEdit(QDate.currentDate())
        self.ov_from.setCalendarPopup(True)
        dlay.addWidget(self.ov_from)
        dlay.addWidget(QLabel("Bis:"))
        self.ov_to = QDateEdit(QDate.currentDate())
        self.ov_to.setCalendarPopup(True)
        dlay.addWidget(self.ov_to)
        ov_l.addLayout(dlay)
        self.btn_override = QPushButton("Override hinzufügen")
        ov_l.addWidget(self.btn_override)
        layout.addWidget(ov_group)

        layout.addWidget(QLabel("Einträge:"))
        self.entry_list = QListWidget()
        layout.addWidget(self.entry_list)
        btns = QHBoxLayout()
        self.btn_delete = QPushButton("Eintrag löschen")
        self.btn_save = QPushButton("Speichern")
        btns.addWidget(self.btn_delete)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

        self.btn_pattern.clicked.connect(self.parent.on_add_pattern)
        self.btn_override.clicked.connect(self.parent.on_add_override)
        self.btn_delete.clicked.connect(self.parent.on_delete)
        self.btn_save.clicked.connect(self.parent.on_save_config)

class StatusTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        hl.addWidget(QLabel("Kinder:"))
        self.child_count = QComboBox()
        self.child_count.addItems([str(i) for i in range(1, 6)])
        hl.addWidget(self.child_count)
        layout.addLayout(hl)

        self.child_checks = []
        self.grid = QGridLayout()
        layout.addLayout(self.grid)

        self.btn_reset = QPushButton("Alle zurücksetzen")
        layout.addWidget(self.btn_reset)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        self.child_count.currentIndexChanged.connect(self.parent.on_child_count_changed)
        self.calendar.selectionChanged.connect(self.parent.on_calendar_click)
        self.btn_reset.clicked.connect(self.parent.on_reset_status)

class ExportTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        hl.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        hl.addWidget(self.date_from)
        hl.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        hl.addWidget(self.date_to)
        layout.addLayout(hl)

        self.cb_text = QCheckBox("Text")
        self.cb_chart = QCheckBox("Chart")
        self.cb_stats = QCheckBox("Stats")
        self.cb_text.setChecked(True)
        o = QHBoxLayout()
        o.addWidget(self.cb_text)
        o.addWidget(self.cb_chart)
        o.addWidget(self.cb_stats)
        layout.addLayout(o)

        self.btn_export = QPushButton("Export starten")
        layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.parent.on_export)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KidsCompass")
        self.resize(800,600)

        self.patterns = []
        self.overrides = []
        self.visit_status = {}

        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        self.tab1 = SettingsTab(self)
        self.tab2 = StatusTab(self)
        self.tab3 = ExportTab(self)
        tabs.addTab(self.tab1, "Einstellungen")
        tabs.addTab(self.tab2, "Status")
        tabs.addTab(self.tab3, "Export")

        self.load_config()
        self.refresh_calendar()
        self.on_child_count_changed(0)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            data = json.load(open(CONFIG_FILE, encoding='utf-8'))
        except:
            return
        self.patterns.clear(); self.overrides.clear(); self.visit_status.clear(); self.tab1.entry_list.clear()
        for p in data.get('patterns', []):
            pat = VisitPattern(p['weekdays'], p['interval_weeks'], date.fromisoformat(p['start_date']))
            self.patterns.append(pat)
            item = QListWidgetItem(str(pat)); item.setData(Qt.UserRole, pat); self.tab1.entry_list.addItem(item)
        for o in data.get('overrides', []):
            if o['type']=='add':
                pat = VisitPattern(o['pattern']['weekdays'], o['pattern']['interval_weeks'], date.fromisoformat(o['pattern']['start_date']))
                ov = OverridePeriod(date.fromisoformat(o['from_date']), date.fromisoformat(o['to_date']), pat)
            else:
                ov = RemoveOverride(date.fromisoformat(o['from_date']), date.fromisoformat(o['to_date']))
            self.overrides.append(ov)
            item = QListWidgetItem(str(ov)); item.setData(Qt.UserRole, ov); self.tab1.entry_list.addItem(item)
        for vs in data.get('visit_status', []):
            d0 = date.fromisoformat(vs['day'])
            st = VisitStatus(day=d0, present_child_a=vs['present_child_a'], present_child_b=vs['present_child_b'])
            self.visit_status[d0] = st

    def save_config(self):
        data={'patterns':[], 'overrides':[], 'visit_status':[]}
        for p in self.patterns:
            data['patterns'].append({'weekdays':p.weekdays,'interval_weeks':p.interval_weeks,'start_date':p.start_date.isoformat()})
        for o in self.overrides:
            e={'type':'add' if isinstance(o,OverridePeriod) else 'remove','from_date':o.from_date.isoformat(),'to_date':o.to_date.isoformat()}
            if isinstance(o,OverridePeriod): e['pattern']={'weekdays':o.pattern.weekdays,'interval_weeks':o.pattern.interval_weeks,'start_date':o.pattern.start_date.isoformat()}
            data['overrides'].append(e)
        for vs in self.visit_status.values():
            data['visit_status'].append({'day':vs.day.isoformat(),'present_child_a':vs.present_child_a,'present_child_b':vs.present_child_b})
        json.dump(data, open(CONFIG_FILE,'w',encoding='utf-8'),indent=2)
    on_save_config=save_config

    def refresh_calendar(self):
        cal=self.tab2.calendar; cal.setDateTextFormat(QDate(),QTextCharFormat())
        today=date.today()
        planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]),self.overrides)
        for d in planned:
            if d<=today:
                fmt=QTextCharFormat(); fmt.setBackground(QBrush(QColor('#A0C4FF'))); cal.setDateTextFormat(QDate(d.year,d.month,d.day),fmt)
        for d,vs in self.visit_status.items():
            if d<=today:
                qd=QDate(d.year,d.month,d.day); fmt=QTextCharFormat()
                if not vs.present_child_a and not vs.present_child_b: fmt.setBackground(QBrush(QColor('#FFADAD')))
                elif not vs.present_child_a: fmt.setBackground(QBrush(QColor('#FFD97D')))
                elif not vs.present_child_b: fmt.setBackground(QBrush(QColor('#A0FFA0')))
                cal.setDateTextFormat(qd,fmt)

    def on_add_pattern(self):
        days=[i for i,cb in self.tab1.weekday_checks if cb.isChecked()]
        iv=self.tab1.interval.value(); sd=self.tab1.start_date.date().toPython()
        pat=VisitPattern(days,iv,sd); self.patterns.append(pat)
        item=QListWidgetItem(str(pat)); item.setData(Qt.UserRole,pat); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_add_override(self):
        f=self.tab1.ov_from.date().toPython(); t=self.tab1.ov_to.date().toPython()
        if self.tab1.ov_add.isChecked(): pat=VisitPattern(list(range(7)),1,f); ov=OverridePeriod(f,t,pat)
        else: ov=RemoveOverride(f,t)
        self.overrides.append(ov); item=QListWidgetItem(str(ov)); item.setData(Qt.UserRole,ov); self.tab1.entry_list.addItem(item)
        self.refresh_calendar(); self.save_config()

    def on_delete(self):
        item=self.tab1.entry_list.currentItem();
        if not item: return
        obj=item.data(Qt.UserRole)
        if obj in self.patterns: self.patterns.remove(obj)
        if obj in self.overrides: self.overrides.remove(obj)
        self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        self.refresh_calendar(); self.save_config()

    def on_child_count_changed(self,idx):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(idx+1): cb=QCheckBox(f"Kind {i+1} nicht da"); self.tab2.grid.addWidget(cb,i//2,i%2); self.tab2.child_checks.append((i,cb))

    def on_calendar_click(self):
        idxs=[i for i,cb in self.tab2.child_checks if cb.isChecked()]
        if not idxs: return
        d=self.tab2.calendar.selectedDate().toPython()
        vs=self.visit_status.get(d,VisitStatus(day=d))
        for i in idxs:
            if i==0: vs.present_child_a=not vs.present_child_a
            if i==1: vs.present_child_b=not vs.present_child_b
        if vs.present_child_a and vs.present_child_b: self.visit_status.pop(d,None)
        else: self.visit_status[d]=vs
        self.refresh_calendar(); self.save_config()

    def on_reset_status(self):
        self.visit_status.clear(); self.refresh_calendar(); self.save_config()

    def on_export(self):
        df=self.tab3.date_from.date().toPython() if hasattr(self.tab3,'date_from') else date.today()
        dt=self.tab3.date_to.date().toPython() if hasattr(self.tab3,'date_to') else date.today()
        today=date.today()
        planned=apply_overrides(sum((generate_standard_days(p,today.year) for p in self.patterns),[]),self.overrides)
        sel=[d for d in planned if df<=d<=dt]
        if self.tab3.cb_text.isChecked():
            fn='report.txt'
            with open(fn,'w',encoding='utf-8') as f:
                f.write('Report\n')
                for d in sel:
                    vs=self.visit_status.get(d,VisitStatus(day=d)); st='OK'
                    if not vs.present_child_a and not vs.present_child_b: st='Kein Kind'
                    elif not vs.present_child_a: st='Kind A fehlt'
                    elif not vs.present_child_b: st='Kind B fehlt'
                    f.write(f"{d}: {st}\n")
        QMessageBox.information(self,'Export','Fertig')

if __name__=='__main__':
    app=QApplication(sys.argv)
    win=MainWindow()
    win.show()
    sys.exit(app.exec())
