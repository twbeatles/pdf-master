from __future__ import annotations

import os
from dataclasses import dataclass

from .constants import MAX_FILE_SIZE, MIN_PDF_SIZE


@dataclass(frozen=True, slots=True)
class PdfValidationResult:
    ok: bool
    reason: str = ""
    size: int = 0


def validate_pdf_file(file_path: str) -> PdfValidationResult:
    if not file_path or not os.path.exists(file_path):
        return PdfValidationResult(False, "missing")

    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return PdfValidationResult(False, "inaccessible")

    if file_size > MAX_FILE_SIZE:
        return PdfValidationResult(False, "too_large", file_size)
    if file_size < MIN_PDF_SIZE:
        return PdfValidationResult(False, "too_small", file_size)

    try:
        with open(file_path, "rb") as handle:
            header = handle.read(8)
    except OSError:
        return PdfValidationResult(False, "inaccessible", file_size)

    if not header.startswith(b"%PDF-"):
        return PdfValidationResult(False, "invalid_header", file_size)

    return PdfValidationResult(True, size=file_size)


def is_valid_pdf_file(file_path: str) -> bool:
    return validate_pdf_file(file_path).ok
