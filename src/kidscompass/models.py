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

@dataclass
class OverridePeriod:
    """Zeitraum, in dem Urlaubsumgänge gelten und das Standard-Pattern überschreiben."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    from_date: date
    to_date: date
    pattern: VisitPattern         # komplett frei definierbare Tage

@dataclass
class RemoveOverride:
    """Zeitraum, in dem Standard-Termine entfernt werden (z.B. Exfrau-Ferienumgang)."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    from_date: date
    to_date: date

@dataclass
class VisitStatus:
    """Status für jeden einzelnen Umgangstag."""
    id: Optional[int] = field(default=None, init=False)    # db-Primärschlüssel
    day: date
    present_child_a: bool = True
    present_child_b: bool = True
