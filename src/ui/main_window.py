import logging
import os
import tempfile

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.constants import UNDO_BACKUP_MAX_AGE_HOURS, UNDO_BACKUP_MAX_SIZE_MB
from ..core.i18n import tm
from ..core.settings import load_settings, save_settings
from ..core.undo_manager import UndoManager
from .main_window_config import APP_NAME, VERSION
from .main_window_core import MainWindowCoreMixin
from .main_window_preview import MainWindowPreviewMixin
from .main_window_tabs_advanced import MainWindowTabsAdvancedMixin
from .main_window_tabs_ai import MainWindowTabsAiMixin
from .main_window_tabs_basic import MainWindowTabsBasicMixin
from .main_window_undo import MainWindowUndoMixin
from .main_window_worker import MainWindowWorkerMixin
from .progress_overlay import ProgressOverlayWidget
from .widgets import WheelEventFilter

logger = logging.getLogger(__name__)


class PDFMasterApp(
    QMainWindow,
    MainWindowCoreMixin,
    MainWindowPreviewMixin,
    MainWindowWorkerMixin,
    MainWindowUndoMixin,
    MainWindowTabsBasicMixin,
    MainWindowTabsAdvancedMixin,
    MainWindowTabsAiMixin,
):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.timeout.connect(self._flush_settings_save)
        self.worker = None
        self._last_output_path = None  # 마지막 저장 경로 추적
        self._current_preview_page = 0
        self._current_preview_doc = None
        self._current_preview_password = None
        self._chat_histories = self._load_chat_histories()
        self._chat_pending_path = None

        # v4.0: Undo/Redo 매니저
        self.undo_manager = UndoManager(max_history=50)

        # v4.3: Undo 백업 디렉토리 (임시 폴더 사용)
        self._undo_backup_dir = os.path.join(tempfile.gettempdir(), "pdf_master_undo")
        os.makedirs(self._undo_backup_dir, exist_ok=True)

        # v4.4: 시작 시 오래된 백업 정리
        self._cleanup_old_undo_backups(max_age_hours=UNDO_BACKUP_MAX_AGE_HOURS)  # v4.5: 상수 사용
        # v4.5: 시작 시 용량 기반 백업 정리
        self._cleanup_undo_backups_by_size(max_size_mb=UNDO_BACKUP_MAX_SIZE_MB)  # v4.5: 상수 사용

        # 휠 이벤트 필터 설치 (스크롤로 값 변경 방지)
        self._wheel_filter = WheelEventFilter(self)

        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1200, 850)  # 더 큰 기본 크기
        self.setMinimumSize(950, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 10, 15, 10)  # 더 컴팩트한 여백
        main_layout.setSpacing(8)

        # Header - 컴팩트하게
        header = self._create_header()
        main_layout.addLayout(header)

        # Menu bar
        self._create_menu_bar()

        # Content area with splitter - 더 큰 비율
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setHandleWidth(5)  # 드래그 핸들 더 넘게
        self.content_splitter.setChildrenCollapsible(False)  # 패널 접기 방지

        # Tabs (left side)
        tabs_widget = QWidget()
        tabs_layout = QVBoxLayout(tabs_widget)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)
        self.content_splitter.addWidget(tabs_widget)

        # Preview panel (right side)
        preview_widget = self._create_preview_panel()
        self.content_splitter.addWidget(preview_widget)
        self.content_splitter.setSizes([650, 450])  # 미리보기 패널 더 크게

        # 사용자 설정 복원
        saved_sizes = self.settings.get("splitter_sizes")
        if saved_sizes:
            self.content_splitter.setSizes(saved_sizes)
        self.content_splitter.splitterMoved.connect(self._save_splitter_state)

        main_layout.addWidget(self.content_splitter, 1)  # stretch factor 1로 최대 확장

        # Setup tabs
        self.setup_merge_tab()
        self.setup_convert_tab()
        self.setup_page_tab()
        self.setup_reorder_tab()  # 페이지 순서 변경
        self.setup_edit_sec_tab()
        self.setup_batch_tab()    # 일괄 처리
        self.setup_advanced_tab() # 고급 기능
        self.setup_ai_tab()       # v4.0: AI 요약

        # 컴팩트한 상태 바
        status_frame = QFrame()
        status_frame.setMaximumHeight(36)  # 높이 제한
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(10)

        self.status_label = QLabel(tm.get("ready"))
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        status_layout.addWidget(self.progress_bar)

        self.btn_open_folder = QPushButton(tm.get("folder"))
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setFixedWidth(70)
        self.btn_open_folder.setFixedHeight(24)
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_last_folder)
        status_layout.addWidget(self.btn_open_folder)

        main_layout.addWidget(status_frame)

        self._apply_theme()
        self._setup_shortcuts()

        # 모든 QSpinBox, QComboBox에 휠 필터 설치
        self._install_wheel_filters()

        # v2.7: 윈도우 위치 복원
        self._restore_window_geometry()

        # v4.3: 진행 오버레이 위젯 초기화 (개선된 UX)
        self.progress_overlay = ProgressOverlayWidget(central)
        self.progress_overlay.cancelled.connect(self._on_worker_cancelled)
        self.progress_overlay.hide()

    def closeEvent(self, event):
        """앱 종료 시 리소스 정리 및 설정 저장"""
        logger.info("Application closing...")

        # 1. 실행 중인 Worker 정리
        if self.worker and self.worker.isRunning():
            logger.info("Stopping running worker...")
            if hasattr(self.worker, 'cancel'):
                self.worker.cancel()
            self.worker.quit()
            if not self.worker.wait(3000):  # 3초 대기
                logger.warning("Worker did not stop in time, forcing termination")
                self.worker.terminate()
                self.worker.wait(1000)

        # 2. 미리보기 문서 리소스 정리
        if hasattr(self, '_current_preview_doc') and self._current_preview_doc:
            try:
                self._current_preview_doc.close()
                self._current_preview_doc = None
                logger.debug("Preview document closed")
            except Exception as e:
                logger.warning(f"Failed to close preview document: {e}")

        # 3. 미사용 undo 백업 정리 (v4.4)
        self._cleanup_unused_undo_backups()

        # 4. 채팅 히스토리 저장
        self._save_chat_histories()

        # 5. 설정 저장
        self._flush_settings_save()
        self._save_settings_on_exit()

        logger.info("Application cleanup complete")
        super().closeEvent(event)

    def _schedule_settings_save(self, delay_ms: int = 400):
        """Debounced settings save for high-frequency UI updates."""
        if delay_ms < 0:
            delay_ms = 0
        self._settings_save_timer.start(delay_ms)

    def _flush_settings_save(self):
        """Flush pending debounced settings save immediately."""
        if self._settings_save_timer.isActive():
            self._settings_save_timer.stop()
        save_settings(self.settings)
