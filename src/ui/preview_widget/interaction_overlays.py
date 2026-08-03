from __future__ import annotations
from __future__ import annotations
import logging
from PyQt6.QtCore import QEvent, QModelIndex, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor
from PyQt6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from ...core.i18n import tm
logger = logging.getLogger(__name__)
from .region_select import (
    RegionSelectOverlay,
    compute_page_display_rect,
    format_rect_coords,
    map_page_points_to_viewport_rect,
    map_viewport_rect_to_page_points,
)
from .queue_overlay import QueueGhostOverlay
from .search import PreviewSearchLineEdit
from .text_placement import TextPlacementOverlay


class PreviewInteractionMixin(object):
    def is_region_select_mode(self) -> bool:
        return bool(self._region_select_mode)

    def set_region_select_mode(self, enabled: bool) -> None:
        """미리보기에서 드래그로 사각형 영역을 고르는 모드."""
        next_enabled = bool(enabled) and self._doc is not None and self._total_pages > 0
        if next_enabled and self._text_placement_mode:
            # 텍스트 배치 모드와 동시 사용 불가
            self.set_text_placement_mode(False)
        if self._region_select_mode == next_enabled and (
            self._region_overlay is None or self._region_overlay.is_active() == next_enabled
        ):
            return
        self._region_select_mode = next_enabled
        if self._region_overlay is not None:
            self._sync_region_overlay_geometry()
            self._region_overlay.set_active(next_enabled)
        self.regionSelectModeChanged.emit(next_enabled)

    def is_text_placement_mode(self) -> bool:
        return bool(self._text_placement_mode)

    def set_text_placement_mode(
        self,
        enabled: bool,
        *,
        text: str = "",
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float = 14.0,
        align: int = 0,
        opacity: float = 1.0,
    ) -> None:
        """미리보기에 텍스트 상자를 표시하고 드래그·리사이즈로 배치를 조정한다."""
        next_enabled = bool(enabled) and self._doc is not None and self._total_pages > 0
        if next_enabled and self._region_select_mode:
            self.set_region_select_mode(False)

        if next_enabled:
            self._text_placement_text = text or self._text_placement_text or " "
            if rect_pts is not None and len(rect_pts) >= 4:
                self._text_placement_pts = (
                    float(rect_pts[0]),
                    float(rect_pts[1]),
                    float(rect_pts[2]),
                    float(rect_pts[3]),
                )
            elif self._text_placement_pts is None:
                self._text_placement_pts = (100.0, 100.0, 300.0, 150.0)
            if color is not None and len(color) >= 3:
                r, g, b = float(color[0]), float(color[1]), float(color[2])
                self._text_placement_color = QColor(
                    int(max(0, min(255, r * 255))),
                    int(max(0, min(255, g * 255))),
                    int(max(0, min(255, b * 255))),
                )
            self._text_placement_fontsize = max(6.0, float(fontsize))
            self._text_placement_align = max(0, min(2, int(align)))
            self._text_placement_opacity = max(0.1, min(1.0, float(opacity)))

        was = self._text_placement_mode
        self._text_placement_mode = next_enabled
        if self._text_placement_overlay is not None:
            self._sync_region_overlay_geometry()
            if next_enabled:
                self._refresh_text_placement_overlay()
                self._text_placement_overlay.set_active(True)
            else:
                self._text_placement_overlay.set_active(False)
        if was != next_enabled:
            self.textPlacementModeChanged.emit(next_enabled)

    def update_text_placement_content(
        self,
        *,
        text: str | None = None,
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float | None = None,
        align: int | None = None,
        opacity: float | None = None,
    ) -> None:
        """배치 모드 중 텍스트/스타일/좌표를 갱신한다."""
        if text is not None:
            self._text_placement_text = text
        if rect_pts is not None and len(rect_pts) >= 4:
            self._text_placement_pts = (
                float(rect_pts[0]),
                float(rect_pts[1]),
                float(rect_pts[2]),
                float(rect_pts[3]),
            )
        if color is not None and len(color) >= 3:
            r, g, b = float(color[0]), float(color[1]), float(color[2])
            self._text_placement_color = QColor(
                int(max(0, min(255, r * 255))),
                int(max(0, min(255, g * 255))),
                int(max(0, min(255, b * 255))),
            )
        if fontsize is not None:
            self._text_placement_fontsize = max(6.0, float(fontsize))
        if align is not None:
            self._text_placement_align = max(0, min(2, int(align)))
        if opacity is not None:
            self._text_placement_opacity = max(0.1, min(1.0, float(opacity)))
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()

    def eventFilter(self, a0, a1):  # type: ignore[no-untyped-def]
        if a1 is not None and a1.type() == QEvent.Type.Resize:
            if a0 is self.pdf_view or a0 is self.pdf_view.viewport():
                self._sync_region_overlay_geometry()
                if self._text_placement_mode:
                    self._refresh_text_placement_overlay()
                if self._queue_ghost_boxes:
                    self._refresh_queue_ghost_overlay()
        return super().eventFilter(a0, a1)

    def set_queue_ghost_boxes(self, boxes: list[dict] | None) -> None:
        """큐 항목 목록(dict: page_num 0-based, rect[4], text)을 고스트로 표시."""
        self._queue_ghost_boxes = list(boxes or [])
        self._sync_region_overlay_geometry()
        self._refresh_queue_ghost_overlay()

    def clear_queue_ghost_boxes(self) -> None:
        self._queue_ghost_boxes = []
        if self._queue_ghost_overlay is not None:
            self._queue_ghost_overlay.clear()

    def _refresh_queue_ghost_overlay(self) -> None:
        if self._queue_ghost_overlay is None:
            return
        if self._doc is None or not self._queue_ghost_boxes:
            self._queue_ghost_overlay.clear()
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            self._queue_ghost_overlay.clear()
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            self._queue_ghost_overlay.clear()
            return
        pw = float(page_size.width())
        ph = float(page_size.height())
        items: list[tuple[QRect, str]] = []
        for idx, box in enumerate(self._queue_ghost_boxes, start=1):
            try:
                pn = int(box.get("page_num", -1))
            except (TypeError, ValueError):
                continue
            if pn != page:
                continue
            rect = box.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) < 4:
                continue
            view_rect = map_page_points_to_viewport_rect(
                float(rect[0]),
                float(rect[1]),
                float(rect[2]),
                float(rect[3]),
                page_display,
                pw,
                ph,
            )
            if view_rect is None:
                continue
            qr = QRect(
                int(round(view_rect.x())),
                int(round(view_rect.y())),
                max(8, int(round(view_rect.width()))),
                max(8, int(round(view_rect.height()))),
            )
            raw = str(box.get("text", "") or "").replace("\n", " ").strip()
            label = f"#{idx} {raw[:24]}" if raw else f"#{idx}"
            items.append((qr, label))
        self._queue_ghost_overlay.set_items(items)

    def _sync_region_overlay_geometry(self) -> None:
        # pdf_view 전체 위에 덮음 (viewport 스크롤 포함 좌표계는 변환 시 보정)
        geo = self.pdf_view.rect()
        if self._region_overlay is not None:
            self._region_overlay.setGeometry(geo)
            if self._region_select_mode:
                self._region_overlay.raise_()
        if self._queue_ghost_overlay is not None:
            self._queue_ghost_overlay.setGeometry(geo)
            if self._queue_ghost_boxes:
                self._queue_ghost_overlay.raise_()
        if self._text_placement_overlay is not None:
            self._text_placement_overlay.setGeometry(geo)
            if self._text_placement_mode:
                self._text_placement_overlay.raise_()

    def _page_display_rect_in_view(self) -> QRectF | None:
        if self._doc is None or self._total_pages <= 0:
            return None
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            logger.debug("pagePointSize failed", exc_info=True)
            return None
        pw = float(page_size.width())
        ph = float(page_size.height())
        if pw <= 0 or ph <= 0:
            return None

        margins = self.pdf_view.documentMargins()
        hbar = self.pdf_view.horizontalScrollBar()
        vbar = self.pdf_view.verticalScrollBar()
        scroll_x = float(hbar.value()) if hbar is not None else 0.0
        scroll_y = float(vbar.value()) if vbar is not None else 0.0
        # 오버레이는 pdf_view 기준 — viewport 원점을 보정
        vp = self.pdf_view.viewport()
        if vp is not None:
            origin = vp.mapTo(self.pdf_view, vp.rect().topLeft())
            viewport = QRectF(origin.x(), origin.y(), vp.width(), vp.height())
        else:
            viewport = QRectF(self.pdf_view.rect())

        return compute_page_display_rect(
            viewport=viewport,
            page_width_pts=pw,
            page_height_pts=ph,
            zoom_factor=float(self.pdf_view.zoomFactor() or 1.0),
            margin_left=float(margins.left()),
            margin_top=float(margins.top()),
            margin_right=float(margins.right()),
            margin_bottom=float(margins.bottom()),
            scroll_x=scroll_x,
            scroll_y=scroll_y,
        )

    def _on_region_selection_finished(self, rect) -> None:
        if self._doc is None or not self._region_select_mode:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            logger.warning("Could not resolve page display rect for region select")
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        selection = QRectF(rect)
        mapped = map_viewport_rect_to_page_points(
            selection,
            page_display,
            float(page_size.width()),
            float(page_size.height()),
        )
        if mapped is None:
            logger.info("Region selection too small or outside page")
            return
        # 선택 완료 후 모드 종료 (한 번 고르면 필드에 반영)
        self.set_region_select_mode(False)
        x0, y0, x1, y1 = mapped
        self.regionSelected.emit(page + 1, x0, y0, x1, y1)

    def _on_region_selection_cancelled(self) -> None:
        self.set_region_select_mode(False)

    def _refresh_text_placement_overlay(self) -> None:
        if self._text_placement_overlay is None or not self._text_placement_mode:
            return
        pts = self._text_placement_pts
        if pts is None:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None or self._doc is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        view_rect = map_page_points_to_viewport_rect(
            pts[0],
            pts[1],
            pts[2],
            pts[3],
            page_display,
            float(page_size.width()),
            float(page_size.height()),
        )
        if view_rect is None:
            return
        zoom = float(self.pdf_view.zoomFactor() or 1.0)
        font_px = max(8, int(round(self._text_placement_fontsize * zoom)))
        # 화면 픽셀 기준 최소 크기 (PDF 포인트 최소와 대략 정합)
        min_h_pts = max(14.0, float(self._text_placement_fontsize) * 1.4 + 4.0)
        min_w_pts = max(40.0, float(self._text_placement_fontsize) * 2.0)
        min_h_px = max(18, int(round(min_h_pts * zoom)))
        min_w_px = max(24, int(round(min_w_pts * zoom)))
        box = QRect(
            int(round(view_rect.x())),
            int(round(view_rect.y())),
            max(min_w_px, int(round(view_rect.width()))),
            max(min_h_px, int(round(view_rect.height()))),
        )
        self._text_placement_overlay.set_content(
            text=self._text_placement_text,
            box=box,
            color=self._text_placement_color,
            font_px=font_px,
            align=self._text_placement_align,
            opacity=self._text_placement_opacity,
            min_w=min_w_px,
            min_h=min_h_px,
        )

    def _on_text_placement_box_moved(self, box: QRect) -> None:
        if self._doc is None or not self._text_placement_mode:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        mapped = map_viewport_rect_to_page_points(
            QRectF(box),
            page_display,
            float(page_size.width()),
            float(page_size.height()),
            min_size_pts=1.0,
        )
        if mapped is None:
            return
        self._text_placement_pts = mapped
        self.textPlacementMoved.emit(page + 1, mapped[0], mapped[1], mapped[2], mapped[3])

    def _on_text_placement_cancelled(self) -> None:
        self.set_text_placement_mode(False)

    def _on_text_placement_text_edited(self, text: str) -> None:
        self._text_placement_text = text or ""
        self.textPlacementTextEdited.emit(self._text_placement_text)
