import logging


# v4.5: 상수를 constants.py에서 통합 관리
from ..core.constants import APP_NAME, VERSION, MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS  # noqa: F401 -- keeper used by main_window.py,main_window_core.py,menu.py,shortcuts.py
logger = logging.getLogger(__name__)

try:
    from ..core.ai_service import GENAI_AVAILABLE as AI_AVAILABLE
except ImportError:
    AI_AVAILABLE = False
    logger.info("AI service module not available. AI features will be disabled.")

