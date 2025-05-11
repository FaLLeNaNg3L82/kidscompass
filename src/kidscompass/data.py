import sqlite3
from datetime import date
from kidscompass.models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "kidscompass.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self.conn.cursor()
        # Muster-Tabellen mit optionalem Endedatum
        cur.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          weekdays TEXT NOT NULL,
          interval_weeks INTEGER NOT NULL,
          start_date TEXT NOT NULL
        )""")
        # Füge end_date hinzu, falls noch nicht vorhanden
        cur.execute("PRAGMA table_info(patterns)")
        cols = [row['name'] for row in cur.fetchall()]
        if 'end_date' not in cols:
            cur.execute("ALTER TABLE patterns ADD COLUMN end_date TEXT")

        # Overrides: Add und Remove
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

    # Muster-Methoden
    def load_patterns(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, weekdays, interval_weeks, start_date, end_date FROM patterns")
        patterns = []
        for row in cur.fetchall():
            wd = [int(x) for x in row["weekdays"].split(",") if x]
            start = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"]) if row["end_date"] else None
            pat = VisitPattern(wd, row["interval_weeks"], start, end)
            pat.id = row["id"]
            patterns.append(pat)
        return patterns

    def save_pattern(self, pat: VisitPattern):
        wd_text = ",".join(str(d) for d in pat.weekdays)
        sd = pat.start_date.isoformat()
        ed = pat.end_date.isoformat() if getattr(pat, "end_date", None) else None
        cur = self.conn.cursor()
        if hasattr(pat, "id"):
            cur.execute(
                "UPDATE patterns SET weekdays=?, interval_weeks=?, start_date=?, end_date=? WHERE id=?",
                (wd_text, pat.interval_weeks, sd, ed, pat.id)
            )
        else:
            cur.execute(
                "INSERT INTO patterns (weekdays, interval_weeks, start_date, end_date) VALUES (?,?,?,?)",
                (wd_text, pat.interval_weeks, sd, ed)
            )
            pat.id = cur.lastrowid
        self.conn.commit()

    def delete_pattern(self, pattern_id: int):
        self.conn.execute("DELETE FROM patterns WHERE id=?", (pattern_id,))
        self.conn.commit()

    # Override-Methoden
    def load_overrides(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM overrides")
        overrides = []
        for row in cur.fetchall():
            f = date.fromisoformat(row["from_date"])
            t = date.fromisoformat(row["to_date"])
            if row["type"] == 'add':
                cur2 = self.conn.cursor()
                cur2.execute(
                    "SELECT weekdays, interval_weeks, start_date, end_date FROM patterns WHERE id=?",
                    (row["pattern_id"],)
                )
                prow = cur2.fetchone()
                wd = [int(x) for x in prow["weekdays"].split(",") if x]
                start = date.fromisoformat(prow["start_date"])
                end = date.fromisoformat(prow["end_date"]) if prow["end_date"] else None
                pat = VisitPattern(wd, prow["interval_weeks"], start, end)
                pat.id = row["pattern_id"]
                ov = OverridePeriod(f, t, pat)
            else:
                ov = RemoveOverride(f, t)
            ov.id = row['id']
            overrides.append(ov)
        return overrides

    def save_override(self, ov):
        cur = self.conn.cursor()
        from_date = ov.from_date.isoformat()
        to_date = ov.to_date.isoformat()
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
                (typ, from_date, to_date, pid, ov.id)
            )
        else:
            cur.execute(
                "INSERT INTO overrides (type, from_date, to_date, pattern_id) VALUES (?,?,?,?)",
                (typ, from_date, to_date, pid)
            )
            ov.id = cur.lastrowid
        self.conn.commit()

    def delete_override(self, override_id: int):
        self.conn.execute("DELETE FROM overrides WHERE id=?", (override_id,))
        self.conn.commit()

    # Status-Methoden
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
        self.conn.execute("DELETE FROM visit_status WHERE day=?", (day.isoformat(),))
        self.conn.commit()

    def clear_status(self):
        self.conn.execute("DELETE FROM visit_status")
        self.conn.commit()
