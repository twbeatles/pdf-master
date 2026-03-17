import os
import tempfile
import traceback
import logging
import time
import re
from typing import Any, cast
from PyQt6.QtCore import QThread, pyqtSignal

from .optional_deps import fitz

# 상수 임포트
try:
    from .constants import (
        COMPRESSION_SETTINGS, PAGE_SIZES, DEFAULT_PAGE_SIZE,
        WATERMARK_DEFAULTS, WATERMARK_TILE_SPACING_X, WATERMARK_TILE_SPACING_Y,
        MAX_PAGE_RANGE_LENGTH, MAX_FILE_SIZE, MIN_PDF_SIZE
    )
    from .i18n import TranslationManager
    tm = TranslationManager()
except ImportError:
    # 독립 실행 시 폴백
    COMPRESSION_SETTINGS = {
        'low': {'garbage': 4, 'deflate': True, 'deflate_images': True, 'deflate_fonts': True, 'clean': True},
        'medium': {'garbage': 3, 'deflate': True, 'deflate_images': True},
        'high': {'garbage': 2, 'deflate': True},
    }
    PAGE_SIZES = {'A4': (595, 842), 'A3': (842, 1191), 'Letter': (612, 792), 'Legal': (612, 1008)}
    DEFAULT_PAGE_SIZE = (595, 842)
    WATERMARK_DEFAULTS = {'opacity': 0.3, 'color': (0.5, 0.5, 0.5), 'fontsize': 40, 'rotation': 45, 'fontname': 'helv'}
    WATERMARK_TILE_SPACING_X = 300
    WATERMARK_TILE_SPACING_Y = 200
    MAX_PAGE_RANGE_LENGTH = 1000
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
    MIN_PDF_SIZE = 100
    tm = None  # 폴백: i18n 없음

class _PerfTimerFallback:
    def __init__(self, *_args: object, **_kwargs: object):
        pass

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object):
        return False


try:
    from .perf import PerfTimer
except ImportError:
    PerfTimer = cast(Any, _PerfTimerFallback)

FITZ_PDF_PERM_ACCESSIBILITY = int(getattr(fitz, "PDF_PERM_ACCESSIBILITY", 0))
FITZ_PDF_PERM_PRINT = int(getattr(fitz, "PDF_PERM_PRINT", 0))
FITZ_PDF_PERM_COPY = int(getattr(fitz, "PDF_PERM_COPY", 0))
FITZ_PDF_ENCRYPT_AES_256 = int(getattr(fitz, "PDF_ENCRYPT_AES_256", 0))


def _as_str(value: Any | None, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_int(value: Any | None, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _as_list(value: Any | None) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

logger = logging.getLogger(__name__)

class CancelledError(Exception):
    """작업 취소 시 발생하는 예외"""
    pass

from .worker_ops import WorkerAiOpsMixin, WorkerPdfOpsMixin

class WorkerThread(QThread, WorkerPdfOpsMixin, WorkerAiOpsMixin):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal(str)


    def __init__(self, mode: str, **kwargs: Any):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs
        self._cancel_requested = False
        self._last_progress_value: int | None = None
        self._last_progress_emit_ts_ms = 0.0
        logger.debug(f"WorkerThread initialized: mode={mode}")

    def _parse_page_range(self, page_range_str: str, total_pages: int) -> list:
        """페이지 범위 문자열을 파싱하여 페이지 번호 리스트(0-indexed) 반환

        Note: 입력 순서를 유지합니다. "5-1"은 5,4,3,2,1 순서로 반환됩니다.
        """
        if not page_range_str:
            return []

        pages = []  # 순서 유지를 위해 리스트 사용
        seen = set()  # 중복 체크용
        max_results = MAX_PAGE_RANGE_LENGTH  # 결과 길이 제한
        parts = page_range_str.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            try:
                if '-' in part:
                    # 범위 처리 (예: 1-5, 5-1)
                    start_str, end_str = part.split('-')
                    start = int(start_str)
                    end = int(end_str)

                    if start <= end:
                        # 순방향: 1-5 -> 1,2,3,4,5
                        for p in range(start, end + 1):
                            if 1 <= p <= total_pages and (p - 1) not in seen:
                                pages.append(p - 1)
                                seen.add(p - 1)
                                if len(pages) >= max_results:
                                    logger.warning(f"페이지 범위가 최대 제한({max_results})에 도달했습니다.")
                                    return pages
                    else:
                        # 역방향: 5-1 -> 5,4,3,2,1
                        for p in range(start, end - 1, -1):
                            if 1 <= p <= total_pages and (p - 1) not in seen:
                                pages.append(p - 1)
                                seen.add(p - 1)
                                if len(pages) >= max_results:
                                    logger.warning(f"페이지 범위가 최대 제한({max_results})에 도달했습니다.")
                                    return pages
                else:
                    # 단일 페이지
                    p = int(part)
                    if 1 <= p <= total_pages and (p - 1) not in seen:
                        pages.append(p - 1)
                        seen.add(p - 1)
                        if len(pages) >= max_results:
                            logger.warning(f"페이지 범위가 최대 제한({max_results})에 도달했습니다.")
                            return pages
            except ValueError:
                logger.warning(f"잘못된 페이지 형식 무시됨: {part}")
                continue

        return pages

    def cancel(self):
        """작업 취소 요청"""
        self._cancel_requested = True
        # QThread 표준 취소 메커니즘도 함께 사용 (cooperative cancellation)
        try:
            self.requestInterruption()
        except Exception:
            logger.debug("requestInterruption() failed", exc_info=True)
        logger.info(f"Cancel requested for task: {self.mode}")

    def _check_cancelled(self):
        """취소 여부 확인 - 장시간 작업 중간에 호출"""
        if self._cancel_requested or self.isInterruptionRequested():
            raise CancelledError("작업이 사용자에 의해 취소되었습니다.")

    def _emit_progress_if_due(self, value: int | float | str, min_step: int = 1, min_interval_ms: int = 50):
        """진행률 신호를 단계/시간 기준으로 스로틀링하여 emit."""
        try:
            value = int(value)
        except Exception:
            return
        value = max(0, min(100, value))

        now_ms = time.monotonic() * 1000.0
        last_value = self._last_progress_value

        should_emit = False
        if last_value is None:
            should_emit = True
        elif value == 100:
            should_emit = True
        elif abs(value - last_value) >= max(1, int(min_step)):
            should_emit = True
        elif (now_ms - self._last_progress_emit_ts_ms) >= max(0, int(min_interval_ms)):
            should_emit = True

        if should_emit:
            self.progress_signal.emit(value)
            self._last_progress_value = value
            self._last_progress_emit_ts_ms = now_ms

    def _sanitize_attachment_filename(self, raw_name: str, fallback: str) -> str:
        """첨부 파일명을 파일시스템 안전한 형태로 정규화."""
        base_name = os.path.basename(str(raw_name or "").strip())
        if not base_name or base_name in {".", ".."}:
            base_name = fallback

        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", base_name)
        safe_name = safe_name.strip(" .")
        if not safe_name:
            safe_name = fallback
        return safe_name

    def _build_safe_attachment_output_path(self, output_dir: str, raw_name: str, index: int, used_names: set):
        """첨부 추출 경로를 output_dir 하위로 강제하고 중복명을 자동 회피."""
        output_dir_abs = os.path.abspath(output_dir or ".")
        fallback = f"attachment_{index + 1}"
        safe_name = self._sanitize_attachment_filename(raw_name, fallback)
        root, ext = os.path.splitext(safe_name)

        candidate = safe_name
        suffix = 1
        lowered = candidate.lower()
        while lowered in used_names:
            candidate = f"{root}_{suffix}{ext}"
            lowered = candidate.lower()
            suffix += 1

        out_path = os.path.abspath(os.path.join(output_dir_abs, candidate))
        try:
            common = os.path.commonpath([output_dir_abs, out_path])
        except ValueError as exc:
            raise ValueError(self._get_msg("err_attachment_path_invalid", raw_name)) from exc
        if common != output_dir_abs:
            raise ValueError(self._get_msg("err_attachment_path_invalid", raw_name))

        used_names.add(lowered)
        return out_path, candidate

    def _atomic_pdf_save(self, doc: Any, output_path: str, **save_kwargs: Any):
        """
        원자적 PDF 저장.

        - 같은 디렉터리에 임시 파일로 먼저 저장한 뒤 os.replace로 교체합니다.
        - 저장/교체 사이에 취소가 들어오면 최종 파일을 만들지 않고 취소 처리합니다.
        """
        if not output_path:
            raise ValueError("output_path is required")

        out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(out_dir, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".pdf_master_", suffix=".tmp.pdf", dir=out_dir)
        os.close(fd)

        # doc가 원본 파일과 같은 경로를 잡고 있을 때(사용자가 덮어쓰기 저장),
        # Windows에서 replace가 실패할 수 있어 fallback 용도로 사용
        same_target = False
        try:
            doc_name = getattr(doc, "name", "") or ""
            if doc_name:
                same_target = os.path.abspath(doc_name) == os.path.abspath(output_path)
        except Exception:
            same_target = False

        try:
            self._check_cancelled()
            doc.save(tmp_path, **cast(Any, save_kwargs))
            self._check_cancelled()
            try:
                os.replace(tmp_path, output_path)
            except PermissionError:
                if same_target:
                    try:
                        doc.close()
                    except Exception:
                        logger.debug("Failed to close document before replace", exc_info=True)
                    os.replace(tmp_path, output_path)
                else:
                    raise
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    logger.debug("Failed to remove temporary PDF file", exc_info=True)

    def _get_msg(self, key: str, *args) -> str:
        """v4.5: i18n 메시지 헬퍼 - 폴백 지원"""
        if tm:
            return tm.get(key, *args)
        # 폴백: 기본 한국어 메시지
        fallback = {
            "err_ai_module_not_found": "AI 서비스 모듈을 찾을 수 없습니다.",
            "err_pdf_not_found": "PDF 파일을 찾을 수 없습니다.",
            "err_api_key_required": "Gemini API 키가 필요합니다.",
            "err_ai_unavailable": "AI 서비스를 사용할 수 없습니다.",
            "err_question_required": "질문을 입력해주세요.",
            "err_input_file_missing": "입력 파일이 존재하지 않습니다.",
            "err_output_path_missing": "출력 경로가 지정되지 않았습니다.",
            "err_cancelled": "작업이 취소되었습니다.",
            "err_pdf_corrupted": "PDF 파일이 손상되었거나 형식이 올바르지 않습니다.",
            "err_operation_failed": "오류 발생: {}",
            "err_file_access_denied": "파일 접근 권한이 없습니다: {}",
            "err_invalid_markup_type": "지원하지 않는 마크업 유형입니다: {}",
            "err_page_out_of_range": "페이지 번호 오류: {} (전체 {}페이지)",
            "err_pdf_has_no_pages": "PDF에 페이지가 없습니다.",
            "err_invalid_page_range": "유효한 페이지 범위가 아닙니다: {}",
            "err_copy_pages_required": "복사할 페이지 범위를 입력해주세요.",
            "err_link_target_zero_based": "대상 페이지 번호 오류(0-based): {} (허용: 0~{})",
            "err_page_number_numeric": "페이지 번호는 숫자여야 합니다: {}",
            "err_attachment_path_invalid": "첨부 파일 경로가 유효하지 않습니다: {}",
        }
        msg = fallback.get(key, key)
        if args:
            try:
                return msg.format(*args)
            except (IndexError, KeyError):
                return msg
        return msg

    def _init_ai_service(self, require_api_key: bool = True):
        """v4.5: AI 서비스 초기화 헬퍼 - 코드 중복 제거

        Returns:
            tuple: (AIService 인스턴스, 에러 메시지) - 성공 시 에러는 None
        """
        try:
            from .ai_service import AIService
        except ImportError:
            return None, self._get_msg("err_ai_module_not_found")

        file_path = self.kwargs.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return None, self._get_msg("err_pdf_not_found")

        api_key = self.kwargs.get('api_key', '')
        if require_api_key and not api_key:
            return None, self._get_msg("err_api_key_required")

        ai_service = AIService(api_key=api_key)
        if not ai_service.is_available:
            return None, self._get_msg("err_ai_unavailable")

        return ai_service, None

    def _validate_file_size(self, file_path: str, emit_error: bool = True) -> bool:
        """v4.5: 파일 크기 검증 헬퍼

        Args:
            file_path: 검증할 파일 경로
            emit_error: True면 에러 시그널 발생

        Returns:
            bool: 유효한 크기면 True
        """
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                size_gb = file_size / (1024**3)
                max_gb = MAX_FILE_SIZE / (1024**3)
                if emit_error:
                    self.error_signal.emit(
                        self._get_msg("err_file_too_large", f"{size_gb:.2f}GB", f"{max_gb:.0f}GB")
                    )
                logger.warning(f"File too large: {file_path} ({size_gb:.2f}GB)")
                return False
            if file_size < MIN_PDF_SIZE:
                if emit_error:
                    self.error_signal.emit(self._get_msg("err_file_too_small"))
                return False
            return True
        except OSError as e:
            logger.error(f"File size check failed: {e}")
            return False

    def _validate_non_pdf_size(self, file_path: str, emit_error: bool = True) -> bool:
        """비-PDF 입력 파일의 존재/최대 크기만 검증."""
        if not file_path or not os.path.exists(file_path):
            if emit_error:
                self.error_signal.emit(self._get_msg("err_input_file_missing"))
            return False
        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                size_gb = file_size / (1024**3)
                max_gb = MAX_FILE_SIZE / (1024**3)
                if emit_error:
                    self.error_signal.emit(
                        self._get_msg("err_file_too_large", f"{size_gb:.2f}GB", f"{max_gb:.0f}GB")
                    )
                logger.warning(f"File too large: {file_path} ({size_gb:.2f}GB)")
                return False
            return True
        except OSError as e:
            logger.error(f"Non-PDF file size check failed: {e}")
            return False

    def _normalize_mode_kwargs(self):
        """
        모드별 kwargs 정규화.

        NOTE: 신규 입력은 정규화 레이어를 통해서만 소비합니다.
        """
        kwargs = self.kwargs

        if self.mode == "draw_shapes":
            shapes = kwargs.get("shapes")
            if not shapes and any(k in kwargs for k in ("shape_type", "x", "y", "width", "height")):
                shape_type = kwargs.get("shape_type", "rect")
                x = float(kwargs.get("x", 100))
                y = float(kwargs.get("y", 100))
                w = float(kwargs.get("width", 120))
                h = float(kwargs.get("height", 80))
                stroke_width = float(kwargs.get("line_width", 1))
                line_color = kwargs.get("line_color", kwargs.get("color", (1, 0, 0)))
                fill_color = kwargs.get("fill_color", kwargs.get("fill"))
                shape = {"type": shape_type, "color": line_color, "width": stroke_width}
                if fill_color is not None:
                    shape["fill"] = fill_color
                if shape_type == "line":
                    shape["p1"] = [x, y]
                    shape["p2"] = [x + w, y + h]
                elif shape_type == "circle":
                    shape["center"] = [x + (w / 2.0), y + (h / 2.0)]
                    shape["radius"] = max(1.0, min(abs(w), abs(h)) / 2.0)
                elif shape_type == "oval":
                    shape["rect"] = [x, y, x + w, y + h]
                else:
                    shape["type"] = "rect"
                    shape["rect"] = [x, y, x + w, y + h]
                kwargs["shapes"] = [shape]

        elif self.mode == "add_link":
            link_type = kwargs.get("link_type", "uri")
            if link_type == "url":
                kwargs["link_type"] = "uri"
            elif link_type == "page":
                kwargs["link_type"] = "goto"

        elif self.mode == "insert_textbox":
            if "rect" not in kwargs:
                x = float(kwargs.get("x", 100))
                y = float(kwargs.get("y", 100))
                w = float(kwargs.get("width", 200))
                h = float(kwargs.get("height", 50))
                kwargs["rect"] = [x, y, x + w, y + h]

        elif self.mode == "copy_page_between_docs":
            if not kwargs.get("target_path"):
                kwargs["target_path"] = kwargs.get("file_path")
            source_pages = kwargs.get("source_pages")
            if source_pages is None:
                page_range = kwargs.get("page_range", "")
                if isinstance(page_range, str) and page_range.strip():
                    kwargs["source_pages"] = self._parse_page_range(page_range, 10**9)
                else:
                    kwargs["source_pages"] = None
            elif isinstance(source_pages, int):
                kwargs["source_pages"] = [source_pages]

        elif self.mode == "image_watermark":
            alias_map = {
                "top-center": "top",
                "bottom-center": "bottom",
            }
            pos = kwargs.get("position")
            if isinstance(pos, str):
                kwargs["position"] = alias_map.get(pos, pos)

            if "scale" in kwargs and kwargs.get("image_path"):
                try:
                    scale = float(kwargs.get("scale", 1.0))
                except (TypeError, ValueError):
                    scale = 1.0
                scale = max(0.01, scale)
                try:
                    pix = fitz.Pixmap(kwargs["image_path"])
                    base_w, base_h = pix.width, pix.height
                    del pix
                    kwargs["width"] = max(1, int(base_w * scale))
                    kwargs["height"] = max(1, int(base_h * scale))
                except Exception:
                    logger.debug("Failed to compute watermark image size from scale", exc_info=True)

    def _preflight_inputs(self) -> bool:
        """작업 실행 전 입력 파일 검증 (fail-fast)."""
        kwargs = self.kwargs

        def _validate_pdf_path(path: str) -> bool:
            if not path or not os.path.exists(path):
                self.error_signal.emit(self._get_msg("err_pdf_not_found"))
                return False
            return self._validate_file_size(path, emit_error=True)

        # 단일 PDF 입력
        for key in ("file_path", "file_path1", "file_path2", "source_path", "target_path", "replace_path"):
            path = kwargs.get(key)
            if isinstance(path, str):
                if not _validate_pdf_path(path):
                    return False

        # 단일 비-PDF 입력
        for key in ("image_path", "signature_path", "attach_path"):
            path = kwargs.get(key)
            if isinstance(path, str):
                if not self._validate_non_pdf_size(path, emit_error=True):
                    return False

        # 목록 입력 검증
        for key in ("files", "file_paths"):
            if key not in kwargs:
                continue
            paths = kwargs.get(key)
            if paths is None:
                continue
            if not isinstance(paths, list):
                paths = [paths]
            if not paths:
                self.error_signal.emit(self._get_msg("err_input_file_missing"))
                return False

            is_pdf_list = not (self.mode == "images_to_pdf" and key == "files")
            valid_count = 0
            for path in paths:
                if not path:
                    continue
                if is_pdf_list:
                    if not _validate_pdf_path(path):
                        return False
                else:
                    if not self._validate_non_pdf_size(path, emit_error=True):
                        return False
                valid_count += 1

            if valid_count == 0:
                if is_pdf_list:
                    self.error_signal.emit(self._get_msg("err_no_valid_pdf"))
                else:
                    self.error_signal.emit(self._get_msg("err_input_file_missing"))
                return False

        return True

    def _is_pdf_encrypted(self, file_path: str) -> bool:
        """암호화된 PDF 여부 확인"""
        doc = None
        try:
            doc = fitz.open(file_path)
            return bool(doc.is_encrypted)
        except Exception:
            return False
        finally:
            if doc:
                doc.close()

    def run(self):
        logger.info(f"Starting task: {self.mode}")
        # v4.5: _cancel_requested는 __init__에서 초기화됨 (중복 제거)
        try:
            self._normalize_mode_kwargs()
            method = getattr(self, self.mode, None)
            if method:
                if not self._preflight_inputs():
                    logger.info(f"Preflight validation failed: {self.mode}")
                    return
                self._last_progress_value = None
                self._last_progress_emit_ts_ms = 0.0
                with PerfTimer(f"core.worker.{self.mode}", logger=logger, extra={"mode": self.mode}):
                    method()
                if not self._cancel_requested:
                    logger.info(f"Task completed: {self.mode}")
            else:
                error_msg = f"Unknown task: {self.mode}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
        except CancelledError:
            logger.info(f"Task cancelled: {self.mode}")
            self.cancelled_signal.emit(self._get_msg("err_cancelled"))
        except FileNotFoundError as e:
            error_msg = self._get_msg("err_pdf_not_found")
            logger.error(f"FileNotFoundError in {self.mode}: {e}")
            self.error_signal.emit(error_msg)
        except PermissionError as e:
            error_msg = self._get_msg("err_file_access_denied", e.filename or "")
            logger.error(f"PermissionError in {self.mode}: {e}")
            self.error_signal.emit(error_msg)
        except fitz.FileDataError as e:
            error_msg = self._get_msg("err_pdf_corrupted")
            logger.error(f"PDF FileDataError in {self.mode}: {e}")
            self.error_signal.emit(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error in {self.mode}: {e}", exc_info=True)
            self.error_signal.emit(self._get_msg("err_operation_failed", str(e)))

    def batch(self):
        """일괄 처리"""
        files = [path for path in _as_list(self.kwargs.get('files')) if isinstance(path, str)]
        output_dir = _as_str(self.kwargs.get('output_dir'))
        operation = _as_str(self.kwargs.get('operation'))
        option = _as_str(self.kwargs.get('option'))
        failed_files = []

        success_count = 0
        skipped_count = 0
        for idx, file_path in enumerate(files):
            self._check_cancelled()  # 취소 체크포인트
            doc = None
            try:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}_processed.pdf")

                doc = fitz.open(file_path)

                if operation == "compress":
                    self._atomic_pdf_save(doc, out_path, garbage=4, deflate=True)
                elif operation == "watermark" and option:
                    for page in doc:
                        # v4.5.3: insert_text는 align/45도 rotate를 지원하지 않음
                        text_rect = fitz.Rect(
                            40,
                            (page.rect.height / 2) - 30,
                            page.rect.width - 40,
                            (page.rect.height / 2) + 30,
                        )
                        page.insert_textbox(
                            text_rect,
                            option,
                            fontsize=40,
                            fontname="helv",
                            color=(0.5, 0.5, 0.5),
                            fill_opacity=0.3,
                            align=1,
                        )
                    self._atomic_pdf_save(doc, out_path)
                elif operation == "encrypt" and option:
                    perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
                    self._atomic_pdf_save(
                        doc,
                        out_path,
                        encryption=FITZ_PDF_ENCRYPT_AES_256,
                        owner_pw=option,
                        user_pw=option,
                        permissions=perm,
                    )
                elif operation == "rotate":
                    for page in doc:
                        page.set_rotation(page.rotation + 90)
                    self._atomic_pdf_save(doc, out_path)
                else:
                    self._atomic_pdf_save(doc, out_path)
                success_count += 1
            except CancelledError:
                raise  # 취소는 상위로 전파
            except Exception as e:
                logger.warning(f"Batch error on {file_path}: {e}")
                failed_files.append((os.path.basename(file_path), str(e)))
                skipped_count += 1
            finally:
                if doc:
                    doc.close()

            self._emit_progress_if_due(int((idx + 1) / len(files) * 100))

        result_msg = f"✅ 일괄 처리 완료!\n{success_count}/{len(files)}개 파일 처리됨"
        if skipped_count > 0:
            result_msg += f"\n⚠️ {skipped_count}개 파일 건너뜀"
            if failed_files:
                result_msg += "\n실패 파일:"
                for name, reason in failed_files[:3]:
                    result_msg += f"\n- {name}: {reason}"
                if len(failed_files) > 3:
                    result_msg += f"\n- 외 {len(failed_files) - 3}개"
        self.finished_signal.emit(result_msg)

    def get_pdf_info(self):
        """PDF 정보 및 통계 추출"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        doc = None

        # 기본 정보
        total_chars = 0
        total_images = 0
        fonts_used = set()
        page_count = 0
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            for i in range(page_count):
                page = doc[i]
                # 텍스트 통계
                text = page.get_text()
                total_chars += len(text)

                # 이미지 수
                images = page.get_images()
                total_images += len(images)

                # 폰트 목록
                for font in page.get_fonts():
                    fonts_used.add(font[3] if len(font) > 3 else font[0])

                self._emit_progress_if_due(int((i + 1) / max(1, page_count) * 100))

            # 결과 저장
            meta = cast(dict[str, Any], doc.metadata or {})
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# PDF 정보: {os.path.basename(file_path)}\n\n")
                f.write(f"## 기본 정보\n")
                f.write(f"- 페이지 수: {page_count}\n")
                f.write(f"- 파일 크기: {os.path.getsize(file_path) / 1024:.1f} KB\n")
                f.write(f"- 제목: {meta.get('title', '-')}\n")
                f.write(f"- 작성자: {meta.get('author', '-')}\n")
                f.write(f"- 생성일: {meta.get('creationDate', '-')}\n\n")
                f.write(f"## 통계\n")
                f.write(f"- 총 글자 수: {total_chars:,}\n")
                f.write(f"- 총 이미지 수: {total_images}\n")
                f.write(f"- 사용 폰트: {', '.join(fonts_used) if fonts_used else '없음'}\n")
        finally:
            if doc:
                doc.close()

        self.finished_signal.emit(f"✅ PDF 정보 추출 완료!\n{page_count}페이지, {total_chars:,}자, {total_images}개 이미지")

    def get_bookmarks(self):
        """PDF 북마크(목차) 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        doc = None
        toc: list[list[Any]] = []
        try:
            doc = fitz.open(file_path)
            toc = cast(list[list[Any]], doc.get_toc() or [])  # [[level, title, page], ...]

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 북마크: {os.path.basename(file_path)}\n\n")
                if toc:
                    for item in toc:
                        level, title, page = item[0], item[1], item[2]
                        indent = "  " * (level - 1)
                        f.write(f"{indent}- [{title}] → 페이지 {page}\n")
                else:
                    f.write("북마크가 없습니다.\n")
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(f"✅ 북마크 추출 완료!\n{len(toc)}개 항목")

    def set_bookmarks(self):
        """PDF 북마크(목차) 설정"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        bookmarks = cast(list[list[Any]], self.kwargs.get('bookmarks') or [])  # [[level, title, page], ...]
        doc = None
        try:
            doc = fitz.open(file_path)
            doc.set_toc(bookmarks)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()

        self._emit_progress_if_due(100)
        self.finished_signal.emit(f"✅ 북마크 설정 완료!\n{len(bookmarks)}개 항목")

    def search_text(self):
        """PDF 내 텍스트 검색"""
        file_path = _as_str(self.kwargs.get('file_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        output_path = _as_str(self.kwargs.get('output_path'))
        results = []
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_instances = page.search_for(search_term)
                if text_instances:
                    results.append({
                        'page': page_num + 1,
                        'count': len(text_instances),
                        'positions': [(r.x0, r.y0) for r in text_instances[:5]]  # 최대 5개 위치
                    })
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # 결과 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 검색 결과: '{search_term}'\n")
                f.write(f"파일: {os.path.basename(file_path)}\n\n")
                if results:
                    total = sum(r['count'] for r in results)
                    f.write(f"총 {total}개 발견 ({len(results)}페이지)\n\n")
                    for r in results:
                        f.write(f"## 페이지 {r['page']}: {r['count']}개\n")
                else:
                    f.write("검색 결과가 없습니다.\n")
        finally:
            if doc:
                doc.close()
        total_found = sum(r['count'] for r in results) if results else 0
        self.finished_signal.emit(f"✅ 검색 완료!\n'{search_term}': {total_found}개 발견")

    def extract_tables(self):
        """PDF에서 테이블 데이터 추출"""
        import csv
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        all_tables = []
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    find_tables = getattr(page, "find_tables", None)
                    tables = _as_list(find_tables() if callable(find_tables) else [])
                    for idx, table in enumerate(tables):
                        table_data = table.extract()
                        all_tables.append({
                            'page': page_num + 1,
                            'table_idx': idx + 1,
                            'data': table_data
                        })
                except Exception as e:
                    logger.error(f"Page {page_num + 1} table extraction error: {e}")
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # CSV로 저장
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for table in all_tables:
                    writer.writerow([f"--- Page {table['page']}, Table {table['table_idx']} ---"])
                    for row in table['data']:
                        cleaned_row = [str(cell) if cell else '' for cell in row]
                        writer.writerow(cleaned_row)
                    writer.writerow([])
        finally:
            if doc:
                doc.close()
        self.finished_signal.emit(f"✅ 테이블 추출 완료!\n{len(all_tables)}개 테이블 발견")

    def decrypt_pdf(self):
        """암호화된 PDF 복호화"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        password = _as_str(self.kwargs.get('password'))
        doc = None
        try:
            doc = fitz.open(file_path)
            # 이미 암호가 풀려있거나 암호화되지 않은 경우 처리
            if doc.is_encrypted:
                if not doc.authenticate(password):
                    raise ValueError(self._get_msg("err_wrong_password"))

            # 암호 없이 저장 (garbage collection & deflate 적용)
            self._atomic_pdf_save(doc, output_path, garbage=4, deflate=True)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_decryption_success"))

    def list_annotations(self):
        """PDF 주석 목록 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        all_annots = []
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                page = doc[page_num]
                annots = page.annots()
                if annots:
                    for annot in annots:
                        annot_info = cast(dict[str, Any], annot.info or {})
                        all_annots.append({
                            'page': page_num + 1,
                            'type': annot.type[1] if annot.type else 'Unknown',
                            'content': annot_info.get('content', ''),
                            'title': annot_info.get('title', ''),
                            'rect': [annot.rect.x0, annot.rect.y0, annot.rect.x1, annot.rect.y1],
                        })
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # 결과 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 주석 목록: {os.path.basename(file_path)}\n\n")
                f.write(f"총 {len(all_annots)}개 주석\n\n")
                for annot in all_annots:
                    f.write(f"## 페이지 {annot['page']} - {annot['type']}\n")
                    if annot['title']:
                        f.write(f"작성자: {annot['title']}\n")
                    if annot['content']:
                        f.write(f"내용: {annot['content']}\n")
                    f.write("\n")
        finally:
            if doc:
                doc.close()
        self.kwargs['result_annotations'] = all_annots
        self.finished_signal.emit(f"✅ 주석 추출 완료!\n{len(all_annots)}개 주석 발견")

    def add_annotation(self):
        """PDF에 주석 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        annot_type = _as_str(self.kwargs.get('annot_type'), 'text')  # text, sticky, freetext
        text = _as_str(self.kwargs.get('text'))
        point = cast(list[float], self.kwargs.get('point') or [100, 100])  # [x, y]
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 300, 150])  # [x0, y0, x1, y1]
        doc = None
        try:
            doc = fitz.open(file_path)
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]
            annot = None
            if annot_type in ('text', 'sticky'):
                annot = page.add_text_annot(fitz.Point(point[0], point[1]), text)
            elif annot_type == 'freetext':
                annot = page.add_freetext_annot(fitz.Rect(rect), text, fontsize=12)
            else:
                self.error_signal.emit(self._get_msg("err_operation_failed", f"unsupported annotation type: {annot_type}"))
                return

            if annot:
                annot.update()

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(f"✅ 주석 추가 완료!\n페이지 {page_num + 1}")

    def remove_annotations(self):
        """PDF에서 모든 주석 제거"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        count = 0
        doc = None
        try:
            doc = fitz.open(file_path)
            for page in doc:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    page.delete_annot(annot)
                    count += 1
                    annot = next_annot

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(f"✅ {count}개 주석 삭제 완료!")

    def add_attachment(self):
        """PDF에 파일 첨부"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        attach_path = _as_str(self.kwargs.get('attach_path'))
        doc = None
        try:
            doc = fitz.open(file_path)

            with open(attach_path, 'rb') as f:
                data = f.read()

            doc.embfile_add(os.path.basename(attach_path), data)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(f"✅ 파일 첨부 완료!\n{os.path.basename(attach_path)}")

    def extract_attachments(self):
        """PDF 첨부 파일 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        doc = None
        count = 0
        used_names = set()
        try:
            os.makedirs(output_dir, exist_ok=True)
            doc = fitz.open(file_path)
            total = doc.embfile_count()

            if total == 0:
                self._emit_progress_if_due(100)
                self.finished_signal.emit("✅ 첨부 파일이 없습니다.")
                return

            for i in range(total):
                info = _as_dict(doc.embfile_info(i))
                data = doc.embfile_get(i)
                raw_name = info.get('name', f'attachment_{i + 1}')
                out_path, _saved_name = self._build_safe_attachment_output_path(output_dir, raw_name, i, used_names)
                with open(out_path, 'wb') as f:
                    f.write(data)
                count += 1
                self._emit_progress_if_due(int((i + 1) / total * 100))
        finally:
            if doc:
                doc.close()
        self.finished_signal.emit(f"✅ {count}개 첨부 파일 추출 완료!")

