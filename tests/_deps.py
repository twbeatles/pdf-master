import pytest

from src.core.optional_deps import FITZ_AVAILABLE


def require_pyqt6() -> None:
    try:
        import PyQt6  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 not available")


def require_pymupdf() -> None:
    if not FITZ_AVAILABLE:
        pytest.skip("PyMuPDF not available")


def require_pyqt6_and_pymupdf() -> None:
    require_pyqt6()
    require_pymupdf()
