import logging
import os

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_float, _as_int, _as_list, _as_str
from ..worker_runtime.save_profiles import (
    DEFAULT_COMPRESSION_SAVE_PROFILE,
    normalize_save_profile,
    resolve_image_optimize_options,
)
from ._pdf_helpers import optimize_pdf_images, subset_document_fonts, text_needs_cjk
from .security_ops import (
    FITZ_PDF_ENCRYPT_AES_256,
    FITZ_PDF_PERM_ACCESSIBILITY,
    FITZ_PDF_PERM_COPY,
    FITZ_PDF_PERM_PRINT,
    _resolve_permissions,
)

logger = logging.getLogger(__name__)

_BATCH_OPERATIONS = frozenset({"compress", "watermark", "encrypt", "rotate"})
_BATCH_OPERATIONS_REQUIRING_OPTION = frozenset({"watermark", "encrypt"})


class WorkerBatchOpsMixin(WorkerHost):
    def batch(self):
        """일괄 처리"""
        files = [path for path in _as_list(self.kwargs.get("files")) if isinstance(path, str)]
        output_dir = _as_str(self.kwargs.get("output_dir"))
        operation = _as_str(self.kwargs.get("operation"))
        option = _as_str(self.kwargs.get("option"))

        if operation not in _BATCH_OPERATIONS:
            self.error_signal.emit(self._get_msg("err_batch_unsupported_operation", operation))
            return
        if operation in _BATCH_OPERATIONS_REQUIRING_OPTION and not option:
            self.error_signal.emit(self._get_msg("err_batch_option_required", operation))
            return

        failed_files: list[tuple[str, str]] = []
        used_output_stems: set[str] = set()

        success_count = 0
        skipped_count = 0
        for idx, file_path in enumerate(files):
            self._check_cancelled()
            doc = None
            try:
                base = os.path.splitext(os.path.basename(file_path))[0]
                unique_stem = self._build_unique_output_stem(
                    output_dir,
                    f"{base}_processed",
                    ".pdf",
                    used_output_stems,
                )
                out_path = os.path.join(output_dir, f"{unique_stem}.pdf")

                doc = self._open_pdf_document(file_path)

                if operation == "compress":
                    save_profile = normalize_save_profile(
                        self.kwargs.get("save_profile"),
                        default=DEFAULT_COMPRESSION_SAVE_PROFILE,
                    )
                    optimize_opts = resolve_image_optimize_options(
                        save_profile,
                        optimize_images=self.kwargs.get("optimize_images"),
                        subset_fonts=self.kwargs.get("subset_fonts"),
                        max_image_dpi=self.kwargs.get("max_image_dpi"),
                        jpeg_quality=self.kwargs.get("jpeg_quality"),
                        grayscale_images=self.kwargs.get("grayscale_images"),
                    )
                    if optimize_opts.get("optimize_images"):
                        optimize_pdf_images(
                            doc,
                            max_dpi=float(optimize_opts.get("max_dpi") or 150.0),
                            jpeg_quality=int(optimize_opts.get("jpeg_quality") or 75),
                            grayscale=bool(optimize_opts.get("grayscale")),
                            check_cancelled=self._check_cancelled,
                        )
                    if optimize_opts.get("subset_fonts"):
                        self._check_cancelled()
                        subset_document_fonts(doc)
                    self._atomic_pdf_save(
                        doc,
                        out_path,
                        save_profile=save_profile,
                    )
                elif operation == "watermark":
                    # 단일 워터마크/텍스트 상자와 동일 계열: CJK 자동 임베드 + 옵션 kwargs
                    wm_fontsize = max(1, _as_int(self.kwargs.get("fontsize"), 40))
                    wm_opacity = max(0.0, min(1.0, _as_float(self.kwargs.get("opacity"), 0.3)))
                    wm_rotation = _as_int(self.kwargs.get("rotation"), 0) % 360
                    wm_rotation = int(round(wm_rotation / 90.0) * 90) % 360
                    wm_fontname = _as_str(self.kwargs.get("fontname"), "")
                    if not wm_fontname:
                        wm_fontname = "cjk" if text_needs_cjk(option) else "helv"
                    raw_color = self.kwargs.get("color", (0.5, 0.5, 0.5))
                    try:
                        wm_color = tuple(float(c) for c in raw_color[:3])  # type: ignore[index]
                        if len(wm_color) < 3:
                            wm_color = (0.5, 0.5, 0.5)
                    except Exception:
                        wm_color = (0.5, 0.5, 0.5)
                    wrote_any = False
                    for page in doc:
                        self._check_cancelled()
                        text_rect = fitz.Rect(
                            40,
                            (page.rect.height / 2) - max(30.0, float(wm_fontsize)),
                            page.rect.width - 40,
                            (page.rect.height / 2) + max(30.0, float(wm_fontsize) * 1.5),
                        )
                        resolved = self._resolve_textbox_fontname(page, wm_fontname, option)
                        ok = self._write_textbox_content(
                            page,
                            text_rect,
                            option,
                            fontsize=wm_fontsize,
                            fontname=resolved,
                            color=wm_color,
                            align=1,
                            rotation=wm_rotation,
                            opacity=wm_opacity,
                            overlay=True,
                        )
                        if ok:
                            wrote_any = True
                    if not wrote_any:
                        raise ValueError(self._get_msg("err_textbox_insert_failed"))
                    self._atomic_pdf_save(doc, out_path)
                elif operation == "encrypt":
                    # 단일 protect와 동일 권한 해석 (미지정 시 기본 accessibility/print/copy)
                    raw_perm = self.kwargs.get("permissions")
                    if raw_perm is None:
                        perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
                    else:
                        perm = _resolve_permissions(raw_perm)
                    owner_pw = _as_str(self.kwargs.get("owner_password")) or option
                    user_pw = _as_str(self.kwargs.get("user_password")) or option
                    self._atomic_pdf_save(
                        doc,
                        out_path,
                        encryption=FITZ_PDF_ENCRYPT_AES_256,
                        owner_pw=owner_pw,
                        user_pw=user_pw,
                        permissions=perm,
                    )
                elif operation == "rotate":
                    for page in doc:
                        self._check_cancelled()
                        page.set_rotation(page.rotation + 90)
                    self._atomic_pdf_save(doc, out_path)
                success_count += 1
            except Exception as exc:
                from ..worker import CancelledError

                if isinstance(exc, CancelledError):
                    raise
                logger.warning("Batch error on %s: %s", file_path, exc)
                failed_files.append((os.path.basename(file_path), str(exc)))
                skipped_count += 1
            finally:
                if doc:
                    doc.close()

            self._emit_progress_if_due(int((idx + 1) / len(files) * 100))

        result_msg = self._get_msg("msg_batch_done", success_count, len(files))
        if skipped_count > 0:
            result_msg += self._get_msg("msg_batch_skipped", skipped_count)
            if failed_files:
                result_msg += self._get_msg("msg_batch_failed_header")
                for name, reason in failed_files[:3]:
                    result_msg += self._get_msg("msg_batch_failed_row", name, reason)
                if len(failed_files) > 3:
                    result_msg += self._get_msg("msg_batch_failed_more", len(failed_files) - 3)
        self.finished_signal.emit(result_msg)
