import json
import os
from pathlib import Path


def _config_path():
    base = os.path.join(os.path.expanduser('~'), '.kidscompass')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'kidscompass_config.json')


def load_config():
    path = _config_path()
    if not os.path.exists(path):
        # sensible defaults
        return {
            'handover_rules': {
                'after_school': 'nach Schulende',
                'school_start': 'zum Schulbeginn',
                'fixed_18': '18:00'
            }
        }
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'handover_rules': {'after_school': 'nach Schulende', 'school_start': 'zum Schulbeginn', 'fixed_18': '18:00'}}


def save_config(cfg: dict):
    path = _config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
