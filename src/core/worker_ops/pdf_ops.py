import os
import tempfile
import logging
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz

try:
    from ..constants import (
        COMPRESSION_SETTINGS, PAGE_SIZES, DEFAULT_PAGE_SIZE,
        WATERMARK_DEFAULTS, WATERMARK_TILE_SPACING_X, WATERMARK_TILE_SPACING_Y,
    )
except ImportError:
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

logger = logging.getLogger(__name__)

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


def _as_float(value: Any | None, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _as_bool(value: Any | None, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _as_list(value: Any | None) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class WorkerPdfOpsMixin(WorkerHost):

    def merge(self):
        files = [path for path in _as_list(self.kwargs.get('files')) if isinstance(path, str)]
        output_path = _as_str(self.kwargs.get('output_path'))

        # 입력 유효성 검사
        if not files:
            self.error_signal.emit(self._get_msg("err_no_files_selected"))
            return
        if not output_path:
            self.error_signal.emit(self._get_msg("err_output_path_missing"))
            return

        # 유효한 파일만 필터링
        valid_files = [f for f in files if f and os.path.exists(f)]
        if not valid_files:
            self.error_signal.emit(self._get_msg("err_no_valid_pdf"))
            return

        skipped_count = 0
        doc_merged = fitz.open()
        try:
            for idx, path in enumerate(valid_files):
                self._check_cancelled()  # 취소 체크포인트
                try:
                    doc = fitz.open(path)
                    # v4.4: 암호화 PDF 감지
                    if doc.is_encrypted:
                        logger.warning(f"Encrypted PDF skipped: {path}")
                        skipped_count += 1
                        doc.close()
                        continue
                    doc_merged.insert_pdf(doc)
                    doc.close()
                except Exception as e:
                    logger.warning(f"Skipping {path}: {e}")
                    skipped_count += 1
                self._emit_progress_if_due(int((idx + 1) / len(valid_files) * 100))

            self._atomic_pdf_save(doc_merged, output_path)

            result_msg = f"✅ 병합 완료!\n{len(valid_files) - skipped_count}개 파일 → 1개 PDF"
            if skipped_count > 0:
                result_msg += f"\n⚠️ {skipped_count}개 파일 건너뜀"
            self.finished_signal.emit(result_msg)
        finally:
            doc_merged.close()

    def convert_to_img(self):
        # 다중 파일 지원
        file_paths = [path for path in (_as_list(self.kwargs.get('file_paths')) or [_as_str(self.kwargs.get('file_path'))]) if isinstance(path, str) and path]
        output_dir = _as_str(self.kwargs.get('output_dir'))
        fmt = _as_str(self.kwargs.get('fmt'), 'png')
        dpi = _as_int(self.kwargs.get('dpi'), 200)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        total_files = len(file_paths)
        total_pages_done = 0

        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = None
            try:
                doc = fitz.open(file_path)
                base = os.path.splitext(os.path.basename(file_path))[0]
                for i in range(len(doc)):
                    page = doc[i]
                    self._check_cancelled()  # 취소 체크포인트
                    pix = page.get_pixmap(matrix=mat)
                    save_path = os.path.join(output_dir, f"{base}_p{i+1:03d}.{fmt}")
                    pix.save(save_path)
                    total_pages_done += 1
            finally:
                if doc:
                    doc.close()
            self._emit_progress_if_due(int((file_idx + 1) / total_files * 100))

        self.finished_signal.emit(f"✅ 변환 완료!\n{total_files}개 파일 → {fmt.upper()} 이미지")

    def extract_text(self):
        # 다중 파일 지원
        file_paths = [path for path in (_as_list(self.kwargs.get('file_paths')) or [_as_str(self.kwargs.get('file_path'))]) if isinstance(path, str) and path]
        output_path = _as_str(self.kwargs.get('output_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        include_details = _as_bool(self.kwargs.get('include_details'), False)  # v3.2: 상세 정보 포함 옵션

        total_files = len(file_paths)

        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = None
            try:
                doc = fitz.open(file_path)
                text_chunks = []

                for i in range(len(doc)):
                    page = doc[i]
                    self._check_cancelled()  # 취소 체크포인트
                    text_chunks.append(f"\n--- Page {i+1} ---\n")

                    if include_details:
                        # v3.2: 상세 정보 추출 (폰트, 크기, 색상)
                        text_dict = _as_dict(page.get_text("dict"))
                        blocks = cast(list[dict[str, Any]], text_dict.get("blocks", []))
                        for block in blocks:
                            if block.get("type") == 0:  # 텍스트 블록
                                for line in cast(list[dict[str, Any]], block.get("lines", [])):
                                    for span in cast(list[dict[str, Any]], line.get("spans", [])):
                                        text = span.get("text", "")
                                        font = span.get("font", "unknown")
                                        size = span.get("size", 0)
                                        color = span.get("color", 0)
                                        # RGB로 변환
                                        r = (color >> 16) & 0xFF
                                        g = (color >> 8) & 0xFF
                                        b = color & 0xFF
                                        text_chunks.append(
                                            f"[Font: {font}, Size: {size:.1f}pt, Color: RGB({r},{g},{b})] {text}\n"
                                        )
                    else:
                        text_chunks.append(page.get_text())
            finally:
                if doc:
                    doc.close()

            # 출력 경로 결정
            if output_dir:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}.txt")
            else:
                out_path = output_path

            full_text = "".join(text_chunks)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            self._emit_progress_if_due(int((file_idx + 1) / total_files * 100))

        detail_msg = " (상세 정보 포함)" if include_details else ""
        self.finished_signal.emit(f"✅ 텍스트 추출 완료!{detail_msg}\n{total_files}개 파일")

    def split(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        page_range = _as_str(self.kwargs.get('page_range'))

        doc_src = fitz.open(file_path)
        doc_final = fitz.open()
        try:
            total_pages = len(doc_src)
            # v3.2: 개선된 페이지 파싱 유틸리티 사용
            pages_to_keep = self._parse_page_range(page_range, total_pages)

            # 원본 순서 유지를 위해 입력 문자열 재파싱 또는 set 정렬 사용
            # _parse_page_range는 정렬된 리스트를 반환하므로, 사용자가 입력한 순서가 중요하다면 로직 변경 필요
            # 현재 로직은 단순 추출이므로 정렬된 순서 유지

            if not pages_to_keep:
                raise ValueError(f"유효한 페이지 범위가 아닙니다: {page_range}")

            total_count = max(1, len(pages_to_keep))  # Division by zero 방지
            for idx, p_num in enumerate(pages_to_keep):
                doc_final.insert_pdf(doc_src, from_page=p_num, to_page=p_num)
                self._emit_progress_if_due(int((idx + 1) / total_count * 100))

            base = os.path.splitext(os.path.basename(file_path))[0]
            out = os.path.join(output_dir, f"{base}_extracted.pdf")
            self._atomic_pdf_save(doc_final, out)
            self.finished_signal.emit(f"✅ 추출 완료!\n{len(pages_to_keep)}페이지 추출됨")
        finally:
            doc_src.close()
            doc_final.close()

    def delete_pages(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_range = _as_str(self.kwargs.get('page_range'))
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)

            # v3.2: 개선된 페이지 파싱 유틸리티 사용
            pages_to_delete = self._parse_page_range(page_range, total_pages)

            # 삭제는 뒤에서부터 해야 인덱스가 꼬이지 않음
            pages_to_delete = sorted(pages_to_delete, reverse=True)
            if not pages_to_delete:
                raise ValueError("삭제할 페이지가 없습니다.")
            total_to_delete = len(pages_to_delete)
            for idx, p in enumerate(pages_to_delete):
                self._check_cancelled()  # 취소 체크포인트
                doc.delete_page(p)
                self._emit_progress_if_due(int((idx + 1) / total_to_delete * 90))
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 삭제 완료!\n{len(pages_to_delete)}페이지 삭제됨")
        finally:
            if doc:
                doc.close()

    def rotate(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        angle = _as_int(self.kwargs.get('angle'))

        doc = fitz.open(file_path)
        try:
            total_pages = max(1, len(doc))  # Division by zero 방지
            for i in range(len(doc)):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                page.set_rotation(page.rotation + angle)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 회전 완료!\n{angle}° 회전됨")
        finally:
            doc.close()

    def watermark(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        text = _as_str(self.kwargs.get('text'))
        opacity = _as_float(self.kwargs.get('opacity'), 0.3)
        color = tuple(self.kwargs.get('color', (0.5, 0.5, 0.5)))
        fontsize = _as_int(self.kwargs.get('fontsize'), 40)
        rotation = _as_int(self.kwargs.get('rotation'), 45)
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        position = _as_str(self.kwargs.get('position'), 'center')
        layer = _as_str(self.kwargs.get('layer'), 'foreground')
        scale_percent = _as_int(self.kwargs.get('scale_percent'), 100)

        # v4.5: 입력 검증 강화
        valid_positions = ['center', 'tile', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right']
        if position not in valid_positions:
            logger.warning(f"Invalid watermark position '{position}', defaulting to 'center'")
            position = 'center'

        # opacity 범위 제한
        opacity = max(0.0, min(1.0, opacity))

        actual_fontsize = int(fontsize * scale_percent / 100)

        doc = fitz.open(file_path)
        try:
            # 입력 검증
            if not text:
                self.error_signal.emit("워터마크 텍스트가 없습니다.")
                return

            total_pages = max(1, len(doc))
            margin = 50  # 가장자리 여백

            for i in range(len(doc)):
                page = doc[i]
                self._check_cancelled()
                rect = page.rect

                # v4.5: 모든 위치 옵션 지원
                positions = {
                    'center': (rect.width / 2, rect.height / 2),
                    'top': (rect.width / 2, margin + actual_fontsize),
                    'bottom': (rect.width / 2, rect.height - margin),
                    'top-left': (margin, margin + actual_fontsize),
                    'top-right': (rect.width - margin, margin + actual_fontsize),
                    'bottom-left': (margin, rect.height - margin),
                    'bottom-right': (rect.width - margin, rect.height - margin),
                }

                if layer == 'background':
                    shape = page.new_shape()
                    if position == 'tile':
                        for y in range(0, int(rect.height), 200):
                            for x in range(0, int(rect.width), 300):
                                shape.insert_text(
                                    fitz.Point(x, y), text, fontsize=actual_fontsize,
                                    fontname=fontname, rotate=rotation,
                                    color=color, fill_opacity=opacity
                                )
                    else:
                        x, y = positions.get(position, positions['center'])
                        shape.insert_text(
                            fitz.Point(x, y), text, fontsize=actual_fontsize,
                            fontname=fontname, rotate=rotation,
                            color=color, fill_opacity=opacity
                        )
                    shape.commit(overlay=False)
                else:
                    if position == 'tile':
                        for y in range(0, int(rect.height), 200):
                            for x in range(0, int(rect.width), 300):
                                page.insert_text(
                                    fitz.Point(x, y), text, fontsize=actual_fontsize,
                                    fontname=fontname, rotate=rotation,
                                    color=color, fill_opacity=opacity
                                )
                    else:
                        x, y = positions.get(position, positions['center'])
                        page.insert_text(
                            fitz.Point(x, y), text, fontsize=actual_fontsize,
                            fontname=fontname, rotate=rotation,
                            color=color, fill_opacity=opacity
                        )
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))
            self._atomic_pdf_save(doc, output_path)
            layer_name = "배경" if layer == 'background' else "전경"
            self.finished_signal.emit(f"✅ 워터마크 적용 완료! ({layer_name}, {int(opacity*100)}%)")
        finally:
            doc.close()

    def metadata_update(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        new_meta = _as_dict(self.kwargs.get('metadata'))

        doc = fitz.open(file_path)
        try:
            meta = cast(dict[str, Any], doc.metadata or {})
            for k, v in new_meta.items():
                if v:
                    meta[k] = v
            doc.set_metadata(meta)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 메타데이터 저장 완료!")
        finally:
            doc.close()

    def protect(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        pw = _as_str(self.kwargs.get('password'))
        doc = None
        try:
            if not pw:
                self.error_signal.emit("비밀번호가 설정되지 않았습니다.")
                return

            doc = fitz.open(file_path)
            perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
            self._atomic_pdf_save(
                doc,
                output_path,
                encryption=FITZ_PDF_ENCRYPT_AES_256,
                owner_pw=pw,
                user_pw=pw,
                permissions=perm,
            )
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 암호화 완료!")
        finally:
            if doc:
                doc.close()

    def compress(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        quality = _as_str(self.kwargs.get('quality'), 'high')  # low, medium, high

        # 입력 유효성 검사
        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit("입력 파일이 존재하지 않습니다.")
            return
        if not output_path:
            self.error_signal.emit("출력 경로가 지정되지 않았습니다.")
            return

        original_size = os.path.getsize(file_path)
        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            # v4.5: 진행률 개선 - 페이지 스캔 20%, 저장(실제 압축) 80%
            for page_num in range(total_pages):
                self._check_cancelled()  # 취소 체크포인트
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 20))

            self._emit_progress_if_due(25)  # 저장 시작
            self._atomic_pdf_save(doc, output_path, **COMPRESSION_SETTINGS.get(quality, COMPRESSION_SETTINGS['high']))
            self._emit_progress_if_due(95)  # 저장 완료
        finally:
            doc.close()

        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
        self._emit_progress_if_due(100)
        quality_name = {'low': '최대 압축', 'medium': '중간', 'high': '고품질'}.get(quality, '고품질')
        self.finished_signal.emit(f"✅ 압축 완료! ({quality_name})\n{original_size//1024}KB → {new_size//1024}KB ({ratio:.1f}% 감소)")

    def images_to_pdf(self):
        files = [path for path in _as_list(self.kwargs.get('files')) if isinstance(path, str)]
        output_path = _as_str(self.kwargs.get('output_path'))
        doc = None
        try:
            doc = fitz.open()
            for idx, img_path in enumerate(files):
                self._check_cancelled()  # 취소 체크포인트
                img = fitz.open(img_path)
                try:
                    pdf_bytes = img.convert_to_pdf()
                finally:
                    img.close()
                img_pdf = fitz.open("pdf", pdf_bytes)
                try:
                    doc.insert_pdf(img_pdf)
                finally:
                    img_pdf.close()
                self._emit_progress_if_due(int((idx + 1) / len(files) * 100))
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 이미지 → PDF 변환 완료!\n{len(files)}개 이미지 → 1개 PDF")
        finally:
            if doc:
                doc.close()

    def reorder(self):
        """페이지 순서 변경"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_order = [_as_int(page_num) for page_num in _as_list(self.kwargs.get('page_order'))]

        doc_src = None
        doc_out = None
        try:
            doc_src = fitz.open(file_path)
            doc_out = fitz.open()

            for idx, page_num in enumerate(page_order):
                self._check_cancelled()  # 취소 체크포인트
                doc_out.insert_pdf(doc_src, from_page=page_num, to_page=page_num)
                self._emit_progress_if_due(int((idx + 1) / len(page_order) * 100))

            self._atomic_pdf_save(doc_out, output_path)
            self.finished_signal.emit(f"✅ 페이지 순서 변경 완료!\n{len(page_order)}페이지 재정렬됨")
        finally:
            if doc_out:
                doc_out.close()
            if doc_src:
                doc_src.close()

    def split_by_pages(self):
        """PDF 분할 - 각 페이지를 개별 파일로"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        split_mode = _as_str(self.kwargs.get('split_mode'), 'each')
        ranges = _as_str(self.kwargs.get('ranges'))

        doc = None
        try:
            doc = fitz.open(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            page_count = len(doc)

            if split_mode == 'each':
                for i in range(page_count):
                    self._check_cancelled()  # 취소 체크포인트
                    new_doc = fitz.open()
                    try:
                        new_doc.insert_pdf(doc, from_page=i, to_page=i)
                        out_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.pdf")
                        self._atomic_pdf_save(new_doc, out_path)
                    finally:
                        new_doc.close()
                    self._emit_progress_if_due(int((i + 1) / page_count * 100))
                self.finished_signal.emit(f"✅ PDF 분할 완료!\n{page_count}개 파일 생성됨")
            else:
                count = 0
                range_list = [r.strip() for r in ranges.split(',') if r.strip()]
                if not range_list:
                    self.error_signal.emit("분할할 범위가 지정되지 않았습니다.")
                    return

                total_ranges = len(range_list)
                for part_idx, rng in enumerate(range_list):
                    self._check_cancelled()  # 취소 체크포인트
                    try:
                        if '-' in rng:
                            parts = rng.split('-')
                            if len(parts) != 2:
                                logger.warning(f"잘못된 범위 형식: {rng}")
                                continue
                            start, end = int(parts[0]), int(parts[1])
                        else:
                            start = end = int(rng)

                        # 페이지 범위 유효성 검사
                        if start < 1 or end < 1:
                            logger.warning(f"유효하지 않은 페이지 번호: {rng}")
                            continue
                        if start > page_count or end > page_count:
                            logger.warning(f"페이지 범위 초과: {rng} (전체 {page_count}페이지)")
                            # 범위를 조정하여 계속 진행
                            start = min(start, page_count)
                            end = min(end, page_count)
                        if start > end:
                            start, end = end, start  # 역순이면 swap

                        new_doc = fitz.open()
                        try:
                            new_doc.insert_pdf(doc, from_page=start-1, to_page=end-1)
                            out_path = os.path.join(output_dir, f"{base_name}_part_{part_idx+1}.pdf")
                            self._atomic_pdf_save(new_doc, out_path)
                        finally:
                            new_doc.close()
                        count += 1
                        self._emit_progress_if_due(int((part_idx + 1) / total_ranges * 100))
                    except ValueError as e:
                        logger.warning(f"범위 파싱 오류: {rng} - {e}")
                        continue

                if count == 0:
                    self.error_signal.emit("유효한 페이지 범위가 없습니다.")
                else:
                    self.finished_signal.emit(f"✅ PDF 분할 완료!\n{count}개 파일 생성됨")
        finally:
            if doc:
                doc.close()

    def add_page_numbers(self):
        """페이지 번호 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_str(self.kwargs.get('position'), 'bottom')  # bottom, top, bottom-left, bottom-right, top-left, top-right
        format_str = _as_str(self.kwargs.get('format'), '{n} / {total}')
        fontsize = _as_int(self.kwargs.get('fontsize'), 10)
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        color = self.kwargs.get('color', (0, 0, 0))
        margin = _as_int(self.kwargs.get('margin'), 30)
        start_number = _as_int(self.kwargs.get('start_number'), 1)  # 시작 번호
        skip_first = _as_bool(self.kwargs.get('skip_first'), False)  # 첫 페이지 건너뛰기
        use_roman = _as_bool(self.kwargs.get('use_roman'), False)  # v3.2: 로마 숫자 형식

        def to_roman(num):
            """숫자를 로마 숫자로 변환"""
            val = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                   (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
                   (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
            roman = ''
            for v, r in val:
                while num >= v:
                    roman += r
                    num -= v
            return roman

        doc = fitz.open(file_path)
        try:
            total = len(doc)

            for i in range(total):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                if skip_first and i == 0:
                    continue

                page_num = start_number + i if not skip_first else start_number + i - 1

                # v3.2: 로마 숫자 변환
                if use_roman:
                    num_str = to_roman(page_num)
                    total_str = to_roman(total)
                else:
                    num_str = str(page_num)
                    total_str = str(total)

                text = format_str.replace('{n}', num_str).replace('{total}', total_str)
                rect = page.rect

                # 위치별 텍스트박스 영역 설정
                if position == 'bottom' or position == 'bottom-center':
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1  # center
                elif position == 'top' or position == 'top-center':
                    r = fitz.Rect(0, margin, rect.width, margin + 20)
                    align = 1
                elif position == 'bottom-left':
                    r = fitz.Rect(margin, rect.height - margin - 20, 150, rect.height - margin)
                    align = 0  # left
                elif position == 'bottom-right':
                    r = fitz.Rect(rect.width - 150, rect.height - margin - 20, rect.width - margin, rect.height - margin)
                    align = 2  # right
                elif position == 'top-left':
                    r = fitz.Rect(margin, margin, 150, margin + 20)
                    align = 0
                elif position == 'top-right':
                    r = fitz.Rect(rect.width - 150, margin, rect.width - margin, margin + 20)
                    align = 2
                else:
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1

                page.insert_textbox(r, text, fontsize=fontsize, fontname=fontname, color=color, align=align)
                self._emit_progress_if_due(int((i + 1) / total * 100))

            self._atomic_pdf_save(doc, output_path)
            format_type = "로마 숫자" if use_roman else "아라비아 숫자"
            self.finished_signal.emit(f"✅ 페이지 번호 삽입 완료! ({format_type})\n{total}페이지")
        finally:
            doc.close()

    def insert_blank_page(self):
        """빈 페이지 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_int(self.kwargs.get('position'), 0)

        doc = fitz.open(file_path)
        try:
            width, height = DEFAULT_PAGE_SIZE  # A4
            doc.insert_page(position, width=width, height=height)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 빈 페이지 삽입 완료!\n위치: {position + 1}페이지")
        finally:
            doc.close()

    def replace_page(self):
        """특정 페이지 교체"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        replace_path = _as_str(self.kwargs.get('replace_path'))
        target_page = _as_int(self.kwargs.get('target_page'), 1) - 1
        source_page = _as_int(self.kwargs.get('source_page'), 1) - 1

        doc = fitz.open(file_path)
        replace_doc = fitz.open(replace_path)
        try:
            # 입력 검증
            if target_page < 0 or target_page >= len(doc):
                self.error_signal.emit(f"대상 페이지 번호가 유효하지 않습니다: {target_page + 1}")
                return
            if source_page < 0 or source_page >= len(replace_doc):
                self.error_signal.emit(f"소스 페이지 번호가 유효하지 않습니다: {source_page + 1}")
                return

            doc.delete_page(target_page)
            doc.insert_pdf(replace_doc, from_page=source_page, to_page=source_page, start_at=target_page)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 페이지 교체 완료!")
        finally:
            replace_doc.close()
            doc.close()

    def image_watermark(self):
        """이미지 워터마크"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        image_path = _as_str(self.kwargs.get('image_path'))
        position = _as_str(self.kwargs.get('position'), 'center')
        # v4.5: 크기/투명도 파라미터 지원
        img_width = _as_int(self.kwargs.get('width'), 150)
        img_height = _as_int(self.kwargs.get('height'), 150)
        opacity = _as_float(self.kwargs.get('opacity'), 1.0)  # 0.0 ~ 1.0

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                if position == 'center':
                    x, y = (rect.width - img_width) / 2, (rect.height - img_height) / 2
                elif position == 'top':
                    x, y = (rect.width - img_width) / 2, 20
                elif position == 'bottom':
                    x, y = (rect.width - img_width) / 2, rect.height - img_height - 20
                elif position == 'top-left':
                    x, y = 20, 20
                elif position == 'top-right':
                    x, y = rect.width - img_width - 20, 20
                elif position == 'bottom-left':
                    x, y = 20, rect.height - img_height - 20
                else:  # bottom-right
                    x, y = rect.width - img_width - 20, rect.height - img_height - 20

                img_rect = fitz.Rect(x, y, x + img_width, y + img_height)
                # v4.5: opacity를 alpha로 변환 (0~255)
                alpha = int(opacity * 255) if 0 <= opacity <= 1 else 255
                page.insert_image(img_rect, filename=image_path, overlay=True, alpha=alpha)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            opacity_pct = int(opacity * 100) if 0 <= opacity <= 1 else 100
            self.finished_signal.emit(f"✅ 이미지 워터마크 완료! ({img_width}x{img_height}, {opacity_pct}%)")
        finally:
            doc.close()

    def crop_pdf(self):
        """PDF 자르기"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        margins = _as_dict(self.kwargs.get('margins') or {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                new_rect = fitz.Rect(
                    rect.x0 + margins['left'], rect.y0 + margins['top'],
                    rect.x1 - margins['right'], rect.y1 - margins['bottom']
                )
                page.set_cropbox(new_rect)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ PDF 자르기 완료!")
        finally:
            doc.close()

    def add_stamp(self):
        """PDF 스탬프 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        stamp_text = _as_str(self.kwargs.get('stamp_text'), '기밀')
        position = _as_str(self.kwargs.get('position'), 'top-right')
        color = self.kwargs.get('color', (1, 0, 0))  # 빨강

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                if position == 'top-right':
                    point = fitz.Point(rect.width - 100, 40)
                elif position == 'top-left':
                    point = fitz.Point(30, 40)
                elif position == 'bottom-right':
                    point = fitz.Point(rect.width - 100, rect.height - 30)
                else:
                    point = fitz.Point(30, rect.height - 30)

                # 스탬프 테두리 (좌표 기반 간단 구현)
                stamp_rect = fitz.Rect(point.x - 10, point.y - 20, point.x + 80, point.y + 5)
                page.draw_rect(stamp_rect, color=color, width=2)
                page.insert_text(point, stamp_text, fontsize=14, fontname="helv", color=color)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 스탬프 추가 완료!")
        finally:
            doc.close()

    def extract_links(self):
        """PDF에서 모든 링크 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = fitz.open(file_path)
        all_links = []
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                links = page.get_links()
                for link in links:
                    if 'uri' in link:
                        all_links.append({
                            'page': i + 1,
                            'url': link['uri']
                        })
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))
        finally:
            doc.close()

        # 결과 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {os.path.basename(file_path)} - 링크 목록\n\n")
            for link in all_links:
                f.write(f"Page {link['page']}: {link['url']}\n")

        self.finished_signal.emit(f"✅ 링크 추출 완료!\n{len(all_links)}개 링크 발견")

    def get_form_fields(self):
        """PDF 양식 필드 목록 반환"""
        file_path = _as_str(self.kwargs.get('file_path'))

        doc = fitz.open(file_path)
        fields = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        rect = widget.rect or fitz.Rect(0, 0, 0, 0)
                        fields.append({
                            'page': page_num + 1,
                            'name': widget.field_name or f"field_{len(fields)}",
                            'type': widget.field_type_string,
                            'value': widget.field_value or "",
                            'rect': [rect.x0, rect.y0, rect.x1, rect.y1],
                        })

            # 결과를 kwargs에 저장 (메인 스레드에서 접근)
            self.kwargs['result_fields'] = fields
            self.finished_signal.emit(f"✅ 양식 필드 감지 완료!\n{len(fields)}개 필드 발견")
        finally:
            doc.close()

    def fill_form(self):
        """PDF 양식 필드에 값 채우기"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        field_values = _as_dict(self.kwargs.get('field_values'))

        doc = fitz.open(file_path)
        filled_count = 0

        try:
            for page in doc:
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        field_name = widget.field_name
                        if field_name and field_name in field_values:
                            widget.field_value = field_values[field_name]
                            widget.update()
                            filled_count += 1

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 양식 작성 완료!\n{filled_count}개 필드 채움")
        finally:
            doc.close()

    def compare_pdfs(self):
        """두 PDF 비교"""
        file_path1 = _as_str(self.kwargs.get('file_path1'))
        file_path2 = _as_str(self.kwargs.get('file_path2'))
        output_path = _as_str(self.kwargs.get('output_path'))
        generate_visual_diff = _as_bool(self.kwargs.get('generate_visual_diff'), False)  # v3.2: 시각적 diff PDF 생성

        doc1 = None
        doc2 = None

        try:
            doc1 = fitz.open(file_path1)
            doc2 = fitz.open(file_path2)

            # v4.5: 암호화된 PDF 체크
            if doc1.is_encrypted:
                self.error_signal.emit(f"파일1이 암호화되어 있습니다: {os.path.basename(file_path1)}")
                return
            if doc2.is_encrypted:
                self.error_signal.emit(f"파일2가 암호화되어 있습니다: {os.path.basename(file_path2)}")
                return

            results = []
            diff_pages = []  # v3.2: 차이가 발견된 페이지 정보
            max_pages = max(len(doc1), len(doc2))

            for i in range(max_pages):
                self._check_cancelled()  # v4.5: 취소 체크포인트
                self._emit_progress_if_due(int((i + 1) / max_pages * 100))

                if i >= len(doc1):
                    results.append(f"페이지 {i+1}: 파일1에 없음")
                    continue
                if i >= len(doc2):
                    results.append(f"페이지 {i+1}: 파일2에 없음")
                    continue

                text1 = _as_str(doc1[i].get_text())
                text2 = _as_str(doc2[i].get_text())

                if text1 != text2:
                    # 간단한 차이 분석
                    lines1 = set(text1.split('\n'))
                    lines2 = set(text2.split('\n'))
                    only_in_1 = lines1 - lines2
                    only_in_2 = lines2 - lines1

                    if only_in_1 or only_in_2:
                        results.append(f"페이지 {i+1}: 차이 발견")
                        diff_pages.append(i)
                        if only_in_1:
                            results.append(f"  - 파일1에만: {len(only_in_1)}줄")
                        if only_in_2:
                            results.append(f"  - 파일2에만: {len(only_in_2)}줄")

            # v3.2: 시각적 diff PDF 생성
            visual_diff_path = None
            if generate_visual_diff and diff_pages:
                visual_diff_path = output_path.replace('.txt', '_visual_diff.pdf')
                diff_doc = fitz.open()

                for page_idx in diff_pages:
                    if page_idx < len(doc1):
                        page1 = doc1[page_idx]
                        # 페이지 복사
                        new_page = diff_doc.new_page(width=page1.rect.width, height=page1.rect.height)
                        new_page.show_pdf_page(new_page.rect, doc1, page_idx)

                        # 파일2에서 다른 텍스트 영역 찾아서 하이라이트
                        if page_idx < len(doc2):
                            text1_blocks = page1.get_text("blocks")
                            page2 = doc2[page_idx]
                            text2_blocks_content = set(
                                b[4] for b in page2.get_text("blocks") if b[6] == 0
                            )

                            for block in text1_blocks:
                                if block[6] == 0:  # 텍스트 블록
                                    block_text = block[4]
                                    if block_text not in text2_blocks_content:
                                        # 빨간색 하이라이트 추가
                                        rect = fitz.Rect(block[:4])
                                        new_page.draw_rect(rect, color=(1, 0, 0), width=2)
                                        # 빨간색 반투명 오버레이
                                        shape = new_page.new_shape()
                                        shape.draw_rect(rect)
                                        shape.finish(color=(1, 0, 0), fill=(1, 0.8, 0.8), fill_opacity=0.3)
                                        shape.commit()

                if len(diff_doc) > 0:
                    self._atomic_pdf_save(diff_doc, visual_diff_path)
                diff_doc.close()

            # 결과 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# PDF 비교 결과\n\n")
                f.write(f"파일1: {os.path.basename(file_path1)}\n")
                f.write(f"파일2: {os.path.basename(file_path2)}\n\n")
                if results:
                    for r in results:
                        f.write(r + "\n")
                else:
                    f.write("두 파일의 텍스트 내용이 동일합니다.\n")
                if visual_diff_path:
                    f.write(f"\n📊 시각적 비교 PDF: {os.path.basename(visual_diff_path)}\n")

            diff_count = len([r for r in results if "차이 발견" in r])
            visual_msg = " +시각적 비교 PDF" if visual_diff_path else ""
            self.finished_signal.emit(f"✅ PDF 비교 완료!{visual_msg}\n{diff_count}개 페이지에서 차이 발견")

        finally:
            if doc1:
                doc1.close()
            if doc2:
                doc2.close()

    def duplicate_page(self):
        """페이지 복제"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)  # 0-indexed
        count = _as_int(self.kwargs.get('count'), 1)

        doc = fitz.open(file_path)
        try:
            for i in range(count):
                self._check_cancelled()  # 취소 체크포인트
                doc.fullcopy_page(page_num, page_num + 1 + i)
                self._emit_progress_if_due(int((i + 1) / count * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 페이지 복제 완료!\n{page_num + 1}페이지를 {count}번 복제")
        finally:
            doc.close()

    def reverse_pages(self):
        """페이지 역순 정렬"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = fitz.open(file_path)
        try:
            page_count = len(doc)

            # 단일 페이지 PDF 처리
            if page_count <= 1:
                self._atomic_pdf_save(doc, output_path)
                self._emit_progress_if_due(100)
                self.finished_signal.emit("✅ 역순 정렬 완료!\n1페이지 (변경 없음)")
                return

            # 역순으로 페이지 이동
            for i in range(page_count - 1):
                self._check_cancelled()  # 취소 체크포인트
                doc.move_page(page_count - 1, i)
                self._emit_progress_if_due(int((i + 1) / (page_count - 1) * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 역순 정렬 완료!\n{page_count}페이지")
        finally:
            doc.close()

    def resize_pages(self):
        """페이지 크기 변경"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        target_size = _as_str(self.kwargs.get('target_size'), 'A4')

        target_w, target_h = PAGE_SIZES.get(target_size, DEFAULT_PAGE_SIZE)

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                # 새 크기로 페이지 설정
                page.set_mediabox(fitz.Rect(0, 0, target_w, target_h))
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 페이지 크기 변경 완료!\n{len(doc)}페이지 → {target_size}")
        finally:
            doc.close()

    def extract_images(self):
        """PDF에서 모든 이미지 추출"""
        import json
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        include_info = _as_bool(self.kwargs.get('include_info'), True)  # v3.2: 상세 정보 포함
        deduplicate = _as_bool(self.kwargs.get('deduplicate'), True)  # v3.2: 중복 제거

        doc = fitz.open(file_path)
        image_count = 0
        image_info_list = []  # v3.2: 이미지 정보 목록
        seen_xrefs = set()  # v3.2: 중복 추적

        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                images = page.get_images()
                for img_idx, img in enumerate(images):
                    xref = img[0]

                    # v3.2: 중복 제거
                    if deduplicate and xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        image_path = os.path.join(output_dir, f"page{page_num + 1}_img{img_idx + 1}.{image_ext}")
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)

                        # v3.2: 상세 정보 수집
                        if include_info:
                            info = {
                                "filename": os.path.basename(image_path),
                                "page": page_num + 1,
                                "xref": xref,
                                "width": base_image.get("width", 0),
                                "height": base_image.get("height", 0),
                                "colorspace": str(base_image.get("colorspace", "unknown")),
                                "bpc": base_image.get("bpc", 0),  # bits per component
                                "size_bytes": len(image_bytes),
                                "format": image_ext
                            }
                            image_info_list.append(info)

                        image_count += 1
                    except Exception as e:
                        logger.error(f"Image extraction error on page {page_num + 1}: {e}")

                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # v3.2: 정보 파일 저장
            if include_info and image_info_list:
                info_path = os.path.join(output_dir, "_images_info.json")
                with open(info_path, "w", encoding="utf-8") as f:
                    json.dump(image_info_list, f, indent=2, ensure_ascii=False)

        finally:
            doc.close()
        dedup_msg = " (중복 제거됨)" if deduplicate else ""
        self.finished_signal.emit(f"✅ 이미지 추출 완료!{dedup_msg}\n{image_count}개 이미지 저장됨")

    def insert_signature(self):
        """전자 서명 이미지 삽입"""
        from datetime import datetime
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        signature_path = _as_str(self.kwargs.get('signature_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        position = _as_str(self.kwargs.get('position'), 'bottom_right')
        signer_name = _as_str(self.kwargs.get('signer_name'))  # v3.2: 서명자 이름
        add_timestamp = _as_bool(self.kwargs.get('add_timestamp'), False)  # v3.2: 타임스탬프

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            if total_pages == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            try:
                page_num = int(page_num)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num), str(total_pages)))
                return

            if page_num == -1:
                page_num = total_pages - 1
            elif page_num < 0 or page_num >= total_pages:
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(total_pages)))
                return

            page = doc[page_num]
            page_rect = page.rect

            # 서명 이미지 크기 (가로 150pt)
            sig_width = 150
            sig_height = 50

            # v3.2: 타임스탬프/서명자 텍스트 높이 추가
            text_height = 0
            if signer_name or add_timestamp:
                text_height = 30

            # 위치 계산
            positions = {
                'bottom_right': fitz.Rect(page_rect.width - sig_width - 50, page_rect.height - sig_height - 50 - text_height,
                                          page_rect.width - 50, page_rect.height - 50 - text_height),
                'bottom_left': fitz.Rect(50, page_rect.height - sig_height - 50 - text_height,
                                         50 + sig_width, page_rect.height - 50 - text_height),
                'top_right': fitz.Rect(page_rect.width - sig_width - 50, 50,
                                       page_rect.width - 50, 50 + sig_height),
                'top_left': fitz.Rect(50, 50, 50 + sig_width, 50 + sig_height),
            }

            rect = positions.get(position, positions['bottom_right'])

            # 서명 이미지 삽입
            page.insert_image(rect, filename=signature_path)

            # v3.2: 서명자 이름 및 타임스탬프 추가
            if signer_name or add_timestamp:
                text_parts = []
                if signer_name:
                    text_parts.append(f"서명자: {signer_name}")
                if add_timestamp:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    text_parts.append(f"일시: {now}")

                text_str = " | ".join(text_parts)
                text_rect = fitz.Rect(rect.x0, rect.y1 + 5, rect.x1, rect.y1 + 25)
                page.insert_textbox(text_rect, text_str, fontsize=8, fontname="helv", 
                                   color=(0.3, 0.3, 0.3), align=1)

            # v3.2: 메타데이터에 서명 정보 기록
            if signer_name:
                meta = cast(dict[str, Any], doc.metadata or {})
                existing_keywords = meta.get('keywords', '') or ''
                new_keywords = f"{existing_keywords}; Signed by: {signer_name}" if existing_keywords else f"Signed by: {signer_name}"
                meta['keywords'] = new_keywords
                doc.set_metadata(meta)

            self._emit_progress_if_due(100)

            self._atomic_pdf_save(doc, output_path)
            extra_info = ""
            if signer_name:
                extra_info += f" (서명자: {signer_name})"
            if add_timestamp:
                extra_info += " +타임스탬프"
            self.finished_signal.emit(f"✅ 전자 서명 삽입 완료!{extra_info}\n{page_num + 1}페이지")
        finally:
            doc.close()

    def highlight_text(self):
        """PDF 내 텍스트 하이라이트"""
        file_path = _as_str(self.kwargs.get('file_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        output_path = _as_str(self.kwargs.get('output_path'))
        color = self.kwargs.get('color', (1, 1, 0))  # 기본 노란색

        doc = fitz.open(file_path)
        highlight_count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=color)
                    highlight.update()
                    highlight_count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 하이라이트 완료!\n'{search_term}': {highlight_count}개 표시")
        finally:
            doc.close()

    def draw_shapes(self):
        """PDF에 도형 그리기"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        shapes = cast(list[dict[str, Any]], self.kwargs.get('shapes') or [])  # [{type, params, color, width}]

        doc = fitz.open(file_path)
        try:
            if not shapes:
                self.error_signal.emit("도형 데이터가 없습니다.")
                return
            # v4.5: 페이지 번호 유효성 검사
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(f"페이지 번호 오류: {page_num + 1} (전체 {len(doc)}페이지)")
                return

            page = doc[page_num]

            for shape_info in shapes:
                shape_type = shape_info.get('type', 'line')
                color = tuple(shape_info.get('color', [1, 0, 0]))
                # v4.5: 색상 값 범위 제한
                color = tuple(max(0.0, min(1.0, c)) for c in color)
                width = shape_info.get('width', 1)
                fill = shape_info.get('fill')
                if fill:
                    fill = tuple(max(0.0, min(1.0, c)) for c in fill)

                if shape_type == 'line':
                    p1 = fitz.Point(shape_info['p1'][0], shape_info['p1'][1])
                    p2 = fitz.Point(shape_info['p2'][0], shape_info['p2'][1])
                    page.draw_line(p1, p2, color=color, width=width)
                elif shape_type == 'rect':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_rect(rect, color=color, width=width, fill=fill)
                elif shape_type == 'circle':
                    center = fitz.Point(shape_info['center'][0], shape_info['center'][1])
                    radius = shape_info.get('radius', 50)
                    page.draw_circle(center, radius, color=color, width=width, fill=fill)
                elif shape_type == 'oval':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_oval(rect, color=color, width=width, fill=fill)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ {len(shapes)}개 도형 추가 완료!")
        finally:
            doc.close()

    def add_link(self):
        """PDF에 하이퍼링크 추가"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        link_type = _as_str(self.kwargs.get('link_type'), 'uri')  # uri, goto
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 200, 120])  # [x0, y0, x1, y1]
        target = self.kwargs.get('target')  # URL 또는 페이지 번호

        # v4.5: link_type 유효성 검사
        valid_link_types = ['uri', 'goto']
        if link_type not in valid_link_types:
            logger.warning(f"Invalid link_type '{link_type}', defaulting to 'uri'")
            link_type = 'uri'

        # v4.5: target 유효성 검사
        if target is None or (isinstance(target, str) and not target.strip()):
            self.error_signal.emit("링크 대상이 지정되지 않았습니다.")
            return

        doc = fitz.open(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(f"페이지 번호 오류: {page_num + 1}")
                return

            page = doc[page_num]

            link = {
                'kind': fitz.LINK_URI if link_type == 'uri' else fitz.LINK_GOTO,
                'from': fitz.Rect(rect),
            }

            if link_type == 'uri':
                target_str = str(target).strip()
                # v4.5: URL 형식 기본 검증
                if not (
                    target_str.startswith('http://') or
                    target_str.startswith('https://') or
                    target_str.startswith('mailto:')
                ):
                    logger.warning(f"URL might be invalid: {target_str}")
                link['uri'] = target_str
            else:
                try:
                    raw_target = int(target)
                    # v4.5.3: goto 대상은 0-based 인덱스만 허용 (UI에서 사전 정규화)
                    target_page = raw_target
                    if target_page < 0 or target_page >= len(doc):
                        self.error_signal.emit(
                            self._get_msg("err_link_target_zero_based", str(target), str(max(0, len(doc) - 1)))
                        )
                        return
                    link['page'] = target_page
                    link['to'] = fitz.Point(0, 0)
                except ValueError:
                    self.error_signal.emit(self._get_msg("err_page_number_numeric", str(target)))
                    return

            page.insert_link(link)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 링크 추가 완료!\n페이지 {page_num + 1}")
        finally:
            doc.close()

    def list_attachments(self):
        """PDF 첨부 파일 목록"""
        file_path = self.kwargs.get('file_path')

        doc = fitz.open(file_path)
        attachments = []

        try:
            count = doc.embfile_count()
            for i in range(count):
                info = doc.embfile_info(i)
                attachments.append({
                    'index': i,
                    'name': info.get('name', 'Unknown'),
                    'size': info.get('size', 0),
                    'created': info.get('creationDate', ''),
                })

            self.kwargs['result_attachments'] = attachments
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 첨부 파일 목록!\n{len(attachments)}개 발견")
        finally:
            doc.close()

    def redact_text(self):
        """PDF에서 텍스트 영구 삭제 (교정)"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        fill_color = self.kwargs.get('fill_color', (0, 0, 0))  # 검정색 기본

        if not search_term:
            self.error_signal.emit("삭제할 텍스트가 입력되지 않았습니다.")
            return

        doc = fitz.open(file_path)
        try:
            redact_count = 0
            total_pages = len(doc)

            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=fill_color)
                    redact_count += 1
                page.apply_redactions()
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ {redact_count}개 영역 교정 완료!")
        finally:
            doc.close()

    def extract_markdown(self):
        """PDF를 Markdown으로 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = fitz.open(file_path)
        markdown_chunks = [f"# {os.path.basename(file_path)}\n\n"]
        total_pages = 0

        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text = _as_str(page.get_text("text"))
                markdown_chunks.append(f"\n---\n\n## Page {page_num + 1}\n\n")
                # 기본 텍스트 변환 (단순 줄바꿈 정리)
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        markdown_chunks.append(line + "\n\n")
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))
        finally:
            doc.close()

        markdown_text = "".join(markdown_chunks)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        self.finished_signal.emit(f"✅ Markdown 추출 완료!\n{total_pages}페이지")

    def copy_page_between_docs(self):
        """다른 PDF에서 페이지 복사"""
        self._normalize_mode_kwargs()
        source_path = _as_str(self.kwargs.get('source_path'))
        target_path = _as_str(self.kwargs.get('target_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        source_pages = self.kwargs.get('source_pages')  # 복사할 페이지 번호들 (0-indexed)
        page_range = self.kwargs.get('page_range', '')
        insert_at = self.kwargs.get('insert_at', -1)  # 삽입 위치 (-1 = 끝)

        source_doc = fitz.open(source_path)
        target_doc = fitz.open(target_path)

        try:
            if source_pages is None:
                if isinstance(page_range, str) and page_range.strip():
                    source_pages = self._parse_page_range(page_range, len(source_doc))
                else:
                    self.error_signal.emit(self._get_msg("err_copy_pages_required"))
                    return
            elif isinstance(source_pages, int):
                source_pages = [source_pages]
            elif isinstance(source_pages, str):
                source_pages = self._parse_page_range(source_pages, len(source_doc))
            elif not isinstance(source_pages, list):
                self.error_signal.emit(self._get_msg("err_invalid_page_range", str(source_pages)))
                return

            if not source_pages:
                input_text = page_range if isinstance(page_range, str) and page_range.strip() else str(source_pages)
                self.error_signal.emit(self._get_msg("err_invalid_page_range", input_text))
                return

            normalized_source_pages = []
            for raw_page in source_pages:
                try:
                    page_num = int(raw_page)
                except (TypeError, ValueError):
                    self.error_signal.emit(self._get_msg("err_page_number_numeric", str(raw_page)))
                    return
                if page_num < 0 or page_num >= len(source_doc):
                    self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num), str(len(source_doc))))
                    return
                normalized_source_pages.append(page_num)
            source_pages = normalized_source_pages

            try:
                insert_pos = int(insert_at)
            except (TypeError, ValueError):
                insert_pos = -1
            if insert_pos < 0:
                insert_pos = len(target_doc)
            insert_pos = min(insert_pos, len(target_doc))

            inserted_count = 0
            total_to_copy = max(1, len(source_pages))

            for i, page_num in enumerate(source_pages):
                self._check_cancelled()  # v4.5: 취소 체크포인트 추가
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num, start_at=insert_pos + inserted_count)
                inserted_count += 1
                self._emit_progress_if_due(int((i + 1) / total_to_copy * 100))

            self._atomic_pdf_save(target_doc, output_path)
            self.finished_signal.emit(f"✅ {inserted_count}페이지 복사 완료!")
        finally:
            source_doc.close()
            target_doc.close()

    def add_background(self):
        """PDF 페이지에 배경색 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        color = self.kwargs.get('color', [1, 1, 0.9])  # 연한 노란색 기본

        # v4.5: 색상 값 범위 검증 (0.0-1.0)
        if isinstance(color, (list, tuple)):
            color = tuple(max(0.0, min(1.0, c)) for c in color)
        else:
            logger.warning(f"Invalid color format, using default")
            color = (1, 1, 0.9)

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(color=color, fill=color)
                shape.commit(overlay=False)  # 배경으로 삽입
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 배경색 추가 완료!\n{len(doc)}페이지")
        finally:
            doc.close()

    def add_text_markup(self):
        """검색어에 밑줄 또는 취소선 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        markup_type = _as_str(self.kwargs.get('markup_type'), 'underline')  # underline, strikeout, squiggly
        valid_markup_types = {'underline', 'strikeout', 'squiggly'}

        if markup_type not in valid_markup_types:
            self.error_signal.emit(self._get_msg("err_invalid_markup_type", str(markup_type)))
            return

        doc = fitz.open(file_path)
        count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                instances = page.search_for(search_term)
                for inst in instances:
                    annot = None
                    if markup_type == 'underline':
                        annot = page.add_underline_annot(inst)
                    elif markup_type == 'strikeout':
                        annot = page.add_strikeout_annot(inst)
                    elif markup_type == 'squiggly':
                        annot = page.add_squiggly_annot(inst)
                    if annot:
                        annot.update()
                    count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            markup_name = {'underline': '밑줄', 'strikeout': '취소선', 'squiggly': '물결선'}.get(markup_type, markup_type)
            self.finished_signal.emit(f"✅ {markup_name} 추가 완료!\n'{search_term}': {count}개")
        finally:
            doc.close()

    def insert_textbox(self):
        """PDF에 텍스트 상자 삽입"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 300, 150])  # [x0, y0, x1, y1]
        text = _as_str(self.kwargs.get('text'))
        fontsize = _as_int(self.kwargs.get('fontsize'), 12)
        color = tuple(self.kwargs.get('color', [0, 0, 0]))
        align = _as_int(self.kwargs.get('align'), 0)  # 0=left, 1=center, 2=right

        doc = fitz.open(file_path)
        try:
            # 유효성 검사 추가
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(f"페이지 번호 오류: {page_num + 1}")
                return

            page = doc[page_num]

            page.insert_textbox(fitz.Rect(rect), text, fontsize=fontsize, 
                               fontname="helv", color=color, align=align)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 텍스트 상자 삽입 완료!\n페이지 {page_num + 1}")
        finally:
            doc.close()

    def add_sticky_note(self):
        """PDF에 스티키 노트(텍스트 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        x = _as_int(self.kwargs.get('x'), 100)  # 노트 위치 X
        y = _as_int(self.kwargs.get('y'), 100)  # 노트 위치 Y
        content = _as_str(self.kwargs.get('content'))  # 노트 내용
        title = _as_str(self.kwargs.get('title'), '메모')  # 노트 제목
        icon = _as_str(self.kwargs.get('icon'), 'Note')  # Note, Comment, Key, Help, Insert, Paragraph

        doc = fitz.open(file_path)
        try:
            if page_num >= len(doc):
                page_num = len(doc) - 1

            page = doc[page_num]
            point = fitz.Point(x, y)

            # 스티키 노트 주석 추가
            annot = page.add_text_annot(point, content, icon=icon)
            if annot:
                annot.set_info(title=title, content=content)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 스티키 노트 추가 완료!\n페이지 {page_num + 1}, 아이콘: {icon}")
        finally:
            doc.close()

    def add_ink_annotation(self):
        """PDF에 프리핸드 드로잉(잉크 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        points = cast(list[list[float]], self.kwargs.get('points') or [])  # [[x1,y1], [x2,y2], ...] 좌표 목록
        color = self.kwargs.get('color', (0, 0, 1))  # 기본 파란색
        width = _as_int(self.kwargs.get('width'), 2)  # 선 두께

        doc = fitz.open(file_path)
        try:
            if page_num >= len(doc):
                page_num = len(doc) - 1

            page = doc[page_num]

            if points and len(points) >= 2:
                # 포인트를 fitz.Point 객체 리스트로 변환
                fitz_points = [fitz.Point(p[0], p[1]) for p in points]

                # 잉크 주석 추가 (자유형 선)
                annot = page.add_ink_annot([fitz_points])
                if annot:
                    annot.set_colors(stroke=color)
                    annot.set_border(width=width)
                    annot.update()

                self._emit_progress_if_due(100)
                self._atomic_pdf_save(doc, output_path)
                self.finished_signal.emit(f"✅ 프리핸드 드로잉 추가 완료!\n페이지 {page_num + 1}, {len(points)}개 포인트")
            else:
                self.error_signal.emit("좌표 포인트가 2개 이상 필요합니다.")
        finally:
            doc.close()

    def add_freehand_signature(self):
        """PDF에 프리핸드 서명 (여러 획) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        strokes = cast(list[list[list[float]]], self.kwargs.get('strokes') or [])  # [[[x1,y1], [x2,y2]], [[x3,y3], [x4,y4]]] 다중 획
        color = self.kwargs.get('color', (0, 0, 0))  # 기본 검정
        width = _as_int(self.kwargs.get('width'), 2)

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            if total_pages == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            try:
                page_num = int(page_num)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num), str(total_pages)))
                return

            if page_num == -1:
                page_num = total_pages - 1
            elif page_num < 0 or page_num >= total_pages:
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(total_pages)))
                return

            page = doc[page_num]

            if not strokes:
                self.error_signal.emit("드로잉 데이터가 없습니다.")
                return

            # 각 획을 fitz.Point 리스트로 변환
            all_strokes = []
            for stroke in strokes:
                fitz_stroke = [fitz.Point(p[0], p[1]) for p in stroke if len(p) >= 2]
                if len(fitz_stroke) >= 2:
                    all_strokes.append(fitz_stroke)

            if not all_strokes:
                self.error_signal.emit("유효한 획이 없습니다.")
                return

            annot = page.add_ink_annot(all_strokes)
            if annot:
                annot.set_colors(stroke=color)
                annot.set_border(width=width)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(f"✅ 프리핸드 서명 추가 완료!\n페이지 {page_num + 1}, {len(all_strokes)}개 획")
        finally:
            doc.close()

