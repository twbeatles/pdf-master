# PDF Master - Claude AI 가이드

> 이 문서는 PDF Master 프로젝트를 Claude AI가 이해하고 효과적으로 지원할 수 있도록 작성된 가이드입니다.

---

## Current Behavior Notes

- PyMuPDF deep-util pass (v4.5.6): `compress` can downsample/re-encode images and subset fonts (`compact`/`web`); cleanup package (`cleanup_ops` facade) covers blank/dedupe pages, bookmark split, auto TOC, sanitize, and N-up; crop supports `content` mode; `redact_area`, `flatten_form`, encrypt `permissions`, compare `visual`/`both`, and `convert_to_svg` are registered Worker modes with Advanced/Security UI.
- SOLID split (2026-07-21): large worker domains live under `worker_ops/{annotation,extract,cleanup,page,transform,compare}/` with thin `*_ops.py` facades; settings/constants/undo use `_*-impl` packages; progress UI under `ui/progress/`.
- 2026-07-22 PROJECT_AUDIT follow-up: `src/core/temp_cleanup.py` sweeps `pdf_master_ai_*` / `.pdf_master_*` orphans on startup/shutdown/cancel/force-terminate; thumbnail loader signals use sender guard; AI `retry_with_backoff` sleeps in slices and does not retry cancel; blank/dedupe/sanitize UI confirm dialogs; cancel cleanup uses only `created_output_paths` (no mtime heuristic); `list_annotations` OperationSpec is `output_kind=text`; batch encrypt tip documents default permissions; chat session create is single-flight per cache key.
- The main right-side preview is wired through `src/ui/zoomable_preview.py`, not a plain `QLabel`, so zoom/pan/page navigation and preview print are part of the real runtime path.
- Preview print now renders through the Qt print pipeline; it no longer delegates to `os.startfile(..., "print")` or `lpr`.
- Thumbnail entry points in the AI and rotate flows are preview-synchronized: if they target a different PDF, preview is switched first and encrypted PDFs reuse the preview password session.
- Preview rerendering is resize-aware: splitter moves and panel resizes request a fresh render instead of leaving a stale scaled pixmap.
- `resize_pages` preserves aspect ratio and fit-centers the original page content on the destination paper size.
- Auto-generated outputs for `convert_to_img` and `extract_text` use collision-safe stems (`name`, `name__2`, `name__3`, ...).
- `compare_pdfs` uses sequence-based line diffing and the Advanced tab can optionally generate a visual diff PDF.
- Page-targeted worker modes share a strict page resolver; `-1` last-page sentinel is reserved for signature insertion flows.
- Directory-output cancellations roll back only files tracked in `kwargs["created_output_paths"]`, not the whole output folder; single-file cancel also removes only tracked created outputs (mtime-based delete removed).
- Single-input/single-output mutation modes can save back onto the original path; preview closes that document before the worker starts and restores it after success/fail/cancel.
- The preview search/bookmark side panel is collapsible, `Ctrl+F` opens the search tab and focuses the query field, and same-path restore reuses captured preview view state.
- Preview file watching now tracks both the active PDF and its parent directory so external atomic replace flows can auto-reload after a bounded retry window.
- Preview page setup and print preview are intentionally split: page setup persists layout state, while each print preview dialog uses a fresh `QPrinter`.
- Compression now routes through central save profiles (`fast`, `compact`, `web`) instead of ad-hoc quality flags.
- Markdown extraction now supports `auto/native/text` mode plus front matter, page marker, and asset placeholder toggles.
- AI chat clearing is scoped to the currently selected PDF path and also clears the in-memory SDK chat session for that PDF.
- Output save/folder dialogs reuse `settings["last_output_dir"]` and update it after a successful selection.
- Undo/Redo is snapshot-based: restore `before_backup_path` on undo and `after_backup_path` on redo instead of re-running the worker.
- Updated worker completion/error messages in the AI/batch/annotation/extract flows are keyed through the i18n catalogs.
- Worker preflight now enforces one-of output contracts through `required_any_kwargs` and rejects non-PDF headers through shared validation.
- Frozen/package verification uses `main.py --smoke` and `scripts/package_smoke.ps1`; Gemini File API live testing remains opt-in through environment variables.
- Compatibility facades remain stable after the 2026-05-13 split: `ai_service.py`, `_pdf_impl.py`, `widgets.py`, `thumbnail_grid.py`, `zoomable_preview.py`, `styles.py`, and `tabs_advanced/builders.py` re-export implementations from smaller packages.
- Batch mode rejects unsupported `operation` values and missing `watermark`/`encrypt` options at preflight and handler boundaries instead of silently copying source PDFs.
- `remove_annotations` checks cancellation at each page loop; `search_text` rejects blank `search_term` at preflight and handler boundaries.
- `set_ui_busy` disables tabs, output-folder button, app shortcuts (`_app_shortcuts`), and the File > Open menu action while a worker is running.
- Pending worker requests are stored in `_pending_workers` FIFO queue; `run_worker` waits up to 3s before finalize and defers when the previous thread is still running.
- `global_exception_handler` in `main.py` uses i18n catalog keys for uncaught exception dialogs.

---

## 📌 프로젝트 개요

**PDF Master v4.5.6**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.10+ |
| **UI 프레임워크** | PyQt6 |
| **PDF 처리** | PyMuPDF (fitz) |
| **AI 기능** | Google Gemini API (google-genai) |
| **빌드 도구** | PyInstaller |

---

## 📂 프로젝트 구조

```
pdf-master/
├── main.py
├── .editorconfig
├── pdf_master.spec
├── pyproject.toml
├── pyrightconfig.json
├── requirements-dev.txt
├── scripts/
│   └── package_smoke.ps1
├── typings/
├── README.md
├── README_EN.md
├── CLAUDE.md
├── GEMINI.md
└── src/
    ├── core/
    │   ├── ai/                    # Gemini service client/cache/schema/session/prompt modules
    │   ├── ai_service.py          # compatibility facade
    │   ├── optional_deps.py        # fitz/keyring optional dependency boundary
    │   ├── _typing.py              # worker mixin host contracts
    │   ├── constants.py            # facade → _constants_impl/
    │   ├── _constants_impl/        # 상수 values 패키지
    │   ├── i18n.py                 # TranslationManager facade
    │   ├── i18n_catalogs/          # KO/EN base catalog + facade
    │   ├── pdf_validation.py       # shared PDF size/header validation
    │   ├── settings.py             # facade → _settings_impl/
    │   ├── _settings_impl/         # defaults/normalize/persistence/api_key
    │   ├── undo_manager.py         # facade → _undo_impl/
    │   ├── _undo_impl/             # ActionRecord + UndoManager
    │   ├── worker.py               # QThread facade
    │   ├── worker_runtime/         # 공통 runtime/dispatch/preflight
    │   └── worker_ops/             # 실제 Worker 기능 구현 (도메인 패키지 + facade)
    │       ├── _pdf_impl.py        # compatibility shim
    │       ├── annotation/         # watermark/markup/redaction/signatures …
    │       ├── annotation_ops.py   # thin facade
    │       ├── extract/            # text/bookmarks/attachments/markdown …
    │       ├── extract_ops.py
    │       ├── cleanup/            # blank/dedupe/sanitize/n-up/bookmarks
    │       ├── cleanup_ops.py
    │       ├── page/ + page_ops.py
    │       ├── transform/ + transform_ops.py
    │       ├── compare/ + compare_ops.py
    │       ├── form_ops.py
    │       ├── compose_ops.py
    │       ├── security_ops.py
    │       ├── batch_ops.py
    │       ├── pdf_ops.py          # compatibility shim
    │       └── ai_ops.py
    └── ui/
        ├── _typing.py                   # UI mixin host contracts
        ├── main_window.py
        ├── main_window_config.py
        ├── main_window_tabs_basic.py     # 호환 shim
        ├── main_window_tabs_advanced.py  # 호환 shim
        ├── main_window_tabs_ai.py        # 호환 shim
        ├── main_window_core.py           # 호환 shim
        ├── main_window_preview.py        # 호환 shim
        ├── main_window_worker.py         # run_worker/on_success 등 (Toast monkeypatch 계약)
        ├── main_window_undo.py           # 호환 shim
        ├── tabs_basic/
        ├── tabs_advanced/
        │   └── tab_builders/
        ├── tabs_ai/
        ├── common_widgets/
        ├── preview_widget/
        ├── thumbnail/
        ├── theme/
        ├── window_core/
        ├── window_preview/
        ├── window_worker/
        ├── window_undo/
        ├── progress/                    # overlay + spinner 구현
        ├── progress_overlay.py          # thin facade
        ├── styles.py
        ├── thumbnail_grid.py
        ├── widgets.py
        └── zoomable_preview.py
```

---

## 🔧 핵심 모듈 설명

### 1. `main.py` - 애플리케이션 진입점

```python
# 주요 기능
- setup_logging()        # 로깅 설정 (~/.pdf_master.log)
- global_exception_handler()  # 전역 예외 처리
- main()                 # QApplication 실행
```

- **HiDPI 지원**: `QT_ENABLE_HIGHDPI_SCALING` 환경변수 설정
- **PyInstaller 호환**: `sys._MEIPASS` 경로 처리

---

### 2. `src/core/worker.py` + `src/core/worker_ops/*` - PDF 작업 스레드

`WorkerThread` 클래스는 모든 PDF 작업을 백그라운드에서 처리합니다.
현재 구조는 `worker.py`가 QThread facade를 유지하고, 공통 실행 로직은 `worker_runtime/*`, 실제 작업 구현은 `worker_ops/*`로 분리됩니다.

#### 주요 시그널
```python
progress_signal = pyqtSignal(int)      # 진행률 (0-100)
finished_signal = pyqtSignal(str)      # 완료 메시지
error_signal = pyqtSignal(str)         # 에러 메시지
```

#### 지원 작업 모드 (mode)
| 모드 | 설명 | 메서드 |
|------|------|--------|
| `merge` | PDF 병합 | `merge()` |
| `convert_to_img` | PDF → 이미지 | `convert_to_img()` |
| `extract_text` | 텍스트 추출 | `extract_text()` |
| `split` | PDF 분할 | `split()` |
| `delete_pages` | 페이지 삭제 | `delete_pages()` |
| `rotate` | 페이지 회전 | `rotate()` |
| `watermark` | 텍스트 워터마크 | `watermark()` |
| `protect` | PDF 암호화 | `protect()` |
| `compress` | PDF 압축 | `compress()` |
| `images_to_pdf` | 이미지 → PDF | `images_to_pdf()` |
| `add_page_numbers` | 페이지 번호 삽입 | `add_page_numbers()` |
| `add_stamp` | 스탬프 추가 | `add_stamp()` |
| `ai_summarize` | AI 요약 | `ai_summarize()` |
| `ai_ask_question` | AI PDF 채팅 (v4.5) | `ai_ask_question()` |
| `ai_extract_keywords` | AI 키워드 추출 (v4.5) | `ai_extract_keywords()` |
| `draw_shapes` | 도형 그리기 (v4.5) | `draw_shapes()` |
| `add_link` | 하이퍼링크 추가 (v4.5) | `add_link()` |
| `insert_textbox` | 텍스트 상자 삽입 (v4.5) | `insert_textbox()` |
| `copy_page_between_docs` | 페이지 복사 (v4.5) | `copy_page_between_docs()` |
| `replace_page` | 페이지 교체 (v4.5.3 UI 노출) | `replace_page()` |
| `set_bookmarks` | 북마크 설정 (v4.5.3 UI 노출) | `set_bookmarks()` |
| `add_annotation` | 주석 추가 (v4.5.3 UI 노출) | `add_annotation()` |
| `get_form_fields` | 양식 필드 감지 | `get_form_fields()` |
| `list_attachments` | 첨부 파일 목록 조회 | `list_attachments()` |
| `extract_attachments` | 첨부 파일 추출 | `extract_attachments()` |
| `add_freehand_signature` | 프리핸드 서명 삽입 | `add_freehand_signature()` |
| `split_by_bookmarks` | 북마크 기준 분할 (v4.5.6) | `split_by_bookmarks()` |
| `remove_blank_pages` | 빈 페이지 제거 (v4.5.6) | `remove_blank_pages()` |
| `dedupe_pages` | 중복 페이지 제거 (v4.5.6) | `dedupe_pages()` |
| `auto_bookmarks` | 자동 목차 (v4.5.6) | `auto_bookmarks()` |
| `sanitize_pdf` | 문서 위생 (v4.5.6) | `sanitize_pdf()` |
| `impose_nup` | N-up 임포지션 (v4.5.6) | `impose_nup()` |
| `redact_area` | 영역 교정 (v4.5.6) | `redact_area()` |
| `flatten_form` | 양식 flatten (v4.5.6) | `flatten_form()` |
| `convert_to_svg` | SVG 내보내기 (v4.5.6) | `convert_to_svg()` |

#### v4.5.1 안정화 핵심 (2026-02-19)
- `run()` 시작 시 `_preflight_inputs()`를 통해 입력 파일 존재/크기를 선검증합니다.
- `_normalize_mode_kwargs()`를 통해 UI/Worker 간 kwargs 계약 차이를 런타임에서 정규화합니다.
- 다음 모드는 구/신 kwargs를 양방향으로 수용합니다:
  - `draw_shapes`
  - `add_link`
  - `insert_textbox`
  - `copy_page_between_docs`
  - `image_watermark`

#### v4.5.3 정책 업데이트 (2026-02-26)
- `batch(operation=watermark)`는 `insert_textbox` 기반으로 동작하며 파일별 실패 원인을 완료 메시지에 요약합니다.
- `copy_page_between_docs`는 무효/누락 `page_range`를 더 이상 묵시 폴백하지 않고 `error_signal`로 종료합니다.
- `add_link(link_type=goto)`는 Worker 경계에서 0-based 페이지 인덱스만 허용합니다.
- `extract_attachments`는 첨부 파일명을 정규화하고 출력 경로를 `output_dir` 하위로 강제합니다.
- `get_pdf_info/get_bookmarks/set_bookmarks/search_text/extract_tables/decrypt_pdf/list_annotations/add_annotation/remove_annotations/add_attachment/extract_attachments`는 `fitz.open()` 자원 정리를 `try/finally` 패턴으로 통일합니다.

#### v4.5.5 감사 후속 업데이트 (2026-05-13)
- `OperationSpec.required_any_kwargs`는 `output_path` 또는 `output_dir`처럼 one-of 필수값을 표현합니다.
- PDF/text/directory 출력 mode는 handler 진입 전 출력 계약을 검사하고, `ai_summarize`는 UI 메모리 결과가 가능하므로 `output_path` optional로 유지합니다.
- `src/core/pdf_validation.py`가 PDF 존재/크기/header 검증을 담당하며 UI file widget과 Worker preflight가 같은 함수를 사용합니다.
- `_pdf_impl.py`는 compatibility shim이며 Worker handler는 page/compare/form/extract/annotation/compose/transform domain module에 있습니다. public Worker mode 이름과 import facade는 유지됩니다.

#### 취소 처리
```python
def cancel(self):
    self._cancel_requested = True

def _check_cancelled(self):
    if self._cancel_requested:
        raise CancelledError()
```

---

### 3. `src/core/ai_service.py` + `src/core/ai/*` - Gemini AI 서비스

`src/core/ai_service.py`는 기존 import 경로를 위한 facade입니다. 실제 구현은 `src/core/ai/` 아래의 `client`, `config`, `cache`, `schemas`, `prompts`, `session`, `generation`, `service`, `errors` 모듈로 분리되어 있습니다.

#### 주요 클래스
```python
class AIService:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: int = 30)
    def summarize_pdf(self, pdf_path: str, language: str = "ko", style: str = "concise")
    def ask_about_pdf(self, pdf_path: str, question: str)
    def extract_keywords(self, pdf_path: str, max_keywords: int = 10, language: str = "ko")  # v4.5
    def validate_api_key(self) -> tuple[bool, str]
```

#### SDK 호환성
```python
# SDK: google-genai only
# File API upload + structured output + streaming partial callbacks
# no legacy fallback
```

#### 예외 클래스
- `AIServiceError` - 기본 예외
- `APIKeyError` - API 키 오류
- `APITimeoutError` - 타임아웃
- `APIRateLimitError` - Rate limit 초과

---

### 4. `src/core/settings.py` - 설정 관리

`settings.py`는 public import 호환 facade입니다. 구현은 `src/core/_settings_impl/`
(`config` / `defaults` / `normalize` / `persistence` / `api_key`)에 있습니다.

#### 저장 위치
- 설정 파일: `~/.pdf_master_settings.json`
- API 키: keyring (또는 설정 파일 폴백)

#### 주요 함수
```python
load_settings() -> dict          # 설정 로드
save_settings(settings) -> bool  # 설정 저장
get_api_key() -> str             # API 키 조회 (keyring 우선)
set_api_key(api_key: str) -> bool  # API 키 저장
reset_settings() -> bool         # 설정 초기화
```

#### 기본 설정
```python
DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "auto",
    "recent_files": [],
    "last_output_dir": "",
    "splitter_sizes": None,
    "window_geometry": None,
}
```

- `load_settings()` now normalizes `recent_files`, `chat_histories`, `splitter_sizes`, `theme`, `language`, `window_geometry`, `last_output_dir` on load.
- Stored UI chat history keys use `v2:{mtime_ns}:{normalized_path}` so a replaced PDF at the same path gets a separate conversation history.

### 타입 계약 파일 (v4.5.4)

- `src/core/_typing.py`
  - Worker 믹스인이 기대하는 signal/helper surface를 정의합니다.
  - v4.5.4 validation follow-up: `_resolve_page_index()` / `_record_created_output_path()` 계약이 포함됩니다.
  - v4.5.5 2026-04-27 follow-up: `_atomic_binary_save()` / `_open_pdf_document()` 계약이 포함됩니다.
- `src/core/optional_deps.py`
  - `fitz`, `keyring` optional import를 중앙화하고, 미설치 환경에서는 proxy/fallback으로 import-time 실패를 막습니다.
- `src/ui/_typing.py`
  - UI 믹스인이 접근하는 공통 위젯/헬퍼 surface를 정의합니다.
- 규칙
  - 믹스인에서 새 속성 접근을 추가하면 대응 `_typing.py`도 함께 갱신합니다.
  - 변경 후 `python -m pyright`를 기본 검증으로 실행합니다.
  - `fitz`/`keyring`는 직접 import하지 말고 `src/core/optional_deps.py` 경계를 우선 사용합니다.

---

### 5. `src/core/constants.py` - 상수 정의

```python
# 페이지 크기
PAGE_SIZES = {'A4': (595, 842), 'A3': (842, 1191), ...}

# 이미지 설정
DEFAULT_DPI = 200
THUMBNAIL_SIZE = 150
MAX_RENDER_DIMENSION = 8000

# 워터마크 기본값
WATERMARK_DEFAULTS = {
    'opacity': 0.3,
    'fontsize': 40,
    'rotation': 45,
    ...
}

# AI 서비스
AI_DEFAULT_TIMEOUT = 30
AI_MAX_TEXT_LENGTH = 30000
AI_MAX_RETRIES = 3
```

---

### 6. `src/core/undo_manager.py` - Undo/Redo 관리

```python
class ActionRecord:
    action_type: str      # 작업 유형
    description: str      # 설명
    before_state: dict    # 이전 상태
    after_state: dict     # 이후 상태
    undo_callback: Callable
    redo_callback: Callable

class UndoManager:
    def push(action_type, description, before, after, undo_fn, redo_fn)
    def undo() -> ActionRecord
    def redo() -> ActionRecord
    @property can_undo -> bool
    @property can_redo -> bool
```

- Current UI integration stores `before_backup_path` / `after_backup_path` / `target_path`.
- Undo coverage includes the single-input/single-output mutation set used by `main_window_worker.py`, including `resize_pages`, `insert_signature`, `highlight_text`, `add_sticky_note`, `add_ink_annotation`, `copy_page_between_docs`.

---

### 7. `src/core/i18n.py` - 다국어 지원

- **TranslationManager**: 싱글톤 번역 관리자
- **기능**:
  - `tm.get(key)`: 키 기반 번역 문자열 반환
  - `locale` 자동 감지 (KO/EN, v4.5.1: `getlocale + env fallback`)
  - 언어 설정 관리 (`language` setting)
- **리소스**: `TRANSLATIONS` 딕셔너리는 `i18n_catalogs/*`에서 로드됩니다.

---

### 8. `src/ui/main_window.py` - 메인 윈도우 조립

`PDFMasterApp`는 여러 믹스인으로 분리된 UI/기능 모듈을 조립합니다.

- `main_window.py`: QMainWindow 구성, `__init__`, `closeEvent`
- `main_window_config.py`: `APP_NAME`, `VERSION`, `AI_AVAILABLE` 등 상수
- `main_window_*.py`: 기존 import 경로 호환을 위한 shim
- `tabs_basic`, `tabs_advanced`, `tabs_ai`: 탭별 실제 구현 모듈
- `window_core`, `window_preview`, `window_worker`, `window_undo`: UI 공통/수명주기 실제 구현 모듈

---

### 9. `src/ui/styles.py` - 테마 스타일시트

#### 색상 팔레트
```python
class ThemeColors:
    PRIMARY = "#4f8cff"        # 메인 블루
    SUCCESS = "#10b981"        # 그린
    WARNING = "#f59e0b"        # 옐로우
    DANGER = "#ef4444"         # 레드

    DARK_BG = "#0a0e14"        # 다크 배경
    DARK_CARD = "#141922"      # 다크 카드
    LIGHT_BG = "#f8fafc"       # 라이트 배경
```

#### 스타일시트 변수
- `DARK_STYLESHEET` - 다크 테마 (프리미엄 글래스모피즘)
- `LIGHT_STYLESHEET` - 라이트 테마

#### 버튼 스타일 ID
| ID | 용도 |
|----|------|
| `actionBtn` | 주요 액션 (그린 그라데이션) |
| `secondaryBtn` | 보조 버튼 (아웃라인) |
| `dangerBtn` | 위험 작업 (레드) |
| `iconBtn` | 아이콘 전용 (36x36) |
| `ghostBtn` | 텍스트 전용 (투명) |
| `successBtn` | 성공 (그린) |
| `warningBtn` | 경고 (옐로우) |

---

### 10. `src/ui/widgets.py` - 커스텀 위젯

#### 주요 위젯
```python
class EmptyStateWidget(QWidget):
    """빈 상태 안내 UI"""
    actionClicked = pyqtSignal()

class DropZoneWidget(QWidget):
    """드래그 앤 드롭 영역"""
    fileDropped = pyqtSignal(str)

class FileSelectorWidget(QWidget):
    """파일 선택기 (드롭존 + 버튼 + 최근 파일)"""
    pathChanged = pyqtSignal(str)

class DraggableListWidget(QListWidget):
    """드래그 가능한 리스트"""
    itemsReordered = pyqtSignal(list)

class WheelEventFilter(QObject):
    """스핀박스/콤보박스 휠 스크롤 방지"""
```

#### 유틸 함수
```python
def is_valid_pdf(file_path: str) -> bool:
    """PDF 헤더 검증 (%PDF-)"""
```

---

### 11. `src/ui/progress_overlay.py` - 진행 오버레이

`progress_overlay.py`는 facade이며 구현은 `src/ui/progress/`
(`overlay.py`, `spinner.py`)에 있습니다.

```python
class ProgressOverlayWidget(QWidget):
    cancelled = pyqtSignal()

    def show_progress(title: str, description: str)
    def update_progress(value: int, description: str)
    def hide_progress()
    def set_theme(is_dark: bool)

class LoadingSpinner(QLabel):
    """이모지 기반 로딩 스피너"""
    def start()
    def stop()
```

---

### 12. `src/ui/thumbnail_grid.py` - 썸네일 그리드

```python
class ThumbnailLoaderThread(QThread):
    """백그라운드 썸네일 로딩"""
    thumbnail_ready = pyqtSignal(int, QPixmap)
    loading_complete = pyqtSignal()

class ThumbnailLabel(QFrame):
    """클릭 가능한 썸네일"""
    clicked = pyqtSignal(int)
    clickedWithModifiers = pyqtSignal(int, object)

class ThumbnailGridWidget(QWidget):
    """PDF 페이지 그리드 표시"""
    pageSelected = pyqtSignal(int)
    selectedPagesChanged = pyqtSignal(list)

    def load_pdf(pdf_path: str, password: str | None = None)
    def select_page(index: int)
    def set_active_page(index: int, emit_signal: bool = False)
    def get_selected_pages() -> list[int]
```

- 암호화 PDF 썸네일 로드는 grid 내부에서 별도 프롬프트를 띄우지 않습니다. preview가 먼저 인증한 뒤 `password`를 넘겨 같은 세션 상태를 재사용합니다.
- User-facing strings in `thumbnail_grid.py` are expected to come from `tm.get(...)`; runtime UI hardcoded-string smoke tests scan `src/ui` broadly with a small allowlist.

---

### 13. `src/ui/zoomable_preview.py` - 줌/패닝 미리보기

```python
class ZoomablePreviewWidget(QWidget):
    zoomChanged = pyqtSignal(float)
    pageChanged = pyqtSignal(int)
    printRequested = pyqtSignal()
    pageSetupRequested = pyqtSignal()

    def set_document(document: QPdfDocument | None, path: str = "")
    def capture_view_state() -> dict[str, object]
    def restore_view_state(state: dict[str, object] | None)
    def go_to_page(page_index: int)
```

- `QPdfDocument + QPdfView + QPdfSearchModel + QPdfBookmarkModel + QPdfPageNavigator` wrapper입니다.
- search/bookmark sidebar, print preview, page setup, page/zoom state restore를 위젯이 직접 담당합니다.
- same-path overwrite 복원, 암호 세션 재사용, external rewrite auto-reload는 이 preview 경로와 `window_preview/*` helper들이 함께 책임집니다.
- 예전 pixmap/control-mode 및 `renderRequested` 계약은 제거되었습니다.

---

## 🔐 보안 고려사항

1. **API 키 저장**: `keyring` 라이브러리 우선 사용, 불가 시 설정 파일 폴백
2. **PDF 검증**: `src/core/pdf_validation.py`에서 파일 크기와 헤더(`%PDF-`)를 공용 검증
3. **파일 크기 제한**: `MAX_FILE_SIZE = 2GB` (Worker preflight와 UI file widget이 같은 기준 사용)
4. **입력 검증**: 페이지 범위 문자열 길이 제한 (`MAX_PAGE_RANGE_LENGTH = 1000`)
5. **첨부 추출 경로 보호**: 파일명 정규화 + `output_dir` 하위 경로 강제
6. **링크 인덱스 정책**: Worker `goto` 타겟은 0-based 단일 정책

---

## 🧪 테스트 업데이트 (v4.5.5)

- canonical manifest: `pyproject.toml`
- 검증 환경 준비: `pip install -e .[dev]`
- 호환 shim: `requirements-dev.txt` -> `-e .[dev]`
- `python -m pyright` -> `0 errors`
- `python -m pytest -q` -> repo-local `.pytest_tmp` 사용, 현재 기준 230 collected / 229 passed / 1 opt-in Gemini smoke skipped
- `python -m build`
- `python -m PyInstaller pdf_master.spec --clean`
- `powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1` -> clean `PYTHONPATH` PyInstaller + EXE `--smoke`
- `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` + `GEMINI_API_KEY` -> Gemini File API 실연동 smoke opt-in
- `.gitignore`는 `build/`, `dist/`, `.pytest_tmp/`, `*.egg-info/`, `*.whl` 같은 검증/패키징 산출물을 기본적으로 제외합니다.
- UTF-8/BOM/U+FFFD/mojibake marker 회귀는 `tests/test_encoding_audit.py`가 검사
- `PyMuPDF` 미설치 환경에서는 PDF 엔진 의존 테스트만 skip되고, 나머지 회귀 테스트는 계속 실행

- `tests/test_ai_thumbnail_grid_flow.py`
  - AI 썸네일 grid의 preview 동기화/암호 세션 재사용 검증
- `tests/test_thumbnail_grid_runtime.py`
  - 암호화 PDF grid 로딩/완료 시그널/loader 정리 검증
- `tests/test_preview_print.py`
  - Qt 인쇄 페이지 범위 해석 및 렌더 경로 검증
- `tests/test_ai_service_cache.py`
  - File API fallback 제한, upload cache/chat session reuse, structured JSON parsing, fake SDK 계약, 텍스트 캐시 재사용 검증
- `tests/test_worker_preflight.py`
  - required kwargs/one-of output contract/PDF header 기반 preflight 검증
- `tests/test_i18n_runtime_widgets.py`
  - progress overlay/file widgets English runtime 문자열 검증
- `tests/test_ai_service_gemini_smoke.py`
  - Gemini File API summary/chat/keyword opt-in smoke 검증
- `tests/test_main_smoke.py`
  - `main.py --smoke` 초기화 종료 검증
- `tests/test_worker_structure_budget.py`
  - legacy facade line budget, public import path, Worker legacy alias 회귀 검증
  - SOLID 분할 후 도메인 패키지 심볼 surface 보존 검증
- `tests/test_worker_regression_modes.py`
  - Markdown 옵션 및 batch compress save profile 회귀 검증
- `tests/test_worker_cancel_regression.py`
  - `split`/양식/프리핸드 서명/추출·검색 page loop 취소 체크와 취소 시 출력 파일 미생성 회귀 검증
- `tests/test_worker_undo_modes.py`
  - Undo 대상 모드 확장과 비대상 모드 제외 검증
- `tests/test_output_dialog_state.py`
  - `last_output_dir` 기반 출력 다이얼로그 시작 경로/갱신 검증
- `tests/test_same_path_preview_restore.py`
  - same-path 저장 전 preview 해제 + 저장 후 preview 복원 검증
- `tests/test_undo_backup_flow.py`
  - Undo/Redo 스냅샷 복원 및 backup cleanup 검증
- `tests/test_worker_regression_modes.py`
  - `metadata_update`/`protect`/`decrypt_pdf`/`reorder`/`split_by_pages`/`extract_markdown` 검증
- `tests/test_ai_worker_ui_flow.py`
  - AI 요약/채팅/키워드 성공/실패 UI 흐름 검증
- `tests/test_close_shutdown_flow.py`
  - 종료 시 cooperative cancel/강제 종료 확인 흐름 검증
- `tests/test_worker_param_compat.py`
  - 고급 기능 kwargs 호환성 검증 (도형/링크/텍스트박스/페이지복사/이미지워터마크)
- `tests/test_worker_preflight.py`
  - 실행 전 입력 검증(fail-fast) 검증
- `tests/test_i18n.py`
  - 비권장 `locale.getdefaultlocale()` 미사용 경로 검증

### v4.5.2 추가 테스트 (2026-02-25)
- `tests/test_worker_markup_validation.py`
  - `add_text_markup` 유효/무효 입력 처리 검증
- `tests/test_worker_form_attachment_modes.py`
  - `get_form_fields`/`list_attachments` payload 및 UI 소비 경로 검증
- `tests/test_convert_format_options.py`
  - PDF→이미지 포맷 노출(`png/jpg/webp/bmp/tiff`) 및 프리셋 fallback 검증
- `tests/test_freehand_signature_ui_flow.py`
  - 프리핸드 서명 stroke 파싱/Worker 연결 검증
- `tests/test_ai_key_storage_path.py`
  - keyring 우선/파일 폴백 저장 경로 정책 검증
- `tests/test_page_index_policy.py`
  - UI 1-based 입력 정규화 검증
- `tests/test_i18n_ui_hardcoded_smoke.py`
  - runtime UI 전체 대상 allowlist 기반 하드코딩 문자열 및 i18n 키 누락 스모크 검증

### v4.5.3 추가 테스트 (2026-02-26)
- `tests/test_worker_batch_watermark.py`
  - 배치 워터마크 출력 생성 및 실패 파일 원인 요약 검증
- `tests/test_worker_copy_page_range_strict.py`
  - 페이지 복사 무효 범위 hard-fail 및 정상 범위 회귀 검증
- `tests/test_worker_attachment_extract_security.py`
  - 첨부 추출 파일명 정규화/중복 처리/출력 경로 고정 검증
- `tests/test_worker_resource_management_structure.py`
  - 대상 Worker 메서드의 `try/finally` 구조 검증
- `tests/test_link_index_policy.py`
  - 하이퍼링크 UI 1-based→Worker 0-based 변환 및 Worker strict 검증
- `tests/test_advanced_new_modes_ui_flow.py`
  - `replace_page`/`set_bookmarks`/`add_annotation` UI 액션 흐름 검증
- `tests/test_worker_rotate_selection.py`
  - 선택 페이지 회전과 전체 회전 회귀 검증
- `tests/test_rotate_selection_ui_flow.py`
  - 회전 탭 action payload/경고/미리보기 동기화 검증
- `tests/test_thumbnail_grid_selection.py`
  - 썸네일 `active page` / `selected pages` 분리 및 미리보기 연동 검증
- `tests/test_worker_ink_signature_runtime.py`
  - 잉크/프리핸드 서명 실제 annot 저장 및 마지막 페이지 sentinel 유지 검증
- `tests/test_worker_page_validation.py`
  - sticky note / blank page / duplicate strict page validation 검증
- `tests/test_worker_cancel_cleanup.py`
  - 디렉터리 출력 rollback + same-path/preexisting output 보호 검증
- `tests/test_validation_docs_config.py`
  - README/가이드/spec/감사 문서/검증 설정 정합성 검증
- `tests/_deps.py`
  - PyQt6/PyMuPDF 의존성 체크를 공용 helper로 통합
- 현재 워크트리 기준 `python -m pytest -q`: 230 collected / 229 passed / 1 opt-in Gemini smoke skipped

### v4.5.6 PyMuPDF deep-util tests (2026-07-14)
- `tests/test_worker_deep_compress.py`
  - 이미지 다운샘플 압축 / 프로필 옵션 / 배치 compress 검증
- `tests/test_worker_pymupdf_extras.py`
  - blank/dedupe/bookmark split/auto TOC/sanitize/n-up/crop content/redact area/flatten/SVG/visual compare 검증

### v4.5.6 PROJECT_AUDIT follow-up tests (2026-07-15)
- `tests/test_ai_ops_cancel_and_encrypted.py`
  - AI cancel 재전파, 암호화 PDF passwords unlock, stream cancel_check
- `tests/test_audit_followup_stability.py`
  - blank-page 렌더 실패 유지, visual_error, set_bookmarks 검증, pending queue 상한

### v4.5.6 PROJECT_AUDIT follow-up tests (2026-07-22)
- `tests/test_audit_2026_07_22_followup.py`
  - temp_cleanup age/include_in_progress, retry interruptible cancel, list_annotations text spec,
    cancel cleanup without mtime delete, thumbnail stale-sender guard, chat create locks, i18n confirm keys

### v4.5.5 audit follow-up tests (2026-06-24)
- `tests/test_worker_batch_unknown_operation.py`
  - 배치 미지원 operation silent copy 방지 및 preflight fail-fast 검증
- `tests/test_worker_batch_missing_option.py`
  - 배치 watermark/encrypt option 누락 fail-fast 검증
- `tests/test_worker_remove_annotations_cancel.py`
  - 주석 삭제 page loop 취소 시 출력 미생성 검증
- `tests/test_run_worker_pending_queue.py`
  - `_pending_workers` FIFO 큐 보존 검증
- `tests/test_set_ui_busy_shortcuts.py`
  - busy 중 단축키/파일 열기 메뉴 비활성화 검증
- `tests/test_worker_search_text_empty_term.py`
  - 빈 검색어 Worker/preflight reject 검증
- `tests/test_compare_scanned_pdf_limitation.py`
  - 텍스트-only compare 한계 스냅샷 검증

---

## 🚀 빌드 가이드

```bash
# 빌드 의존성
pip install PyInstaller

# 빌드 실행
python -m PyInstaller pdf_master.spec --clean

# clean env 패키지 smoke
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1

# 결과물
dist/PDF_Master_v4.5.6.exe (~30-40MB)
```

### 경량화 최적화
- 불필요한 PyQt6 모듈 제외 (WebEngine, Multimedia, 3D 등)
- UPX 압축 적용
- PDF to Word 기능 제거 (pdf2docx 의존성 삭제)

---

## 📋 코드 작성 가이드라인

### 1. 스레드 안전성
```python
# 올바른 예: 시그널 사용
self.worker.finished_signal.connect(self.on_success)

# 잘못된 예: 직접 UI 조작
# self.label.setText("완료")  # ❌ 메인 스레드에서만!
```

### 2. 리소스 관리
```python
# PDF 문서는 반드시 닫기
doc = fitz.open(path)
try:
    # 작업 수행
finally:
    doc.close()
```

### 3. 테마 동기화
```python
# 모든 커스텀 위젯에 set_theme() 구현
def set_theme(self, is_dark: bool):
    self._is_dark = is_dark
    self._apply_theme_style()
```

### 4. 진행률 표시
```python
for i, page in enumerate(pages):
    self._check_cancelled()  # 취소 확인
    # 작업 수행
    self.progress_signal.emit(int((i + 1) / len(pages) * 100))
```

---

## ⚠️ 알려진 제한사항

1. **AI 요약**: 최대 30,000자 텍스트 제한
2. **렌더링**: 최대 8000px 해상도 제한
3. **암호화된 PDF**: 일부 작업에서 복호화 필요
4. **대용량 파일**: 2GB 이상 처리 불가

---

## 🔧 디버깅 팁

1. **로그 파일**: `~/.pdf_master.log`
2. **테마 확인**: `self.settings['theme']` 값 확인
3. **작업 상태**: `self.worker.isRunning()` 체크
4. **메모리 누수**: PDF 문서 핸들 닫힘 확인

---

*이 문서는 PDF Master v4.5.6 기준으로 작성되었습니다. (2026-07-22)*

---

## 2026-07-22 PROJECT_AUDIT Follow-up Addendum

- `src/core/temp_cleanup.py`: `pdf_master_ai_*` / `.pdf_master_*` orphan 스윕 (기동·종료·취소·강제 terminate).
- 썸네일: `_is_active_loader_sender`로 ready/progress/complete 잔여 시그널 차단.
- AI: `retry_with_backoff` 분할 sleep + cancel 비재시도; chat session per-key single-flight create lock.
- UI: blank/dedupe/sanitize 확인 다이얼로그; 배치 암호 기본 권한 안내 문구.
- Worker: 취소 롤백 mtime 휴리스틱 제거; `list_annotations` → `output_kind=text`.
- 회귀: `tests/test_audit_2026_07_22_followup.py`.
- 검증: `python -m pyright` 0 errors; `python -m pytest -q` → 230 collected / 229 passed / 1 opt-in Gemini smoke skipped.
- 의도적 미구현(로드맵): OCR, 미리보기 드래그 교정, compare 인터랙티브 리포트, SDK-level AI abort.

## 2026-07-21 SOLID 코드 분할 Addendum

- Worker 대형 도메인: `annotation` / `extract` / `cleanup` / `page` / `transform` / `compare` 패키지 + thin `*_ops.py` facade.
- Core: `settings` → `_settings_impl/`, `constants` → `_constants_impl/`, `undo_manager` → `_undo_impl/`.
- UI: `progress_overlay` → `ui/progress/` facade. preview/thumbnail 위젯 본체는 PyQt 시그널·MRO·pyright 안정성을 위해 단일 파일 유지.
- `main_window_worker.py`의 `run_worker`/`on_success` 등은 ToastWidget·WorkerThread 모듈 monkeypatch 계약 때문에 유지.
- public import 경로·mode 이름·kwargs 계약 불변. 설계: `docs/superpowers/specs/2026-07-21-code-split-solid-design.md`.
- 검증(당시 SOLID 분할 직후): 222 collected / 221 passed / 1 skip. 현재 기준선은 2026-07-22 Addendum.

## 2026-07-15 PROJECT_AUDIT Follow-up Addendum

- AI Worker: `cancel_check` 전 경로 전파, 취소 시 `CancelledError` 재전파로 `finished_signal` 차단.
- 암호화 PDF AI: preview `passwords` 인증 후 임시 비암호화 PDF로 File API/텍스트 추출, 완료 시 임시 파일 삭제.
- `remove_blank_pages`: pixmap 렌더 실패 시 빈 페이지로 간주하지 않음(페이지 유지).
- `compare_pdfs` visual 예외 → `visual_error` status + `visual_error_count` payload/요약 UI.
- `redact_area` UI 확인 다이얼로그; batch watermark/rotate 페이지 cancel; auto_bookmarks 스캔 cancel.
- batch encrypt: `_resolve_permissions` + optional owner/user kwargs; extract 리포트 i18n; pending queue 상한 8.
- 회귀: `tests/test_ai_ops_cancel_and_encrypted.py`, `tests/test_audit_followup_stability.py`.
- 검증 기준선(당시): `python -m pytest -q` → 219 collected / 218 passed / 1 opt-in Gemini smoke skipped.
- 현재 기준선은 2026-07-22 PROJECT_AUDIT Follow-up Addendum 참고.

## 2026-07-14 PyMuPDF Deep-Util Addendum

- `compress` deep path: profile-driven image optimize (`max_dpi`/`jpeg_quality`/`subset_fonts`) plus kwargs override; batch compress reuses the same path.
- `save` with `linear=True` falls back when the installed PyMuPDF build no longer supports linearisation.
- Domain cleanup surface lives under `src/core/worker_ops/cleanup/` with `cleanup_ops.py` facade mixed into `WorkerPdfOpsMixin`.
- Compare supports `compare_mode=text|visual|both` with pixel sampling for scanned/image-only pages.
- OCR remains intentionally out of scope until an optional-extra packaging design is approved.

## 2026-04-21 Stability Addendum

- AI result payloads now include `meta` fields for `source`, `truncated`, `page_focus_limit`, `fallback_pages_total`, `fallback_pages_used`, and `max_text_chars`.
- The AI tab UI now renders warning-capable meta labels for summary/chat/keyword results so fallback text extraction and truncation are visible to the operator.
- `AIService.clear_chat_session()` now clears both the chat session and the cached uploaded Gemini file for the currently selected PDF; LRU eviction and app shutdown also attempt best-effort remote delete.
- Worker-side text outputs now use atomic saves, batch outputs avoid case-insensitive filename collisions, and compare visual diff PDFs now show bidirectional block overlays with a legend.
- Undo snapshot failures are surfaced as "undo unavailable" warnings instead of silent degradation, and API key saves now require explicit consent before plaintext settings-file fallback.
- `pdf_master.spec`, `README.md`, `README_EN.md`, `CLAUDE.md`, and `GEMINI.md` are aligned around `pyproject.toml`, `requirements-dev.txt`, `python -m pyright`, `python -m pytest -q`, `python -m build`, and `python -m PyInstaller pdf_master.spec --clean`.

## 2026-04-27 Worker/AI/Compare Stabilization Addendum

- `split_by_pages` preflight is now aligned to the UI contract and no longer requires unsupported page-count chunking options.
- Stored AI chat histories use `path + mtime_ns` versioned keys; legacy path-only histories migrate once on load.
- AI tab actions are consolidated in `src.ui.tabs_ai.actions`; `actions_meta.py` remains only for compatibility.
- Worker PDF opening supports explicit password args plus `passwords={normalized_path: password}` mapping for preview password reuse.
- `compare_pdfs` now returns structured payload data and the UI presents a summary dialog after completion.
- Worker-side binary outputs now use atomic saves for image/attachment extraction and rollback tracking on cancellation.
- Packaging/docs and `.gitignore` are synced to cover `.pdf_master_*.tmp*` atomic-save temporary files.

## 2026-05-13 Functional Audit Follow-up

- `required_any_kwargs` makes output path/directory requirements explicit at dispatch/preflight time while leaving `ai_summarize` output-file optional.
- `src/core/pdf_validation.py` is the single source for PDF size/header validation used by Worker preflight and UI file widgets.
- Progress overlay and common file widget labels/tooltips are now i18n catalog keys and covered by runtime hardcoded-string smoke tests.
- `main.py --smoke` provides app initialization smoke coverage, and `scripts/package_smoke.ps1` performs clean `PYTHONPATH` PyInstaller build plus EXE smoke.
- `tests/test_ai_service_gemini_smoke.py` is opt-in and exercises Gemini File API summary, chat, and keyword payloads when `GEMINI_API_KEY` is provided.
- Worker handlers now live in domain modules, `AIService` lives under `src/core/ai/*`, and long UI/style/catalog files are split behind compatibility facades; public Worker mode names and import paths are unchanged.

## 2026-05-22 Audit Follow-up Hardening

- `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md` is the current repo-local audit document; docs tests now reject maintained docs that reference missing functional-audit files.
- `get_pdf_info`, `search_text`, `extract_tables`, and `list_annotations` check `_check_cancelled()` at each page-loop start before writing output files.
- `tests/test_worker_cancel_regression.py` covers those four modes and asserts cancelled runs do not leave result files behind.
- `tests/test_ai_service_cache.py` uses fake `google-genai` objects to validate upload cache reuse, generate/stream calls, chat creation/reuse, structured JSON parsing, and upload fallback without credentials.
- `pdf_master.spec`, README/README_EN/CLAUDE/GEMINI/roadmap, and `.gitignore` coverage were rechecked against the current codebase; no `.gitignore` rule change was required.
- Compare visual pixel mode shipped in v4.5.6; richer compare/report UI expansion and OCR engine support remain future product tasks.
