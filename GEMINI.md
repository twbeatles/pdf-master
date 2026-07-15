# GEMINI.md — PDF Master v4.5.6 개발 가이드

AI 어시스턴트(Gemini)가 PDF Master 코드베이스를 이해하고 개발을 지원하기 위한 레퍼런스 문서입니다.
현재 동작 기준 메모 및 전체 구현 계약은 `CLAUDE.md`를 참조하세요.

---

## 📋 프로젝트 개요

**PDF Master**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

| 항목 | 내용 |
|------|------|
| **버전** | v4.5.6 |
| **언어** | Python 3.10+ |
| **UI 프레임워크** | PyQt6 6.5+ |
| **PDF 엔진** | PyMuPDF (fitz) |
| **AI 기능** | Google Gemini API (google-genai SDK) |
| **빌드 도구** | PyInstaller |
| **라이선스** | MIT |

### 주요 기능 요약

- PDF 병합 / 분할 / 변환 (이미지·텍스트)
- 페이지 편집 (삭제, 회전, 순서 변경, 복제, 크기 변경)
- 워터마크, 스탬프, 암호화 / 복호화, 압축
- 주석 · 마크업 (하이라이트, 도형, 링크, 서명)
- AI 요약, 채팅, 키워드 추출 (Gemini)
- 다크 / 라이트 테마, Undo / Redo, 다국어(KO/EN)

---

## 🗂️ 디렉토리 구조

```
pdf-master/
├── main.py
├── pdf_master.spec
├── pyproject.toml
├── pyrightconfig.json
├── requirements-dev.txt
├── scripts/
│   └── package_smoke.ps1
├── typings/
└── src/
    ├── core/
    │   ├── ai/                    # Gemini client/cache/schema/session/prompt 구현
    │   ├── ai_service.py          # compatibility facade
    │   ├── optional_deps.py       # fitz/keyring optional import 경계
    │   ├── _typing.py             # Worker 믹스인 host 계약
    │   ├── constants.py
    │   ├── i18n.py                # TranslationManager facade
    │   ├── i18n_catalogs/         # KO/EN base catalog
    │   ├── pdf_validation.py      # PDF size/header 공용 검증
    │   ├── settings.py
    │   ├── undo_manager.py
    │   ├── worker.py              # QThread facade
    │   ├── worker_runtime/        # 공통 runtime/dispatch/preflight
    │   └── worker_ops/            # Worker 기능 domain module 분할
    │       ├── _pdf_impl.py       # compatibility shim
    │       ├── page_ops.py
    │       ├── compare_ops.py
    │       ├── form_ops.py
    │       ├── extract_ops.py
    │       ├── annotation_ops.py
    │       ├── compose_ops.py
    │       ├── transform_ops.py
    │       ├── pdf_ops.py         # compatibility shim
    │       └── ai_ops.py
    └── ui/
        ├── _typing.py
        ├── main_window.py
        ├── main_window_config.py
        ├── main_window_*.py       # 호환 shim 계열
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
        ├── progress_overlay.py
        ├── styles.py
        ├── thumbnail_grid.py
        ├── widgets.py
        └── zoomable_preview.py
```

---

## 🔑 핵심 모듈 상세

### 1. `src/core/worker.py` — WorkerThread

PDF 작업을 백그라운드에서 처리하는 QThread 기반 워커입니다.

**시그널:**
```python
progress_signal = pyqtSignal(int)     # 진행률 (0-100)
finished_signal = pyqtSignal(str)     # 완료 메시지
error_signal = pyqtSignal(str)        # 에러 메시지
```

**작업 모드 (mode 파라미터):**

| 모드 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `merge` | PDF 병합 | `files`, `output_path` |
| `convert_to_img` | PDF → 이미지 | `file_path`, `output_dir`, `fmt`, `dpi` |
| `extract_text` | 텍스트 추출 | `file_path`, `output_path` 또는 `output_dir` |
| `split` | PDF 분할 (범위) | `file_path`, `page_range`, `output_dir` |
| `split_by_pages` | 페이지별 분할 | `file_path`, `output_dir` |
| `delete_pages` | 페이지 삭제 | `file_path`, `page_range`, `output_path` |
| `rotate` | 페이지 회전 | `file_path`, `angle`, `output_path`, `page_indices?` |
| `watermark` | 텍스트 워터마크 | `file_path`, `text`, `output_path` |
| `image_watermark` | 이미지 워터마크 | `file_path`, `image_path`, `output_path` |
| `add_page_numbers` | 페이지 번호 | `file_path`, `position`, `format`, `output_path` |
| `compress` | PDF 압축 (`fast`/`compact`/`web`, 이미지·폰트 최적화) | `file_path`, `save_profile`, `optimize_images?`, `output_path` |
| `protect` | PDF 암호화 | `file_path`, `password`, `permissions?`, `output_path` |
| `split_by_bookmarks` | 북마크 기준 분할 | `file_path`, `output_dir`, `max_level?` |
| `remove_blank_pages` | 빈 페이지 제거 | `file_path`, `output_path` |
| `dedupe_pages` | 중복 페이지 제거 | `file_path`, `output_path` |
| `auto_bookmarks` | 자동 목차 | `file_path`, `output_path` |
| `sanitize_pdf` | 문서 위생 | `file_path`, `output_path` |
| `impose_nup` | N-up | `file_path`, `nup`, `output_path` |
| `redact_area` | 영역 교정 | `file_path`, `rects`, `output_path` |
| `flatten_form` | 양식 flatten | `file_path`, `output_path` |
| `convert_to_svg` | SVG 내보내기 | `file_path`, `output_dir` |
| `compare_pdfs` | 비교 (`text`/`visual`/`both`) | `file_path1`, `file_path2`, `compare_mode?`, `output_path` |
| `images_to_pdf` | 이미지 → PDF | `files`, `output_path` |
| `reorder` | 페이지 순서 변경 | `file_path`, `page_order`, `output_path` |
| `add_stamp` | 스탬프 추가 | `file_path`, `stamp_text`, `position`, `output_path` |
| `ai_summarize` | AI 요약 | `file_path`, `api_key` |
| `ai_ask_question` | AI PDF 채팅 | `file_path`, `api_key`, `question` |
| `ai_extract_keywords` | AI 키워드 추출 | `file_path`, `api_key`, `max_keywords` |
| `draw_shapes` | 도형 그리기 | `file_path`, `shapes` 또는 `shape_type/x/y/…`, `output_path` |
| `add_link` | 하이퍼링크 | `file_path`, `link_type`, `target`, `rect`, `output_path` |
| `insert_textbox` | 텍스트 상자 | `file_path`, `text`, `rect` 또는 `x/y`, `output_path` |
| `copy_page_between_docs` | 페이지 복사 | `file_path`, `source_path`, `page_range` |
| `replace_page` | 페이지 교체 | `file_path`, `source_path`, `page_index`, `output_path` |
| `set_bookmarks` | 북마크 설정 | `file_path`, `bookmarks`, `output_path` |
| `add_annotation` | 주석 추가 | `file_path`, `annot_type`, `rect`, `output_path` |

**주요 정책:**
- `run()` 시작 시 `_preflight_inputs()`로 입력 파일 존재/크기 사전 검증 (fail-fast)
- `_normalize_mode_kwargs()`로 UI/레거시 kwargs 양방향 정규화
- `add_link(goto)` — Worker 경계는 0-based 페이지 인덱스만 허용
- `copy_page_between_docs` — 무효/누락 `page_range`는 hard-fail (묵시 폴백 없음)
- `ai_summarize` — `output_path`는 선택사항 (UI에서 메모리 결과 소비 가능)
- `-1` last-page sentinel은 서명 계열 모드에만 예약됨

### 2. `src/core/ai_service.py` + `src/core/ai/*` — AIService

`ai_service.py`는 기존 import 경로를 유지하는 facade입니다. 실제 구현은 `src/core/ai/` 하위 모듈에 분리되어 있습니다.

```python
class AIService:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: int = 30)
    def summarize_pdf(self, pdf_path: str, language: str = "ko", style: str = "concise")
    def ask_about_pdf(self, pdf_path: str, question: str)
    def extract_keywords(self, pdf_path: str, max_keywords: int = 10, language: str = "ko")
    def validate_api_key(self) -> tuple[bool, str]
    def clear_chat_session(self, pdf_path: str) -> None   # clears the currently selected PDF's session
```

- SDK: `google-genai` only (레거시 SDK 없음)
- 기본 경로: Gemini File API 업로드 + structured output + streaming
- 반환 결과에 `meta` 딕셔너리 포함 (`source`, `truncated`, `page_focus_limit`, 등)
- 업로드된 Gemini 파일은 LRU eviction / Clear Chat / 앱 종료 시 best-effort remote delete

**예외 클래스:**
- `AIServiceError` — 기본 예외
- `APIKeyError` — API 키 오류
- `APITimeoutError` — 타임아웃
- `APIRateLimitError` — Rate limit 초과

### 3. `src/core/settings.py` — 설정 관리

```python
DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "auto",
    "recent_files": [],
    "last_output_dir": "",
    "preview_search_expanded": True,
    "splitter_sizes": None,
    "window_geometry": None,
}

def load_settings() -> dict
def save_settings(settings: dict) -> bool
def get_api_key() -> str          # keyring 우선, 설정 파일 폴백
def set_api_key(api_key: str) -> bool
def reset_settings() -> bool
```

- `load_settings()`는 `recent_files`, `chat_histories`, `splitter_sizes`, `theme`, `language`, `window_geometry`, `last_output_dir`, `preview_search_expanded`를 로드 시 정규화
- AI 채팅 기록 key: `v2:{mtime_ns}:{normalized_path}` (같은 경로 PDF 교체 시 기록 분리)
- API 키 저장: keyring 우선; secure storage 불가 시 사용자 확인 후 plaintext fallback

### 4. `src/core/constants.py` — 상수

```python
PAGE_SIZES = {'A4': (595, 842), 'A3': (842, 1191), 'Letter': (612, 792), ...}

DEFAULT_DPI = 200
THUMBNAIL_SIZE = 150
MAX_RENDER_DIMENSION = 8000

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024   # 2GB
MIN_PDF_SIZE = 100
MAX_PAGE_RANGE_LENGTH = 1000

AI_DEFAULT_TIMEOUT = 30
AI_MAX_TEXT_LENGTH = 30000
AI_MAX_RETRIES = 3
```

### 5. `src/core/undo_manager.py` — UndoManager

```python
@dataclass
class ActionRecord:
    action_type: str
    description: str
    timestamp: datetime
    before_state: dict    # before_backup_path, target_path
    after_state: dict     # after_backup_path
    undo_callback: Optional[Callable]
    redo_callback: Optional[Callable]

class UndoManager:
    def push(self, action_type, description, before_state, after_state, undo_callback, redo_callback)
    def undo(self) -> Optional[ActionRecord]
    def redo(self) -> Optional[ActionRecord]
    @property can_undo -> bool
    @property can_redo -> bool
```

Undo 대상 모드: `resize_pages`, `insert_signature`, `highlight_text`, `add_sticky_note`, `add_ink_annotation`, `copy_page_between_docs` 포함.
스냅샷 백업 실패 시 작업은 계속되고 UI에 "Undo 불가" 경고 표시.

### 6. `src/core/i18n.py` — TranslationManager

```python
class TranslationManager:   # Singleton
    def get(self, key: str, *args) -> str
    active_lang_code: str
```

- 한국어 / 영어 지원
- `locale.getlocale()` + 환경변수 fallback으로 시스템 언어 자동 감지
- 번역 데이터는 `src/core/i18n_catalogs/ko_base.py`, `en_base.py`에 분리

### 7. `src/ui/zoomable_preview.py` — ZoomablePreviewWidget

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

- `QPdfDocument + QPdfView + QPdfSearchModel + QPdfBookmarkModel + QPdfPageNavigator` 조합 래퍼
- 검색/북마크 사이드바, 인쇄 미리보기, 페이지 설정, view state 저장/복원 담당
- same-path overwrite 복원, 암호화 PDF 비밀번호 재사용, external rewrite auto-reload는 `window_preview/*`와 공동 책임
- 예전 pixmap/control-mode 및 `renderRequested` 계약은 제거됨

### 8. `src/ui/thumbnail_grid.py` — ThumbnailGridWidget

```python
class ThumbnailGridWidget(QWidget):
    pageSelected = pyqtSignal(int)
    selectedPagesChanged = pyqtSignal(list)

    def load_pdf(pdf_path: str, password: str | None = None)
    def select_page(index: int)
    def set_active_page(index: int, emit_signal: bool = False)
    def get_selected_pages() -> list[int]
```

- `active page`(미리보기 동기화)와 `selected pages`(회전 대상 등)를 분리 관리
- 암호화 PDF 로딩 시 preview에서 인증한 `password`를 재사용 (별도 프롬프트 없음)

---

## ⚙️ 개발 가이드라인

### PDF 작업 추가하기

1. `src/core/worker_runtime/dispatch.py`의 `MODE_TO_HANDLER`에 모드 추가
2. 적절한 domain module(`page_ops.py`, `annotation_ops.py` 등)에 메서드 구현:

```python
def new_operation(self):
    try:
        file_path = self.kwargs["file_path"]
        output_path = self.kwargs["output_path"]
        doc = fitz.open(file_path)
        try:
            for i, page in enumerate(doc):
                self._check_cancelled()
                # 작업 수행...
                self._emit_progress_if_due(int((i + 1) / len(doc) * 100))
            self._atomic_pdf_save(doc, output_path, garbage=4, deflate=True)
            self.finished_signal.emit(tm.get("op_done"))
        finally:
            doc.close()
    except CancelledError:
        self.finished_signal.emit(tm.get("op_cancelled"))
    except Exception as e:
        self.error_signal.emit(str(e))
```

3. `src/core/worker_runtime/preflight.py`의 `OperationSpec`에 출력 계약 추가 (`required_any_kwargs` 포함)
4. 믹스인 host 계약 변경 시 `src/core/_typing.py` 업데이트 후 `python -m pyright` 재실행

### UI 위젯 추가 시 체크리스트

- `ThemeColors` 상수 사용
- `set_theme(is_dark: bool)` 메서드 구현
- 스크롤 가능 위젯에 `WheelEventFilter` 적용
- 사용자 문자열은 `tm.get(...)` 경유 (하드코딩 금지)
- `src/ui/_typing.py`에 접근하는 공통 속성 추가

### 코딩 규칙

- PDF 문서는 반드시 `try/finally`로 닫기
- Worker에서 UI 직접 조작 금지 — 시그널/슬롯만 사용
- 장시간 루프 내 `_check_cancelled()` 호출
- `fitz` / `keyring` 직접 import 대신 `src/core/optional_deps.py` 사용
- 바이너리 출력은 `_atomic_binary_save()`, PDF 출력은 `_atomic_pdf_save()` 사용

---

## 📝 모듈 매핑 (분할 구조)

| 경로 | 역할 |
|------|------|
| `src/core/worker.py` | Worker QThread facade |
| `src/core/worker_runtime/*` | dispatch / preflight / atomic save 공통 로직 |
| `src/core/pdf_validation.py` | Worker/UI 공용 PDF size/header 검증 |
| `src/core/ai_service.py` | AIService compatibility facade |
| `src/core/ai/*` | Gemini client/cache/schema/session/prompt 구현 |
| `src/core/i18n_catalogs/ko_base.py`, `en_base.py` | KO/EN 번역 카탈로그 |
| `src/core/worker_ops/page_ops.py` | split / reorder / insert / replace / duplicate |
| `src/core/worker_ops/annotation_ops.py` | highlight / redact / shape / link / textbox / ink |
| `src/core/worker_ops/compose_ops.py` | merge / images-to-PDF / copy-page |
| `src/core/worker_ops/transform_ops.py` | metadata / compress / crop / resize / SVG |
| `src/core/worker_ops/cleanup_ops.py` | blank/dedupe/sanitize/n-up/bookmark split/auto TOC |
| `src/core/worker_ops/extract_ops.py` | text / image / link / bookmark / markdown (`auto/native/text`) / attachment |
| `src/core/worker_ops/compare_ops.py` | PDF 비교 (text/visual/both) |
| `src/core/worker_ops/form_ops.py` | 양식 필드 조회/채우기/flatten |
| `src/core/worker_ops/ai_ops.py` | AI 요약/채팅/키워드 |
| `src/ui/tabs_basic/*` | 병합/변환/페이지/보안/순서/배치 탭 |
| `src/ui/tabs_advanced/*` | 고급 탭 (편집/추출/마크업) |
| `src/ui/tabs_ai/*` | AI 탭 / 스토리지 / 액션 |
| `src/ui/window_core/*` | 메뉴 / 테마 / 단축키 / 상태 |
| `src/ui/window_preview/*` | 미리보기 / 문서 / 네비게이션 |
| `src/ui/window_worker/*` | Worker UI 수명주기 |
| `src/ui/window_undo/*` | Undo/Redo / 백업 정리 |

---

## 🔧 빌드 및 검증

```bash
# 개발 실행
python main.py

# 의존성 설치
pip install -e .[dev]
pip install -e .[ai]      # AI 기능
pip install -e .[build]   # 빌드 도구

# 정적 분석
python -m pyright          # 0 errors 목표

# 테스트
python -m pytest -q        # 219 collected / 218 passed / 1 opt-in Gemini smoke skipped

# 패키지 빌드
python -m build

# 실행 파일 빌드
python -m PyInstaller pdf_master.spec --clean

# 앱 초기화 smoke
python main.py --smoke

# 패키지 smoke (clean PYTHONPATH)
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1

# Gemini File API live smoke (opt-in)
$env:PDF_MASTER_GEMINI_FILE_API_SMOKE = "1"
$env:GEMINI_API_KEY = "<your-key>"
python -m pytest tests/test_ai_service_gemini_smoke.py -v
```

---

## 2026-07-15 감사 후속 (요약)

- AI: `cancel_check` 전파, 암호화 PDF는 preview passwords로 임시 복호 후 처리
- blank-page / visual compare / redact_area 확인 / batch permissions·cancel 보강
- 상세: `PROJECT_AUDIT.md`, `CLAUDE.md` 2026-07-15 addendum
- 검증: `python -m pytest -q` → 219 collected / 218 passed / 1 opt-in skip

---

*이 문서는 PDF Master v4.5.6 기준으로 작성되었습니다. (2026-07-15)*
