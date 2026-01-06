import json
from datetime import date
from typing import List, Dict, Optional, Any
from kidscompass.models import OverridePeriod, RemoveOverride


_VAC_TYPE_NAMES = {
    'weihnachten': 'Weihnachtsferien',
    'sommer': 'Sommerferien',
    'oster': 'Osterferien',
    'herbst': 'Herbstferien',
}


def _ensure_meta(meta: Any) -> Optional[Dict]:
    if not meta:
        return None
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        try:
            return json.loads(meta)
        except Exception:
            return None
    return None


def format_visit_window(d: date, overrides: List, config: Optional[Dict] = None) -> str:
    """
    Gib eine menschenlesbare Kurzbeschreibung zurück für besondere Übergabe-/Meta-Infos
    an Datum `d`. Nutzt OverridePeriod.vac_type und OverridePeriod.meta (JSON oder dict).
    `config` kann eine Mapping `handover_rules` enthalten, z.B. {'after_school': 'nach Schulende'}.
    """
    cfg = config or {}
    hr = cfg.get('handover_rules', {}) or {}

    for ov in overrides:
        if isinstance(ov, RemoveOverride):
            continue
        if not (ov.from_date <= d <= ov.to_date):
            continue

        vt = getattr(ov, 'vac_type', None)
        meta_raw = getattr(ov, 'meta', None)
        m = _ensure_meta(meta_raw)

        # Weihnachten: besondere Regeln (first_holiday / jan1)
        if vt == 'weihnachten':
            if m:
                end_type = m.get('end_type') or m.get('anchor')
                end_time = m.get('end_time') or m.get('time')
                if end_type == 'first_holiday':
                    t = end_time or '18:00'
                    return f"Weihnachtsferien: Übergabe am ersten Feiertag {t}"
                if end_type == 'jan1' or end_type == '01-01' or end_type == '01.01':
                    t = end_time or '17:00'
                    return f"Weihnachtsferien: Übergabe am 01.01 {t}"
            # fallback label
            return _VAC_TYPE_NAMES.get(vt, 'Weihnachtsferien')

        # Generische Regel über meta.rule
        if m and 'rule' in m:
            rn = m.get('rule')
            if rn in hr:
                return f"Übergabe: {hr[rn]}"
            # fixed time rules like 'fixed_18' or 'fixed_18:30'
            if rn and rn.startswith('fixed_'):
                # try to map via config first
                if rn in hr:
                    return f"Übergabe: {hr[rn]}"
                # else take suffix as time
                suffix = rn.split('_', 1)[1]
                return f"Übergabe: {suffix}"

        # Some imports might include direct handover_time or handover text
        if m:
            if 'handover_time' in m:
                return f"Übergabe: {m.get('handover_time')}"
            if 'handover' in m:
                return f"Übergabe: {m.get('handover')}"

        # If vac_type present, return localized name
        if vt:
            return _VAC_TYPE_NAMES.get(vt, vt.capitalize())

    return ""
