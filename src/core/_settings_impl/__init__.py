from __future__ import annotations

from ..optional_deps import KEYRING_AVAILABLE, keyring
from .api_key import _legacy_set_api_key, get_api_key, set_api_key
from .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE
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
from .persistence import load_settings, reset_settings, save_settings

__all__ = [
    "SETTINGS_FILE",
    "KEYRING_SERVICE",
    "KEYRING_USERNAME",
    "KEYRING_AVAILABLE",
    "keyring",
    "default_settings",
    "get_api_key",
    "_legacy_set_api_key",
    "set_api_key",
    "load_settings",
    "save_settings",
    "reset_settings",
    "_normalize_recent_files",
    "_normalize_chat_histories",
    "_normalize_splitter_sizes",
    "_normalize_theme",
    "_normalize_language",
    "_normalize_window_geometry",
    "_normalize_last_output_dir",
    "_normalize_bool",
]
