from datetime import date, timedelta
from typing import List, Union
from .models import VisitPattern, OverridePeriod, RemoveOverride, VisitStatus


def generate_standard_days(pattern: VisitPattern, year: int) -> List[date]:
    """Erzeuge alle Besuchsdaten im Jahr nach weekday-Liste, Wochen-Intervall
       und optionalem end_date."""
    start_of_year = date(year, 1, 1)
    end_of_year   = date(year, 12, 31)

    # Ab dem späteren Datum starten
    cursor = max(start_of_year, pattern.start_date)
    dates: List[date] = []

    for wd in pattern.weekdays:
        # ersten Termin dieses Wochentags ermitteln
        delta_days = (wd - cursor.weekday() + 7) % 7
        current = cursor + timedelta(days=delta_days)

        # in Intervall-Schritten bis Jahresende und bis end_date (falls gesetzt)
        while current <= end_of_year and (pattern.end_date is None or current <= pattern.end_date):
            dates.append(current)
            current += timedelta(weeks=pattern.interval_weeks)

    # sort & dedupe
    return sorted(set(dates))


def apply_overrides(
    standard_days: List[date],
    overrides: List[Union[OverridePeriod, RemoveOverride]]
) -> List[date]:
    """
    Wende Overrides an:
      - RemoveOverride: entfernt Standard-Termine im Zeitraum.
      - OverridePeriod: entfernt Standard-Termine im Zeitraum, fügt an Stelle dessen die Pattern-Termine im Zeitraum hinzu.
    """
    result_days   = set(standard_days)
    override_days = set()

    for ov in overrides:
        # Entferne alle Std.-Tage im Override-Zeitraum
        to_remove = {d for d in result_days if ov.from_date <= d <= ov.to_date}
        result_days -= to_remove

        if isinstance(ov, OverridePeriod):
            # generiere für das Jahr des Overrides
            year = ov.from_date.year
            cal  = generate_standard_days(ov.pattern, year)
            for d in cal:
                if ov.from_date <= d <= ov.to_date:
                    override_days.add(d)

    # Vereine verbleibende Standard- und Override-Termine
    combined = result_days.union(override_days)
    return sorted(combined)


def summarize_visits(planned: List[date],
                     status: dict[date, VisitStatus]) -> dict:
    """
    Gegeben eine Liste geplanter Termine und ein Mapping auf VisitStatus,
    liefert die absoluten und prozentualen Ausfallzahlen pro Kind.
    """
    total = len(planned)
    missed_a = sum(1 for d in planned if d in status and not status[d].present_child_a)
    missed_b = sum(1 for d in planned if d in status and not status[d].present_child_b)
    attended_a_pct = round((total - missed_a) / total * 100, 1) if total else 0.0
    attended_b_pct = round((total - missed_b) / total * 100, 1) if total else 0.0
    return {
        "total": total,
        "missed_a": missed_a,
        "missed_b": missed_b,
        "attended_a_pct": attended_a_pct,
        "attended_b_pct": attended_b_pct,
    }
