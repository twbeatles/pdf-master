import os
import json
import logging
import shutil
import tempfile
from datetime import datetime

from .constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from .optional_deps import KEYRING_AVAILABLE, keyring
from .path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key

# 로깅 설정
logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

if not KEYRING_AVAILABLE:
    logger.info("keyring not available, API key will be stored in settings file")

KEYRING_SERVICE = "PDFMaster"
KEYRING_USERNAME = "gemini_api_key"


def _normalize_recent_files(value) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        path_key = normalize_path_key(item)
        if not path_key or path_key in seen or not os.path.exists(path_key):
            continue
        seen.add(path_key)
        normalized.append(path_key)
    return normalized


def _normalize_chat_histories(value) -> dict:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for raw_path, raw_entries in value.items():
        path_key, version_mtime_ns = parse_chat_history_key(raw_path)
        if not path_key or not isinstance(raw_entries, list) or not os.path.exists(path_key):
            continue
        history_key = (
            make_chat_history_key(path_key, version_mtime_ns)
            if version_mtime_ns is not None
            else make_chat_history_key(path_key)
        )
        if not history_key:
            continue
        cleaned_entries = normalized.setdefault(history_key, [])
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            content = entry.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                cleaned_entries.append({"role": role, "content": content})

    trimmed: dict[str, list[dict[str, str]]] = {}
    for path_key, entries in normalized.items():
        if not entries:
            continue
        trimmed[path_key] = entries[-MAX_CHAT_HISTORY_ENTRIES:]

    if len(trimmed) > MAX_CHAT_HISTORY_PDFS:
        trimmed = dict(list(trimmed.items())[-MAX_CHAT_HISTORY_PDFS:])
    return trimmed


def _normalize_splitter_sizes(value) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        return None

    normalized: list[int] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        size = int(item)
        if size < 0:
            return None
        normalized.append(size)

    return normalized or None


def _normalize_theme(value) -> str:
    return value if value in {"dark", "light"} else "dark"


def _normalize_language(value) -> str:
    return value if value in {"auto", "ko", "en"} else "auto"


def _normalize_window_geometry(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value
    return None


def _normalize_last_output_dir(value) -> str:
    return value if isinstance(value, str) else ""


def _normalize_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return bool(default)

def default_settings() -> dict:
    """
    기본 설정 생성.

    NOTE: list/dict 같은 mutable 기본값이 호출 간 공유되지 않도록
    매 호출마다 새 객체를 생성합니다.
    """
    return {
        "theme": "dark",
        "recent_files": [],
        "last_output_dir": "",
        "splitter_sizes": None,
        "window_geometry": None,
        "language": "auto",  # auto, ko, en
        "preview_search_expanded": True,
        "chat_histories": {},
        # gemini_api_key는 keyring 미사용 시에만 파일에 저장됨
    }

def get_api_key() -> str:
    """
    API 키 안전하게 가져오기 (keyring 우선, 파일 폴백)
    
    Returns:
        API 키 문자열 (없으면 빈 문자열)
    """
    if KEYRING_AVAILABLE and keyring is not None:
        try:
            key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if key:
                return key
        except Exception as e:
            logger.warning(f"Failed to get API key from keyring: {e}")
    
    # 파일에서 폴백
    settings = load_settings()
    return settings.get("gemini_api_key", "")

def _legacy_set_api_key(api_key: str) -> bool:
    """
    API 키 안전하게 저장하기 (keyring 우선, 파일 폴백)
    
    Args:
        api_key: 저장할 API 키
        
    Returns:
        저장 성공 여부
    """
    if KEYRING_AVAILABLE and keyring is not None:
        try:
            if api_key:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            else:
                try:
                    keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
                except Exception:
                    pass  # 삭제할 키가 없는 경우 무시
            
            # 파일에서 기존 키 제거 (보안)
            settings = load_settings()
            if "gemini_api_key" in settings:
                del settings["gemini_api_key"]
                save_settings(settings)
            
            logger.info("API key saved to keyring")
            return True
        except Exception as e:
            logger.warning(f"Failed to save API key to keyring, falling back to file: {e}")
    
    # 파일에 폴백 저장
    settings = load_settings()
    settings["gemini_api_key"] = api_key
    return save_settings(settings)


def set_api_key(api_key: str, allow_file_fallback: bool = False) -> bool:
    """
    Save the Gemini API key securely when possible.

    Args:
        api_key: API key to store.
        allow_file_fallback: When True, allow plaintext settings-file storage
            if keyring is unavailable or saving to keyring fails.

    Returns:
        True if the save or cleanup succeeded, False otherwise.
    """
    settings = load_settings()

    if not api_key:
        if KEYRING_AVAILABLE and keyring is not None:
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                logger.debug("API key was not present in keyring during delete", exc_info=True)
        if "gemini_api_key" in settings:
            del settings["gemini_api_key"]
            return save_settings(settings)
        return True

    if KEYRING_AVAILABLE and keyring is not None:
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            if "gemini_api_key" in settings:
                del settings["gemini_api_key"]
                save_settings(settings)
            logger.info("API key saved to keyring")
            return True
        except Exception as exc:
            logger.warning("Failed to save API key to keyring: %s", exc)
            if not allow_file_fallback:
                return False

    if not allow_file_fallback:
        return False

    settings["gemini_api_key"] = api_key
    logger.warning("Saving API key to plaintext settings file due to explicit fallback approval")
    return save_settings(settings)

def load_settings():
    """Load application settings from JSON file."""
    defaults = default_settings()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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
            backup_path = f"{SETTINGS_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(SETTINGS_FILE, backup_path)
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
    
    tmp_path = None
    try:
        # v4.5: 원자적 파일 쓰기 - 임시 파일에 먼저 쓰고 교체
        dir_name = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=dir_name,
            delete=False, suffix='.tmp'
        ) as tmp:
            json.dump(settings, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        
        # 원자적으로 교체 (Windows/Linux 모두 지원)
        os.replace(tmp_path, SETTINGS_FILE)
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
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
        
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
