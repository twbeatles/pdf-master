import sys
import os
import logging
import traceback
import tempfile
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 로그 파일 경로
LOG_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master.log")

def setup_logging():
    """로깅 설정 초기화 (v4.5: 로그 파일 순환 적용)"""
    # v4.5: RotatingFileHandler로 로그 파일 무한 증가 방지
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# PyInstaller 환경에서의 경로 설정 (Import 전에 실행되어야 함)
if getattr(sys, 'frozen', False):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# 창 없는 EXE에서 자식 콘솔 프로그램(표준 라이브러리의 `cmd /c ver` 등)이 터미널 창을
# 띄우지 않게 한다. 다른 모듈이 프로세스를 만들기 전에, 가장 먼저 적용해야 한다.
from src.core.win_console import suppress_child_console_windows

suppress_child_console_windows()

# NOTE: 이 지점에서는 stdlib + PyQt6 + path_utils(stdlib only)까지만 import 한다.
# qfluentwidgets / google-genai / main_window 등 무거운 모듈은 스플래시 표시 이후
# main() 내부에서 지연 import하여 cold-start blank 기간을 최소화한다.
from PyQt6.QtCore import QLockFile
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QGuiApplication, QFont, QIcon, QPixmap

from src.core.path_utils import resource_path

#: 단일 인스턴스 가드 락 파일명 (%TEMP% 하위).
_SINGLE_INSTANCE_LOCK_NAME = "pdf_master_single_instance.lock"

#: 실행 중 인스턴스 탐색용 창 제목 prefix (main_window: f"{APP_NAME} v{VERSION}").
_SINGLE_INSTANCE_TITLE_PREFIX = "PDF Master"

#: 스플래시 이미지 (번들 datas에 포함된 에셋).
_SPLASH_IMAGE_PARTS = ("assets", "app_icon.png")

# 프로세스 수명 동안 락을 유지하기 위한 전역 참조 (GC 해제 시 락이 풀리므로 필수).
_single_instance_lock: QLockFile | None = None


def _tr(key: str, *args: object) -> str:
    """tm 지연 조회. i18n import 실패 시 키 폴백."""
    try:
        from src.core.i18n import tm

        return tm.get(key, *args)
    except Exception:
        return key if not args else f"{key}: {args[0]}"


def global_exception_handler(exc_type, exc_value, exc_tb):
    """전역 예외 핸들러 - 처리되지 않은 예외를 로그에 기록"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Uncaught exception:\n{error_msg}")

    # 사용자에게 오류 알림 (QApplication이 존재하는 경우)
    app = QApplication.instance()
    if app and "--smoke" not in sys.argv:
        QMessageBox.critical(
            None,
            _tr("err_uncaught_exception_title"),
            _tr("err_uncaught_exception_body", exc_value, LOG_FILE),
        )


def single_instance_lock_path() -> str:
    """단일 인스턴스 가드 락 파일 경로."""
    return os.path.join(tempfile.gettempdir(), _SINGLE_INSTANCE_LOCK_NAME)


def try_acquire_single_instance(lock_path: str | None = None) -> tuple[bool, QLockFile | None]:
    """프로세스 전역 단일 인스턴스 락 획득 시도.

    Returns:
        (True, lock): 선점 성공 — 호출자가 lock 참조를 유지하는 동안 단일 인스턴스 보장.
        (False, None): 살아있는 다른 인스턴스가 락 보유 중 — focus 후 종료해야 함.
        (True, None): 락 시스템 자체가 동작하지 않아 가드 없이 진행 (fail-open:
            %TEMP% 파괴 같은 극단 상황에서 앱 기동을 막지 않기 위함).
    """
    path = lock_path or single_instance_lock_path()
    try:
        lock = QLockFile(path)
        # A running app holds this for hours; only PID liveness marks it stale.
        lock.setStaleLockTime(0)
        if lock.tryLock():
            return True, lock
        # tryLock automatically reclaims locks left by dead processes.
        # Never forcibly remove a lock belonging to a live instance.
        if lock.error() == QLockFile.LockError.LockFailedError:
            return False, None
        logger.warning("Single-instance lock unavailable (%s); continuing unguarded", lock.error())
        return True, None
    except Exception:
        logger.debug("Single-instance lock unavailable; continuing unguarded", exc_info=True)
        return True, None


def focus_existing_instance(title_prefix: str = _SINGLE_INSTANCE_TITLE_PREFIX) -> bool:
    """이미 실행 중인 인스턴스 창을 전면에 표시. 성공 시 True."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found: list[int] = []
        enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        # Explicit pointer-sized HWND signatures are required on 64-bit Windows.
        user32.EnumWindows.argtypes = [enum_callback, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        for name in ("IsWindowVisible", "IsIconic", "SetForegroundWindow"):
            function = getattr(user32, name)
            function.argtypes = [wintypes.HWND]
            function.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL

        @enum_callback
        def _enum_proc(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value.startswith(title_prefix):
                    found.append(int(hwnd))
            except Exception:
                pass
            return True

        user32.EnumWindows(_enum_proc, 0)
        if not found:
            return False
        hwnd = found[0]
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            return bool(user32.SetForegroundWindow(hwnd))
        except Exception:
            logger.debug("SetForegroundWindow failed", exc_info=True)
        return False
    except Exception:
        logger.debug("focus_existing_instance failed", exc_info=True)
        return False


def show_startup_splash(app: QApplication, image_path: str | None = None) -> QSplashScreen | None:
    """Heavy import 전에 즉시 스플래시를 표시. 실패 시 None (정상 계속)."""
    try:
        path = image_path or resource_path(*_SPLASH_IMAGE_PARTS)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        splash = QSplashScreen(pixmap)
        splash.show()
        app.processEvents()
        return splash
    except Exception:
        logger.debug("Startup splash skipped", exc_info=True)
        return None


def main() -> int:
    if "--apply-update" in sys.argv:
        from src.core.update_installer import apply_update

        def update_argument(name: str) -> str:
            try:
                return sys.argv[sys.argv.index(name) + 1]
            except (ValueError, IndexError):
                return ""

        return apply_update(
            update_argument("--update-target"),
            update_argument("--update-staged"),
            int(update_argument("--update-parent-pid") or 0),
        )
    # 전역 예외 핸들러 설정
    sys.excepthook = global_exception_handler
    smoke_mode = "--smoke" in sys.argv
    app_argv = [arg for arg in sys.argv if arg != "--smoke"]

    # HiDPI 지원 활성화
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    logger.info("PDF Master starting...")

    try:
        _hi_policy_applied = False
        try:
            from PyQt6.QtCore import Qt as _Qt

            _policy = getattr(_Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough", None)
            if _policy is not None:
                # QApplication 생성 전에 호출되어야 함 (생성 후 호출 시 경고만 발생).
                QGuiApplication.setHighDpiScaleFactorRoundingPolicy(_policy)
                _hi_policy_applied = True
        except Exception:
            logger.debug("HiDPI rounding policy setup skipped", exc_info=True)

        app = QApplication(app_argv)
        app.setApplicationName("PDFMaster")
        app.setOrganizationName("PDFMaster")

        # 단일 인스턴스 가드 (--smoke/업데이트는 검증 목적이므로 제외).
        global _single_instance_lock
        if not smoke_mode:
            acquired, _single_instance_lock = try_acquire_single_instance()
            if not acquired:
                focus_existing_instance()
                logger.info("Another instance is already running; exiting")
                return 0

        # 무거운 import 전에 즉시 피드백 (cold-start blank 최소화).
        splash = None if smoke_mode else show_startup_splash(app)

        try:
            # PyMuPDF 미설치 시 조기 안내 (proxy 예외 전에 사용자 메시지)
            try:
                from src.core.optional_deps import FITZ_AVAILABLE
            except Exception:
                FITZ_AVAILABLE = True  # import 실패 시 기존 경로 유지
            if not FITZ_AVAILABLE and not smoke_mode:
                QMessageBox.critical(
                    None,
                    _tr("err_fitz_required_title"),
                    _tr("err_fitz_required_body"),
                )
                logger.critical("PyMuPDF (fitz) is not available; aborting startup")
                return 1

            # Keep every heavy import inside splash cleanup protection.
            # Explicit imports also ensure PyInstaller bundles them.
            import src.ui.styles  # noqa: F401
            import src.ui.widgets  # noqa: F401
            import src.core.settings  # noqa: F401
            import src.core.worker  # noqa: F401
            from src.ui.main_window import PDFMasterApp

            from src.ui.fluent_theme import setup_app_theme

            if not setup_app_theme(app):
                raise RuntimeError(
                    "PyQt6 Fluent UI is unavailable. Install the default project dependencies "
                    "in a clean environment without PySide6-Fluent-Widgets."
                )
            app.setFont(QFont("Segoe UI", 9))  # Windows 기본 폰트 크기 설정
            app_icon_path = resource_path("assets", "app_icon.png")
            if os.path.isfile(app_icon_path):
                app.setWindowIcon(QIcon(app_icon_path))
            window = PDFMasterApp()
            if smoke_mode:
                from src.ui.fluent_widgets import is_fluent_widgets_available

                if not is_fluent_widgets_available() or not window.tabs._use_fluent:
                    raise RuntimeError("Fluent widgets or navigation failed to initialize")
                app.processEvents()
                window.close()
                logger.info("PDF Master smoke initialization succeeded")
                return 0
            window.show()
            if splash is not None:
                try:
                    splash.finish(window)
                except Exception:
                    logger.debug("Splash finish skipped", exc_info=True)
            splash = None
            logger.info("PDF Master ready")
            return int(app.exec())
        finally:
            if splash is not None:
                try:
                    splash.close()
                except Exception:
                    pass
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        raise

if __name__ == "__main__":
    sys.exit(main())
