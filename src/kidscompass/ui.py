import os
import json
import sys
from datetime import date

import matplotlib.pyplot as plt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QCalendarWidget, QCheckBox, QPushButton, QLabel,
    QSpinBox, QListWidget, QListWidgetItem, QMessageBox, QDateEdit,
    QComboBox, QGroupBox, QRadioButton, QGridLayout, QTextEdit 
)
from PySide6.QtGui import QTextCharFormat, QBrush, QColor
from PySide6.QtCore import Qt, QDate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from .calendar_logic import generate_standard_days, apply_overrides

from kidscompass.data import Database
from kidscompass.statistics import count_missing_by_weekday

from datetime import date
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.models import VisitStatus


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

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


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
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Zeitraum von:"))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        hl.addWidget(self.date_from)
        hl.addWidget(QLabel("bis:"))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        hl.addWidget(self.date_to)
        layout.addLayout(hl)
        # Einziger Export-Button
        self.btn_export = QPushButton("Export: Abweichungen + Diagramme")
        layout.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.parent.on_export)

    # hier KEINE zweite __init__ mehr!


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KidsCompass")
        self.resize(900,600)

        # 1) Patterns & Overrides aus JSON laden
        self.patterns = []
        self.overrides = []

        # 2) Datenbank initialisieren und Status laden
        self.db = Database()  
        # überschreibt nur visit_status aus JSON, behält Muster und Overrides
        self.visit_status = self.db.load_all_status()  

        # 3) UI-Tabs anlegen
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        self.tab1 = SettingsTab(self)
        self.tab2 = StatusTab(self)
        self.tab3 = ExportTab(self)
        self.tab4 = StatisticsTab(self)
        tabs.addTab(self.tab1, "Einstellungen")
        tabs.addTab(self.tab2, "Status")
        tabs.addTab(self.tab3, "Export")
        tabs.addTab(self.tab4, "Statistiken")

        # 4) Rufe Config-Load & Kalenderaufbau auf
        self.load_config()           # lädt nur patterns & overrides + json-Status
        self.refresh_calendar()
        self.on_child_count_changed(0)


    def load_config(self):
        # 1) Muster aus DB laden
        self.patterns = self.db.load_patterns()
        self.tab1.entry_list.clear()
        for pat in self.patterns:
            item = QListWidgetItem(str(pat))
            item.setData(Qt.UserRole, pat)
            self.tab1.entry_list.addItem(item)

        # 2) Overrides aus DB laden
        self.overrides = self.db.load_overrides()
        for ov in self.overrides:
            item = QListWidgetItem(str(ov))
            item.setData(Qt.UserRole, ov)
            self.tab1.entry_list.addItem(item)

        # 3) Besuchsstatus bereits in __init__ aus DB geholt

    def refresh_calendar(self):
        cal = self.tab2.calendar
        # Reset all formats
        cal.setDateTextFormat(QDate(), QTextCharFormat())

        today = date.today()
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year) for p in self.patterns), []),
            self.overrides
        )

        # Blaue Markierung für geplante Umgänge
        for d in planned:
            if d <= today:
                qd = QDate(d.year, d.month, d.day)         # <— hier qd definieren
                fmt = QTextCharFormat()
                fmt.setBackground(QBrush(QColor('#A0C4FF')))
                cal.setDateTextFormat(qd, fmt)             # <— und hier verwenden

        # Abwesenheitsstatus färben
        for d, vs in self.visit_status.items():
            if d <= today:
                qd = QDate(d.year, d.month, d.day)         # <— ebenfalls qd definieren
                fmt = QTextCharFormat()
                if not vs.present_child_a and not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#FFADAD')))
                elif not vs.present_child_a:
                    fmt.setBackground(QBrush(QColor('#FFD97D')))
                elif not vs.present_child_b:
                    fmt.setBackground(QBrush(QColor('#A0FFA0')))
                cal.setDateTextFormat(qd, fmt)             # <— korrekt


    def on_add_pattern(self):
        days=[i for i,cb in self.tab1.weekday_checks if cb.isChecked()]; iv=self.tab1.interval.value(); sd=self.tab1.start_date.date().toPython()
        pat = VisitPattern(days, iv, sd)
        self.db.save_pattern(pat)
        self.patterns.append(pat)
        item = QListWidgetItem(str(pat))
        item.setData(Qt.UserRole, pat)
        self.tab1.entry_list.addItem(item)
        self.refresh_calendar()

    def on_add_override(self):
        # 1) Erzeuge das Override-Objekt
        f = self.tab1.ov_from.date().toPython()
        t = self.tab1.ov_to.date().toPython()
        if self.tab1.ov_add.isChecked():
            pat_o = VisitPattern(list(range(7)), 1, f)
            ov = OverridePeriod(f, t, pat_o)
        else:
            ov = RemoveOverride(f, t)

        # 2) In DB speichern
        self.db.save_override(ov)

        # 3) In-memory Liste und UI-Liste updaten
        self.overrides.append(ov)
        item = QListWidgetItem(str(ov))
        item.setData(Qt.UserRole, ov)
        self.tab1.entry_list.addItem(item)

        # 4) Kalender neu zeichnen
        self.refresh_calendar()

    def on_delete_entry(self):
        item = self.tab1.entry_list.currentItem()
        # Löschen in DB und In‐Memory
        if isinstance(obj, VisitPattern):
            self.db.delete_pattern(obj.id)
            self.patterns.remove(obj)
        else:
            self.db.delete_override(obj.id)
            self.overrides.remove(obj)
        if item is None:
            return      # nichts ausgewählt → abbrechen
        obj = item.data(Qt.UserRole)        
        if isinstance(obj, VisitPattern):
            self.db.delete_pattern(obj.id)
            self.patterns.remove(obj)
        else:
            self.db.delete_override(obj.id)
            self.overrides.remove(obj)
        self.tab1.entry_list.takeItem(self.tab1.entry_list.row(item))
        self.refresh_calendar()

    def on_child_count_changed(self, index):
        for _,cb in self.tab2.child_checks: cb.deleteLater()
        self.tab2.child_checks.clear()
        for i in range(index+1): cb=QCheckBox(f"Kind {i+1} nicht da"); self.tab2.grid.addWidget(cb, i//2, i%2); self.tab2.child_checks.append((i, cb))

    def on_calendar_click(self):
        # 1) Nur an geplanten Besuchstagen reagieren
        today = date.today()
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year) for p in self.patterns), []),
            self.overrides
        )
        d = self.tab2.calendar.selectedDate().toPython()
        if d not in planned:
            return  # Klickt auf Nicht‐Besuchstage ignorieren

        # 2) Standard‐Status: beide Kinder waren da
        vs = self.visit_status.get(d, VisitStatus(day=d))
        #    VisitStatus initialisiert mit present_child_a=True, present_child_b=True

        # 3) Fehlzeiten toggeln je nachdem, welche Checkboxen ausgewählt sind
        idxs = [i for i, cb in self.tab2.child_checks if cb.isChecked()]
        if not idxs:
            return  # Ohne Checkbox-Auswahl nichts tun

        for i in idxs:
            if i == 0:
                vs.present_child_a = not vs.present_child_a
            elif i == 1:
                vs.present_child_b = not vs.present_child_b

        # 4) Wenn nach dem Klicken wieder beide True sind,
        #    löschen wir den Eintrag komplett (Default-Fall)
        if vs.present_child_a and vs.present_child_b:
            self.visit_status.pop(d, None)
            self.db.conn.execute("DELETE FROM visit_status WHERE day = ?", (d.isoformat(),))
            self.db.conn.commit()
        else:
            # ansonsten speichern wir die Ausnahme in memory und in der DB
            self.visit_status[d] = vs
            self.db.save_status(vs)

        self.refresh_calendar()

    def on_reset_status(self):
        """Alle Status-Einträge löschen (UI, JSON & DB)."""
        self.visit_status.clear()      # in-memory
        self.db.clear_status()         # in SQLite
        self.refresh_calendar()

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

class StatisticsTab(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)

        # — Zeitraum —
        period = QHBoxLayout()
        period.addWidget(QLabel("Von:"))
        self.date_from = QDateEdit(QDate.currentDate()); self.date_from.setCalendarPopup(True)
        period.addWidget(self.date_from)
        period.addWidget(QLabel("Bis:"))
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        period.addWidget(self.date_to)
        layout.addLayout(period)

        # — Wochentags‐Filter —
        wd_group = QGroupBox("Wochentage wählen")
        wd_layout = QHBoxLayout(wd_group)
        self.wd_checks = []
        for i, name in enumerate(["Mo","Di","Mi","Do","Fr","Sa","So"]):
            cb = QCheckBox(name)
            wd_layout.addWidget(cb)
            self.wd_checks.append((i, cb))
        layout.addWidget(wd_group)

        # — Kind‐Status‐Filter —
        status_group = QGroupBox("Status‐Filter")
        status_layout = QHBoxLayout(status_group)
        self.cb_a_absent    = QCheckBox("A fehlt")
        self.cb_b_absent    = QCheckBox("B fehlt")
        self.cb_both_absent = QCheckBox("beide fehlen")
        self.cb_both_present= QCheckBox("beide da")
        for cb in (self.cb_a_absent,
                   self.cb_b_absent,
                   self.cb_both_absent,
                   self.cb_both_present):
            status_layout.addWidget(cb)
        layout.addWidget(status_group)

        # — Berechnen —
        self.btn_calc = QPushButton("Statistik berechnen")
        layout.addWidget(self.btn_calc)

        # — Ausgabe —
        from PySide6.QtWidgets import QTextEdit
        self.result = QTextEdit(); self.result.setReadOnly(True)
        layout.addWidget(self.result)

        self.btn_calc.clicked.connect(self.on_calculate)


    def on_calculate(self):
        from kidscompass.calendar_logic import generate_standard_days, apply_overrides
        from kidscompass.models import VisitStatus
        from kidscompass.data import Database
        from kidscompass.statistics import count_missing_by_weekday  # oder eigene Logik

        # 1) Roh-Daten: alle geplanten Tage dieses Jahres
        today = date.today()
        planned = apply_overrides(
            sum((generate_standard_days(p, today.year)
                 for p in self.parent.patterns), []),
            self.parent.overrides
        )

        # 2) Zeitraum‐Filter
        df = self.date_from.date().toPython()
        dt = self.date_to.date().toPython()
        sel_dates = [d for d in planned if df <= d <= dt]

        # 3) Wochentags‐Filter
        sel_wds = [i for i, cb in self.wd_checks if cb.isChecked()]
        if sel_wds:
            sel_dates = [d for d in sel_dates if d.weekday() in sel_wds]

        # 4) Status‐Filter
        # Lade aktuelle VisitStatus aus DB
        db = self.parent.db
        all_status = db.load_all_status()
        filtered = {}
        for d in sel_dates:
            vs = all_status.get(d, VisitStatus(day=d))
            # Prüfe die gewählten Status‐Checkboxen
            ok = False
            if self.cb_a_absent.isChecked() and not vs.present_child_a:
                ok = True
            if self.cb_b_absent.isChecked() and not vs.present_child_b:
                ok = True
            if self.cb_both_absent.isChecked() and not vs.present_child_a and not vs.present_child_b:
                ok = True
            if self.cb_both_present.isChecked() and vs.present_child_a and vs.present_child_b:
                ok = True
            # Falls gar keine Status-Checkbox gewählt sind, akzeptiere alle
            if not any(cb.isChecked() for cb in
                       [self.cb_a_absent, self.cb_b_absent,
                        self.cb_both_absent, self.cb_both_present]):
                ok = True

            if ok:
                filtered[d] = vs

        # 5) Statistik‐Berechnung
        # Wir können jetzt count_missing_by_weekday auf filtered anwenden – oder
        # eigene Aggregation schreiben
        # Einfachstes Beispiel: Gesamtzahl gefilterter Tage
        total = len(filtered)
        text = f"Gefundene Termine nach Filter: {total}\n\n"

        # Beispiel: Wieviele der gefilterten Tage sind Mo?
        by_wd = {}
        for d in filtered:
            wd = d.weekday()
            by_wd[wd] = by_wd.get(wd, 0) + 1

        # Ausgabe pro Wochentag
        weekdays = ["Mo","Di","Mi","Do","Fr","Sa","So"]
        for wd, cnt in sorted(by_wd.items()):
            text += f"{weekdays[wd]}: {cnt} Termine\n"

        # Oder detaillierter mit count_missing_by_weekday
        # berechne Fehl-/Anwesenheit nur auf den gerade gefilterten Terminen
        missed_a      = sum(1 for vs in filtered.values() if not vs.present_child_a)
        missed_b      = sum(1 for vs in filtered.values() if not vs.present_child_b)
        both_missing  = sum(1 for vs in filtered.values()
                             if not vs.present_child_a and not vs.present_child_b)
        both_present  = sum(1 for vs in filtered.values()
                             if  vs.present_child_a and  vs.present_child_b)
    
        text += "\nGesamt-Statistik A/B/Beide:\n"
        text += f"A fehlt: {missed_a}  |  "
        text += f"B fehlt: {missed_b}  |  "
        text += f"Beide fehlen: {both_missing}  |  "
        text += f"Beide da: {both_present}\n"
        # Both_present müsste deine Statistik-Funktion noch liefern, wenn du sie ergänzt hast.

        self.result.setPlainText(text)


    # Hilfsklasse, um count_missing_by_weekday ein dict statt DB zu füttern
class SimpleDB:
    def __init__(self, status_dict):
        self._status = status_dict
    def load_all_status(self):
        return self._status
