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
from .persistence import load_settings, save_settings

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
