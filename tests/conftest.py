import logging
import os
import sys
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

# pytest 9 can run with importlib import mode where cwd isn't reliably on sys.path.
# Ensure the repo root (which contains the `src/` package) is importable.
ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_SESSION_QAPP = None


def _ensure_session_qapp():
    """스위트 전체에서 QApplication 1개 유지.

    테스트별 재생성은 Fluent C++ 싱글톤(Router 등)을 삭제해
    이후 NavigationInterface/Fluent 위젯 생성을 깨뜨리므로 금지.
    """
    global _SESSION_QAPP
    if _SESSION_QAPP is None:
        try:
            from PySide6.QtWidgets import QApplication

            _SESSION_QAPP = QApplication.instance() or QApplication([])
        except Exception:
            logger.debug("session QApplication unavailable", exc_info=True)
            _SESSION_QAPP = None
    return _SESSION_QAPP


def pytest_configure(config):
    _ensure_session_qapp()


@pytest.fixture(autouse=True)
def _reset_app_state_between_tests():
    yield
    try:
        app = _ensure_session_qapp()
        if app is not None:
            app.setStyleSheet("")
            app.processEvents()
    except Exception:
        logger.debug("app state reset skipped", exc_info=True)


def _teardown_qt_widgets() -> None:
    """남은 탑레벨 위젯을 확정 순서로 닫고 DeleteLater를 전달한다."""
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        return
    try:
        app = QApplication.instance()
        if app is None:
            return
        for _ in range(10):
            widgets = app.topLevelWidgets()
            if not widgets:
                break
            for widget in widgets:
                try:
                    widget.close()
                except Exception:
                    pass
                try:
                    widget.deleteLater()
                except Exception:
                    pass
            try:
                app.processEvents()
            except Exception:
                break
    except Exception:
        logger.debug("Qt widget teardown skipped", exc_info=True)


def pytest_sessionfinish(session, exitstatus):
    """세션 종료 후크: 남은 위젯 확정 정리.

    GC/모듈 teardown 순서에 맡기면 DeleteLater를 쥔 위젯이
    인터프리터 종료와 겹쳐 간헐적 access violation이 발생한다.
    살아있는 상태에서 닫고 DeleteLater를 전달한다.
    """
    logger.debug("pytest session finished with exitstatus=%s", exitstatus)
    _teardown_qt_widgets()
