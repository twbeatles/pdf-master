from __future__ import annotations

import logging
import os

from ..optional_deps import KEYRING_AVAILABLE

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

if not KEYRING_AVAILABLE:
    logger.info("keyring not available, API key will be stored in settings file")

KEYRING_SERVICE = "PDFMaster"
KEYRING_USERNAME = "gemini_api_key"
