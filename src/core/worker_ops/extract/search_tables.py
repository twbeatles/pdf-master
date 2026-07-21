from __future__ import annotations
import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast
from ..._typing import WorkerHost
from ...constants import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZES,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ...optional_deps import fitz
from ...worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from .._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)
logger = logging.getLogger(__name__)


class WorkerExtractSearchTablesMixin(WorkerHost):
    def search_text(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        search_term = _as_str(self.kwargs.get("search_term"))
        output_path = _as_str(self.kwargs.get("output_path"))
        if not search_term.strip():
            self.error_signal.emit(self._get_msg("err_search_term_required"))
            return
        results: list[dict[str, Any]] = []
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                self._check_cancelled()
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

        lines = [
            f"# {self._get_msg('extract_search_title', search_term)}",
            f"{self._get_msg('extract_search_file', os.path.basename(file_path))}",
            "",
        ]
        if results:
            total_found = sum(result["count"] for result in results)
            lines.extend(
                [
                    self._get_msg("extract_search_total", total_found, len(results)),
                    "",
                ]
            )
            for result in results:
                lines.append(
                    f"## {self._get_msg('extract_search_page', result['page'], result['count'])}"
                )
        else:
            lines.append(self._get_msg("extract_search_empty"))
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
            doc = self._open_pdf_document(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                self._check_cancelled()
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
