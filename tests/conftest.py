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
            from PyQt6.QtWidgets import QApplication

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
