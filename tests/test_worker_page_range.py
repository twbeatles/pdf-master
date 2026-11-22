from _deps import require_pyside6


def test_parse_page_range_forward_and_reverse():
    require_pyside6()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")

    assert w._parse_page_range("1-3, 5, 7-10", total_pages=12) == [
        0,
        1,
        2,
        4,
        6,
        7,
        8,
        9,
    ]
    assert w._parse_page_range("5-1", total_pages=10) == [4, 3, 2, 1, 0]


def test_parse_page_range_dedup_and_limit():
    require_pyside6()
    from src.core.worker import WorkerThread

    w = WorkerThread("merge")

    assert w._parse_page_range("1,1,2-3,2", total_pages=5) == [0, 1, 2]

    # MAX_PAGE_RANGE_LENGTH=1000 (constants) - 상한 도달은 조용히 자르지 않고 에러로 표면화
    errors: list[str] = []
    w.error_signal.connect(errors.append)
    assert w._parse_page_range("1-2000", total_pages=5000) == []
    assert errors and "1000" in errors[-1]

    # 정확히 상한까지는 기존처럼 통과
    w2 = WorkerThread("merge")
    assert len(w2._parse_page_range("1-1000", total_pages=5000)) == 1000
