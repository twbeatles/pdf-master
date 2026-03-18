# PDF Master - Claude AI 가이드

> 이 문서는 PDF Master 프로젝트를 Claude AI가 이해하고 효과적으로 지원할 수 있도록 작성된 가이드입니다.

---

## 📌 프로젝트 개요

**PDF Master v4.5.4**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

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
├── pyrightconfig.json
├── README.md
├── README_EN.md
├── CLAUDE.md
├── GEMINI.md
└── src/
    ├── core/
    │   ├── ai_service.py
    │   ├── optional_deps.py        # fitz/keyring optional dependency boundary
    │   ├── _typing.py              # worker mixin host contracts
    │   ├── constants.py
    │   ├── i18n.py                 # TranslationManager facade
    │   ├── i18n_catalogs/          # 번역 카탈로그 저장소
    │   ├── settings.py
    │   ├── undo_manager.py
    │   ├── worker.py               # QThread facade
    │   ├── worker_runtime/         # 공통 runtime/dispatch/preflight
    │   └── worker_ops/             # 실제 Worker 기능 구현
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

#### 취소 처리
```python
def cancel(self):
    self._cancel_requested = True

def _check_cancelled(self):
    if self._cancel_requested:
        raise CancelledError()
```

---

### 3. `src/core/ai_service.py` - Gemini AI 서비스

#### 주요 클래스
```python
class AIService:
    def __init__(self, api_key: str, model: str = "gemini-flash-latest", timeout: int = 30)
    def summarize_pdf(self, pdf_path: str, language: str = "ko", style: str = "concise")
    def ask_about_pdf(self, pdf_path: str, question: str)
    def extract_keywords(self, pdf_path: str, max_keywords: int = 10, language: str = "ko")  # v4.5
    def validate_api_key(self) -> tuple[bool, str]
```

#### SDK 호환성
```python
# 새 SDK (권장): google-genai
# 기존 SDK (폴백): google-generativeai (2025.11 deprecated)
# v4.5.4: 런타임에서는 importlib 기반 선택적 로딩을 사용
```

#### 예외 클래스
- `AIServiceError` - 기본 예외
- `APIKeyError` - API 키 오류
- `APITimeoutError` - 타임아웃
- `APIRateLimitError` - Rate limit 초과

---

### 4. `src/core/settings.py` - 설정 관리

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

### 타입 계약 파일 (v4.5.4)

- `src/core/_typing.py`
  - Worker 믹스인이 기대하는 signal/helper surface를 정의합니다.
- `src/core/optional_deps.py`
  - `fitz`, `keyring` optional import를 중앙화하고, 미설치 환경에서는 proxy/fallback으로 import-time 실패를 막습니다.
- `src/ui/_typing.py`
  - UI 믹스인이 접근하는 공통 위젯/헬퍼 surface를 정의합니다.
- 규칙
  - 믹스인에서 새 속성 접근을 추가하면 대응 `_typing.py`도 함께 갱신합니다.
  - 변경 후 `pyright`를 기본 검증으로 실행합니다.
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
    
    def load_pdf(pdf_path: str)
    def select_page(index: int)
    def set_active_page(index: int, emit_signal: bool = False)
    def get_selected_pages() -> list[int]
```

---

### 13. `src/ui/zoomable_preview.py` - 줌/패닝 미리보기

```python
class ZoomableGraphicsView(QGraphicsView):
    """마우스 휠 줌, 드래그 패닝"""
    zoomChanged = pyqtSignal(float)
    
    def set_zoom(zoom: float)
    def zoom_in() / zoom_out()
    def fit_in_view()
    
class ZoomablePreviewWidget(QWidget):
    """줌 컨트롤 포함 미리보기"""
    def load_pdf(pdf_path: str)
    def go_to_page(page_index: int)
```

---

## 🔐 보안 고려사항

1. **API 키 저장**: `keyring` 라이브러리 우선 사용, 불가 시 설정 파일 폴백
2. **PDF 검증**: 파일 헤더 (`%PDF-`) 확인으로 유효성 검증
3. **파일 크기 제한**: `MAX_FILE_SIZE = 2GB` (v4.5.1: Worker preflight에서 실행 전 검증)
4. **입력 검증**: 페이지 범위 문자열 길이 제한 (`MAX_PAGE_RANGE_LENGTH = 1000`)
5. **첨부 추출 경로 보호**: 파일명 정규화 + `output_dir` 하위 경로 강제
6. **링크 인덱스 정책**: Worker `goto` 타겟은 0-based 단일 정책

---

## 🧪 테스트 업데이트 (v4.5.4)

- `pyright` -> `0 errors`
- `python -m pytest` -> 현재 환경 `63 passed, 1 warning`
- UTF-8/BOM/U+FFFD 회귀는 `tests/test_encoding_audit.py`가 검사
- `PyMuPDF` 미설치 환경에서는 PDF 엔진 의존 테스트만 skip되고, 나머지 회귀 테스트는 계속 실행

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
  - UI 하드코딩 문자열 및 i18n 키 누락 스모크 검증

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
- `tests/_deps.py`
  - PyQt6/PyMuPDF 의존성 체크를 공용 helper로 통합
- 현재 워크트리 기준 `python -m pytest`: `63 passed, 1 warning`

---

## 🚀 빌드 가이드

```bash
# 빌드 실행
pyinstaller pdf_master.spec --clean

# 결과물
dist/PDF_Master_v4.5.4.exe (~30-40MB)
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

*이 문서는 PDF Master v4.5.4 기준으로 작성되었습니다. (2026-03-18)*
