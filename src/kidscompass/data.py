import os
import sqlite3
import shutil
import tempfile
import datetime as _dt
from datetime import date
from typing import List, Dict
from pathlib import Path
from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus
from kidscompass.calendar_logic import generate_standard_days
import logging
import re
import shutil
import time

class Database:
    def __init__(self, db_path: str = None):
        try:
            # Resolve stable absolute DB path. Default: ~/.kidscompass/kidscompass.db
            default = os.path.join(os.path.expanduser("~"), ".kidscompass", "kidscompass.db")
            self.db_path = os.fspath(Path(db_path) if db_path else Path(default))
            # Special in-memory DB
            if self.db_path != ':memory:':
                parent = os.path.dirname(self.db_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
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
        if 'label' not in cols:
            try:
                cur.execute("ALTER TABLE patterns ADD COLUMN label TEXT")
            except Exception:
                pass

        # Overrides: Add und Remove mit Referenz auf patterns
        cur.execute("""
        CREATE TABLE IF NOT EXISTS overrides (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type TEXT NOT NULL,
          from_date TEXT NOT NULL,
          to_date TEXT NOT NULL,
          pattern_id INTEGER,
          holder TEXT,
                    vac_type TEXT,
                    meta TEXT,
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

        # Ensure holder column exists for older DBs
        cur.execute("PRAGMA table_info(overrides)")
        cols = [r['name'] for r in cur.fetchall()]
        if 'holder' not in cols:
            try:
                cur.execute("ALTER TABLE overrides ADD COLUMN holder TEXT")
            except Exception:
                pass
        if 'vac_type' not in cols:
            try:
                cur.execute("ALTER TABLE overrides ADD COLUMN vac_type TEXT")
            except Exception:
                pass
        if 'meta' not in cols:
            try:
                cur.execute("ALTER TABLE overrides ADD COLUMN meta TEXT")
            except Exception:
                pass
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

    def atomic_import_from_sql(self, filename: str):
        """
        Atomarer Import: importiert das SQL in eine temporäre DB, verifiziert
        dass mindestens die `patterns`-Tabelle existiert und ersetzt dann die
        aktuelle DB-Datei durch die temporäre DB (mit Backup).
        Bei `:memory:`-DB wird `import_from_sql` ausgeführt.
        """
        if self.db_path == ':memory:':
            return self.import_from_sql(filename)

        with open(filename, 'r', encoding='utf-8') as f:
            script = f.read()

        ts = _dt.datetime.now().strftime('%Y%m%d_%H%M%S')
        tmpdb = os.path.join(os.path.dirname(self.db_path), f'.tmp_restore_{ts}.db')
        if os.path.exists(tmpdb):
            os.remove(tmpdb)

        conn_tmp = sqlite3.connect(tmpdb)
        conn_tmp.row_factory = sqlite3.Row
        try:
            conn_tmp.executescript(script)
            conn_tmp.commit()
            cur = conn_tmp.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patterns'")
            if cur.fetchone() is None:
                raise ValueError('Import enthält keine Tabelle "patterns"; Restore abgebrochen.')
        except Exception:
            conn_tmp.close()
            if os.path.exists(tmpdb):
                os.remove(tmpdb)
            raise
        finally:
            conn_tmp.close()

        bak = f"{self.db_path}.bak_before_restore_{ts}"
        try:
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, bak)
            shutil.copy2(tmpdb, self.db_path)
        except Exception:
            if os.path.exists(tmpdb):
                os.remove(tmpdb)
            raise
        finally:
            if os.path.exists(tmpdb):
                os.remove(tmpdb)

        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
        finally:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self._ensure_tables()

    # Pattern-Methoden
    def load_patterns(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, weekdays, interval_weeks, start_date, end_date, label FROM patterns"
        )
        out = []
        bad_ids = []
        for row in cur.fetchall():
            wk = row['weekdays'] or ''
            # validate weekdays format: digits and commas only, e.g. '0,1,2'
            if not re.match(r'^\d+(,\d+)*$', wk):
                logging.warning(f"Invalid weekdays for pattern id={row['id']}: '{wk}' - skipping")
                bad_ids.append(row['id'])
                continue
            wd = [int(x) for x in wk.split(',') if x]
            start = date.fromisoformat(row['start_date'])
            end = date.fromisoformat(row['end_date']) if row['end_date'] else None
            pat = VisitPattern(wd, row['interval_weeks'], start, end, label=row['label'] if 'label' in row.keys() else None)
            pat.id = row['id']
            out.append(pat)
        if bad_ids:
            logging.debug(f"load_patterns found invalid weekday rows: {bad_ids}")
        return out    
    def save_pattern(self, pat: VisitPattern):
        try:
            wd_text = ','.join(str(d) for d in pat.weekdays)
            sd = pat.start_date.isoformat()
            ed = pat.end_date.isoformat() if pat.end_date else None
            lab = getattr(pat, 'label', None)
            cur = self.conn.cursor()
            # Prevent duplicate inserts: check for existing identical pattern
            if getattr(pat, 'id', None) is None:
                if ed is None:
                    cur.execute(
                        "SELECT id FROM patterns WHERE weekdays=? AND interval_weeks=? AND start_date=? AND end_date IS NULL",
                        (wd_text, pat.interval_weeks, sd)
                    )
                else:
                    cur.execute(
                        "SELECT id FROM patterns WHERE weekdays=? AND interval_weeks=? AND start_date=? AND end_date=?",
                        (wd_text, pat.interval_weeks, sd, ed)
                    )
                row = cur.fetchone()
                if row:
                    pat.id = row['id']
                    logging.info(f"Duplicate pattern detected; using existing id={pat.id}")
                    return
            if getattr(pat, 'id', None) is not None:
                cur.execute(
                    "UPDATE patterns SET weekdays=?, interval_weeks=?, start_date=?, end_date=?, label=? WHERE id=?",
                    (wd_text, pat.interval_weeks, sd, ed, lab, pat.id)
                )
                print(f"Updated pattern id={pat.id}")
            else:
                cur.execute(
                    "INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date, label) VALUES (?,?,?,?,?)",
                    (wd_text, pat.interval_weeks, sd, ed, lab)
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
                    "SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns WHERE id=?",
                    (row['pattern_id'],)
                )
                prow = pcur.fetchone()
                if prow:
                    wd = [int(x) for x in prow['weekdays'].split(',') if x]
                    start = date.fromisoformat(prow['start_date'])
                    end = date.fromisoformat(prow['end_date']) if prow['end_date'] else None
                    pat = VisitPattern(wd, prow['interval_weeks'], start, end)
                    pat.id = prow['id']
                    ov = OverridePeriod(f, t, pat, holder=row['holder'] if 'holder' in row.keys() else None,
                                         vac_type=row['vac_type'] if 'vac_type' in row.keys() else None,
                                         meta=row['meta'] if 'meta' in row.keys() else None)
                else:
                    # Falls Pattern nicht gefunden -> loggen und überspringen
                    logging.warning(f"Override verweist auf fehlendes Pattern id={row['pattern_id']}")
                    continue
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
            # Stelle sicher, dass das Pattern gespeichert ist und eine id hat
            if getattr(ov.pattern, 'id', None) is None:
                self.save_pattern(ov.pattern)
            pid = ov.pattern.id
            typ = 'add'
        else:
            pid = None
            typ = 'remove'
        holder = getattr(ov, 'holder', None) if isinstance(ov, OverridePeriod) else None
        vac_type = getattr(ov, 'vac_type', None) if isinstance(ov, OverridePeriod) else None
        meta = getattr(ov, 'meta', None) if isinstance(ov, OverridePeriod) else None
        if getattr(ov, 'id', None) is not None:
            cur.execute(
                "UPDATE overrides SET type=?, from_date=?, to_date=?, pattern_id=?, holder=?, vac_type=?, meta=? WHERE id=?",
                (typ, f_iso, t_iso, pid, holder, vac_type, meta, ov.id)
            )
        else:
            cur.execute(
                "INSERT INTO overrides (type, from_date, to_date, pattern_id, holder, vac_type, meta) VALUES (?,?,?,?,?,?,?)",
                (typ, f_iso, t_iso, pid, holder, vac_type, meta)
            )
            ov.id = cur.lastrowid
        self.conn.commit()
        # Debug: logge das gespeicherte Override
        try:
            cur.execute("SELECT * FROM overrides WHERE id=?", (ov.id,))
            logging.debug(f"Saved override: {cur.fetchone()}")
        except Exception:
            pass

    def delete_override(self, override_id: int):
        cur = self.conn.cursor()
        # Ermittele, ob dieses Override auf ein Pattern referenziert (nur zu Informationszwecken)
        try:
            cur.execute("SELECT pattern_id FROM overrides WHERE id=?", (override_id,))
            row = cur.fetchone()
            pattern_id = row['pattern_id'] if row and 'pattern_id' in row.keys() else None
            if pattern_id:
                logging.info(f"Lösche Override id={override_id} (referenziert pattern_id={pattern_id}). Pattern wird nicht automatisch entfernt.")
            # Lösche nur das Override — sicherer, damit keine Muster unbeabsichtigt verloren gehen
            cur.execute("DELETE FROM overrides WHERE id=?", (override_id,))
            self.conn.commit()
        except Exception as e:
            logging.exception(f"Fehler beim Löschen des Overrides id={override_id}: {e}")
            raise

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

    def find_unreferenced_patterns(self, start_date: date | None = None, end_date: date | None = None) -> List[Dict]:
        """Returns list of pattern rows (dict) that are not referenced by any override and
        that produce at least one date in the given date window (if provided).
        """
        cur = self.conn.cursor()
        cur.execute("SELECT pattern_id FROM overrides WHERE pattern_id IS NOT NULL")
        referenced = {r['pattern_id'] for r in cur.fetchall()}

        cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns")
        out = []
        for row in cur.fetchall():
            pid = row['id']
            if pid in referenced:
                continue
            # If no window is provided, include all unreferenced patterns
            if start_date is None and end_date is None:
                out.append(dict(row))
                continue
            # Validate weekdays format
            wk = row['weekdays'] or ''
            if not re.match(r'^\d+(,\d+)*$', wk):
                logging.warning(f"Skipping pattern id={pid} due to invalid weekdays='{wk}'")
                continue
            # Build pattern and check if it produces dates in window
            wd = [int(x) for x in wk.split(',') if x]
            sd = date.fromisoformat(row['start_date'])
            ed = date.fromisoformat(row['end_date']) if row['end_date'] else None
            pat = VisitPattern(wd, row['interval_weeks'], sd, ed)
            years = range(sd.year, (ed.year if ed else (end_date.year if end_date else sd.year)) + 1)
            has = False
            for y in years:
                for d in generate_standard_days(pat, y):
                    if start_date <= d <= end_date:
                        has = True
                        break
                if has:
                    break
            if has:
                out.append(dict(row))
        cur.close()
        return out

    def find_duplicate_patterns(self) -> List[List[int]]:
        """Return list of lists of pattern ids that are duplicates (same key)."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns ORDER BY id")
        by_key = {}
        for row in cur.fetchall():
            key = (','.join(sorted([x for x in row['weekdays'].split(',') if x])), row['interval_weeks'], row['start_date'], row['end_date'] if row['end_date'] else None)
            by_key.setdefault(key, []).append(row['id'])
        cur.close()
        return [ids for ids in by_key.values() if len(ids) > 1]

    def list_fk_refs_to_patterns(self) -> List[tuple]:
        """Return list of (table, from_col, to_table, to_col) where foreign keys point to patterns(id)."""
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r['name'] for r in cur.fetchall()]
        refs = []
        for tbl in tables:
            try:
                fk_rows = self.conn.execute(f"PRAGMA foreign_key_list('{tbl}')").fetchall()
            except Exception:
                fk_rows = []
            for fk in fk_rows:
                if fk['table'] == 'patterns' and fk['to'] == 'id':
                    refs.append((tbl, fk['from'], fk['table'], fk['to']))
        cur.close()
        return refs

    def _pattern_row(self, pattern_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date, label FROM patterns WHERE id=?", (pattern_id,))
        row = cur.fetchone()
        cur.close()
        return row

    def find_bad_patterns(self) -> List[Dict]:
        """Return list of rows from patterns that have invalid weekdays values."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, weekdays FROM patterns")
        bad = []
        for row in cur.fetchall():
            wk = row['weekdays'] or ''
            if not re.match(r'^\d+(,\d+)*$', wk):
                bad.append({'id': row['id'], 'weekdays': wk})
        cur.close()
        return bad

    def repair_patterns_weekdays(self, action: str = 'quarantine') -> Dict:
        """
        Repair invalid patterns.weekdays entries.
        action: 'quarantine' (move to bad_patterns) or 'delete' (remove rows).
        Returns report: {'count': int, 'ids': [...], 'backup': path}
        """
        bad = self.find_bad_patterns()
        if not bad:
            return {'count': 0, 'ids': [], 'backup': None}

        ts = time.strftime('%Y%m%d_%H%M%S')
        backup = f"{self.db_path}.bak_weekdays_{ts}"
        try:
            shutil.copy2(self.db_path, backup)
        except Exception as e:
            logging.exception(f"Failed to create DB backup before repair: {e}")
            raise

        ids = [r['id'] for r in bad]
        cur = self.conn.cursor()
        try:
            if action == 'quarantine':
                # create bad_patterns table if not exists with same columns
                cur.execute("CREATE TABLE IF NOT EXISTS bad_patterns AS SELECT * FROM patterns WHERE 0")
                # insert rows into bad_patterns preserving id where possible
                for r in bad:
                    # fetch full row
                    prow = self.conn.execute("SELECT * FROM patterns WHERE id=?", (r['id'],)).fetchone()
                    if prow:
                        cols = list(prow.keys())
                        placeholders = ','.join('?' for _ in cols)
                        values = [prow[c] for c in cols]
                        cur.execute(f"INSERT INTO bad_patterns ({','.join(cols)}) VALUES ({placeholders})", values)
            # delete from original table
            cur.execute(f"DELETE FROM patterns WHERE id IN ({','.join('?' for _ in ids)})", ids)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

        return {'count': len(ids), 'ids': ids, 'backup': backup}

    def _find_pattern_by_key(self, weekdays_text: str, interval_weeks: int, start_date_iso: str, end_date_iso: str | None):
        cur = self.conn.cursor()
        if end_date_iso is None:
            cur.execute("SELECT id FROM patterns WHERE weekdays=? AND interval_weeks=? AND start_date=? AND end_date IS NULL", (weekdays_text, interval_weeks, start_date_iso))
        else:
            cur.execute("SELECT id FROM patterns WHERE weekdays=? AND interval_weeks=? AND start_date=? AND end_date=?", (weekdays_text, interval_weeks, start_date_iso, end_date_iso))
        row = cur.fetchone()
        cur.close()
        return row['id'] if row else None

    def split_pattern(self, pattern_id: int, split_date: date, new_weekdays: List[int], new_interval_weeks: int = None, end_prev: bool = True):
        """
        Split an existing pattern at split_date: optionally end the old pattern at split_date-1
        and create a new pattern starting at split_date with new_weekdays and new_interval_weeks.

        Returns dict with keys: old_updated (bool), new_pattern_id (int or None), message (str).
        """
        row = self._pattern_row(pattern_id)
        if not row:
            raise ValueError(f'Pattern id={pattern_id} not found')

        old_start = date.fromisoformat(row['start_date'])
        old_end = date.fromisoformat(row['end_date']) if row['end_date'] else None

        # If old pattern ends before split_date, nothing to do
        if old_end is not None and old_end < split_date:
            return {'old_updated': False, 'new_pattern_id': None, 'message': 'Kein Änderungsbedarf, altes Pattern endet vor dem Split-Datum.'}

        # If split_date <= old_start, caller should decide to replace; here we'll perform replace behaviour
        if split_date <= old_start:
            # Replace: update existing pattern's weekdays/interval/start_date
            with self.conn:
                wd_text = ','.join(str(d) for d in sorted(new_weekdays))
                niw = new_interval_weeks if new_interval_weeks is not None else row['interval_weeks']
                cur = self.conn.cursor()
                # Derive new label
                old_label = row['label'] if 'label' in row.keys() else None
                new_label = f"{old_label} (ab {split_date.isoformat()} geändert)" if old_label else f"Pattern (ab {split_date.isoformat()} geändert)"
                cur.execute("UPDATE patterns SET weekdays=?, interval_weeks=?, start_date=?, label=? WHERE id=?", (wd_text, niw, split_date.isoformat(), new_label, pattern_id))
                return {'old_updated': True, 'new_pattern_id': pattern_id, 'message': 'Pattern ersetzt (kein Split, da Split-Datum vor Start).'}

        # Normal split: set old end_date = split_date -1 if asked
        new_id = None
        old_updated = False
        wd_text_new = ','.join(str(d) for d in sorted(new_weekdays))
        niw = new_interval_weeks if new_interval_weeks is not None else row['interval_weeks']
        old_end_target = (split_date - _dt.timedelta(days=1)).isoformat()
        old_end_iso = row['end_date'] if row['end_date'] else None

        try:
            with self.conn:
                cur = self.conn.cursor()
                # Update old pattern end_date if requested and if it was NULL or >= split_date
                if end_prev and (row['end_date'] is None or date.fromisoformat(row['end_date']) >= split_date):
                    cur.execute("UPDATE patterns SET end_date=? WHERE id=?", (old_end_target, pattern_id))
                    old_updated = cur.rowcount > 0

                # Check if identical new pattern already exists
                existing = self._find_pattern_by_key(wd_text_new, niw, split_date.isoformat(), old_end_iso)
                if existing:
                    new_id = existing
                else:
                    # Insert new pattern with start_date=split_date and end_date = old_end_iso
                    # Derive label from old pattern if present
                    old_label = row['label'] if 'label' in row.keys() else None
                    new_label = f"{old_label} (ab {split_date.isoformat()} geändert)" if old_label else None
                    cur.execute("INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date, label) VALUES (?,?,?,?,?)", (wd_text_new, niw, split_date.isoformat(), old_end_iso, new_label))
                    new_id = cur.lastrowid
        except Exception as e:
            # Any error triggers rollback automatically via context manager
            raise

        return {'old_updated': old_updated, 'new_pattern_id': new_id, 'message': 'Split durchgeführt.'}

    def import_vacations_from_csv(self, filename: str, anchor_year: int = 2025):
        """
        Import simple CSV with columns: from_date, to_date, label (label optional).
        For each vacation range, split into two halves and create OverridePeriod entries
        for first/second half according to parity anchored at `anchor_year`.
        """
        import csv
        created = []
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                try:
                    f0 = date.fromisoformat(row[0].strip())
                    t0 = date.fromisoformat(row[1].strip())
                    label = row[2].strip() if len(row) > 2 else ''
                except Exception:
                    continue
                halves = self._split_into_halves(f0, t0)
                year = f0.year
                first_holder, second_holder = self._holders_for_year_and_label(year, label, anchor_year)
                # create override-adds covering each half: pattern = all weekdays
                for (hf, ht), holder in zip(halves, (first_holder, second_holder)):
                    pat = VisitPattern(list(range(7)), 1, hf, ht)
                    ov = OverridePeriod(hf, ht, pat, holder=holder)
                    self.save_override(ov)
                    created.append(ov)
        return created

    def import_vacations_from_ics(self, filename: str, anchor_year: int = 2025):
        """
        Minimal ICS parser: extract VEVENT blocks with DTSTART/DTEND and SUMMARY (optional).
        Create overrides similar to CSV import.
        """
        created = []
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        # Very simple parsing: find VEVENT blocks
        events = content.split('BEGIN:VEVENT')
        for ev in events[1:]:
            # find DTSTART and DTEND lines
            dtstart = None
            dtend = None
            label = ''
            for line in ev.splitlines():
                line = line.strip()
                if line.upper().startswith('DTSTART'):
                    parts = line.split(':')
                    if len(parts) > 1:
                        val = parts[-1]
                        try:
                            if len(val) == 8 and val.isdigit():
                                dtstart = date(int(val[0:4]), int(val[4:6]), int(val[6:8]))
                            else:
                                dtstart = date.fromisoformat(val[:10])
                        except Exception:
                            dtstart = None
                if line.upper().startswith('DTEND'):
                    parts = line.split(':')
                    if len(parts) > 1:
                        val = parts[-1]
                        try:
                            if len(val) == 8 and val.isdigit():
                                dtend = date(int(val[0:4]), int(val[4:6]), int(val[6:8]))
                            else:
                                dtend = date.fromisoformat(val[:10])
                        except Exception:
                            dtend = None
                if line.upper().startswith('SUMMARY'):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        label = parts[1].strip()
            if dtstart and dtend:
                # Detect vacation type from SUMMARY
                import re, json
                l = (label or '').lower()
                vac_type = None
                if re.search(r'weihnacht', l):
                    vac_type = 'weihnachten'
                elif re.search(r'oster', l):
                    vac_type = 'oster'
                elif re.search(r'sommer', l):
                    vac_type = 'sommer'
                elif re.search(r'herbst', l):
                    vac_type = 'herbst'
                else:
                    vac_type = self._ask_vacation_type(label)

                halves = self._split_into_halves(dtstart, dtend)
                year = dtstart.year
                first_holder, second_holder = self._holders_for_year_and_label(year, label, anchor_year)

                # For Christmas, attach special metadata about handover times
                for (hf, ht), holder, half_idx in zip(halves, (first_holder, second_holder), (0,1)):
                    pat = VisitPattern(list(range(7)), 1, hf, ht)
                    meta = None
                    if vac_type == 'weihnachten':
                        # First half: ends at first holiday 18:00, second half: until Jan 1 17:00
                        if half_idx == 0:
                            meta = json.dumps({'end_type':'first_holiday','end_time':'18:00','anchor_year':anchor_year})
                        else:
                            meta = json.dumps({'end_type':'jan1','end_time':'17:00','anchor_year':anchor_year})
                    ov = OverridePeriod(hf, ht, pat, holder=holder, vac_type=vac_type, meta=meta)
                    self.save_override(ov)
                    created.append(ov)
        return created

    def _split_into_halves(self, start: date, end: date):
        """Split inclusive date range into two halves (first half may be larger by one day)."""
        days = (end - start).days + 1
        half = days // 2
        first_end = start + _dt.timedelta(days=half - 1)
        second_start = first_end + _dt.timedelta(days=1)
        return [(start, first_end), (second_start, end)]

    def _holders_for_year_and_label(self, year: int, label: str, anchor_year: int = 2025):
        """
        Decide which holder gets first or second half based on anchor_year parity and label.
        Default: anchor_year's first-half goes to 'mother'. For following years it alternates.
        Label can be used to apply special rules for 'Weihnachten' etc. (not fully specialized here).
        Returns (first_holder, second_holder)
        """
        parity = (year - anchor_year) % 2 == 0
        # Anchor_year parity True => mother gets first half
        if parity:
            return 'mother', 'father'
        return 'father', 'mother'

    def _ask_vacation_type(self, label: str) -> str:
        """
        Ask the user to classify a vacation when import cannot decide.
        If running headless (no QApplication), return 'unknown'.
        """
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app is None:
                return 'unknown'
            # Present dialog
            opts = ['Weihnachten', 'Ostern', 'Sommer', 'Herbst', 'Unbekannt']
            msg = QMessageBox()
            msg.setWindowTitle('Welche Ferienart ist das?')
            msg.setText(f'Ferienbeschreibung: "{label}"\nWelche Ferienart ist das?')
            buttons = []
            for o in opts:
                buttons.append(msg.addButton(o, QMessageBox.ActionRole))
            msg.exec()
            btn = msg.clickedButton()
            if btn:
                idx = buttons.index(btn)
                choice = opts[idx]
                if choice == 'Weihnachten':
                    return 'weihnachten'
                if choice == 'Ostern':
                    return 'oster'
                if choice == 'Sommer':
                    return 'sommer'
                if choice == 'Herbst':
                    return 'herbst'
                return 'unknown'
        except Exception:
            return 'unknown'

    def remove_duplicate_patterns(self, keep_first=True) -> int:
        """
        Safe duplicate removal by merging references first.

        Strategy:
        - Find duplicate groups
        - For each group pick canonical id (min id if keep_first)
        - Find all tables that have a foreign key referencing patterns(id)
        - For each such table/column: UPDATE table SET col=canonical WHERE col=duplicate
        - After remapping all references, DELETE duplicate pattern rows
        Returns number of deleted rows.
        """
        dup_groups = self.find_duplicate_patterns()
        if not dup_groups:
            return 0

        cur = self.conn.cursor()
        # Discover referencing tables/columns via PRAGMA foreign_key_list
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r['name'] for r in cur.fetchall()]
        refs = []  # list of (table, from_col, to_table, to_col)
        for tbl in tables:
            try:
                fk_rows = self.conn.execute(f"PRAGMA foreign_key_list('{tbl}')").fetchall()
            except Exception:
                fk_rows = []
            for fk in fk_rows:
                # fk fields: id, seq, table, from, to, on_update, on_delete, match
                if fk['table'] == 'patterns' and fk['to'] == 'id':
                    refs.append((tbl, fk['from']))

        if not refs:
            raise RuntimeError('Keine Foreign-Key-Referenzen auf patterns gefunden; Abbruch.')

        total_removed = 0
        total_updated = 0
        backup_path = None
        # Create automatic backup of DB file before modifying (if not in-memory)
        try:
            if self.db_path and self.db_path != ':memory:' and os.path.exists(self.db_path):
                ts = _dt.datetime.now().strftime('%Y%m%d_%H%M%S')
                bak = f"{self.db_path}.backup_before_merge_{ts}"
                shutil.copy2(self.db_path, bak)
                backup_path = bak
        except Exception as e:
            logging.exception('Could not create DB backup before dedup: %s', e)
            # proceed anyway, but note backup_path is None
        try:
            # Use a transaction
            with self.conn:
                for ids in dup_groups:
                    canonical = ids[0] if keep_first else ids[-1]
                    duplicates = [pid for pid in ids if pid != canonical]
                    # Remap references
                    for tbl, col in refs:
                        for dup in duplicates:
                            cur.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (canonical, dup))
                            total_updated += cur.rowcount
                    # Delete duplicate patterns
                    for dup in duplicates:
                        cur.execute("DELETE FROM patterns WHERE id=?", (dup,))
                        total_removed += cur.rowcount
        finally:
            cur.close()

        # Integrity check
        try:
            fk_issues = list(self.conn.execute("PRAGMA foreign_key_check").fetchall())
            if fk_issues:
                raise RuntimeError(f'Foreign key check failed after merge: {fk_issues}')
        except Exception:
            # rethrow with context
            raise

        # Return counts and backup path (if available)
        if backup_path:
            return total_removed, total_updated, backup_path
        return total_removed, total_updated

    def reset_plan(self, keep_visit_status: bool = True):
        """Löscht alle patterns und overrides. Wenn keep_visit_status==True, bleibt visit_status erhalten."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM overrides")
        cur.execute("DELETE FROM patterns")
        if not keep_visit_status:
            cur.execute("DELETE FROM visit_status")
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
