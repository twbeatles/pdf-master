import os
import json
import logging
import shutil
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

# 기본 설정
DEFAULT_SETTINGS = {
    "theme": "dark",
    "recent_files": [],
    "last_output_dir": "",
    "splitter_sizes": None,
    "window_geometry": None
}

def load_settings():
    """Load application settings from JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # 누락된 키에 기본값 추가
                for key, default_value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = default_value
                return settings
        except json.JSONDecodeError as e:
            # 손상된 설정 파일 백업
            backup_path = f"{SETTINGS_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(SETTINGS_FILE, backup_path)
                logger.warning(f"Settings file corrupted, backed up to {backup_path}: {e}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted settings: {backup_error}")
            # 기본 설정 반환
            return DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return DEFAULT_SETTINGS.copy()
    # 기본 설정 반환
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save application settings to JSON file."""
    if settings is None:
        logger.warning("Attempted to save None settings, skipping")
        return False
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return False

def reset_settings():
    """Reset settings to defaults."""
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
        logger.info("Settings reset to defaults")
        return True
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return False
