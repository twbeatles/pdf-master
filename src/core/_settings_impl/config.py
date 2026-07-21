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

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

if not KEYRING_AVAILABLE:
    logger.info("keyring not available, API key will be stored in settings file")

KEYRING_SERVICE = "PDFMaster"
KEYRING_USERNAME = "gemini_api_key"

