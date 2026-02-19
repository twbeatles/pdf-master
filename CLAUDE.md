# PDF Master - Claude AI 가이드

> 이 문서는 PDF Master 프로젝트를 Claude AI가 이해하고 효과적으로 지원할 수 있도록 작성된 가이드입니다.

---

## 📌 프로젝트 개요

**PDF Master v4.5**는 PyQt6 기반의 올인원 PDF 편집 데스크톱 애플리케이션입니다.

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
pdf-master-main/
├── main.py                    # 애플리케이션 진입점
├── pdf_master.spec            # PyInstaller 빌드 설정
├── README.md                  # 프로젝트 설명서
└── src/
    ├── __init__.py
    ├── core/                  # 핵심 비즈니스 로직
    │   ├── __init__.py
    │   ├── ai_service.py      # Gemini AI 서비스
    │   ├── constants.py       # 상수 정의
    │   ├── i18n.py            # 다국어 지원 (v4.4)
    │   ├── settings.py        # 설정 관리
    │   ├── undo_manager.py    # Undo/Redo 관리
    │   └── worker.py          # PDF 작업 스레드
    └── ui/                              # UI 컴포넌트
        ├── __init__.py
        ├── main_window.py               # 메인 윈도우 조립/수명주기
        ├── main_window_config.py        # 앱 상수/AI 가용성
        ├── main_window_core.py          # 메뉴/헤더/테마/단축키
        ├── main_window_preview.py       # 미리보기/최근 파일
        ├── main_window_worker.py        # Worker 연결/오버레이
        ├── main_window_undo.py          # Undo/Redo/백업 정리
        ├── main_window_tabs_basic.py    # 기본 탭 (병합/변환/페이지/보안/순서/배치)
        ├── main_window_tabs_advanced.py # 고급 탭 (편집/추출/마크업/기타)
        ├── main_window_tabs_ai.py       # AI 탭/채팅/키워드/그리드
        ├── progress_overlay.py          # 진행 오버레이
        ├── styles.py                    # 테마 스타일시트
        ├── thumbnail_grid.py            # 썸네일 그리드
        ├── widgets.py                   # 커스텀 위젯
        └── zoomable_preview.py          # 줌/패닝 미리보기
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

### 2. `src/core/worker.py` - PDF 작업 스레드 (2342줄)

`WorkerThread` 클래스는 모든 PDF 작업을 백그라운드에서 처리합니다.

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

#### v4.5.1 안정화 핵심 (2026-02-19)
- `run()` 시작 시 `_preflight_inputs()`를 통해 입력 파일 존재/크기를 선검증합니다.
- `_normalize_mode_kwargs()`를 통해 UI/Worker 간 kwargs 계약 차이를 런타임에서 정규화합니다.
- 다음 모드는 구/신 kwargs를 양방향으로 수용합니다:
  - `draw_shapes`
  - `add_link`
  - `insert_textbox`
  - `copy_page_between_docs`
  - `image_watermark`

#### 취소 처리
```python
def cancel(self):
    self._cancel_requested = True

def _check_cancelled(self):
    if self._cancel_requested:
        raise CancelledError()
```

---

### 3. `src/core/ai_service.py` - Gemini AI 서비스 (574줄)

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
try:
    from google import genai
except ImportError:
    try:
        import google.generativeai
    except ImportError:
        pass
```

#### 예외 클래스
- `AIServiceError` - 기본 예외
- `APIKeyError` - API 키 오류
- `APITimeoutError` - 타임아웃
- `APIRateLimitError` - Rate limit 초과

---

### 4. `src/core/settings.py` - 설정 관리 (149줄)

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
    "recent_files": [],
    "last_output_dir": "",
    "splitter_sizes": None,
    "window_geometry": None,
}
```

---

### 5. `src/core/constants.py` - 상수 정의 (133줄)

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

### 6. `src/core/undo_manager.py` - Undo/Redo 관리 (178줄)

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

### 7. `src/core/i18n.py` - 다국어 지원 (v4.4, 1087줄)

- **TranslationManager**: 싱글톤 번역 관리자
- **기능**:
  - `tm.get(key)`: 키 기반 번역 문자열 반환
  - `locale` 자동 감지 (KO/EN, v4.5.1: `getlocale + env fallback`)
  - 언어 설정 관리 (`language` setting)
- **리소스**: `TRANSLATIONS` 딕셔너리에 언어별(ko, en) 문자열 정의

---

### 8. `src/ui/main_window.py` - 메인 윈도우 조립

`PDFMasterApp`는 여러 믹스인으로 분리된 UI/기능 모듈을 조립합니다.

- `main_window.py`: QMainWindow 구성, `__init__`, `closeEvent`
- `main_window_config.py`: `APP_NAME`, `VERSION`, `AI_AVAILABLE` 등 상수
- `main_window_core.py`: 메뉴/헤더/테마/단축키
- `main_window_preview.py`: 미리보기 렌더링/최근 파일
- `main_window_worker.py`: Worker 연결, 진행 오버레이, 성공/실패 처리
- `main_window_undo.py`: Undo/Redo, 백업 관리
- `main_window_tabs_basic.py`: 기본 탭 구성 및 액션
- `main_window_tabs_advanced.py`: 고급 탭/서브탭 및 액션
- `main_window_tabs_ai.py`: AI 탭/채팅/키워드/썸네일 그리드

---

### 9. `src/ui/styles.py` - 테마 스타일시트 (846줄)

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

### 10. `src/ui/widgets.py` - 커스텀 위젯 (731줄)

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

### 11. `src/ui/progress_overlay.py` - 진행 오버레이 (281줄)

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

### 12. `src/ui/thumbnail_grid.py` - 썸네일 그리드 (397줄)

```python
class ThumbnailLoaderThread(QThread):
    """백그라운드 썸네일 로딩"""
    thumbnail_ready = pyqtSignal(int, QPixmap)
    loading_complete = pyqtSignal()
    
class ThumbnailLabel(QLabel):
    """클릭 가능한 썸네일"""
    clicked = pyqtSignal(int)
    
class ThumbnailGridWidget(QWidget):
    """PDF 페이지 그리드 표시"""
    pageSelected = pyqtSignal(int)
    
    def load_pdf(pdf_path: str)
    def select_page(index: int)
```

---

### 13. `src/ui/zoomable_preview.py` - 줌/패닝 미리보기 (399줄)

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

---

## 🧪 테스트 업데이트 (v4.5.1)

- `tests/test_worker_param_compat.py`
  - 고급 기능 kwargs 호환성 검증 (도형/링크/텍스트박스/페이지복사/이미지워터마크)
- `tests/test_worker_preflight.py`
  - 실행 전 입력 검증(fail-fast) 검증
- `tests/test_i18n.py`
  - 비권장 `locale.getdefaultlocale()` 미사용 경로 검증

---

## 🚀 빌드 가이드

```bash
# 빌드 실행
pyinstaller pdf_master.spec --clean

# 결과물
dist/PDF_Master_v4.5.exe (~30-40MB)
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

*이 문서는 PDF Master v4.5 기준으로 작성되었습니다. (2026-01-22)*
