import csv
import logging
import os
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_dict, _as_int, _as_list, _as_str
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin

logger = logging.getLogger(__name__)


class WorkerExtractOpsMixin(WorkerHost):
    extract_links = _LegacyWorkerPdfOpsMixin.extract_links
    get_form_fields = _LegacyWorkerPdfOpsMixin.get_form_fields
    fill_form = _LegacyWorkerPdfOpsMixin.fill_form
    list_attachments = _LegacyWorkerPdfOpsMixin.list_attachments
    extract_markdown = _LegacyWorkerPdfOpsMixin.extract_markdown
    extract_images = _LegacyWorkerPdfOpsMixin.extract_images
    extract_text = _LegacyWorkerPdfOpsMixin.extract_text

    def get_pdf_info(self):
        """PDF 정보 및 통계 추출"""
        total_chars = 0
        total_images = 0
        fonts_used: set[str] = set()
        page_count = 0
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        doc = None
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            for i in range(page_count):
                page = doc[i]
                total_chars += len(page.get_text())
                total_images += len(page.get_images())
                for font in page.get_fonts():
                    fonts_used.add(font[3] if len(font) > 3 else font[0])
                self._emit_progress_if_due(int((i + 1) / max(1, page_count) * 100))

            meta = cast(dict[str, Any], doc.metadata or {})
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(f"# PDF 정보: {os.path.basename(file_path)}\n\n")
                handle.write("## 기본 정보\n")
                handle.write(f"- 페이지 수: {page_count}\n")
                handle.write(f"- 파일 크기: {os.path.getsize(file_path) / 1024:.1f} KB\n")
                handle.write(f"- 제목: {meta.get('title', '-')}\n")
                handle.write(f"- 작성자: {meta.get('author', '-')}\n")
                handle.write(f"- 생성일: {meta.get('creationDate', '-')}\n\n")
                handle.write("## 통계\n")
                handle.write(f"- 총 글자 수: {total_chars:,}\n")
                handle.write(f"- 총 이미지 수: {total_images}\n")
                handle.write(f"- 사용 폰트: {', '.join(fonts_used) if fonts_used else '없음'}\n")
        finally:
            if doc:
                doc.close()

        self.finished_signal.emit(
            self._get_msg("msg_pdf_info_done", page_count, total_chars, total_images)
        )

    def get_bookmarks(self):
        """PDF 북마크(목차) 추출"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        doc = None
        toc: list[list[Any]] = []
        try:
            doc = fitz.open(file_path)
            toc = cast(list[list[Any]], doc.get_toc() or [])

            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(f"# 북마크: {os.path.basename(file_path)}\n\n")
                if toc:
                    for item in toc:
                        level, title, page = item[0], item[1], item[2]
                        indent = "  " * (level - 1)
                        handle.write(f"{indent}- [{title}] → 페이지 {page}\n")
                else:
                    handle.write("북마크가 없습니다.\n")
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_bookmarks_extracted", len(toc)))

    def set_bookmarks(self):
        """PDF 북마크(목차) 설정"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        bookmarks = cast(list[list[Any]], self.kwargs.get("bookmarks") or [])
        doc = None
        try:
            doc = fitz.open(file_path)
            doc.set_toc(bookmarks)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()

        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_bookmarks_set", len(bookmarks)))

    def search_text(self):
        """PDF 내 텍스트 검색"""
        file_path = _as_str(self.kwargs.get("file_path"))
        search_term = _as_str(self.kwargs.get("search_term"))
        output_path = _as_str(self.kwargs.get("output_path"))
        results: list[dict[str, Any]] = []
        doc = None
        try:
            doc = fitz.open(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_instances = page.search_for(search_term)
                if text_instances:
                    results.append(
                        {
                            "page": page_num + 1,
                            "count": len(text_instances),
                            "positions": [(r.x0, r.y0) for r in text_instances[:5]],
                        }
                    )
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(f"# 검색 결과: '{search_term}'\n")
                handle.write(f"파일: {os.path.basename(file_path)}\n\n")
                if results:
                    total = sum(r["count"] for r in results)
                    handle.write(f"총 {total}개 발견 ({len(results)}페이지)\n\n")
                    for item in results:
                        handle.write(f"## 페이지 {item['page']}: {item['count']}개\n")
                else:
                    handle.write("검색 결과가 없습니다.\n")
        finally:
            if doc:
                doc.close()
        total_found = sum(r["count"] for r in results) if results else 0
        self.finished_signal.emit(
            self._get_msg("msg_search_text_done", search_term, total_found)
        )

    def extract_tables(self):
        """PDF에서 테이블 데이터 추출"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        all_tables: list[dict[str, Any]] = []
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
                        all_tables.append(
                            {
                                "page": page_num + 1,
                                "table_idx": idx + 1,
                                "data": table.extract(),
                            }
                        )
                except Exception as exc:
                    logger.error("Page %s table extraction error: %s", page_num + 1, exc)
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            with open(output_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                for table in all_tables:
                    writer.writerow([f"--- Page {table['page']}, Table {table['table_idx']} ---"])
                    for row in table["data"]:
                        writer.writerow([str(cell) if cell else "" for cell in row])
                    writer.writerow([])
        finally:
            if doc:
                doc.close()
        self.finished_signal.emit(self._get_msg("msg_tables_extracted", len(all_tables)))

    def list_annotations(self):
        """PDF 주석 목록 추출"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        all_annots: list[dict[str, Any]] = []
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
                        all_annots.append(
                            {
                                "page": page_num + 1,
                                "type": annot.type[1] if annot.type else "Unknown",
                                "content": annot_info.get("content", ""),
                                "title": annot_info.get("title", ""),
                                "rect": [annot.rect.x0, annot.rect.y0, annot.rect.x1, annot.rect.y1],
                            }
                        )
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(f"# 주석 목록: {os.path.basename(file_path)}\n\n")
                handle.write(f"총 {len(all_annots)}개 주석\n\n")
                for annot in all_annots:
                    handle.write(f"## 페이지 {annot['page']} - {annot['type']}\n")
                    if annot["title"]:
                        handle.write(f"작성자: {annot['title']}\n")
                    if annot["content"]:
                        handle.write(f"내용: {annot['content']}\n")
                    handle.write("\n")
        finally:
            if doc:
                doc.close()
        self.kwargs["result_annotations"] = all_annots
        self._set_result_payload(annotations=all_annots)
        self.finished_signal.emit(
            self._get_msg("msg_annotations_extracted", len(all_annots))
        )

    def add_attachment(self):
        """PDF에 파일 첨부"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        attach_path = _as_str(self.kwargs.get("attach_path"))
        doc = None
        try:
            doc = fitz.open(file_path)
            with open(attach_path, "rb") as handle:
                data = handle.read()

            doc.embfile_add(os.path.basename(attach_path), data)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(
            self._get_msg("msg_attachment_added", os.path.basename(attach_path))
        )

    def extract_attachments(self):
        """PDF 첨부 파일 추출"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        doc = None
        count = 0
        used_names: set[str] = set()
        try:
            os.makedirs(output_dir, exist_ok=True)
            doc = fitz.open(file_path)
            total = doc.embfile_count()

            if total == 0:
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_no_attachments_found"))
                return

            for i in range(total):
                info = _as_dict(doc.embfile_info(i))
                data = doc.embfile_get(i)
                raw_name = info.get("name", f"attachment_{i + 1}")
                out_path, _saved_name = self._build_safe_attachment_output_path(output_dir, raw_name, i, used_names)
                out_path_exists = os.path.exists(out_path)
                with open(out_path, "wb") as handle:
                    handle.write(data)
                if not out_path_exists:
                    self._record_created_output_path(out_path)
                count += 1
                self._emit_progress_if_due(int((i + 1) / total * 100))
        finally:
            if doc:
                doc.close()
        self.finished_signal.emit(self._get_msg("msg_attachments_extracted", count))
