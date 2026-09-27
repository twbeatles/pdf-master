"""Fluent redesign P1 foundation regression (DESKTOP_UI_DESIGN_RULES §5·§6·§20)."""

from pathlib import Path

import tomllib

from src.ui import design_tokens as tok
from src.ui import fluent_theme

ROOT = Path(__file__).resolve().parents[1]


def test_spacing_scale_uses_allowed_values_only():
    assert tok.ALLOWED_SPACING == frozenset({4, 8, 12, 16, 24, 32})
    assert tok.FORM_ROW_GAP in tok.ALLOWED_SPACING
    assert tok.GROUP_GAP in tok.ALLOWED_SPACING
    assert tok.SECTION_GAP in tok.ALLOWED_SPACING
    assert tok.PAGE_MARGIN_COMFORTABLE in tok.ALLOWED_SPACING
    assert tok.ICON_TEXT_GAP in tok.ALLOWED_SPACING


def test_typography_scale_ordering_and_fallback_chain():
    assert tok.FONT_SIZE_PAGE > tok.FONT_SIZE_SECTION > tok.FONT_SIZE_BODY
    assert tok.FONT_SIZE_BODY > tok.FONT_SIZE_SECONDARY > tok.FONT_SIZE_CAPTION
    assert "Segoe UI" in tok.FONT_FAMILIES  # Windows fallback 유지


def test_preferred_window_size_clamps_to_available_geometry():
    assert tok.preferred_window_size(None, None) == tok.WINDOW_DEFAULT_SIZE
    assert tok.preferred_window_size(2000, 1200) == tok.WINDOW_DEFAULT_SIZE
    # 작은 화면에서는 가용 영역 기준으로 축소
    w, h = tok.preferred_window_size(1000, 700)
    assert (w, h) == (960, 700)
    # clamp된 최소 크기가 창보다 커지지 않음
    mw, mh = tok.clamp_minimum_size(w, h)
    assert mw <= w and mh <= h


def test_fluent_bridge_is_noop_without_dependency():
    # 미설치 환경에서도 import·호출이 예외 없이 동작 (하드 의존 금지 §1.1)
    assert isinstance(fluent_theme.is_fluent_available(), bool)
    assert fluent_theme.sync_fluent_theme("dark") in (True, False)
    fluent_theme.configure_fluent_window(object())
    fluent_theme.apply_native_widget_style(object())


def test_fluent_extra_and_packaging_declared():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    fluent = data["project"]["optional-dependencies"].get("fluent", [])
    assert any("PyQt6-Fluent-Widgets" in d for d in fluent)
    assert any("darkdetect" in d for d in fluent)
    # PySide6 변형 혼합 금지
    assert not any("PySide6-Fluent" in d for d in fluent)
    spec = (ROOT / "pdf_master.spec").read_text(encoding="utf-8")
    assert "qfluentwidgets" in spec
    assert "Fluent theme bridge disabled" in spec


def test_design_doc_exists_and_references_rules():
    doc = (ROOT / "docs" / "fluent-redesign-design.md").read_text(encoding="utf-8")
    assert "DESKTOP_UI_DESIGN_RULES" in doc
    assert "design_tokens" in doc
    assert "fluent_theme" in doc
