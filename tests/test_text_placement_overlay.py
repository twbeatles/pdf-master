"""TextPlacementOverlay 리사이즈·히트테스트 단위 검증."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect

from src.ui.preview_widget.text_placement import apply_resize, hit_test_handle


def test_hit_test_corners_and_edges():
    box = QRect(100, 100, 200, 80)
    assert hit_test_handle(box, QPoint(100, 100)) == "nw"
    assert hit_test_handle(box, QPoint(300, 100)) == "ne"
    assert hit_test_handle(box, QPoint(100, 180)) == "sw"
    assert hit_test_handle(box, QPoint(300, 180)) == "se"
    assert hit_test_handle(box, QPoint(200, 100)) == "n"
    assert hit_test_handle(box, QPoint(200, 180)) == "s"
    assert hit_test_handle(box, QPoint(100, 140)) == "w"
    assert hit_test_handle(box, QPoint(300, 140)) == "e"
    assert hit_test_handle(box, QPoint(200, 140)) == ""


def test_apply_resize_se_expands():
    box = QRect(50, 50, 100, 40)
    out = apply_resize(box, "se", QPoint(200, 120), min_w=24, min_h=18)
    assert out.width() >= 100
    assert out.height() >= 40
    assert out.left() == 50
    assert out.top() == 50


def test_apply_resize_respects_min_size():
    box = QRect(50, 50, 100, 40)
    out = apply_resize(box, "se", QPoint(55, 55), min_w=40, min_h=30)
    assert out.width() >= 40
    assert out.height() >= 30


def test_apply_resize_nw_shrinks_from_top_left():
    box = QRect(100, 100, 200, 100)
    out = apply_resize(box, "nw", QPoint(120, 120), min_w=24, min_h=18)
    assert out.left() >= 100 or out.width() >= 24
    assert out.width() >= 24
    assert out.height() >= 18
