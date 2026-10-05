"""UI/UX 리팩터링 회귀 (2026-10-05): 테마 팔레트, 파일 선택칸, 열린 PDF 이어 주기, 일괄 옵션."""

import string

from _deps import require_pyqt6


def _qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_theme_palette_follows_app_theme_not_os():
    require_pyqt6()
    _qapp()
    from PyQt6.QtGui import QPalette

    from src.ui.window_core.theme import build_theme_palette

    light = build_theme_palette(False)
    dark = build_theme_palette(True)
    role = QPalette.ColorRole
    assert light.color(role.Window).name() == "#f8fafc"
    assert light.color(role.WindowText).name() == "#1e293b"
    assert dark.color(role.Window).name() == "#0a0e14"
    assert dark.color(role.WindowText).name() == "#f0f4f8"
    # 본문 글자와 배경이 같은 밝기대로 겹치지 않아야 한다.
    for palette in (light, dark):
        assert abs(palette.color(role.Base).lightness() - palette.color(role.Text).lightness()) > 120


def test_file_selector_reflects_selection_state(tmp_path):
    require_pyqt6()
    _qapp()
    from src.ui.widgets import FileSelectorWidget

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    selector = FileSelectorWidget()
    image_selector = FileSelectorWidget("", [".png", ".jpg"])
    try:
        assert not selector.btn_clear.isEnabled()
        assert not selector.drop_zone.text_label.isHidden()

        selector.set_path(str(pdf))
        assert selector.btn_clear.isEnabled()
        assert selector.drop_zone.text_label.isHidden()  # 안내 문구 대신 파일 이름만
        assert "a.pdf" in selector.drop_zone.path_label.text()

        changed = []
        selector.pathChanged.connect(changed.append)
        selector.clear_path()
        assert changed == [""]
        assert not selector.btn_clear.isEnabled()
        assert not selector.drop_zone.text_label.isHidden()

        # 최근 파일 목록은 PDF 전용이라 이미지 선택칸에서는 숨긴다.
        assert not selector.btn_recent.isHidden()
        assert image_selector.btn_recent.isHidden()
    finally:
        selector.deleteLater()
        image_selector.deleteLater()


def test_drop_zone_click_opens_file_picker():
    require_pyqt6()
    _qapp()
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest

    from src.ui.widgets import DropZoneWidget

    zone = DropZoneWidget()
    try:
        zone.resize(300, 80)
        clicks = []
        zone.clicked.connect(lambda: clicks.append(1))
        QTest.mouseClick(zone, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(20, 20))
        assert clicks == [1]
    finally:
        zone.deleteLater()


def test_active_pdf_is_carried_to_empty_primary_selectors(tmp_path):
    require_pyqt6()
    _qapp()
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

    from src.ui.widgets import FileSelectorWidget
    from src.ui.window_core.active_file import _carry_active_pdf_to_visible_tools

    active = tmp_path / "active.pdf"
    other = tmp_path / "other.pdf"
    for path in (active, other):
        path.write_bytes(b"%PDF-1.4\n")

    host = QWidget()
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    layout = QVBoxLayout(host)

    def group(*selectors):
        box = QGroupBox("tool")
        box_layout = QVBoxLayout(box)
        for selector in selectors:
            box_layout.addWidget(selector)
        layout.addWidget(box)

    empty, compare_first, compare_second = FileSelectorWidget(), FileSelectorWidget(), FileSelectorWidget()
    prefilled, image = FileSelectorWidget(), FileSelectorWidget("", [".png"])
    hidden = FileSelectorWidget()
    prefilled.set_path(str(other))
    group(empty)
    group(compare_first, compare_second)
    group(prefilled)
    group(image)
    group(hidden)
    hidden.parentWidget().hide()

    emitted = []
    empty.pathChanged.connect(emitted.append)
    try:
        host.show()
        host._current_preview_path = str(active)
        filled = _carry_active_pdf_to_visible_tools(host)

        assert filled == 2
        assert empty.get_path() and compare_first.get_path()
        assert emitted == [empty.get_path()]
        assert compare_second.get_path() == ""  # 두 번째 칸은 다른 파일을 고르는 자리
        assert prefilled.get_path() == str(other)  # 이미 고른 파일은 유지
        assert image.get_path() == ""
        assert hidden.get_path() == ""  # 보이지 않는 화면은 건드리지 않음
        assert host._carrying_active_pdf is False

        host._current_preview_path = ""
        assert _carry_active_pdf_to_visible_tools(host) == 0
    finally:
        host.close()
        host.deleteLater()


def test_update_preview_keeps_view_while_carrying_same_file(tmp_path):
    from src.ui.window_preview.update import _update_preview

    pdf = tmp_path / "same.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    class Host:
        _carrying_active_pdf = True
        _current_preview_path = str(pdf)

        def _ensure_preview_document(self, _path):  # pragma: no cover - 호출되면 실패
            raise AssertionError("preview must not be reloaded while carrying the same file")

    _update_preview(Host(), str(pdf))


def test_batch_tab_shows_only_options_for_selected_operation():
    require_pyqt6()
    _qapp()
    from PyQt6.QtWidgets import QLineEdit, QTabWidget, QWidget

    from src.core.i18n import tm
    from src.ui.tabs_basic import batch

    class Host(QWidget):
        def __init__(self):
            super().__init__()
            self.tabs = QTabWidget(self)

        def _on_list_item_clicked(self, *_args):
            pass

        _batch_add_files = _batch_add_folder = action_batch = _on_list_item_clicked

    host = Host()
    try:
        batch.setup_batch_tab(host)

        def select(operation):
            host.cmb_batch_op.setCurrentIndex(host.cmb_batch_op.findData(operation))

        select("compress")
        assert host._batch_text_row.isHidden() and host._batch_wm_row.isHidden() and host._batch_perm_box.isHidden()

        select("watermark")
        assert not host._batch_text_row.isHidden() and not host._batch_wm_row.isHidden()
        assert host._batch_perm_box.isHidden()
        assert host.inp_batch_opt.echoMode() == QLineEdit.EchoMode.Normal
        host.inp_batch_opt.setText("CONFIDENTIAL")

        select("encrypt")
        assert not host._batch_text_row.isHidden() and not host._batch_perm_box.isHidden()
        assert host._batch_wm_row.isHidden()
        assert host.inp_batch_opt.echoMode() == QLineEdit.EchoMode.Password
        assert host.inp_batch_opt.text() == ""  # 워터마크 문구가 비밀번호로 넘어가지 않는다
        assert host._batch_hint.text() == tm.get("hint_batch_encrypt")

        select("rotate")
        assert host._batch_text_row.isHidden() and host._batch_perm_box.isHidden()
    finally:
        host.deleteLater()


def test_tab_shell_rail_helpers_are_safe_without_rail():
    require_pyqt6()
    _qapp()
    from src.ui.tab_shell import TabShell

    shell = TabShell(mode="pivot")
    try:
        shell.configure_rail()
        shell.expand_rail()  # 레일이 아니면 no-op
    finally:
        shell.deleteLater()


def _positional_fields(text):
    return [spec for _lit, name, spec, _conv in string.Formatter().parse(text) if name == ""]


def test_catalogs_keep_placeholders_in_sync_and_page_label_is_not_a_tab_name():
    from src.core.i18n_catalogs import TRANSLATIONS

    ko, en = TRANSLATIONS["ko"], TRANSLATIONS["en"]
    assert set(ko) == set(en)
    mismatched = [key for key in ko if len(_positional_fields(ko[key])) != len(_positional_fields(en[key]))]
    assert not mismatched, mismatched
    # "페이지:" 입력 라벨은 탭 이름 키를 재사용하지 않는다 (탭 이름이 바뀌어도 라벨이 깨지지 않게).
    assert ko["lbl_page"] == "페이지:" and en["lbl_page"] == "Page:"
    for operation in ("compress", "watermark", "encrypt", "rotate"):
        assert ko[f"hint_batch_{operation}"] and en[f"hint_batch_{operation}"]


def test_no_tab_name_key_reused_as_field_label():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "ui"
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if 'tm.get("tab_page") + ":"' in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders
