import pytest

from src.core.optional_deps import FITZ_AVAILABLE


def require_pyside6() -> None:
    try:
        import PySide6  # noqa: F401
    except Exception:
        pytest.skip("PySide6 not available")


def require_pymupdf() -> None:
    if not FITZ_AVAILABLE:
        pytest.skip("PyMuPDF not available")


def require_pyside6_and_pymupdf() -> None:
    require_pyside6()
    require_pymupdf()
