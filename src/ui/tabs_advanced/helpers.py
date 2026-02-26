from ...core.i18n import tm


def _normalize_page_input(self, page_value: int, last_page_value: int = 0) -> int:
    """UI 1-based 페이지 입력을 worker 0-based 인덱스로 정규화."""
    return -1 if page_value == last_page_value else page_value - 1

def _parse_freehand_strokes(self, text: str):
    """x1,y1;x2,y2|x3,y3;x4,y4 형식을 strokes 배열로 변환."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError(tm.get("msg_stroke_required"))

    strokes = []
    for chunk in raw.split("|"):
        stroke_points = []
        chunk = chunk.strip()
        if not chunk:
            continue
        for point in chunk.split(";"):
            pair = point.strip()
            if not pair:
                continue
            coords = [c.strip() for c in pair.split(",")]
            if len(coords) != 2:
                raise ValueError(tm.get("msg_invalid_stroke_format"))
            try:
                stroke_points.append([float(coords[0]), float(coords[1])])
            except ValueError as exc:
                raise ValueError(tm.get("msg_invalid_stroke_format")) from exc
        if len(stroke_points) < 2:
            raise ValueError(tm.get("msg_invalid_stroke_no_points"))
        strokes.append(stroke_points)

    if not strokes:
        raise ValueError(tm.get("msg_stroke_required"))
    return strokes

def _parse_bookmark_lines(self, text: str):
    """줄 단위 `level|title|page` 포맷을 북마크 배열로 변환."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError(tm.get("msg_bookmarks_required"))

    bookmarks = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        row = line.strip()
        if not row:
            continue
        parts = [p.strip() for p in row.split("|")]
        if len(parts) != 3:
            raise ValueError(tm.get("msg_invalid_bookmark_line", line_no))
        try:
            level = int(parts[0])
            page = int(parts[2])
        except ValueError as exc:
            raise ValueError(tm.get("msg_invalid_bookmark_line", line_no)) from exc

        title = parts[1]
        if level < 1 or page < 1 or not title:
            raise ValueError(tm.get("msg_invalid_bookmark_line", line_no))
        bookmarks.append([level, title, page])

    if not bookmarks:
        raise ValueError(tm.get("msg_bookmarks_required"))
    return bookmarks
