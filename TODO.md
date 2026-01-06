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

- Änderungen an Importfunktionen (CSV/ICS): mine_only=True als Default; OverridePeriod(s) nur für meinen Anteil (holder='mother'); meta enthält anchor_year, assigned ('first'|'second'|'first_14'|'last_14'|'entire'), year.
- Kalender/Statistik: nur importierte Tage erscheinen als planned (keine kompletten Ferien mehr automatisch als Umgang).
- Tests: neue Tests ergänzt (vacation_only_my_days, pfingsten short vacation). Alle Tests müssen lokal grün laufen.

Wenn die Änderungen getestet und committet sind, erstelle ich den PR-Branch und pushe die Änderungen.
