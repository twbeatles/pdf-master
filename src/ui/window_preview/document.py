import logging
import os

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from ...core.i18n import tm
from ...core.path_utils import normalize_path_key

logger = logging.getLogger(__name__)

PREVIEW_RELOAD_INTERVAL_MS = 250
PREVIEW_RELOAD_MAX_ATTEMPTS = 10


def _preview_dir_path(path: str) -> str:
    path_key = normalize_path_key(path)
    if not path_key:
        return ""
    return os.path.dirname(path_key)


def _clear_preview_reload_state(self) -> None:
    self._preview_reload_attempts = 0
    self._preview_reload_target_path = ""
    self._preview_reload_restore_state = None


def _ensure_preview_watchers(self):
    if getattr(self, "_preview_file_watcher", None) is None:
        parent = self if isinstance(self, QObject) else None
        self._preview_file_watcher = QFileSystemWatcher(parent)
        self._preview_file_watcher.fileChanged.connect(self._on_preview_file_changed)
    if getattr(self, "_preview_dir_watcher", None) is None:
        parent = self if isinstance(self, QObject) else None
        self._preview_dir_watcher = QFileSystemWatcher(parent)
        self._preview_dir_watcher.directoryChanged.connect(self._on_preview_directory_changed)
    if getattr(self, "_preview_reload_timer", None) is None:
        parent = self if isinstance(self, QObject) else None
        self._preview_reload_timer = QTimer(parent)
        self._preview_reload_timer.setSingleShot(True)
        self._preview_reload_timer.timeout.connect(self._reload_preview_after_external_change)


def _watch_preview_file(self, path: str):
    _ensure_preview_watchers(self)
    file_watcher = self._preview_file_watcher
    dir_watcher = self._preview_dir_watcher
    current_files = file_watcher.files()
    current_dirs = dir_watcher.directories()
    if current_files:
        file_watcher.removePaths(current_files)
    if current_dirs:
        dir_watcher.removePaths(current_dirs)

    path_key = normalize_path_key(path)
    dir_path = _preview_dir_path(path)
    if dir_path and os.path.isdir(dir_path):
        dir_watcher.addPath(dir_path)
    if path_key and os.path.exists(path_key):
        file_watcher.addPath(path_key)


def _unwatch_preview_file(self):
    file_watcher = getattr(self, "_preview_file_watcher", None)
    dir_watcher = getattr(self, "_preview_dir_watcher", None)
    reload_timer = getattr(self, "_preview_reload_timer", None)
    if file_watcher is not None:
        current_files = file_watcher.files()
        if current_files:
            file_watcher.removePaths(current_files)
    if dir_watcher is not None:
        current_dirs = dir_watcher.directories()
        if current_dirs:
            dir_watcher.removePaths(current_dirs)
    if reload_timer is not None:
        reload_timer.stop()
    _clear_preview_reload_state(self)


def _schedule_preview_reload(self, path: str | None = None):
    current_path = path or getattr(self, "_current_preview_path", "")
    path_key = normalize_path_key(current_path)
    if not path_key:
        return

    _ensure_preview_watchers(self)
    current_target = normalize_path_key(getattr(self, "_preview_reload_target_path", ""))
    if current_target != path_key or getattr(self, "_preview_reload_restore_state", None) is None:
        restore_state = self.preview_image.capture_view_state() if hasattr(self, "preview_image") else None
        self._preview_reload_restore_state = restore_state
    self._preview_reload_target_path = path_key
    self._preview_reload_attempts = PREVIEW_RELOAD_MAX_ATTEMPTS
    self._preview_reload_timer.start(PREVIEW_RELOAD_INTERVAL_MS)


def _on_preview_file_changed(self, _path: str):
    current_path = getattr(self, "_current_preview_path", "")
    if not current_path:
        return
    _schedule_preview_reload(self, current_path)


def _on_preview_directory_changed(self, _path: str):
    current_path = getattr(self, "_current_preview_path", "")
    if not current_path:
        return
    _watch_preview_file(self, current_path)
    _schedule_preview_reload(self, current_path)


def _reload_preview_after_external_change(self):
    path = normalize_path_key(getattr(self, "_preview_reload_target_path", "") or getattr(self, "_current_preview_path", ""))
    if not path:
        _clear_preview_reload_state(self)
        return

    _watch_preview_file(self, path)
    if not os.path.exists(path):
        attempts = int(getattr(self, "_preview_reload_attempts", 0) or 0)
        if attempts > 0:
            self._preview_reload_attempts = attempts - 1
            self._preview_reload_timer.start(PREVIEW_RELOAD_INTERVAL_MS)
        else:
            _clear_preview_reload_state(self)
        return

    restore_state = getattr(self, "_preview_reload_restore_state", None)
    _clear_preview_reload_state(self)
    self._preview_password_hint = getattr(self, "_current_preview_password", None)
    try:
        self._update_preview(path, restore_state=restore_state)
    finally:
        self._preview_password_hint = None


def _close_preview_document(self):
    _unwatch_preview_file(self)
    doc = getattr(self, "_current_preview_doc", None)
    if hasattr(self, "preview_image"):
        preview_doc = self.preview_image.document() if hasattr(self.preview_image, "document") else None
        self.preview_image.clear()
        if doc is not None and doc is not preview_doc:
            try:
                doc.close()
            except Exception:
                logger.debug("Failed to close preview document", exc_info=True)
    elif doc:
        try:
            doc.close()
        except Exception:
            logger.debug("Failed to close preview document", exc_info=True)
    self._current_preview_doc = None


def _load_qpdf_document(path: str, password: str | None = None) -> tuple[QPdfDocument, object]:
    doc = QPdfDocument(None)
    if password:
        doc.setPassword(password)
    error = doc.load(path)
    return doc, error


def _ensure_preview_document(self, path: str):
    path_key = normalize_path_key(path)
    current_path = normalize_path_key(getattr(self, "_current_preview_path", ""))
    doc = getattr(self, "_current_preview_doc", None)
    if doc and current_path == path_key and doc.status() == QPdfDocument.Status.Ready:
        return doc, None

    self._close_preview_document()
    new_doc, locked_state = self._open_preview_document(path)
    if new_doc:
        self._current_preview_doc = new_doc
        self._current_preview_path = path_key
        self.preview_image.set_document(new_doc, path_key)
        _watch_preview_file(self, path_key)
    return new_doc, locked_state


def _ensure_preview_access(self, path: str):
    path_key = normalize_path_key(path)
    if not path_key or not os.path.exists(path_key):
        return False, None

    current_path = getattr(self, "_current_preview_path", "")
    current_doc = getattr(self, "_current_preview_doc", None)
    if not current_doc or normalize_path_key(current_path) != path_key:
        self._update_preview(path_key)

    current_path = getattr(self, "_current_preview_path", "")
    current_doc = getattr(self, "_current_preview_doc", None)
    if not current_doc or normalize_path_key(current_path) != path_key:
        return False, None
    if current_doc.status() != QPdfDocument.Status.Ready:
        return False, None
    return True, getattr(self, "_current_preview_password", None)


def _reset_preview_state(self, close_doc: bool = True):
    if close_doc:
        self._close_preview_document()
    elif hasattr(self, "preview_image"):
        self.preview_image.clear_display()
        _clear_preview_reload_state(self)
    self._current_preview_path = ""
    self._preview_total_pages = 0
    self._current_preview_page = 0
    self._current_preview_password = None
    self._set_preview_navigation_enabled(False)


def _prompt_pdf_password(self, path: str):
    password, ok = QInputDialog.getText(
        self,
        tm.get("password_title"),
        tm.get("password_msg").format(os.path.basename(path)),
        QLineEdit.EchoMode.Password,
    )
    if not ok or not password:
        return None
    return password


def _open_preview_document(self, path: str):
    path_key = normalize_path_key(path)
    if not path_key or not os.path.exists(path_key):
        return None, "error"

    no_error = QPdfDocument.Error.None_
    wrong_password = QPdfDocument.Error.IncorrectPassword

    password_hint = getattr(self, "_preview_password_hint", None)
    if isinstance(password_hint, str) and password_hint:
        doc, error = _load_qpdf_document(path_key, password_hint)
        if error == no_error:
            self._current_preview_password = password_hint
            return doc, None
        doc.close()

    doc, error = _load_qpdf_document(path_key)
    if error == no_error:
        self._current_preview_password = None
        return doc, None
    doc.close()

    if error != wrong_password:
        return None, "error"

    while True:
        password = self._prompt_pdf_password(path_key)
        if not password:
            self._current_preview_password = None
            return None, "cancelled"
        doc, error = _load_qpdf_document(path_key, password)
        if error == no_error:
            self._current_preview_password = password
            return doc, None
        doc.close()
        retry = QMessageBox.question(
            self,
            tm.get("password_title"),
            tm.get("password_retry"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if retry != QMessageBox.StandardButton.Yes:
            self._current_preview_password = None
            return None, "wrong"
