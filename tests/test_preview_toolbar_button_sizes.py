"""미리보기 툴바 버튼 텍스트 잘림 회귀 테스트.

전역 QPushButton padding(12px 24px)과 과도한 setFixedSize 조합으로
이전/다음·맞춤·1:1 등이 잘리던 문제를 방지한다.
"""

from __future__ import annotations

import os

from _deps import require_pyqt6


def _make_app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _apply_theme(app):
    from src.ui.theme import DARK_STYLESHEET

    app.setStyleSheet(DARK_STYLESHEET)


def _assert_button_fits_text(btn, *, min_pad_x: int = 8, min_pad_y: int = 4) -> None:
    """sizeHint / 실제 크기가 라벨 텍스트를 담을 만큼 넓은지 확인."""
    from PyQt6.QtWidgets import QSizePolicy

    text = (btn.text() or "").strip()
    if not text:
        # 아이콘/토글 등 빈 라벨은 최소 치수만 확인
        assert btn.sizeHint().width() >= 20
        assert btn.sizeHint().height() >= 24
        return

    fm = btn.fontMetrics()
    text_w = fm.horizontalAdvance(text)
    text_h = fm.height()
    hint = btn.sizeHint()

    assert hint.width() >= text_w + min_pad_x, (
        f"{btn.objectName() or btn!r} width too small for '{text}': "
        f"hint={hint.width()} text={text_w}"
    )
    assert hint.height() >= text_h + min_pad_y, (
        f"{btn.objectName() or btn!r} height too small for '{text}': "
        f"hint={hint.height()} text_h={text_h}"
    )

    # 고정 폭이 있으면 힌트보다 작아 잘리는지 검사
    max_w = btn.maximumWidth()
    if max_w < 16777215:  # Qt 기본 QWIDGETSIZE_MAX
        assert max_w >= text_w, (
            f"{btn.objectName() or btn!r} maxWidth={max_w} clips text '{text}' ({text_w}px)"
        )

    max_h = btn.maximumHeight()
    if max_h < 16777215:
        assert max_h >= text_h, (
            f"{btn.objectName() or btn!r} maxHeight={max_h} clips text height"
        )

    # Expanding이 아닌 한, 정책이 콘텐츠 기반이어야 함
    h_policy = btn.sizePolicy().horizontalPolicy()
    assert h_policy != QSizePolicy.Policy.Ignored


def test_preview_toolbar_buttons_size_hint_fits_labels():
    require_pyqt6()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.core.i18n import tm
    from src.ui.zoomable_preview import ZoomablePreviewWidget

    app = _make_app()
    _apply_theme(app)

    widget = ZoomablePreviewWidget()
    # 토글 버튼 라벨이 채워지도록 패널 상태 동기화
    widget.set_search_panel_visible(True)
    widget.resize(800, 600)
    widget.show()
    app.processEvents()

    buttons = [
        widget.btn_zoom_out,
        widget.btn_zoom_in,
        widget.btn_fit,
        widget.btn_actual,
        widget.btn_toggle_search,
        widget.btn_page_setup,
        widget.btn_print,
        widget.btn_search,
        widget.btn_prev,
        widget.btn_next,
    ]

    # 객체 이름 계약: compact 툴바 스타일 사용
    assert widget.btn_zoom_out.objectName() == "toolbarIconBtn"
    assert widget.btn_zoom_in.objectName() == "toolbarIconBtn"
    assert widget.btn_fit.objectName() == "toolbarBtn"
    assert widget.btn_actual.objectName() == "toolbarBtn"
    assert widget.btn_prev.objectName() == "toolbarBtn"
    assert widget.btn_next.objectName() == "toolbarBtn"
    assert widget.btn_page_setup.objectName() == "toolbarSecondaryBtn"
    assert widget.btn_print.objectName() == "toolbarSecondaryBtn"
    assert widget.btn_toggle_search.objectName() == "toolbarSecondaryBtn"

    # 라벨이 i18n 키와 일치하는지(잘림 전에 올바른 문자열인지)
    assert widget.btn_fit.text() == tm.get("btn_fit_view")
    assert widget.btn_prev.text() == tm.get("prev_page")
    assert widget.btn_next.text() == tm.get("next_page")
    assert widget.btn_actual.text() == "1:1"

    for btn in buttons:
        _assert_button_fits_text(btn)

    # 과도한 fixed size 회귀 방지: 텍스트 버튼에 좁은 fixed width 금지
    for btn in (widget.btn_prev, widget.btn_next, widget.btn_fit, widget.btn_page_setup):
        assert btn.minimumWidth() == 0 or btn.minimumWidth() >= 40
        # fixed size 였다면 maximum == minimum == 고정값
        if btn.minimumWidth() == btn.maximumWidth() and btn.maximumWidth() < 16777215:
            fm = btn.fontMetrics()
            assert btn.maximumWidth() >= fm.horizontalAdvance(btn.text()) + 16

    widget.close()


def test_theme_defines_compact_toolbar_button_styles():
    """dark/light 테마에 toolbar* 스타일이 정의되어 있어야 한다."""
    from src.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET

    for sheet in (DARK_STYLESHEET, LIGHT_STYLESHEET):
        assert "QPushButton#toolbarBtn" in sheet
        assert "QPushButton#toolbarIconBtn" in sheet
        assert "QPushButton#toolbarSecondaryBtn" in sheet
        # compact padding 존재 확인 (전역 12/24 와 구분)
        assert "padding: 4px 10px" in sheet
