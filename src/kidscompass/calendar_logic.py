# src/kidscompass/calendar_logic.py
from datetime import date, timedelta
from typing import List, Union
from .models import VisitPattern, OverridePeriod, RemoveOverride


def generate_standard_days(pattern: VisitPattern, year: int) -> List[date]:
    """Erzeuge alle Besuchsdaten im Jahr nach weekday-Liste und Wochen-Intervall."""
    start_of_year = date(year, 1, 1)
    end_of_year = date(year, 12, 31)
    # Ab dem späteren Datum starten
    cursor = max(start_of_year, pattern.start_date)
    dates: List[date] = []

    for wd in pattern.weekdays:
        # ersten Termin dieses Wochentags ermitteln
        delta_days = (wd - cursor.weekday() + 7) % 7
        current = cursor + timedelta(days=delta_days)
        # in Intervall-Schritten bis Jahresende
        while current <= end_of_year and (pattern.end_date is None or current <= pattern.end_date):
            dates.append(current)
            current += timedelta(weeks=pattern.interval_weeks)

    return sorted(set(dates))


def apply_overrides(
    standard_days: List[date],
    overrides: List[Union[OverridePeriod, RemoveOverride]]
) -> List[date]:
    """
    Wende Overrides an:
      - RemoveOverride: entfernt Standard-Termine im Zeitraum.
      - OverridePeriod: entfernt Standard-Termine im Zeitraum, fügt anstelle dessen die Pattern-Termine im Zeitraum hinzu.
    """
    # Beginne mit allen Standard-Tagen
    result_days = set(standard_days)
    override_days = set()

    for ov in overrides:
        # Entfernte Phase für beide Override-Typen
        to_remove = {d for d in result_days if ov.from_date <= d <= ov.to_date}
        result_days -= to_remove

        # Für reine RemoveOverrides nichts hinzufügen
        if isinstance(ov, RemoveOverride):
            continue

        # Für OverridePeriod generiere zusätzliche Tage
        if isinstance(ov, OverridePeriod):
            # generiere für das Jahr des Overrides
            year = ov.from_date.year
            cal = generate_standard_days(ov.pattern, year)
            for d in cal:
                if ov.from_date <= d <= ov.to_date:
                    override_days.add(d)

    # Vereinige verbleibende Standard- und alle Override-Termine
    combined = result_days.union(override_days)
    return sorted(combined)
