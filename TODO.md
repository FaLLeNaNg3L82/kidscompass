# KidsCompass – TODO

- [x] Dedup/Cleanup functions
- [x] Reset "Plan aus Urteil erstellen" flow
- [x] Vacation import (ICS/CSV) + half-splitting
- [ ] Phases model & generator wiring (pragmatisch: Labels + split_pattern)
- [ ] Handover rules config + export metadata (PDF Text)
- [x] Tests: restore, dedup, reset, weekends/midweek, vacation halves
 
Aktueller Projektstand (rekonstruiert):

- VisitPattern hat optionales Feld `label` und wird beim Laden/Speichern berücksichtigt.
- DB-Migrationslogik fügt `label` in patterns und `meta`/`vac_type` in overrides ein (data._ensure_tables).
- export_utils.format_visit_window(...) existiert und parst `OverridePeriod.meta` (JSON) sowie eine `handover_rules`-Config.
- Settings-UI wurde erweitert: einfache Eingabefelder für Handover-Regeln (after_school, school_start, fixed_18) und Speicherung in ~/.kidscompass/kidscompass_config.json via neuem modul `kidscompass.config`.
- Export-PDF (ExportWorker/UI) erzeugt jetzt zusätzlich eine Tabelle "Geplante Termine (mit Metadaten)" und ruft format_visit_window für Hinweise auf.

Offene/noch zu prüfende Punkte:

- Export: Vollständige Handhabung aller meta-Fälle (Weihnachten-Special, generische Regeln) testen und Strings konsistent lokalisieren.
- Settings: UI speichert config, aber Anzeige/Validierung und Export-Integration prüfen (werden aktuell geladen und verwendet).
- Phasen: Patterns können Labels haben; Flow für Reset "Plan aus Urteil" und split_pattern soll Labels sinnvoll setzen/ableiten.

Nächste kleine, risikoarme Tasks (priorisiert):

1) Export/Handover-Text (klein)
	- Tests: Ergänze tests/test_export_formatting.py (Weihnachten meta + generische rule) — sicher, rein funktional.
	- Verbessere export_utils.format_visit_window Fallbacks/Localization falls meta fehlt.
	- Stelle sicher, dass ExportWorker/UI die config aus kc_config lädt und übergibt (ist größtenteils implementiert).

2) Pattern-Labels als Phasen (klein)
	- UI: Beim Anzeigen von Patterns Label voranstellen (z.B. in entry_list und AnnotatedCalendar-Annotationen).
	- Reset "Plan aus Urteil": beim Erstellen der Muster Labels setzen (z.B. "Wochenende (Urteil)").
	- split_pattern: Beim Erzeugen eines neuen Pattern das Label automatisch auf "<alt> (ab YYYY-MM-DD geändert)" setzen.

3) Optional: Minimal UI-Verbesserung für Handover-Regeln
	- Validierung/Tooltips für Eingabefelder (z.B. feste Zeitangabe für fixed_...)
	- Export-Text: konsistente Datumsformatierung (z.B. DD.MM oder ISO) in PDF-Tabelle.

Ich habe diese Punkte in die lokale TODO.md geschrieben. Wenn du möchtest, mache ich als Nächstes die Tests (1) an und committe in zwei Commits: (a) Export + Tests, (b) Labels/DB/UI.
