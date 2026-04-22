import csv
import io
import json
import logging
import os
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import _as_dict, _as_int, _as_list, _as_str
from ._pdf_impl import (
    WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin,
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _page_asset_placeholders,
)

logger = logging.getLogger(__name__)


class _WorkerExtractOpsBaseMixin(WorkerHost):
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


class WorkerExtractOpsMixin(_WorkerExtractOpsBaseMixin):
    def extract_text(self):
        file_paths = [
            path
            for path in (_as_list(self.kwargs.get("file_paths")) or [_as_str(self.kwargs.get("file_path"))])
            if isinstance(path, str) and path
        ]
        output_path = _as_str(self.kwargs.get("output_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        include_details = bool(self.kwargs.get("include_details", False))
        total_files = len(file_paths)
        used_output_stems: set[str] = set()

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = None
            try:
                doc = fitz.open(file_path)
                text_chunks: list[str] = []
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    self._check_cancelled()
                    text_chunks.append(f"\n--- Page {page_index + 1} ---\n")
                    if include_details:
                        text_dict = _as_dict(page.get_text("dict"))
                        blocks = cast(list[dict[str, Any]], text_dict.get("blocks", []))
                        for block in blocks:
                            if block.get("type") != 0:
                                continue
                            for line in cast(list[dict[str, Any]], block.get("lines", [])):
                                for span in cast(list[dict[str, Any]], line.get("spans", [])):
                                    text = span.get("text", "")
                                    font = span.get("font", "unknown")
                                    size = span.get("size", 0)
                                    color = span.get("color", 0)
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

            if output_dir:
                base = os.path.splitext(os.path.basename(file_path))[0]
                unique_stem = self._build_unique_output_stem(output_dir, base, ".txt", used_output_stems)
                out_path = os.path.join(output_dir, f"{unique_stem}.txt")
            else:
                out_path = output_path

            self._atomic_text_save(out_path, "".join(text_chunks))
            self._emit_progress_if_due(int((file_idx + 1) / max(1, total_files) * 100))

        self.finished_signal.emit(
            self._get_msg(
                "msg_extract_text_done",
                total_files,
                self._get_msg("msg_extract_text_detail_suffix") if include_details else "",
            )
        )

    def extract_links(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        doc = fitz.open(file_path)
        all_links: list[dict[str, Any]] = []
        try:
            total_pages = max(1, len(doc))
            for page_index in range(len(doc)):
                page = doc[page_index]
                self._check_cancelled()
                for link in page.get_links():
                    if "uri" in link:
                        all_links.append({"page": page_index + 1, "url": link["uri"]})
                self._emit_progress_if_due(int((page_index + 1) / total_pages * 100))
        finally:
            doc.close()

        body = [f"# {os.path.basename(file_path)} - Link List", ""]
        body.extend(f"Page {link['page']}: {link['url']}" for link in all_links)
        self._atomic_text_save(output_path, "\n".join(body).rstrip() + "\n")
        self.finished_signal.emit(f"✅ 링크 추출 완료!\n{len(all_links)}개 링크 발견")

    def get_pdf_info(self):
        total_chars = 0
        total_images = 0
        fonts_used: set[str] = set()
        page_count = 0
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        doc = None
        meta: dict[str, Any] = {}
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
        finally:
            if doc:
                doc.close()

        lines = [
            f"# PDF 정보: {os.path.basename(file_path)}",
            "",
            "## 기본 정보",
            f"- 페이지 수: {page_count}",
            f"- 파일 크기: {os.path.getsize(file_path) / 1024:.1f} KB",
            f"- 제목: {meta.get('title', '-')}",
            f"- 작성자: {meta.get('author', '-')}",
            f"- 생성일: {meta.get('creationDate', '-')}",
            "",
            "## 통계",
            f"- 총 글자 수: {total_chars:,}",
            f"- 총 이미지 수: {total_images}",
            f"- 사용 폰트: {', '.join(sorted(fonts_used)) if fonts_used else '없음'}",
            "",
        ]
        self._atomic_text_save(output_path, "\n".join(lines))
        self.finished_signal.emit(self._get_msg("msg_pdf_info_done", page_count, total_chars, total_images))

    def get_bookmarks(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        toc: list[list[Any]] = []
        doc = None
        try:
            doc = fitz.open(file_path)
            toc = cast(list[list[Any]], doc.get_toc() or [])
        finally:
            if doc:
                doc.close()

        lines = [f"# 북마크: {os.path.basename(file_path)}", ""]
        if toc:
            for item in toc:
                level, title, page = item[0], item[1], item[2]
                indent = "  " * (max(0, int(level) - 1))
                lines.append(f"{indent}- [{title}] -> 페이지 {page}")
        else:
            lines.append("북마크가 없습니다.")
        lines.append("")
        self._atomic_text_save(output_path, "\n".join(lines))
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_bookmarks_extracted", len(toc)))

    def search_text(self):
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
        finally:
            if doc:
                doc.close()

        lines = [f"# 검색 결과: '{search_term}'", f"파일: {os.path.basename(file_path)}", ""]
        if results:
            total_found = sum(result["count"] for result in results)
            lines.extend([f"총 {total_found}개 발견 ({len(results)}페이지)", ""])
            for result in results:
                lines.append(f"## 페이지 {result['page']}: {result['count']}개")
        else:
            lines.append("검색 결과가 없습니다.")
        lines.append("")
        self._atomic_text_save(output_path, "\n".join(lines))
        total_found = sum(r["count"] for r in results) if results else 0
        self.finished_signal.emit(self._get_msg("msg_search_text_done", search_term, total_found))

    def extract_tables(self):
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
                    tables_result = find_tables() if callable(find_tables) else None
                    tables = getattr(tables_result, "tables", tables_result)
                    for idx, table in enumerate(_as_list(tables)):
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
        finally:
            if doc:
                doc.close()

        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        for table in all_tables:
            writer.writerow([f"--- Page {table['page']}, Table {table['table_idx']} ---"])
            for row in table["data"]:
                writer.writerow([str(cell) if cell else "" for cell in row])
            writer.writerow([])
        self._atomic_text_save(output_path, buffer.getvalue(), newline="")
        self.finished_signal.emit(self._get_msg("msg_tables_extracted", len(all_tables)))

    def list_annotations(self):
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
        finally:
            if doc:
                doc.close()

        lines = [f"# 주석 목록: {os.path.basename(file_path)}", "", f"총 {len(all_annots)}개 주석", ""]
        for annot in all_annots:
            lines.append(f"## 페이지 {annot['page']} - {annot['type']}")
            if annot["title"]:
                lines.append(f"작성자: {annot['title']}")
            if annot["content"]:
                lines.append(f"내용: {annot['content']}")
            lines.append("")
        self._atomic_text_save(output_path, "\n".join(lines))
        self.kwargs["result_annotations"] = all_annots
        self._set_result_payload(annotations=all_annots)
        self.finished_signal.emit(self._get_msg("msg_annotations_extracted", len(all_annots)))

    def extract_markdown(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        markdown_mode = _as_str(self.kwargs.get("markdown_mode"), "auto")
        if markdown_mode not in {"auto", "native", "text"}:
            markdown_mode = "auto"
        include_front_matter = bool(self.kwargs.get("include_front_matter", False))
        include_page_markers = bool(self.kwargs.get("include_page_markers", True))
        include_asset_placeholders = bool(self.kwargs.get("include_asset_placeholders", False))

        doc = fitz.open(file_path)
        markdown_chunks: list[str] = []
        total_pages = 0
        try:
            total_pages = len(doc)
            if include_front_matter:
                markdown_chunks.append(_markdown_front_matter(file_path, doc))

            metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
            document_title = _as_str(metadata.get("title")) or os.path.basename(file_path)
            markdown_chunks.append(f"# {document_title}\n\n")

            for page_num in range(total_pages):
                page = doc[page_num]
                self._check_cancelled()
                if page_num > 0:
                    markdown_chunks.append("\n")
                if include_page_markers:
                    markdown_chunks.append(f"---\n\n## Page {page_num + 1}\n\n")
                if include_asset_placeholders:
                    placeholders = _page_asset_placeholders(page)
                    if placeholders:
                        markdown_chunks.append("\n".join(placeholders))
                        markdown_chunks.append("\n\n")

                if markdown_mode == "text":
                    markdown_text = _fallback_markdown_from_text(page)
                else:
                    try:
                        markdown_text = _extract_page_markdown(page, markdown_mode)
                    except RuntimeError as exc:
                        self.error_signal.emit(str(exc))
                        return

                if markdown_text:
                    markdown_chunks.append(markdown_text)
                    markdown_chunks.append("\n\n")
                self._emit_progress_if_due(int((page_num + 1) / max(1, total_pages) * 100))
        finally:
            doc.close()

        self._atomic_text_save(output_path, "".join(markdown_chunks))
        self.finished_signal.emit(f"✅ Markdown 추출 완료!\n{total_pages}페이지")

    def extract_images(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        include_info = bool(self.kwargs.get("include_info", True))
        deduplicate = bool(self.kwargs.get("deduplicate", True))

        doc = fitz.open(file_path)
        image_count = 0
        image_info_list: list[dict[str, Any]] = []
        seen_xrefs: set[int] = set()
        try:
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()
                for img_idx, img in enumerate(page.get_images()):
                    xref = img[0]
                    if deduplicate and xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        image_path = os.path.join(output_dir, f"page{page_num + 1}_img{img_idx + 1}.{image_ext}")
                        image_path_exists = os.path.exists(image_path)
                        with open(image_path, "wb") as handle:
                            handle.write(image_bytes)
                        if not image_path_exists:
                            self._record_created_output_path(image_path)
                        if include_info:
                            image_info_list.append(
                                {
                                    "filename": os.path.basename(image_path),
                                    "page": page_num + 1,
                                    "xref": xref,
                                    "width": base_image.get("width", 0),
                                    "height": base_image.get("height", 0),
                                    "colorspace": str(base_image.get("colorspace", "unknown")),
                                    "bpc": base_image.get("bpc", 0),
                                    "size_bytes": len(image_bytes),
                                    "format": image_ext,
                                }
                            )
                        image_count += 1
                    except Exception as exc:
                        logger.error("Image extraction error on page %s: %s", page_num + 1, exc)
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            if include_info and image_info_list:
                info_path = os.path.join(output_dir, "_images_info.json")
                self._atomic_text_save(
                    info_path,
                    json.dumps(image_info_list, indent=2, ensure_ascii=False) + "\n",
                )
        finally:
            doc.close()

        dedup_msg = " (중복 제거)" if deduplicate else ""
        self.finished_signal.emit(f"✅ 이미지 추출 완료!{dedup_msg}\n{image_count}개 이미지 저장됨")
