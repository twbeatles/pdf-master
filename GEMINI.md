# GEMINI.md - PDF Master v4.5.4 AI 가이드

이 문서는 AI 어시스턴트(Gemini)가 PDF Master 프로젝트를 이해하고 개발을 지원하기 위한 가이드입니다.

---

## 📋 프로젝트 개요

**PDF Master**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

### 기본 정보

| 항목 | 내용 |
|------|------|
| **버전** | v4.5.4 |
| **언어** | Python 3.10+ |
| **UI 프레임워크** | PyQt6 6.5+ |
| **PDF 엔진** | PyMuPDF (fitz) |
| **AI 기능** | Google Gemini API (google-genai SDK) |
| **빌드 도구** | PyInstaller |
| **라이선스** | MIT |

### 주요 기능

- PDF 병합/분할
- PDF ↔ 이미지 변환
- 텍스트 추출
- 페이지 편집 (삭제, 회전, 순서변경)
- 워터마크/스탬프 추가
- 페이지 번호 삽입
- PDF 암호화/복호화
- PDF 압축
- AI 기반 PDF 요약
- AI PDF 채팅 (v4.5)
- AI 키워드 추출 (v4.5)
- 다크/라이트 테마
- Undo/Redo 지원

---

## 🗂️ 디렉토리 구조

```
pdf-master/
├── main.py
├── .editorconfig
├── pdf_master.spec
├── pyrightconfig.json
├── README.md
├── README_EN.md
├── CLAUDE.md
├── GEMINI.md
└── src/
    ├── core/
    │   ├── ai_service.py
    │   ├── optional_deps.py
    │   ├── _typing.py
    │   ├── constants.py
    │   ├── i18n.py                 # TranslationManager facade
    │   ├── i18n_catalogs/          # 번역 카탈로그 저장소
    │   ├── settings.py
    │   ├── undo_manager.py
    │   ├── worker.py               # QThread facade
    │   ├── worker_runtime/         # 공통 runtime/dispatch/preflight
    │   └── worker_ops/             # Worker 기능 분할 구현
    │       ├── pdf_ops.py          # compatibility shim
    │       └── ai_ops.py
    └── ui/
        ├── _typing.py
        ├── main_window.py
        ├── main_window_config.py
        ├── main_window_tabs_basic.py     # 호환 shim
        ├── main_window_tabs_advanced.py  # 호환 shim
        ├── main_window_tabs_ai.py        # 호환 shim
        ├── main_window_core.py           # 호환 shim
        ├── main_window_preview.py        # 호환 shim
        ├── main_window_worker.py         # 호환 shim
        ├── main_window_undo.py           # 호환 shim
        ├── tabs_basic/
        ├── tabs_advanced/
        ├── tabs_ai/
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

### 1. `src/core/worker.py` - WorkerThread

PDF 작업을 백그라운드에서 처리하는 QThread 기반 워커입니다.

**시그널:**
```python
progress_signal = pyqtSignal(int)     # 진행률 (0-100)
finished_signal = pyqtSignal(str)     # 완료 메시지
error_signal = pyqtSignal(str)        # 에러 메시지
```

**작업 모드 (mode 파라미터):**

| 모드 | 설명 | 필수 파라미터 |
|------|------|--------------|
| `merge` | PDF 병합 | `files`, `output_path` |
| `convert_to_img` | PDF → 이미지 | `file_path` 또는 `file_paths`, `output_dir`, `fmt`, `dpi` |
| `extract_text` | 텍스트 추출 | `file_path` 또는 `file_paths`, `output_path` 또는 `output_dir` |
| `split` | PDF 분할 (범위) | `file_path`, `page_range`, `output_dir` |
| `split_by_pages` | 페이지별 분할 | `file_path`, `output_dir` |
| `delete_pages` | 페이지 삭제 | `file_path`, `page_range`, `output_path` |
| `rotate` | 페이지 회전 | `file_path`, `angle`, `output_path`, `page_indices?` |
| `watermark` | 텍스트 워터마크 | `file_path`, `text`, `output_path` |
| `image_watermark` | 이미지 워터마크 | `file_path`, `image_path`, `output_path` |
| `add_page_numbers` | 페이지 번호 | `file_path`, `position`, `format`, `output_path` |
| `compress` | PDF 압축 | `file_path`, `quality`, `output_path` |
| `protect` | PDF 암호화 | `file_path`, `password`, `output_path` |
| `images_to_pdf` | 이미지 → PDF | `files`, `output_path` |
| `reorder` | 페이지 순서변경 | `file_path`, `page_order`, `output_path` |
| `add_stamp` | 스탬프 추가 | `file_path`, `stamp_text`, `position`, `output_path` |
| `ai_summarize` | AI 요약 | `file_path`, `api_key` |
| `ai_ask_question` | AI PDF 채팅 (v4.5) | `file_path`, `api_key`, `question` |
| `ai_extract_keywords` | AI 키워드 추출 (v4.5) | `file_path`, `api_key`, `max_keywords` |
| `draw_shapes` | 도형 그리기 (v4.5) | `file_path`, `shape_type` 또는 `shapes`, `output_path` |
| `add_link` | 하이퍼링크 추가 (v4.5) | `file_path`, `link_type`, `target`, `rect`, `output_path` |
| `insert_textbox` | 텍스트 상자 (v4.5) | `file_path`, `text`, `rect` 또는 `x/y`, `output_path` |
| `copy_page_between_docs` | 페이지 복사 (v4.5) | `file_path`, `source_path`, `page_range` |

> 참고 (v4.5.1): `WorkerThread`는 `_normalize_mode_kwargs()`를 통해 UI/레거시 kwargs를 정규화하여 양방향 호환을 보장합니다.

### Worker kwargs 계약 보강 (v4.5.1)

- `draw_shapes`
  - 단일 입력(`shape_type/x/y/width/height/line_color/fill_color`)도 내부 `shapes=[...]`로 정규화됨
- `add_link`
  - `link_type`로 `url/page` 별칭 허용 (`uri/goto`로 매핑)
  - `target`은 Worker 경계에서 0-based만 허용 (UI에서 1-based 입력을 사전 정규화)
- `insert_textbox`
  - `rect` 미지정 시 `x,y,width,height`로 자동 사각형 생성 (기본 200x50)
- `copy_page_between_docs`
  - `target_path`가 없으면 `file_path`를 대상 문서로 사용
  - `source_pages`가 없으면 `page_range`를 파싱하여 사용
- `image_watermark`
  - `scale` 입력 시 원본 이미지 기준으로 `width/height` 계산
  - 위치 별칭 `top-center`, `bottom-center` 허용

### 입력 사전검증 (v4.5.1)

- `run()` 시작 시 `_preflight_inputs()` 수행
- PDF 입력은 존재/크기(최소/최대) 선검증
- 비-PDF 입력(`image_path`, `signature_path`, `attach_path`)은 존재/최대 크기 선검증
- 검증 실패 시 작업 실행 전 `error_signal`로 즉시 종료 (fail-fast)

### 2. `src/core/ai_service.py` - AIService

Gemini API를 사용한 AI 서비스 클래스입니다.

```python
class AIService:
    def __init__(self, api_key: str, model: str = "gemini-flash-latest", timeout: int = 30)
    def summarize_pdf(self, pdf_path: str, language: str = "ko", style: str = "concise")
    def ask_about_pdf(self, pdf_path: str, question: str)
    def extract_keywords(self, pdf_path: str, max_keywords: int = 10, language: str = "ko")  # v4.5
    def validate_api_key(self) -> tuple[bool, str]
```

**SDK 호환성:**
- 공식: `google-genai` (추천)
- 레거시: `google-generativeai` (Deprecated, 2025.11 중단)
- v4.5.4: 런타임에서는 `importlib.import_module()` 기반 선택적 로딩을 사용하므로, 문서/빌드 설정도 hiddenimports 기준으로 동기화해야 합니다.

**예외 클래스:**
- `AIServiceError` - 기본 예외
- `APIKeyError` - API 키 오류
- `APITimeoutError` - 타임아웃
- `APIRateLimitError` - Rate limit 초과

### 3. `src/core/settings.py` - 설정 관리

```python
SETTINGS_FILE = "~/.pdf_master_settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "recent_files": [],
    "last_output_dir": "",
    "splitter_sizes": None,
    "window_geometry": None,
}

# 함수
def load_settings() -> dict
def save_settings(settings: dict) -> bool
def get_api_key() -> str     # keyring 우선, 파일 폴백
def set_api_key(api_key: str) -> bool
def reset_settings() -> bool
```

### 타입 계약 파일 (v4.5.4)

- `src/core/_typing.py`
  - `WorkerHost` 계약 정의
  - `WorkerPdfOpsMixin`, `WorkerAiOpsMixin`이 기대하는 signal/helper 속성 명시
- `src/core/optional_deps.py`
  - `fitz`, `keyring` optional import 경계
  - 미설치 환경에서는 proxy/fallback으로 import-time 오류를 막고, 실제 사용 시점에만 실패하게 함
- `src/ui/_typing.py`
  - `MainWindowHost` 계약 정의
  - 분리된 UI 믹스인이 접근하는 공통 위젯/헬퍼 속성 명시
- 변경 규칙
  - 믹스인에서 `self.<attr>`를 새로 사용하면 대응 `_typing.py` 계약도 같이 갱신
  - 수정 후 `pyright`를 반드시 다시 실행
  - `fitz`/`keyring` 직접 import 대신 `src/core/optional_deps.py`를 우선 사용

### 4. `src/core/constants.py` - 상수

```python
# 페이지 크기 (포인트)
PAGE_SIZES = {
    'A4': (595, 842),
    'A3': (842, 1191),
    'A5': (420, 595),
    'Letter': (612, 792),
    'Legal': (612, 1008),
}

# 이미지 설정
DEFAULT_DPI = 200
THUMBNAIL_SIZE = 150
SUPPORTED_IMAGE_FORMATS = ('png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp')

# 제한값
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MIN_PDF_SIZE = 100
MAX_PAGE_RANGE_LENGTH = 1000

# 압축 설정
COMPRESSION_SETTINGS = {
    'low': {'garbage': 4, 'deflate': True, 'deflate_images': True, 'deflate_fonts': True, 'clean': True},
    'medium': {'garbage': 3, 'deflate': True, 'deflate_images': True},
    'high': {'garbage': 2, 'deflate': True},
}

# AI 서비스
AI_DEFAULT_TIMEOUT = 30
AI_MAX_TEXT_LENGTH = 30000
AI_MAX_RETRIES = 3
```

### 5. `src/core/undo_manager.py` - UndoManager

```python
@dataclass
class ActionRecord:
    action_type: str
    description: str
    timestamp: datetime
    before_state: dict
    after_state: dict
    undo_callback: Optional[Callable]
    redo_callback: Optional[Callable]

class UndoManager:
    def __init__(self, max_history: int = 50)
    def push(self, action_type, description, before_state, after_state, undo_callback, redo_callback)
    def undo(self) -> Optional[ActionRecord]
    def redo(self) -> Optional[ActionRecord]
    def can_undo -> bool
    def can_redo -> bool

### 6. `src/core/i18n.py` - TranslationManager

```python
class TranslationManager:
    def __init__(self)  # Singleton
    def get(self, key: str, *args) -> str
```

**특징:**
- 한국어/영어 지원 (`ko`, `en`)
- `locale` 모듈을 통한 시스템 언어 자동 감지
  - v4.5.1: `locale.getdefaultlocale()` 대신 `getlocale + 환경변수 fallback`
- `TranslationManager().get("key")`로 사용
- `active_lang_code` 속성으로 현재 언어 확인
```

### 7. `src/ui/main_window.py` - PDFMasterApp

메인 애플리케이션 윈도우입니다.

**믹스인 구성 (UI 분리 구조):**
- `main_window.py`: QMainWindow 구성, `__init__`, `closeEvent`
- `main_window_config.py`: 앱 상수/AI 가용성
- `main_window_*.py`: 기존 import 경로 호환 shim
- `tabs_basic`, `tabs_advanced`, `tabs_ai`: 탭 기능 실제 구현
- `window_core`, `window_preview`, `window_worker`, `window_undo`: 공통 UI 동작 실제 구현

**단축키:**
| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 종료 |
| `Ctrl+T` | 테마 전환 |
| `Ctrl+Z` | 실행 취소 |
| `Ctrl+Y` | 다시 실행 |
| `Ctrl+1~8` | 탭 전환 |

**주요 메서드:**
```python
def run_worker(self, mode, output_path=None, **kwargs)  # 작업 실행
def _toggle_theme(self)  # 테마 전환
def _apply_theme(self)   # 테마 적용
def _update_preview(self, path)  # 미리보기 업데이트
```

추가 반영 (v4.5.1):
- `_open_last_folder()`에서 비-Windows 환경은 Qt `QDesktopServices` 기반으로 폴더 열기 처리

### 8. `src/ui/styles.py` - ThemeColors

```python
class ThemeColors:
    # 브랜드 색상
    PRIMARY = "#4f8cff"
    PRIMARY_LIGHT = "#7fb3ff"
    PRIMARY_DARK = "#3a7ae8"
    PRIMARY_GLOW = "rgba(79, 140, 255, 0.4)"
    
    # 상태 색상
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    
    # 다크 테마
    DARK_BG = "#0a0e14"
    DARK_CARD = "#141922"
    DARK_BORDER = "#2d3748"
    DARK_TEXT = "#f0f4f8"
    
    # 라이트 테마
    LIGHT_BG = "#f8fafc"
    LIGHT_CARD = "#ffffff"
    LIGHT_BORDER = "#e2e8f0"
    LIGHT_TEXT = "#1e293b"
```

### 9. `src/ui/widgets.py` - 커스텀 위젯

| 클래스 | 용도 |
|--------|------|
| `is_valid_pdf(file_path)` | PDF 유효성 검사 |
| `WheelEventFilter` | 휠 이벤트 필터 |
| `EmptyStateWidget` | 빈 상태 안내 UI |
| `DropZoneWidget` | 드래그 앤 드롭 영역 |
| `FileSelectorWidget` | 파일 선택 위젯 |
| `FileListWidget` | 파일 목록 위젯 |
| `DraggableListWidget` | 드래그 가능 리스트 |

### 10. `src/ui/progress_overlay.py` - 진행 오버레이

```python
class ProgressOverlayWidget(QWidget):
    cancelled = pyqtSignal()
    
    def show_progress(title: str, description: str)
    def update_progress(value: int, description: str)
    def hide_progress()
    def set_theme(is_dark: bool)

class LoadingSpinner(QLabel):
    # 이모지 기반 애니메이션
```

### 11. `src/ui/thumbnail_grid.py` - 썸네일 그리드

```python
class ThumbnailLoaderThread(QThread):
    thumbnail_ready = pyqtSignal(int, QPixmap)
    loading_complete = pyqtSignal()

class ThumbnailGridWidget(QWidget):
    pageSelected = pyqtSignal(int)
    selectedPagesChanged = pyqtSignal(list)
    
    def load_pdf(pdf_path: str)
    def select_page(index: int)
    def set_active_page(index: int, emit_signal: bool = False)
    def get_selected_pages() -> list[int]
```

### 12. `src/ui/zoomable_preview.py` - 줌 미리보기

```python
class ZoomableGraphicsView(QGraphicsView):
    zoomChanged = pyqtSignal(float)
    
    def set_zoom(zoom: float)
    def zoom_in() / zoom_out()
    def fit_in_view()

class ZoomablePreviewWidget(QWidget):
    def load_pdf(pdf_path: str)
    def go_to_page(page_index: int)
```

---

## ⚙️ 개발 가이드라인

### PDF 작업 추가하기

1. `src/core/worker_runtime/dispatch.py`의 `MODE_TO_HANDLER`에 모드 추가
2. 새 메서드 구현:

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
            self.finished_signal.emit(f"완료: {output_path}")
        finally:
            doc.close()  # 중요: 반드시 리소스 해제
            
    except CancelledError:
        self.finished_signal.emit("취소됨")
    except Exception as e:
        self.error_signal.emit(str(e))
```

### UI 위젯 추가하기

1. `ThemeColors` 상수 사용
2. `set_theme(is_dark: bool)` 메서드 구현
3. 스크롤 가능 위젯에 `WheelEventFilter` 적용

### 테마 대응

```python
def set_theme(self, is_dark: bool):
    self._is_dark = is_dark
    self._apply_theme_style()

def _apply_theme_style(self):
    if self._is_dark:
        bg = ThemeColors.DARK_CARD
        text = ThemeColors.DARK_TEXT
    else:
        bg = ThemeColors.LIGHT_CARD
        text = ThemeColors.LIGHT_TEXT
    
    self.setStyleSheet(f"background: {bg}; color: {text};")
```

---

## ⚠️ 주의사항

### 1. 리소스 관리
```python
doc = fitz.open(path)
try:
    # 작업 수행
finally:
    doc.close()  # 반드시!
```

### 2. 스레드 안전
- UI 업데이트는 시그널/슬롯만 사용
- `WorkerThread`에서 직접 UI 조작 금지

### 3. 취소 지원
- 장시간 작업에서 `_check_cancelled()` 호출
- `CancelledError` 예외 처리

### 4. 에러 처리
```python
try:
    # 작업
except Exception as e:
    logger.error(f"Failed: {e}")
    self.error_signal.emit(str(e))
```

---

## 🔧 빌드 및 실행

### 개발 실행
```bash
python main.py
```

### 의존성 설치
```bash
pip install PyQt6 PyMuPDF
pip install google-genai  # AI 기능 (선택)
```

### 프로덕션 빌드
```bash
pyinstaller pdf_master.spec --clean
# 결과: dist/PDF_Master_v4.5.4.exe (~30-40MB)
```

### 정합성 검증 (v4.5.4)
```bash
pyright
python -m pytest
```

- 기준 결과:
  - `pyright` -> `0 errors`
  - 현재 환경 `python -m pytest` -> `63 passed, 1 warning`
  - `tests/test_encoding_audit.py` -> UTF-8 decode/BOM/U+FFFD 회귀 방지
  - `PyMuPDF` 미설치 환경에서는 PDF 엔진 의존 테스트만 skip

---

## 📝 모듈 매핑 (분할 구조)

| 경로 | 역할 |
|------|------|
| `src/core/worker.py` | Worker QThread facade 및 공개 진입점 |
| `src/core/worker_runtime/*` | dispatch/preflight/i18n message/atomic save 공통 로직 |
| `src/core/worker_ops/pdf_ops.py` | PDF worker mixin compatibility shim |
| `src/core/worker_ops/ai_ops.py` | AI 요약/질의/키워드 작업 구현 |
| `src/ui/main_window_*.py` | UI 호환 shim |
| `src/ui/tabs_basic/*` | 기본 탭(병합/변환/페이지/보안/순서/배치) |
| `src/ui/tabs_advanced/*` | 고급 탭(편집/추출/마크업/기타) |
| `src/ui/tabs_ai/*` | AI 탭/스토리지/액션 |
| `src/ui/window_core/*` | 메뉴/테마/단축키/상태 |
| `src/ui/window_preview/*` | 미리보기/문서/네비게이션 |
| `src/ui/window_worker/*` | Worker UI 수명주기 |
| `src/ui/window_undo/*` | Undo/Redo/백업 정리 |

---

## 🚀 버전 히스토리

### v4.5.4 (2026-03-09)
- `pyrightconfig.json` 추가 및 저장소 전체 `pyright .` 통과
- `src/core/_typing.py`, `src/ui/_typing.py` 추가로 믹스인 host 계약 문서화
- `ai_service`의 optional Gemini SDK 로딩을 importlib 기반 런타임/빌드 계약으로 정리
- Qt 위젯/Worker 계층 optional narrowing 정리 및 UTF-8 인코딩 점검 완료
- `.gitignore`, `pdf_master.spec`, README 계열 문서 동기화

### v4.5.4 (2026-03-18 addendum)
- 페이지 탭 회전 섹션에 전용 썸네일 목록 추가
- `rotate`가 선택적 `page_indices`를 받아 선택 페이지 부분 회전을 지원
- `ThumbnailGridWidget`이 `active page`와 `selected pages`를 분리 지원
- 오른쪽 미리보기 이동 시 회전 섹션 활성 페이지를 동기화

### v4.5.4 (2026-03-18 core refactor)
- `src/core/worker.py`를 공개 facade로 축소하고 공통 실행 로직을 `src/core/worker_runtime/*`로 분리
- `src/core/worker_ops`를 책임별 mixin 구조로 재편
- `src/core/worker_ops/pdf_ops.py`는 compatibility shim으로 유지
- `src/core/i18n.py`는 런타임 API만 유지하고 번역 카탈로그는 `src/core/i18n_catalogs/*`로 분리
- Worker dispatch registry / i18n catalog facade / resource cleanup 구조 테스트 추가

### v4.5.3 (2026-02-26)
- 배치 워터마크 런타임 실패 수정 및 파일별 실패 원인 요약
- 페이지 복사 strict range 정책 적용(무효 범위 hard-fail)
- 첨부 추출 파일명 정규화/경로 탈출 차단 강화
- Worker 링크 페이지 정책을 0-based 단일 정책으로 통일
- `replace_page`/`set_bookmarks`/`add_annotation` UI 기본 노출
- UI/Worker 대형 파일을 폴더 기반 모듈로 분할(`tabs_*`, `window_*`, `worker_ops`)

### v4.5 (현재)
- 도형 그리기 UI (draw_shapes)
- 하이퍼링크 추가 UI (add_link)
- 텍스트 상자 삽입 (insert_textbox)
- 페이지 복사 (copy_page_between_docs)
- 이미지 워터마크 개선 (위치/크기/투명도 파라미터 적용)
- 미리보기 인쇄 버튼
- AI PDF 채팅 (ai_ask_question)
- AI 키워드 추출 (ai_extract_keywords)
- AI 싱글톤 스레드 안전성 (Double-check locking)
- i18n 88개 키 추가 + 하드코딩 메시지 제거

### v4.5.1 (2026-02-19) - 안정화
- Worker kwargs 정규화 레이어 추가 (`_normalize_mode_kwargs`)
- Worker 실행 전 입력 사전검증 추가 (`_preflight_inputs`)
- 고급 기능 5종 UI/Worker 계약 불일치 수정
- Undo 등록 모드 오타 수정 (`duplicate_page`)
- Linux/macOS 폴더 열기 호환 개선 (Qt `QDesktopServices`)
- i18n 로케일 감지 비권장 경로 제거
- 테스트 추가:
  - `tests/test_worker_param_compat.py`
  - `tests/test_worker_preflight.py`
  - `tests/test_i18n.py`

### v4.4
- 다국어 지원 (i18n): 한국어/영어
- 언어 설정 기능
- UI 리팩토링

### v4.3
- 진행 오버레이 (ProgressOverlay)
- EmptyStateWidget
- Premium 버튼 스타일
- 미리보기 줌/패닝

### v4.2
- google-genai SDK 전환
- gemini-flash-latest 모델
- PDF → Word 기능 제거
- 리소스 관리 개선
- 빌드 경량화

---

*이 문서는 PDF Master v4.5.4 기준으로 작성되었습니다. (2026-03-18)*
