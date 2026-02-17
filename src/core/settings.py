import os
import json
import logging
import shutil
import tempfile
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

# keyring 가용성 체크 (보안 저장용)
KEYRING_AVAILABLE = False
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    logger.info("keyring not available, API key will be stored in settings file")

KEYRING_SERVICE = "PDFMaster"
KEYRING_USERNAME = "gemini_api_key"

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
        "chat_histories": {},
        # gemini_api_key는 keyring 미사용 시에만 파일에 저장됨
    }

def get_api_key() -> str:
    """
    API 키 안전하게 가져오기 (keyring 우선, 파일 폴백)
    
    Returns:
        API 키 문자열 (없으면 빈 문자열)
    """
    if KEYRING_AVAILABLE:
        try:
            key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if key:
                return key
        except Exception as e:
            logger.warning(f"Failed to get API key from keyring: {e}")
    
    # 파일에서 폴백
    settings = load_settings()
    return settings.get("gemini_api_key", "")

def set_api_key(api_key: str) -> bool:
    """
    API 키 안전하게 저장하기 (keyring 우선, 파일 폴백)
    
    Args:
        api_key: 저장할 API 키
        
    Returns:
        저장 성공 여부
    """
    if KEYRING_AVAILABLE:
        try:
            if api_key:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            else:
                try:
                    keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
                except keyring.errors.PasswordDeleteError:
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
                if not isinstance(settings.get("recent_files", []), list):
                    settings["recent_files"] = []
                if not isinstance(settings.get("chat_histories", {}), dict):
                    settings["chat_histories"] = {}
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
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                logger.debug("Failed to delete API key from keyring during reset", exc_info=True)
        
        logger.info("Settings reset to defaults")
        return True
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return False
