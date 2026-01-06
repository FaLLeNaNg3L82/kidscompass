import json
from datetime import date
from typing import List, Dict, Optional
from kidscompass.models import OverridePeriod, RemoveOverride


def format_visit_window(d: date, overrides: List, config: Optional[Dict] = None) -> str:
    """
    Return a human-readable string describing special handover/metadata for date `d`.
    Checks overrides covering `d` and uses `vac_type`/`meta` when available.
    Config can contain `handover_rules` mapping.
    """
    cfg = config or {}
    hr = cfg.get('handover_rules', {})

    # Find any add-override that covers the date
    for ov in overrides:
        if isinstance(ov, RemoveOverride):
            continue
        if ov.from_date <= d <= ov.to_date:
            # OverridePeriod
            vt = getattr(ov, 'vac_type', None)
            meta = getattr(ov, 'meta', None)
            # try parse meta if JSON
            m = None
            if meta:
                try:
                    m = json.loads(meta)
                except Exception:
                    m = None
            # Christmas special
            if vt == 'weihnachten':
                if m and m.get('end_type') == 'first_holiday':
                    t = m.get('end_time', '18:00')
                    return f"Weihnachtsferien: Übergabe am ersten Feiertag {t}"
                if m and m.get('end_type') == 'jan1':
                    t = m.get('end_time', '17:00')
                    return f"Weihnachtsferien: Übergabe am 01.01 {t}"
                # fallback
                return "Weihnachtsferien"

            # Generic handover rule via meta.rule or vac_type mapping
            if m and 'rule' in m:
                rn = m['rule']
                if rn in hr:
                    return f"Übergabe: {hr[rn]}"
                # fixed time
                if rn.startswith('fixed_'):
                    return f"Übergabe: {rn.split('_',1)[1]}"

            # Default: if vac_type present, show it
            if vt:
                return f"{vt.capitalize()}"
    return ""
