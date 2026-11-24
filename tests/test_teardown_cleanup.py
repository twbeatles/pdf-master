"""종료 시점 Qt 정리 후크 회귀 테스트 (teardown access violation 방지)."""

from __future__ import annotations


def test_teardown_qt_widgets_is_safe_and_idempotent():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import conftest
    from PySide6.QtWidgets import QApplication, QWidget

    _teardown_qt_widgets = conftest._teardown_qt_widgets

    app = QApplication.instance() or QApplication([])
    first = QWidget()
    first.setObjectName("teardown-probe-1")
    first.show()
    second = QWidget()
    second.setObjectName("teardown-probe-2")
    second.show()

    import conftest

    conftest._teardown_qt_widgets()
    conftest._teardown_qt_widgets()

    assert QApplication.instance() is app


def test_sessionfinish_hook_never_raises():
    import conftest

    conftest.pytest_sessionfinish(session=None, exitstatus=0)
