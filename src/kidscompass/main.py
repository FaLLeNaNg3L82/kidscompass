# src/kidscompass/main.py

import json
from datetime import date
from typing import List

from .models import VisitPattern, OverridePeriod, VisitStatus, RemoveOverride
from .calendar_logic import generate_standard_days, apply_overrides

CONFIG_FILE = "kidscompass_config.json"

def input_visit_pattern() -> VisitPattern:
    print("\n✏️  Neuer Standard-Rhythmus:")
    days_str = input("  Wochentage (0=Mo … 6=So), kommasepariert: ")
    weekdays = [int(x) for x in days_str.split(",") if x.strip().isdigit()]
    interval = int(input("  Intervall in Wochen (z.B. 1): "))
    start_str = input("  Startdatum (YYYY-MM-DD) [leer=heute]: ").strip()
    start = date.today() if not start_str else date.fromisoformat(start_str)
    return VisitPattern(weekdays=weekdays, interval_weeks=interval, start_date=start)

def input_override() -> OverridePeriod:
    print("\n🛑  Neuer Urlaubs-Override:")
    from_str = input("  Von (YYYY-MM-DD): ")
    to_str   = input("  Bis (YYYY-MM-DD): ")
    ov_pat   = input_visit_pattern()
    return OverridePeriod(
        from_date=date.fromisoformat(from_str),
        to_date=date.fromisoformat(to_str),
        pattern=ov_pat
    )

def run_wizard():
    print("🎯 Willkommen zum KidsCompass Setup Wizard 🎯")
    year = int(input("Für welches Jahr soll der Kalender erstellt werden? "))

    # 1) Standard-Muster erfassen
    patterns: List[VisitPattern] = []
    while True:
        patterns.append(input_visit_pattern())
        if input("Weiteren Rhythmus hinzufügen? (j/n) ").lower() != "j":
            break

    # 2) Overrides erfassen
    overrides = []
    if input("Urlaubs-Overrides hinzufügen? (j/n) ").lower() == "j":
        while True:
            mode = input("  Welcher Typ? [1] Ersatz-Pattern, [2] Entfernen aller Tage: ")
            if mode == "1":
                overrides.append(input_override())            # wie bisher
            else:
                f = date.fromisoformat(input("  Von (YYYY-MM-DD): "))
                t = date.fromisoformat(input("  Bis (YYYY-MM-DD): "))
                overrides.append(RemoveOverride(from_date=f, to_date=t))
            if input("Weiteren Override? (j/n) ").lower() != "j":
                break

    # 3) Termine generieren
    std_days = []
    for pat in patterns:
        std_days += generate_standard_days(pat, year)
    all_days = apply_overrides(std_days, overrides)

    # 4) Ausgabe und Speichern
    print(f"\n✅ Insgesamt {len(all_days)} Umgangstermine im Jahr {year}:")
    for d in all_days:
        print(" ", d.isoformat())

    save = input("\nKonfiguration speichern? (j/n) ").lower()
    if save == "j":
        data = {
            "year": year,
            "patterns": [pat.__dict__ for pat in patterns],
            "overrides": [
                {
                    "from_date": ov.from_date.isoformat(),
                    "to_date": ov.to_date.isoformat(),
                    "pattern": ov.pattern.__dict__,
                }
                for ov in overrides
            ]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Konfiguration in {CONFIG_FILE} gespeichert.")

if __name__ == "__main__":
    run_wizard()
