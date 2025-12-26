import os
import json

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

def load_settings():
    """Load application settings from JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Default settings
    return {
        "theme": "dark",
        "recent_files": [],
        "last_output_dir": ""
    }

def save_settings(settings):
    """Save application settings to JSON file."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
