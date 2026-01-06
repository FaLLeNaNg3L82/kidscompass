# KidsCompass – TODO (aktualisiert)

Aktueller Status:

- Pfingstferien-Erkennung: implemented ✅
- Export-Mapping angepasst ✅
- Tests: aktuell grün (vor Änderung der Import-Logik) ✅

Abgleich mit Assistants 10-Schritte-Liste (reconciled):

1) Implement weekend patterns support — offen
2) Add tests for weekend every-N-weeks behavior — offen
3) Update calendar rendering to show weekend phases — offen
4) Implement Pfingstferien detection and rules — erledigt ✅
5) Add import parity for vacation types and fallback mapping — in Arbeit (siehe next step)
6) Add cancelled visits table and APIs — offen
7) Integrate cancellations with export and statistics — offen
8) Add migration & post-import integrity checks — offen
9) Run full test suite and fix regressions — offen
10) Create PR for feature branch — offen

Nächster Schritt (aufgetragen / in Arbeit):

- Ferienimport-Paritätslogik: mine_only-Import (nur "meine" Ferientage) implementieren; Anchor-Year-Parität (anchor_year=2025) und Sommer-14-Tage-Regel einbauen. Tests und Metadaten (anchor_year, assigned, year) hinzufügen.

Technische Notizen:

- Änderungen an Importfunktionen (CSV/ICS): mine_only=True als Default; OverridePeriod(s) nur für meinen Anteil (holder='father'); meta enthält anchor_year, assigned ('first'|'second'|'first_14'|'last_14'|'entire'), year.
- Kalender/Statistik: nur importierte Tage erscheinen als planned (keine kompletten Ferien mehr automatisch als Umgang).
- Tests: neue Tests ergänzt (vacation_only_my_days, pfingsten short vacation). Alle Tests müssen lokal grün laufen.

Wenn die Änderungen getestet und committet sind, erstelle ich den PR-Branch und pushe die Änderungen.


RUNBOOK:
# KidsCompass – Next Steps (Runbook)

# 0) Setup / sanity
git status
git branch --show-current
python -V

# 1) Ostern/Herbst day-based split (Commit D)
# - switch_day = first Sunday on/after (start_date + 6 days)
# - Sunday = neutral (not planned)
# - Phase A: start..Saturday
# - Phase B: Monday..end
# - mine_only=True => only father override
# - Update/extend tests for these rules
python -m pytest -q

# 2) Sommer-Regel vereinfachen (Commit E)
# - 2025: last 14 days
# - 2026: first 14 days
# - alternating thereafter
# - No times, no Sa/So anchoring, day-based only
python -m pytest -q

# 3) Short-vacation rules 1–2 days (Commit F)
# - 1 day: that day (mine_only)
# - 2 days: 1/1 split by parity
python -m pytest -q

# 4) “Ignorieren/Neutralisieren”-Feature (Excluded days) (Commit G)
# - Add excluded_days table + UI button
# - Excluded days removed from planned/stats/export
python -m pytest -q

# 5) Full regression + cleanup
python -m pytest -q
git status

# 6) PR erstellen
# base: main
# head: fix/holiday-and-planned-logic
