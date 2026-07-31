"""미리보기 드래그 교정: 뷰포트→PDF 좌표 매핑 단위 테스트."""

from __future__ import annotations

from PyQt6.QtCore import QRectF

from src.ui.preview_widget.region_select import (
    compute_page_display_rect,
    format_rect_coords,
    map_page_points_to_viewport_rect,
    map_viewport_rect_to_page_points,
)


def test_compute_page_display_rect_centers_page():
    viewport = QRectF(0, 0, 400, 600)
    page = compute_page_display_rect(
        viewport=viewport,
        page_width_pts=200,
        page_height_pts=300,
        zoom_factor=1.0,
    )
    # 200x300 페이지가 400x600 뷰에 중앙
    assert abs(page.width() - 200) < 0.01
    assert abs(page.height() - 300) < 0.01
    assert abs(page.x() - 100) < 0.01
    assert abs(page.y() - 150) < 0.01


def test_compute_page_display_rect_respects_zoom_and_scroll():
    viewport = QRectF(0, 0, 400, 400)
    page = compute_page_display_rect(
        viewport=viewport,
        page_width_pts=100,
        page_height_pts=100,
        zoom_factor=2.0,
        scroll_x=10,
        scroll_y=20,
    )
    assert abs(page.width() - 200) < 0.01
    assert abs(page.height() - 200) < 0.01
    # centered at (100,100) then -scroll
    assert abs(page.x() - 90) < 0.01
    assert abs(page.y() - 80) < 0.01


def test_map_viewport_rect_to_page_points_identity_scale():
    page_display = QRectF(50, 50, 200, 300)
    # 페이지 좌상단 근처 50x50 선택 (viewport)
    selection = QRectF(50, 50, 50, 50)
    mapped = map_viewport_rect_to_page_points(
        selection,
        page_display,
        page_width_pts=200,
        page_height_pts=300,
    )
    assert mapped is not None
    x0, y0, x1, y1 = mapped
    assert abs(x0 - 0) < 0.5
    assert abs(y0 - 0) < 0.5
    assert abs(x1 - 50) < 0.5
    assert abs(y1 - 50) < 0.5


def test_map_outside_page_returns_none():
    page_display = QRectF(100, 100, 100, 100)
    selection = QRectF(0, 0, 10, 10)
    assert (
        map_viewport_rect_to_page_points(
            selection,
            page_display,
            page_width_pts=200,
            page_height_pts=200,
        )
        is None
    )


def test_map_too_small_returns_none():
    page_display = QRectF(0, 0, 200, 200)
    selection = QRectF(0, 0, 0.5, 0.5)
    assert (
        map_viewport_rect_to_page_points(
            selection,
            page_display,
            page_width_pts=200,
            page_height_pts=200,
            min_size_pts=1.0,
        )
        is None
    )


def test_format_rect_coords():
    assert format_rect_coords((1.234, 5.678, 9.0, 10.1), decimals=1) == "1.2,5.7,9.0,10.1"
def test_map_page_points_to_viewport_roundtrip():
    page_display = QRectF(50, 50, 200, 300)
    view = map_page_points_to_viewport_rect(
        10, 20, 60, 80, page_display, page_width_pts=200, page_height_pts=300
    )
    assert view is not None
    assert abs(view.x() - 60) < 0.5
    assert abs(view.y() - (50 + 20)) < 0.5
    mapped = map_viewport_rect_to_page_points(
        view, page_display, page_width_pts=200, page_height_pts=300
    )
    assert mapped is not None
    assert abs(mapped[0] - 10) < 1.0
    assert abs(mapped[1] - 20) < 1.0
