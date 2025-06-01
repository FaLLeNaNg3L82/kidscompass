import os
import sqlite3
from datetime import date
from typing import List, Dict
from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
import logging

class Database:
    def __init__(self, db_path: str = None):
        try:
            self.db_path = db_path or os.path.join(os.path.expanduser("~"), ".kidscompass", "kidscompass.db")
            if self.db_path != ':memory:':
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key constraints
            self._ensure_tables()
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            raise

    def _ensure_tables(self):
        cur = self.conn.cursor()
        # Muster-Tabelle mit optionalem Enddatum
        cur.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          weekdays TEXT NOT NULL,
          interval_weeks INTEGER NOT NULL,
          start_date TEXT NOT NULL
        )""")
        # Prüfen und ggf. Spalte end_date hinzufügen
        cur.execute("PRAGMA table_info(patterns)")
        cols = [row['name'] for row in cur.fetchall()]
        if 'end_date' not in cols:
            cur.execute("ALTER TABLE patterns ADD COLUMN end_date TEXT")

        # Overrides: Add und Remove mit Referenz auf patterns
        cur.execute("""
        CREATE TABLE IF NOT EXISTS overrides (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type TEXT NOT NULL,
          from_date TEXT NOT NULL,
          to_date TEXT NOT NULL,
          pattern_id INTEGER,
          FOREIGN KEY(pattern_id) REFERENCES patterns(id)
        )""")

        # Besuchsstatus
        cur.execute("""
        CREATE TABLE IF NOT EXISTS visit_status (
          day TEXT PRIMARY KEY,
          present_child_a INTEGER NOT NULL,
          present_child_b INTEGER NOT NULL
        )""")

        self.conn.commit()

    # Export/Import
    def export_to_sql(self, filename: str):
        """Dump aller Tabellen als SQL-Statements"""
        with open(filename, 'w', encoding='utf-8') as f:
            for line in self.conn.iterdump():
                f.write(f"{line}\n")

    def import_from_sql(self, filename: str):
        """Vorhandene Tabellen löschen, Dump einlesen und ausführen"""
        cur = self.conn.cursor()
        for tbl in ('visit_status', 'overrides', 'patterns'):
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")
        self.conn.commit()

        with open(filename, 'r', encoding='utf-8') as f:
            script = f.read()
        self.conn.executescript(script)
        self.conn.commit()

    # Pattern-Methoden
    def load_patterns(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns"
        )
        out = []
        for row in cur.fetchall():
            wd = [int(x) for x in row['weekdays'].split(',') if x]
            start = date.fromisoformat(row['start_date'])
            end = date.fromisoformat(row['end_date']) if row['end_date'] else None
            pat = VisitPattern(wd, row['interval_weeks'], start, end)
            pat.id = row['id']
            out.append(pat)
        return out    
    def save_pattern(self, pat: VisitPattern):
        try:
            wd_text = ','.join(str(d) for d in pat.weekdays)
            sd = pat.start_date.isoformat()
            ed = pat.end_date.isoformat() if pat.end_date else None
            cur = self.conn.cursor()
            if getattr(pat, 'id', None) is not None:
                cur.execute(
                    "UPDATE patterns SET weekdays=?, interval_weeks=?, start_date=?, end_date=? WHERE id=?",
                    (wd_text, pat.interval_weeks, sd, ed, pat.id)
                )
                print(f"Updated pattern id={pat.id}")
            else:
                cur.execute(
                    "INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)",
                    (wd_text, pat.interval_weeks, sd, ed)
                )
                pat.id = cur.lastrowid
                print(f"Inserted new pattern with id={pat.id}")
            self.conn.commit()
            # Verify the save
            cur.execute("SELECT * FROM patterns WHERE id=?", (pat.id,))
            row = cur.fetchone()
            print(f"Saved pattern: {dict(row)}")
        except Exception as e:
            print(f"Error saving pattern: {e}")

    def delete_pattern(self, pattern_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM patterns WHERE id=?", (pattern_id,))
        self.conn.commit()

    # Override-Methoden
    def load_overrides(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM overrides")
        out = []
        for row in cur.fetchall():
            f = date.fromisoformat(row['from_date'])
            t = date.fromisoformat(row['to_date'])
            if row['type'] == 'add':
                # Lade zugehöriges Pattern
                pcur = self.conn.cursor()
                pcur.execute(
                    "SELECT weekdays, interval_weeks, start_date, end_date FROM patterns WHERE id=?",
                    (row['pattern_id'],)
                )
                prow = pcur.fetchone()
                wd = [int(x) for x in prow['weekdays'].split(',') if x]
                start = date.fromisoformat(prow['start_date'])
                end = date.fromisoformat(prow['end_date']) if prow['end_date'] else None
                pat = VisitPattern(wd, prow['interval_weeks'], start, end)
                pat.id = row['pattern_id']
                ov = OverridePeriod(f, t, pat)
            else:
                ov = RemoveOverride(f, t)
            ov.id = row['id']
            out.append(ov)
        return out

    def save_override(self, ov):
        cur = self.conn.cursor()
        f_iso = ov.from_date.isoformat()
        t_iso = ov.to_date.isoformat()
        if isinstance(ov, OverridePeriod):
            self.save_pattern(ov.pattern)
            pid = ov.pattern.id
            typ = 'add'
        else:
            pid = None
            typ = 'remove'
        if hasattr(ov, 'id'):
            cur.execute(
                "UPDATE overrides SET type=?, from_date=?, to_date=?, pattern_id=? WHERE id=?",
                (typ, f_iso, t_iso, pid, ov.id)
            )
        else:
            cur.execute(
                "INSERT INTO overrides (type, from_date, to_date, pattern_id) VALUES (?,?,?,?)",
                (typ, f_iso, t_iso, pid)
            )
            ov.id = cur.lastrowid
        self.conn.commit()

    def delete_override(self, override_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM overrides WHERE id=?", (override_id,))
        self.conn.commit()

    # VisitStatus-Methoden
    def load_all_status(self) -> dict[date, VisitStatus]:
        cur = self.conn.cursor()
        cur.execute("SELECT day, present_child_a, present_child_b FROM visit_status")
        status = {}
        for row in cur.fetchall():
            d0 = date.fromisoformat(row['day'])
            vs = VisitStatus(d0, bool(row['present_child_a']), bool(row['present_child_b']))
            status[d0] = vs
        return status

    def save_status(self, vs: VisitStatus):
        cur = self.conn.cursor()
        day = vs.day.isoformat()
        a = int(vs.present_child_a)
        b = int(vs.present_child_b)
        cur.execute(
            "REPLACE INTO visit_status (day, present_child_a, present_child_b) VALUES (?,?,?)",
            (day, a, b)
        )
        self.conn.commit()

    def delete_status(self, day: date):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM visit_status WHERE day=?", (day.isoformat(),))
        self.conn.commit()

    def clear_status(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM visit_status")
        self.conn.commit()
        
    def close(self):
        """Schließe die Datenbankverbindung sauber"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def query_visits(
        self,
        start_date: date,
        end_date: date,
        weekdays: List[int],
        status_filters: dict[str,bool]
    ) -> List[dict]:
        cur = self.conn.cursor()
        query = "SELECT day, present_child_a, present_child_b FROM visit_status WHERE day BETWEEN ? AND ?"
        params = [start_date.isoformat(), end_date.isoformat()]

        results = []
        for row in cur.execute(query, params):
            day_date  = date.fromisoformat(row['day'])
            present_a = bool(row['present_child_a'])
            present_b = bool(row['present_child_b'])
            # 1) Wochen-Filtern
            if weekdays and day_date.weekday() not in weekdays:
                continue

            # 2) Status-Filter
            if status_filters.get("both_present") and not (present_a and present_b):
                continue
            if status_filters.get("both_absent") and (present_a or present_b):
                continue
            if status_filters.get("a_absent") and present_a:
                continue
            if status_filters.get("b_absent") and present_b:
                continue

            results.append({
                "day": day_date,
                "present_child_a": present_a,
                "present_child_b": present_b
            })

        return results

    def load_all_status(self) -> Dict[date, 'VisitStatus']:
        cur = self.conn.cursor()
        cur.execute("SELECT day, present_child_a, present_child_b FROM visit_status")
        status = {}
        for row in cur.fetchall():
            d0 = date.fromisoformat(row['day'])
            vs = VisitStatus(d0, bool(row['present_child_a']), bool(row['present_child_b']))
            status[d0] = vs
        cur.close()
        return status

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
