"""미리보기 중인 PDF를 화면에 보이는 도구의 빈 파일 선택칸에 이어 주는 흐름.

파일을 한 번 열면(메뉴·단축키·최근 파일·다른 도구에서 선택) 지금 보이는 화면의
각 도구가 같은 파일을 바로 쓸 수 있게 한다. 이미 파일이 지정된 선택칸과, 한 도구 안의
두 번째 PDF 선택칸(비교 대상·원본 PDF 등)은 건드리지 않는다.
"""

from __future__ import annotations

import logging
import os

from PyQt6.QtWidgets import QGroupBox

from ...core.path_utils import normalize_path_key
from ..widgets import FileSelectorWidget

logger = logging.getLogger(__name__)


def _owning_group(selector: FileSelectorWidget) -> object:
    parent = selector.parentWidget()
    while parent is not None:
        if isinstance(parent, QGroupBox):
            return parent
        parent = parent.parentWidget()
    return None


def _carry_active_pdf_to_visible_tools(self) -> int:
    """보이는 화면의 빈 '첫 PDF 선택칸'에 현재 미리보기 파일을 채운다. 채운 개수 반환."""
    if getattr(self, "_carrying_active_pdf", False):
        return 0
    path = normalize_path_key(getattr(self, "_current_preview_path", "") or "")
    if not path or not os.path.exists(path):
        return 0

    filled = 0
    seen_groups: set[int] = set()
    self._carrying_active_pdf = True
    try:
        for selector in self.findChildren(FileSelectorWidget):
            if ".pdf" not in selector.extensions or not selector.isVisible():
                continue
            # 도구(그룹)마다 첫 PDF 선택칸만 대상 — 두 번째 칸은 다른 파일을 고르는 자리다.
            group = _owning_group(selector)
            group_key = id(group) if group is not None else id(selector)
            if group_key in seen_groups:
                continue
            seen_groups.add(group_key)
            if selector.get_path():
                continue
            selector.set_path(path)
            selector.pathChanged.emit(path)
            filled += 1
    except Exception:
        logger.debug("Active PDF carry-over failed", exc_info=True)
    finally:
        self._carrying_active_pdf = False
    return filled
