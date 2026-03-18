import locale
import logging
import os

from .i18n_catalogs import TRANSLATIONS
from .settings import load_settings

logger = logging.getLogger(__name__)


class TranslationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = load_settings()
        self.current_lang = self.settings.get("language", "auto")

        if self.current_lang == "auto":
            sys_lang = self._detect_system_language()
            if sys_lang.startswith("ko"):
                self.active_lang_code = "ko"
            else:
                self.active_lang_code = "en"
        else:
            self.active_lang_code = self.current_lang

        logger.info(
            "TranslationManager initialized. Lang: %s, Active: %s",
            self.current_lang,
            self.active_lang_code,
        )
        self._initialized = True

    def _detect_system_language(self) -> str:
        """비권장 API(locale.getdefaultlocale) 없이 시스템 언어를 감지."""
        candidates = []
        try:
            lang, _ = locale.getlocale()
            if lang:
                candidates.append(lang)
        except Exception:
            logger.debug("locale.getlocale() failed", exc_info=True)

        for env_key in ("LC_ALL", "LC_MESSAGES", "LANG"):
            env_val = os.environ.get(env_key)
            if env_val:
                candidates.append(env_val)

        for cand in candidates:
            normalized = str(cand).strip().lower()
            if normalized.startswith("ko"):
                return "ko"
        return "en"

    def get(self, key: str, *args) -> str:
        lang_dict = TRANSLATIONS.get(self.active_lang_code, TRANSLATIONS["en"])
        text = lang_dict.get(key, key)
        if args:
            try:
                return text.format(*args)
            except IndexError:
                return text
        return text


tm = TranslationManager()
