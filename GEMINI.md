# GEMINI.md - PDF Master v4.5 AI 가이드

이 문서는 AI 어시스턴트(Gemini)가 PDF Master 프로젝트를 이해하고 개발을 지원하기 위한 가이드입니다.

---

## 📋 프로젝트 개요

**PDF Master**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

### 기본 정보

| 항목 | 내용 |
|------|------|
| **버전** | v4.5 |
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
pdf-master-main/
├── main.py                    # 애플리케이션 진입점
├── pdf_master.spec            # PyInstaller 빌드 설정
├── README.md                  # 프로젝트 문서
├── CLAUDE.md                  # Claude AI 가이드
├── GEMINI.md                  # Gemini AI 가이드 (이 파일)
└── src/
    ├── __init__.py
    ├── core/                  # 핵심 비즈니스 로직
    │   ├── ai_service.py      # Gemini AI 서비스
    │   ├── constants.py       # 전역 상수
    │   ├── i18n.py            # 다국어 지원
    │   ├── settings.py        # 설정 관리
    │   ├── undo_manager.py    # Undo/Redo 관리
    │   └── worker.py          # PDF 작업 워커 스레드
    └── ui/                              # 사용자 인터페이스
        ├── main_window.py               # 메인 윈도우 조립/수명주기
        ├── main_window_config.py        # 앱 상수/AI 가용성
        ├── main_window_core.py          # 메뉴/헤더/테마/단축키
        ├── main_window_preview.py       # 미리보기/최근 파일
        ├── main_window_worker.py        # Worker 연결/오버레이
        ├── main_window_undo.py          # Undo/Redo/백업 정리
        ├── main_window_tabs_basic.py    # 기본 탭 (병합/변환/페이지/보안/순서/배치)
        ├── main_window_tabs_advanced.py # 고급 탭 (편집/추출/마크업/기타)
        ├── main_window_tabs_ai.py       # AI 탭/채팅/키워드/그리드
        ├── progress_overlay.py          # 진행률 오버레이
        ├── styles.py                    # 테마/스타일
        ├── thumbnail_grid.py            # 썸네일 그리드
        ├── widgets.py                   # 커스텀 위젯
        └── zoomable_preview.py          # 줌 가능 미리보기
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
| `merge` | PDF 병합 | `pdf_list`, `output_path` |
| `convert_to_img` | PDF → 이미지 | `pdf_path`, `output_dir`, `format`, `dpi` |
| `extract_text` | 텍스트 추출 | `pdf_path` |
| `split` | PDF 분할 (범위) | `pdf_path`, `page_range`, `output_path` |
| `split_by_pages` | 페이지별 분할 | `pdf_path`, `output_dir` |
| `delete_pages` | 페이지 삭제 | `pdf_path`, `page_range`, `output_path` |
| `rotate` | 페이지 회전 | `pdf_path`, `angle`, `page_range` |
| `watermark` | 텍스트 워터마크 | `pdf_path`, `text`, `options` |
| `image_watermark` | 이미지 워터마크 | `pdf_path`, `image_path` |
| `add_page_numbers` | 페이지 번호 | `pdf_path`, `position`, `format` |
| `compress` | PDF 압축 | `pdf_path`, `level` |
| `protect` | PDF 암호화 | `pdf_path`, `password` |
| `images_to_pdf` | 이미지 → PDF | `image_list`, `output_path` |
| `reorder` | 페이지 순서변경 | `pdf_path`, `new_order` |
| `add_stamp` | 스탬프 추가 | `pdf_path`, `stamp_text`, `position` |
| `ai_summarize` | AI 요약 | `pdf_path`, `api_key` |
| `ai_ask_question` | AI PDF 채팅 (v4.5) | `pdf_path`, `api_key`, `question` |
| `ai_extract_keywords` | AI 키워드 추출 (v4.5) | `pdf_path`, `api_key`, `max_keywords` |
| `draw_shapes` | 도형 그리기 (v4.5) | `pdf_path`, `shape_type`, `x`, `y` |
| `add_link` | 하이퍼링크 추가 (v4.5) | `pdf_path`, `link_type`, `target`, `rect` |
| `insert_textbox` | 텍스트 상자 (v4.5) | `pdf_path`, `text`, `x`, `y` |
| `copy_page_between_docs` | 페이지 복사 (v4.5) | `file_path`, `source_path`, `page_range` |

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
- `TranslationManager().get("key")`로 사용
- `active_lang_code` 속성으로 현재 언어 확인
```

### 7. `src/ui/main_window.py` - PDFMasterApp

메인 애플리케이션 윈도우입니다.

**믹스인 구성 (UI 분리 구조):**
- `main_window.py`: QMainWindow 구성, `__init__`, `closeEvent`
- `main_window_config.py`: 앱 상수/AI 가용성
- `main_window_core.py`: 메뉴/헤더/테마/단축키
- `main_window_preview.py`: 미리보기/최근 파일
- `main_window_worker.py`: Worker 연결/오버레이/성공·실패 처리
- `main_window_undo.py`: Undo/Redo, 백업 정리
- `main_window_tabs_basic.py`: 기본 탭 UI/액션
- `main_window_tabs_advanced.py`: 고급 탭 UI/액션
- `main_window_tabs_ai.py`: AI 탭 UI/액션

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
    
    def load_pdf(pdf_path: str)
    def select_page(index: int)
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

1. `WorkerThread.run()`에 모드 분기 추가
2. 새 메서드 구현:

```python
def new_operation(self):
    try:
        pdf_path = self.kwargs['pdf_path']
        doc = fitz.open(pdf_path)
        
        try:
            for i, page in enumerate(doc):
                self._check_cancelled()
                # 작업 수행...
                self.progress_signal.emit(int((i + 1) / len(doc) * 100))
            
            doc.save(output_path, garbage=4, deflate=True)
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
# 결과: dist/PDF_Master_v4.5.exe (~30-40MB)
```

---

## 📝 파일별 라인 수

| 파일 | 라인 수 | 설명 |
|------|--------|------|
| `main.py` | 82 | 진입점 |
| `src/core/worker.py` | 2342 | PDF 작업 워커 |
| `src/core/ai_service.py` | 574 | AI 서비스 |
| `src/core/settings.py` | 149 | 설정 관리 |
| `src/core/constants.py` | 133 | 상수 |
| `src/core/undo_manager.py` | 178 | Undo/Redo |
| `src/core/i18n.py` | 1087 | 다국어 지원 |
| `src/ui/main_window.py` | 205 | 메인 윈도우 조립 |
| `src/ui/main_window_config.py` | 15 | 앱 상수 |
| `src/ui/main_window_core.py` | 339 | 메뉴/헤더/테마/단축키 |
| `src/ui/main_window_preview.py` | 285 | 미리보기/최근 파일 |
| `src/ui/main_window_worker.py` | 260 | Worker 연결/오버레이 |
| `src/ui/main_window_undo.py` | 234 | Undo/Redo/백업 정리 |
| `src/ui/main_window_tabs_basic.py` | 828 | 기본 탭 |
| `src/ui/main_window_tabs_advanced.py` | 1386 | 고급 탭 |
| `src/ui/main_window_tabs_ai.py` | 526 | AI 탭 |
| `src/ui/styles.py` | 846 | 테마/스타일 |
| `src/ui/widgets.py` | 731 | 커스텀 위젯 |
| `src/ui/progress_overlay.py` | 281 | 진행 오버레이 |
| `src/ui/thumbnail_grid.py` | 397 | 썸네일 그리드 |
| `src/ui/zoomable_preview.py` | 399 | 줌 미리보기 |

---

## 🚀 버전 히스토리

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

*이 문서는 PDF Master v4.5 기준으로 작성되었습니다. (2026-01-22)*
