from __future__ import annotations

import os


def normalize_path_key(path: object) -> str:
    if not isinstance(path, str):
        return ""
    stripped = path.strip()
    if not stripped:
        return ""
    return os.path.normcase(os.path.abspath(stripped))
