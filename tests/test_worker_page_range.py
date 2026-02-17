import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def test_parse_page_range_forward_and_reverse():
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")

    assert w._parse_page_range("1-3, 5, 7-10", total_pages=12) == [0, 1, 2, 4, 6, 7, 8, 9]
    assert w._parse_page_range("5-1", total_pages=10) == [4, 3, 2, 1, 0]


def test_parse_page_range_dedup_and_limit():
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")

    assert w._parse_page_range("1,1,2-3,2", total_pages=5) == [0, 1, 2]

    # MAX_PAGE_RANGE_LENGTH=1000 (constants) - ensure we cap
    pages = w._parse_page_range("1-2000", total_pages=5000)
    assert len(pages) == 1000

