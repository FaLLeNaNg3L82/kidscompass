import logging
import os
import json
import tempfile
from PySide6.QtCore import QObject, Signal
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from kidscompass.models import VisitStatus
from kidscompass.charts import create_pie_chart
from kidscompass.calendar_logic import generate_standard_days, apply_overrides
from kidscompass.export_utils import format_visit_window

# Color constants used by ExportWorker (kept here for consistency)
COLOR_B_ABSENT = '#A0FFA0'
COLOR_A_ABSENT = '#FFD97D'
COLOR_BOTH_MISSING = '#FF0000'

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
            all_planned = sum((generate_standard_days(p, year) for p in self.patterns for year in years), [])
            planned = apply_overrides(all_planned, self.overrides)
            planned = [d for d in planned if self.df <= d <= self.dt]

            removed_by_any = set(all_planned) - set(planned)
            removed_by_remove = set()
            from kidscompass.data import RemoveOverride
            for ov in self.overrides:
                if isinstance(ov, RemoveOverride):
                    removed_by_remove.update({d for d in all_planned if ov.from_date <= d <= ov.to_date})
            excluded_by_remove = len(removed_by_remove & removed_by_any)
            excluded_days = sorted(list(removed_by_remove & removed_by_any))

            deviations = []
            for d in planned:
                vs = self.visit_status.get(d, VisitStatus(d))
                if not (vs.present_child_a and vs.present_child_b):
                    status = (
                        "Beide fehlen" if not vs.present_child_a and not vs.present_child_b else
                        ("Amilia fehlt" if not vs.present_child_a else "Malia fehlt")
                    )
                    deviations.append((d, status))
            stats = {}
            try:
                # import here to avoid circular at module import time
                from kidscompass.statistics import summarize_visits
                stats = summarize_visits(planned, self.visit_status)
            except Exception:
                stats = {'total': len(planned), 'missed_a': 0, 'missed_b': 0, 'both_present': 0, 'both_missing': 0}

            png_a, png_b, png_both = 'kind_a.png','kind_b.png','both.png'
            for f in (png_a, png_b, png_both):
                if not os.path.exists(f):
                    self.error.emit(f"Fehler: Bilddatei '{f}' nicht gefunden. Bitte zuerst Statistik berechnen.")
                    return
            try:
                colors_list = [COLOR_B_ABSENT, COLOR_A_ABSENT]
                create_pie_chart([stats['total']-stats['missed_a'],stats['missed_a']],['Anwesend','Fehlend'],png_a, colors=colors_list)
                create_pie_chart([stats['total']-stats['missed_b'],stats['missed_b']],['Anwesend','Fehlend'],png_b, colors=colors_list)
                beide_da = stats.get('both_present', 0)
                mindestens_ein_kind_fehlt = stats.get('total',0) - stats.get('both_present',0) - stats.get('both_missing',0)
                beide_fehlen = stats.get('both_missing',0)
                mindestens_einer_oder_beide = mindestens_ein_kind_fehlt + beide_fehlen
                pct_mindestens_einer_oder_beide = round(mindestens_einer_oder_beide / stats['total'] * 100, 1) if stats.get('total') else 0.0
                colors_both = [COLOR_B_ABSENT, COLOR_A_ABSENT, COLOR_BOTH_MISSING]
                wedges, texts, autotexts = create_pie_chart(
                    [beide_da, mindestens_ein_kind_fehlt, beide_fehlen],
                    ['Beide da', f'Mind. 1 fehlt ({pct_mindestens_einer_oder_beide}%)', 'Beide fehlen'],
                    png_both,
                    colors=colors_both,
                    return_handles=True
                )
            except Exception as e:
                logging.error(f"Fehler bei create_pie_chart: {e}")
                self.error.emit(f"Fehler bei Diagrammerstellung: {e}")
                return

            # Build PDF
            doc = SimpleDocTemplate(self.out_fn, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph('<b>KidsCompass Report</b>', styles['Title']))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Zeitraum: {self.df.isoformat()} bis {self.dt.isoformat()}", styles['Normal']))
            elements.append(Spacer(1, 12))
            total = stats.get('total', 0)
            if total == 0:
                elements.append(Paragraph("Keine geplanten Umgänge im gewählten Zeitraum.", styles['Normal']))
                doc.build(elements)
                self.finished.emit('PDF erstellt')
                return
            elements.append(Paragraph(f"Geplante Umgänge: {total}", styles['Normal']))
            dev = len(deviations)
            pct_dev = round(dev / total * 100, 1) if total else 0.0
            miss_a = stats.get('missed_a', 0)
            pct_a = round(miss_a / total * 100, 1) if total else 0.0
            miss_b = stats.get('missed_b', 0)
            pct_b = round(miss_b / total * 100, 1) if total else 0.0
            elements.append(Paragraph(f"Abweichungstage: {dev} ({pct_dev}%)", styles['Normal']))
            elements.append(Paragraph(f"Amilia Abweichungstage: {miss_a} ({pct_a}%)", styles['Normal']))
            elements.append(Paragraph(f"Malia Abweichungstage: {miss_b} ({pct_b}%)", styles['Normal']))
            elements.append(Spacer(1, 12))

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

            elements.append(Paragraph("<b>Geplante Termine (mit Metadaten)</b>", styles['Heading2']))
            elements.append(Spacer(1, 6))
            table_meta = [["Datum", "Wochentag", "Status", "Hinweis"]]
            for d in planned:
                vs = self.visit_status.get(d, VisitStatus(d))
                st = (
                    "Alle da" if vs.present_child_a and vs.present_child_b else
                    ("Beide fehlen" if not vs.present_child_a and not vs.present_child_b else
                     ("Amilia fehlt" if not vs.present_child_a else "Malia fehlt"))
                )
                cfg = getattr(self.parent, 'config', None) if hasattr(self, 'parent') else None
                if cfg is None and hasattr(self, 'parent') and hasattr(self.parent, 'config'):
                    cfg = self.parent.config
                hint = format_visit_window(d, self.overrides, cfg)
                table_meta.append([d.isoformat(), weekdays[d.weekday()], st, hint])
            tm = Table(table_meta, repeatRows=1)
            tm.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(tm)
            elements.append(Spacer(1, 24))

            img_row = []
            label_row = []
            for img_path, label in zip([png_a, png_b], ["Amilia", "Malia"]):
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
            # Use atomic import to verify and replace DB atomically
            db.atomic_import_from_sql(self.fn)
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
