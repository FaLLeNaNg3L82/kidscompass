# src/kidscompass/models.py
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

@dataclass
class VisitPattern:
    """Ein wiederkehrendes Besuchs-Muster (z. B. jeden 2. Samstag)."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    weekdays: List[int]           # 0=Montag … 6=Sonntag
    interval_weeks: int = 1       # Alle X Wochen
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = None

    def __str__(self):
        weekdays = [['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][d] for d in sorted(self.weekdays)]
        days = ', '.join(weekdays)
        end = f" bis {self.end_date}" if self.end_date else ""
        return f"Alle {self.interval_weeks} Wochen an {days} (ab {self.start_date}{end})"

@dataclass
class OverridePeriod:
    """Zeitraum, in dem Urlaubsumgänge gelten und das Standard-Pattern überschreiben."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    from_date: date
    to_date: date
    pattern: VisitPattern         # komplett frei definierbare Tage
    holder: Optional[str] = None  # 'mother' or 'father' or None

@dataclass
class RemoveOverride:
    """Zeitraum, in dem Standard-Termine entfernt werden (z.B. Exfrau-Ferienumgang)."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    from_date: date
    to_date: date

    def __str__(self):
        # Benutzerfreundliche Anzeige im UI
        end = f" bis {self.to_date}" if self.to_date else ""
        return f"Entfernen ({self.from_date}{end}) (id={self.id})"

@dataclass
class VisitStatus:
    """Status für jeden einzelnen Umgangstag."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    day: date
    present_child_a: bool = True
    present_child_b: bool = True
