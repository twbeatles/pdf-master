from __future__ import annotations

from .en_base import TRANSLATIONS as EN_TRANSLATIONS
from .ko_base import TRANSLATIONS as KO_TRANSLATIONS

TRANSLATIONS = {
    "ko": KO_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}

__all__ = ["TRANSLATIONS"]
