from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime

from ..constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from ..optional_deps import KEYRING_AVAILABLE, keyring
from ..path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key
from .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE, logger
from .defaults import default_settings
from .normalize import (
    _normalize_bool,
    _normalize_chat_histories,
    _normalize_language,
    _normalize_last_output_dir,
    _normalize_recent_files,
    _normalize_splitter_sizes,
    _normalize_theme,
    _normalize_window_geometry,
)


def _resolve_settings_file() -> str:
    """facade 모듈에서 monkeypatch된 SETTINGS_FILE을 우선 사용."""
    import sys

    facade = sys.modules.get("src.core.settings")
    if facade is not None:
        patched = getattr(facade, "SETTINGS_FILE", None)
        if isinstance(patched, str) and patched:
            return patched
    return SETTINGS_FILE


def load_settings():
    """Load application settings from JSON file."""
    settings_file = _resolve_settings_file()
    defaults = default_settings()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if not isinstance(settings, dict):
                    logger.warning("Settings file content is not a JSON object, falling back to defaults")
                    return defaults
                # 누락된 키에 기본값 추가
                for key, default_value in defaults.items():
                    if key not in settings:
                        settings[key] = default_value

                # 타입 방어: 잘못된 타입이면 기본값으로 교체
                settings["recent_files"] = _normalize_recent_files(settings.get("recent_files", []))
                settings["chat_histories"] = _normalize_chat_histories(settings.get("chat_histories", {}))
                settings["splitter_sizes"] = _normalize_splitter_sizes(settings.get("splitter_sizes"))
                settings["theme"] = _normalize_theme(settings.get("theme"))
                settings["language"] = _normalize_language(settings.get("language"))
                settings["window_geometry"] = _normalize_window_geometry(settings.get("window_geometry"))
                settings["last_output_dir"] = _normalize_last_output_dir(settings.get("last_output_dir"))
                settings["preview_search_expanded"] = _normalize_bool(
                    settings.get("preview_search_expanded"),
                    True,
                )
                return settings
        except json.JSONDecodeError as e:
            # 손상된 설정 파일 백업
            backup_path = f"{settings_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(settings_file, backup_path)
                logger.warning(f"Settings file corrupted, backed up to {backup_path}: {e}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted settings: {backup_error}")
            # 기본 설정 반환
            return defaults
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return defaults
    # 기본 설정 반환
    return defaults

def save_settings(settings):
    """Save application settings to JSON file (atomic write for safety)."""
    if settings is None:
        logger.warning("Attempted to save None settings, skipping")
        return False

    settings_file = _resolve_settings_file()
    tmp_path = None
    try:
        # v4.5: 원자적 파일 쓰기 - 임시 파일에 먼저 쓰고 교체
        dir_name = os.path.dirname(settings_file)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=dir_name,
            delete=False, suffix='.tmp'
        ) as tmp:
            json.dump(settings, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name

        # 원자적으로 교체 (Windows/Linux 모두 지원)
        os.replace(tmp_path, settings_file)
        return True
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        # 임시 파일 정리
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("Failed to remove temporary settings file", exc_info=True)
        return False

def reset_settings():
    """Reset settings to defaults."""
    settings_file = _resolve_settings_file()
    try:
        if os.path.exists(settings_file):
            os.remove(settings_file)

        # keyring에서도 API 키 삭제
        if KEYRING_AVAILABLE and keyring is not None:
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                logger.debug("Failed to delete API key from keyring during reset", exc_info=True)

        logger.info("Settings reset to defaults")
        return True
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return False
