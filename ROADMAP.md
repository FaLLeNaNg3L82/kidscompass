# KidsCompass Roadmap & To‑Dos

Dieses Dokument fasst alle größeren anstehenden Aufgaben zusammen und kann versioniert im Git‑Repo abgelegt werden.

---

## 1. Persistenz-Modell
- JSON‑Datei entfernen, alle Muster, Overrides und VisitStatus in SQLite ablegen
- Klare DAO‑Schnittstelle in `data.py` implementieren
- Migrationstool: bestehende JSON‑Daten in DB importieren

## 2. Reporting‑Tab ausbauen
- Erweiterte PDF‑Layouts (Titelblatt, Tabellen)
- Chart‑Integration direkt im UI (mini‑Vorschau)
- Auswahl mehrerer Diagrammtypen (Linien, Balken, Heatmap)

## 3. Erweiterte Statistik-Abfragen
- Mittwochs‑Ausfälle (Filter nach Wochentag)
- Trend‑Analyse über Zeiträume (z.B. Rolling Average)
- Häufigkeit nach Wochentags‑ und Wochenendverteilung
- Export der Statistiken als CSV/Excel

## 4. Tests erweitern
- Unit‑Tests für alle DB‑Funktionen (`data.py`)
- UI‑Tests (z.B. mit pytest‑qt) für Tab‑Interaktionen
- Schnell‑Integrationstests (PDF/Chart‑Erzeugung)

## 5. Linting & Formatting
- Black als Code‑Formatter konfigurieren
- isort für Imports
- flake8 für static linting
- pre-commit‑Hook zur Automatisierung

## 6. Workflow & Git‑Best Practices
- GitHub Projects / Issues anlegen und verknüpfen
- Branching‑Modell definieren (Git Flow / trunk‑based)
- Release‑Tags automatisiert (CI/CD)

---

*Legende:*
- ✅ abgeschlossen 
- ➕ in Arbeit 
- ⏳ geplant

