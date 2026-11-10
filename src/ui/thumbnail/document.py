from __future__ import annotations

import logging

from ...core.i18n import tm
from ...core.optional_deps import fitz

logger = logging.getLogger(__name__)


def _open_thumbnail_document(pdf_path: str, password: str | None = None):
    doc = fitz.open(pdf_path)
    if not doc.is_encrypted:
        return doc, None

    if not password:
        doc.close()
        return None, tm.get("preview_encrypted")

    if not doc.authenticate(password):
        doc.close()
        return None, tm.get("preview_password_wrong")

    return doc, None
