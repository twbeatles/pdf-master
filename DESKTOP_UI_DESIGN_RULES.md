# KTrain-Compatible Desktop Qt UI Design Rules
## PySide6 / PyQt6 데스크톱 앱 공통 에이전트 지시서 — Strict KTrain Profile

> **목표:** 모든 Qt 데스크톱 앱을 `twbeatles/ktrain`과 **같은 제품군으로 보일 정도로 유사한 UI/UX**로 구축한다.
>
> 단순히 “Fluent 느낌”을 내는 것이 아니다. KTrain의 실제 GUI 구조인 `MSFluentWindow`, Fluent Navigation, `HeaderCardWidget`, `Pivot`, `InfoBar`, 화면 여백, 작업 상태 표현, 다크/라이트 연동, HiDPI 처리까지 기본 구현 계약으로 재현한다.

---

# 0. 문서 우선순위와 강제 수준

이 문서는 일반적인 디자인 참고자료가 아니라 **UI 구현 계약(Design Contract)** 이다.

에이전트는 UI 신규 구현, UI 전면 재구축, 화면 현대화, 디자인 통일 작업을 수행할 때 다음 문장을 기본 요구사항으로 해석한다.

```text
이 앱을 KTrain과 같은 개발자가 만든 동일 제품군 앱처럼 보이게 만든다.
```

이 문서 앞부분의 **Strict KTrain Profile**이 뒤쪽의 일반적인 디자인 원칙보다 우선한다. 서로 충돌할 경우 KTrain Profile을 적용한다.

사용자가 별도 스타일을 명시하지 않는 한 에이전트는 새로운 디자인 언어를 발명하지 않는다.

---

# 1. Canonical Reference — 반드시 먼저 볼 KTrain 파일

KTrain 저장소에 접근 가능한 경우 UI 작업 전에 다음 파일을 먼저 읽는다.

```text
ktrain/gui/app.py
ktrain/gui/main_window.py
ktrain/gui/theme.py
ktrain/gui/qt_binding.py

ktrain/gui/pages/booking/base.py
ktrain/gui/pages/booking/base_shell.py
ktrain/gui/pages/booking/base_train_list.py

ktrain/gui/pages/reservation_page.py

ktrain/gui/pages/settings/page.py
ktrain/gui/pages/settings/login_tab.py
ktrain/gui/pages/settings/card_tab.py
ktrain/gui/pages/settings/options_tab.py

ktrain/gui/pages/update_page.py
```

이 문서와 KTrain 코드가 다를 경우 **현재 KTrain 코드의 구조와 동작을 우선 참고**하되, 기존 프로젝트의 비즈니스 로직은 보존한다.

KTrain 저장소에 접근할 수 없는 환경에서는 이 문서에 포함된 수치와 코드 골격을 기준으로 구현한다.

---

# 2. 기본 기술 스택 — 전면 UI 재구축의 표준

UI를 새로 만들거나 전면 재구축할 때 기본 스택은 다음과 같다.

```text
Python
PySide6
PySide6-Fluent-Widgets
```

권장 `pyproject.toml`:

```toml
[project.optional-dependencies]
gui = [
    "PySide6>=6.6,<7",
    "PySide6-Fluent-Widgets>=1.6,<2",
    "darkdetect>=0.8,<1",
]

dev = [
    "pytest>=8",
    "pytest-qt>=4.4",
    "pytest-timeout>=2.3",
]

build = [
    "pyinstaller>=6.3",
]
```

기본 설치 예:

```bash
pip install PySide6 PySide6-Fluent-Widgets darkdetect
```

프로젝트가 optional dependency를 제공하면 다음 방식을 우선한다.

```bash
pip install -e ".[gui]"
```

`superqt`, `qt-material`, 별도 테마 라이브러리는 기본 의존성이 아니다. KTrain과 동일한 UI를 만드는 데 실제로 필요한 경우에만 추가한다.

---

# 3. 기존 PyQt6 프로젝트 처리

단순 버그 수정이나 작은 UI 수정에서는 기존 Qt binding을 유지할 수 있다.

그러나 사용자의 요청이 다음에 해당하면:

```text
UI 전면 재구축
KTrain 스타일로 변경
디자인 통일
UI 현대화
메인 화면/Navigation 개편
```

**특별한 기술적 제약이 없는 한 PySide6 + PySide6-Fluent-Widgets로 전환하는 것을 기본값으로 한다.**

PyQt6 유지를 허용하는 사유:

- PyQt6 전용 외부 라이브러리에 강하게 종속되어 있음
- binding 전환이 핵심 기능 안정성을 크게 위협함
- 사용자가 PyQt6 유지를 명시함
- 배포/플러그인 환경이 PyQt6에 고정되어 있음

PyQt6를 유지해야 한다면 `PyQt6-Fluent-Widgets`를 사용하되 **화면 구조와 디자인 규칙은 본 문서와 동일하게** 적용한다.

---

# 4. Fluent Binding 충돌 방지

`PySide6-Fluent-Widgets`와 `PyQt6-Fluent-Widgets`는 모두 다음 namespace를 사용한다.

```python
import qfluentwidgets
```

따라서 PySide6 프로젝트에서 다음 배포판이 함께 설치되어 있으면 충돌 위험으로 간주한다.

```text
PyQt6-Fluent-Widgets
PyQt5-Fluent-Widgets
PyQt-Fluent-Widgets
PyQt6-Frameless-Window
PyQt5-Frameless-Window
```

필요하면 정리한다.

```bash
pip uninstall PyQt6-Fluent-Widgets PyQt6-Frameless-Window \
              PyQt5-Fluent-Widgets PyQt5-Frameless-Window
pip install PySide6 PySide6-Fluent-Widgets
```

배포 앱에서는 KTrain의 `ktrain/gui/qt_binding.py`와 같은 validation을 두는 것을 권장한다.

에이전트는 `qfluentwidgets`가 실제로 어느 binding을 참조하는지 확인하지 않은 상태에서 PyInstaller 문제를 임의 수정하지 않는다.

---

# 5. 목표 UI의 시각 프로필

최종 UI는 다음 특성을 가져야 한다.

```text
Windows Fluent 스타일
낮은 시각적 노이즈
업무용 데스크톱 앱 밀도
좌측 Fluent Navigation
명확한 Primary / Secondary Action
16~24px 중심의 여백
필요한 영역에만 HeaderCardWidget
OS 다크/라이트 자동 연동
InfoBar 기반 비차단 피드백
긴 작업은 Worker Thread
HiDPI와 창 Resize 대응
```

다음 결과는 실패로 간주한다.

```text
웹 대시보드 같은 과도한 카드 UI
Material Design이 강하게 드러나는 UI
Bootstrap 느낌
Glassmorphism
Gradient
큰 Drop Shadow
과도한 Border Radius
모든 버튼이 Primary 색상
화면별 제각각인 Margin
Emoji icon
거대한 전역 QSS 테마
```

---

# 6. QApplication 진입점 — KTrain 방식 그대로

앱 시작 순서는 다음을 유지한다.

```text
1. GUI dependency / binding 확인
2. HiDPI 정책 설정
3. QApplication 생성
4. applicationName / organizationName 설정
5. App icon 설정
6. Theme 초기화
7. MainWindow 생성
8. show()
9. app.exec()
```

권장 골격:

```python
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


def configure_high_dpi() -> None:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def main() -> None:
    from .icon import get_app_icon
    from .main_window import MainWindow
    from .theme import setup_app_theme

    configure_high_dpi()

    app = QApplication(sys.argv)
    app.setApplicationName("APP_NAME")
    app.setOrganizationName("APP_NAME")
    app.setWindowIcon(get_app_icon())

    setup_app_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
```

Theme을 MainWindow 생성 후 적용하지 않는다.

---

# 7. MainWindow — MSFluentWindow를 기본으로 강제

KTrain과 같은 전체 인상을 만들기 위해 MainWindow는 원칙적으로 다음을 사용한다.

```python
class MainWindow(MSFluentWindow):
    ...
```

호환 fallback:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qfluentwidgets import FluentWindow as MSFluentWindow
else:
    try:
        from qfluentwidgets import MSFluentWindow
    except ImportError:
        from qfluentwidgets import FluentWindow as MSFluentWindow
```

특별한 이유 없이 `QMainWindow + 자체 Sidebar`를 새로 만들지 않는다.

---

# 8. KTrain Window Profile — 숫자까지 동일하게

다음을 기본값으로 사용한다.

```python
_DEFAULT_WINDOW_WIDTH = 1100
_DEFAULT_WINDOW_HEIGHT = 800
_MIN_WINDOW_WIDTH = 640
_MIN_WINDOW_HEIGHT = 560
_SCREEN_MARGIN = 40
```

창 크기는 화면 가용 영역을 고려한다.

```python
def preferred_window_size(
    avail_width: int,
    avail_height: int,
) -> tuple[int, int]:
    width = min(
        _DEFAULT_WINDOW_WIDTH,
        max(_MIN_WINDOW_WIDTH, avail_width - _SCREEN_MARGIN),
    )
    height = min(
        _DEFAULT_WINDOW_HEIGHT,
        max(_MIN_WINDOW_HEIGHT, avail_height - _SCREEN_MARGIN),
    )
    return width, height
```

다음과 같은 대형 창 강제는 피한다.

```text
1400x900 고정
1600x1000 고정
최소 크기 1200px 이상
```

---

# 9. Main Navigation — KTrain과 같은 배치

주요 페이지는 `addSubInterface()`를 사용한다.

```python
self.addSubInterface(
    self.main_page,
    FIF.HOME,
    "메인",
)
```

설정과 업데이트는 KTrain처럼 하단에 둔다.

```python
self.addSubInterface(
    self.settings_page,
    FIF.SETTING,
    "설정",
    position=NavigationItemPosition.BOTTOM,
)

self.addSubInterface(
    self.update_page,
    FIF.UPDATE,
    "업데이트",
    position=NavigationItemPosition.BOTTOM,
)
```

상단 Navigation:

```text
핵심 기능
검색
변환
처리
결과
내역
```

하단 Navigation:

```text
설정
업데이트
정보
```

금지:

```text
직접 만든 QWidget Sidebar
세로 QPushButton 묶음 Sidebar
QTabWidget을 전체 앱 Navigation으로 사용
```

---

# 10. MainWindow 권장 완성형

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QGuiApplication
from qfluentwidgets import (
    FluentIcon as FIF,
    NavigationItemPosition,
    setThemeColor,
)

if TYPE_CHECKING:
    from qfluentwidgets import FluentWindow as MSFluentWindow
else:
    try:
        from qfluentwidgets import MSFluentWindow
    except ImportError:
        from qfluentwidgets import FluentWindow as MSFluentWindow

from .icon import get_app_icon
from .theme import configure_fluent_window

_DEFAULT_WINDOW_WIDTH = 1100
_DEFAULT_WINDOW_HEIGHT = 800
_MIN_WINDOW_WIDTH = 640
_MIN_WINDOW_HEIGHT = 560
_SCREEN_MARGIN = 40


def preferred_window_size(avail_width: int, avail_height: int) -> tuple[int, int]:
    width = min(_DEFAULT_WINDOW_WIDTH, max(_MIN_WINDOW_WIDTH, avail_width - _SCREEN_MARGIN))
    height = min(_DEFAULT_WINDOW_HEIGHT, max(_MIN_WINDOW_HEIGHT, avail_height - _SCREEN_MARGIN))
    return width, height


class MainWindow(MSFluentWindow):
    def __init__(self) -> None:
        super().__init__()

        configure_fluent_window(self)
        setThemeColor("#0078D4")

        self.setWindowTitle("APP_NAME")
        self.setWindowIcon(get_app_icon())

        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        width, height = preferred_window_size(
            avail.width() if avail is not None else _DEFAULT_WINDOW_WIDTH,
            avail.height() if avail is not None else _DEFAULT_WINDOW_HEIGHT,
        )
        self.resize(width, height)
        self.setMinimumSize(
            min(_MIN_WINDOW_WIDTH, width),
            min(_MIN_WINDOW_HEIGHT, height),
        )

        self.main_page = MainPage(self)
        self.history_page = HistoryPage(self)
        self.settings_page = SettingsPage(self)

        self.main_page.setObjectName("mainInterface")
        self.history_page.setObjectName("historyInterface")
        self.settings_page.setObjectName("settingsInterface")

        self.addSubInterface(self.main_page, FIF.HOME, "메인")
        self.addSubInterface(self.history_page, FIF.HISTORY, "내역")
        self.addSubInterface(
            self.settings_page,
            FIF.SETTING,
            "설정",
            position=NavigationItemPosition.BOTTOM,
        )
```

`setThemeColor()`의 색상은 앱 Brand Color가 있으면 바꿀 수 있지만, 별도 이유가 없으면 Windows Fluent 계열 Blue를 기본으로 한다.

---

# 11. Theme — KTrain 방식 복제

`theme.py`를 별도 파일로 둔다.

기본 초기화:

```python
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import Theme, setTheme


def setup_app_theme(app: QApplication) -> None:
    setTheme(Theme.AUTO)
    sync_system_theme()
    _install_theme_watcher(app)
```

OS theme 동기화:

```python
def sync_system_theme() -> None:
    try:
        import darkdetect
        system = darkdetect.theme()
    except Exception:
        return

    if system == "Dark":
        setTheme(Theme.DARK)
    elif system == "Light":
        setTheme(Theme.LIGHT)
```

Watcher:

```python
def _install_theme_watcher(app: QApplication) -> None:
    hints = QGuiApplication.styleHints()

    if hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(
            lambda _scheme: QTimer.singleShot(0, sync_system_theme)
        )

    timer = QTimer(app)
    timer.timeout.connect(sync_system_theme)
    timer.start(3000)
```

---

# 12. Mica 기본 비활성

KTrain처럼 환경별 배경 깨짐을 피하기 위해 Mica는 기본적으로 끈다.

```python
def configure_fluent_window(window: QWidget) -> None:
    set_mica = getattr(window, "setMicaEffectEnabled", None)
    if callable(set_mica):
        try:
            set_mica(False)
        except Exception:
            pass
```

사용자가 명시적으로 요구하지 않는 한:

```text
Mica = OFF
```

---

# 13. KTrain Layout Density — 핵심 수치

이 값은 전체 프로젝트의 기본 SSOT로 취급한다.

```python
WINDOW_DEFAULT_WIDTH = 1100
WINDOW_DEFAULT_HEIGHT = 800
WINDOW_MIN_WIDTH = 640
WINDOW_MIN_HEIGHT = 560
SCREEN_MARGIN = 40

PAGE_MARGIN = 24
WORK_PAGE_MARGIN = 16
DEFAULT_SPACING = 8
SECTION_SPACING = 16

CARD_VIEW_MARGINS = (12, 8, 12, 12)
SPLITTER_HANDLE_WIDTH = 8

CONDITION_PANEL_MIN_WIDTH = 400
RESULT_PANEL_MIN_WIDTH = 360

PROGRESS_RING_SIZE = 28
TABLE_ROW_MIN_HEIGHT = 40
```

일반 페이지:

```python
layout.setContentsMargins(24, 24, 24, 24)
```

조건 + 결과형 작업 페이지:

```python
root.setContentsMargins(16, 16, 16, 16)
root.setSpacing(0)
```

기본 위젯/행 간격:

```python
layout.setSpacing(8)
```

Grid가 넓어야 할 때:

```python
grid.setHorizontalSpacing(16)
grid.setVerticalSpacing(8)
```

---

# 14. KTrain 작업 화면 — QSplitter + HeaderCardWidget

조건과 결과가 함께 있는 앱은 다음 형태를 기본으로 한다.

```text
┌──────────────────────────────────────────────┐
│ Fluent Navigation                            │
├──────────────────────────────────────────────┤
│                                              │
│ ┌──────────────┐  ┌────────────────────────┐ │
│ │ 조건 Card     │  │ 결과 Card               │ │
│ │              │  │                        │ │
│ │ 입력 Form     │  │ Header Toolbar         │ │
│ │              │  │                        │ │
│ │ Scroll       │  │ Table / Result         │ │
│ │              │  │                        │ │
│ │ Action Bar   │  │                        │ │
│ │ Status       │  │                        │ │
│ └──────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────┘
```

루트:

```python
root = QHBoxLayout(self)
root.setContentsMargins(16, 16, 16, 16)
root.setSpacing(0)
```

Splitter:

```python
splitter = QSplitter(Qt.Orientation.Horizontal, self)
splitter.setChildrenCollapsible(False)
splitter.setHandleWidth(8)
```

왼쪽 Card:

```python
left_card = HeaderCardWidget("작업 조건", self)
left_card.setMinimumWidth(400)
left_card.viewLayout.setContentsMargins(12, 8, 12, 12)
```

오른쪽 Card:

```python
right_card = HeaderCardWidget("결과", self)
right_card.setMinimumWidth(360)
right_card.viewLayout.setContentsMargins(12, 8, 12, 12)
```

Header toolbar:

```python
right_card.headerLayout.addStretch()
right_card.headerLayout.addWidget(filter_widget)
right_card.headerLayout.addWidget(sort_widget)
right_card.headerLayout.addWidget(action_button)
```

---

# 15. Scrollable Condition Panel + 고정 Action Bar

조건이 길면 Card 내부 Form만 Scroll하고 핵심 Action Bar는 아래에 고정한다.

```python
scroll = QScrollArea(parent)
scroll.setWidgetResizable(True)
scroll.setFrameShape(QFrame.Shape.NoFrame)
scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
```

Form:

```python
form_layout.setSpacing(8)
form_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
```

Action:

```python
self.run_btn = PrimaryPushButton("실행", self)
self.secondary_btn = PushButton("보조 작업", self)
self.cancel_btn = PushButton("진행 중단", self)
```

작업 상태:

```python
self.progress_ring = ProgressRing(self)
self.progress_ring.setFixedSize(28, 28)
self.progress_ring.hide()
self.status_label = BodyLabel("대기 중", self)
```

---

# 16. List + Detail Page — KTrain Reservation 패턴

목록/상세 화면은 다음 구성을 기본으로 한다.

```text
SubtitleLabel   Toggle...                     Primary Action

List (1)              Detail (2)
                      Secondary Actions
```

페이지:

```python
layout = QVBoxLayout(self)
layout.setContentsMargins(24, 24, 24, 24)
```

Header:

```python
header = QHBoxLayout()
header.addWidget(SubtitleLabel("내역"))
header.addWidget(option_button)
header.addStretch()
header.addWidget(primary_button)
```

Body:

```python
body.addWidget(list_widget, 1)
body.addWidget(detail_panel, 2)
```

**목록 : 상세 = 1 : 2**를 기본 비율로 사용한다.

---

# 17. Settings Page — ScrollArea + Pivot + QStackedWidget

KTrain과 같은 설정 화면을 만들려면 다음 구조를 기본으로 한다.

```python
class SettingsPage(ScrollArea):
    ...
```

Container:

```python
self.setWidgetResizable(True)
container = QWidget()
self.setWidget(container)
layout = QVBoxLayout(container)
layout.setContentsMargins(0, 0, 0, 0)
```

Pivot:

```python
self.pivot = Pivot(self)
self.stacked = QStackedWidget(self)
```

탭 등록:

```python
self.pivot.addItem("general", "일반")
self.stacked.addWidget(self.general_tab)
```

Pivot Row:

```python
pivot_row = QHBoxLayout()
pivot_row.addWidget(self.pivot)
pivot_row.addStretch()
layout.addLayout(pivot_row)
layout.addWidget(self.stacked)
```

각 설정 Tab은 다음 여백을 기본으로 한다.

```python
layout = QVBoxLayout(self)
layout.setContentsMargins(24, 24, 24, 24)
```

설정 화면을 하나의 거대한 Form으로 평면 배치하지 않는다.

---

# 18. Settings Tab의 KTrain형 입력 배치

동등한 두 입력:

```python
row = QHBoxLayout()
row.setSpacing(8)
row.addWidget(self.username, 1)
row.addWidget(self.password, 1)
```

Grid:

```python
grid = QGridLayout()
grid.setHorizontalSpacing(8)
grid.setVerticalSpacing(8)
```

비율이 다른 필드:

```python
grid.setColumnStretch(0, 2)
grid.setColumnStretch(1, 1)
```

저장 버튼:

```python
PrimaryPushButton("저장", self)
```

저장 성공:

```python
InfoBar.success(...)
```

---

# 19. 컴포넌트 매핑 — 가능한 한 KTrain과 동일하게

| 목적 | 기본 컴포넌트 |
|---|---|
| 페이지 제목 | `SubtitleLabel` |
| 일반 설명/상태 | `BodyLabel` |
| 문자열 입력 | `LineEdit` |
| 비밀번호 | `PasswordLineEdit` |
| 검색 | `SearchLineEdit` |
| 선택 | `ComboBox` |
| 직접 입력 가능한 선택 | `EditableComboBox` |
| 정수 | `SpinBox` |
| On/Off | `SwitchButton` |
| 체크 | 필요 시 `QCheckBox` |
| 여러 줄 텍스트 | `TextEdit` |
| 결과 표 | `TableWidget` |
| 작업 Card | `HeaderCardWidget` |
| 핵심 행동 | `PrimaryPushButton` |
| 보조 행동 | `PushButton` |
| 진행 상태 | `ProgressRing` / `ProgressBar` |
| 일반 알림 | `InfoBar` |
| 확인/위험 작업 | `MessageBox` |
| 설정 내부 탭 | `Pivot` |
| 설정 Scroll | `ScrollArea` |

기본 Qt Widget을 QSS로 꾸며 QFluentWidgets 컴포넌트를 흉내 내지 않는다.

---

# 20. Feedback — InfoBarPosition.TOP을 기본값으로

일반 성공/오류/경고는 KTrain처럼 화면 상단 InfoBar를 사용한다.

```python
InfoBar.success(
    "완료",
    "작업을 완료했습니다.",
    parent=self.window(),
    position=InfoBarPosition.TOP,
)
```

오류:

```python
InfoBar.error(
    "오류",
    message,
    parent=self.window(),
    position=InfoBarPosition.TOP,
)
```

`MessageBox`는 사용자의 결정이 반드시 필요한 경우에만 사용한다.

```text
삭제 여부
작업 취소
프로그램 종료
설치 여부
되돌릴 수 없는 변경
```

단순 저장 완료, 새로고침 완료, 일반 오류에는 MessageBox를 사용하지 않는다.

---

# 21. Worker / Busy State — KTrain 방식

파일 처리, 네트워크, 크롤링, 업데이트 등 시간이 걸리는 작업은 UI thread에서 실행하지 않는다.

기본:

```text
QObject Worker
+
QThread 또는 공통 WorkerThread
+
Signal
```

예:

```python
worker = SomeWorker(...)
thread = WorkerThread(worker)

worker.success.connect(self._on_success)
worker.error.connect(self._on_error)
worker.success.connect(thread.quit)
worker.error.connect(thread.quit)
thread.finished.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.start()
```

Busy 중에는 관련 컨트롤만 잠근다.

```python
self.run_btn.setEnabled(False)
self.cancel_btn.setEnabled(True)
self.progress_ring.show()
self.status_label.setText("처리 중...")
```

완료:

```python
self.run_btn.setEnabled(True)
self.cancel_btn.setEnabled(False)
self.progress_ring.hide()
self.status_label.setText("완료")
```

---

# 22. QSS — KTrain 스타일을 유지하기 위한 강화 규칙

QSS 우선순위:

```text
QFluentWidgets 기본 스타일
> theme.py의 Native Widget 보정
> 정말 필요한 공통 Helper
> 개별 Page QSS (최후 수단)
```

다음은 원칙적으로 금지한다.

```python
self.button.setStyleSheet(...)
self.input.setStyleSheet(...)
self.card.setStyleSheet(...)
self.title.setStyleSheet(...)
```

예외는 KTrain의 도메인 선택 버튼처럼 상태 자체가 색상 의미를 가지며, 재사용 가능한 helper 함수로 중앙 관리할 때뿐이다.

---

# 23. Native Qt Widget 보정

QFluentWidgets로 대체하기 어려운 `QCheckBox`, `QListWidget` 등은 `theme.py`의 공통 함수에서만 보정한다.

```python
def apply_native_widget_style(root: QWidget) -> None:
    ...
```

Theme 변경 시 필요하면:

```python
from qfluentwidgets import qconfig
qconfig.themeChanged.connect(
    lambda: apply_native_widget_style(container)
)
```

Fluent Widget 자체를 이 함수로 다시 디자인하지 않는다.

---

# 24. Table — KTrain 밀도

가능하면 `qfluentwidgets.TableWidget`을 사용한다.

```python
table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
table.verticalHeader().setVisible(False)
table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
```

HiDPI에서 checkbox와 text가 잘리지 않도록 행 높이는 **최소 40px 수준**을 확보한다.

Toolbar를 Table 위에 별도 큰 패널로 만들기보다 `HeaderCardWidget.headerLayout`에 적당히 배치하는 것을 우선한다.

---

# 25. Icon

아이콘은 우선:

```python
from qfluentwidgets import FluentIcon as FIF
```

사용.

```text
FIF.HOME
FIF.SEARCH
FIF.HISTORY
FIF.FOLDER
FIF.SAVE
FIF.SETTING
FIF.UPDATE
FIF.DELETE
```

Emoji는 정식 UI Icon으로 사용하지 않는다.

---

# 26. KTrain 호환 여부 Visual Acceptance Test

최종 UI를 KTrain과 나란히 실행했다고 가정하고 다음 질문에 답한다.

```text
같은 개발자가 만든 앱처럼 보이는가?
Navigation 구조와 밀도가 비슷한가?
Button / Input / Card의 시각 언어가 동일한가?
24px / 16px 여백 체계가 유지되는가?
Settings가 Pivot 구조로 자연스럽게 보이는가?
알림이 InfoBar 중심인가?
Dark/Light에서 동일 제품군처럼 보이는가?
별도 QSS 테마 앱처럼 보이지 않는가?
```

명확한 NO가 있으면 UI 작업을 완료로 간주하지 않는다.

---

# 27. Strict KTrain Profile 요약

```text
Reference             = twbeatles/ktrain
Qt Binding            = PySide6
UI Library            = PySide6-Fluent-Widgets
Main Window           = MSFluentWindow / FluentWindow
Navigation            = addSubInterface
Bottom Navigation     = Settings / Update

Window Default        = 1100 x 800
Window Minimum        = 640 x 560
Screen Margin         = 40

Normal Page Margin    = 24
Work Page Margin      = 16
Default Spacing       = 8
Section Spacing       = 16~24

Work Layout           = QSplitter
Panel                 = HeaderCardWidget
Card View Margin      = 12 / 8 / 12 / 12
Condition Min Width   = 400
Result Min Width      = 360

Primary Action        = PrimaryPushButton
Secondary Action      = PushButton
Notification          = InfoBarPosition.TOP
Confirmation          = MessageBox
Settings              = ScrollArea + Pivot + QStackedWidget

Theme                 = Theme.AUTO
System Theme Sync     = Yes
Mica                  = Off by default
HiDPI                 = PassThrough

Long Task             = QObject Worker + QThread
Busy Indicator        = ProgressRing(28x28) + BodyLabel
Table Row             = >= 40px

Page-level QSS        = Avoid
Native Widget QSS     = Centralized in theme.py
```

---

# 4. 프로젝트 UI 디렉터리 구조

UI 코드가 커지면 최소한 다음 구조로 분리한다.

```text
src/
└─ ui/
   ├─ main_window.py
   ├─ theme.py
   ├─ components/
   │  ├─ __init__.py
   │  ├─ cards.py
   │  ├─ dialogs.py
   │  ├─ empty_state.py
   │  └─ status.py
   │
   ├─ pages/
   │  ├─ home_page.py
   │  ├─ settings_page.py
   │  └─ ...
   │
   └─ resources/
```

규모가 더 크면:

```text
ui/
├─ design_tokens.py
├─ theme.py
├─ components/
├─ pages/
├─ dialogs/
└─ icons/
```

### 책임 분리

`MainWindow`는 다음 역할만 가진다.

- 페이지 구성
- Navigation
- 전역 UI 상태
- tray/window lifecycle
- page 간 coordination

`MainWindow` 안에 다음을 직접 넣지 않는다.

- 대규모 비즈니스 로직
- 네트워크 요청 구현
- 파일 파싱 구현
- DB 처리
- 복잡한 worker 내부 로직
- 수백 줄짜리 개별 페이지 UI

---

# 5. Design Token 규칙

UI에서 임의의 숫자와 색상을 반복해서 쓰지 않는다.

공통 토큰을 정의한다.

예:

```python
SPACE_XXS = 4
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

CONTROL_HEIGHT_SM = 32
CONTROL_HEIGHT_MD = 36
CONTROL_HEIGHT_LG = 40

PAGE_MARGIN = 24
SECTION_GAP = 24
CARD_RADIUS = 8
```

## 간격 기준

기본 spacing scale:

```text
4
8
12
16
24
32
```

가능하면 이 값 외의 임의 spacing을 만들지 않는다.

### 권장값

| 용도 | 값 |
|---|---:|
| 아이콘 ↔ 텍스트 | 8px |
| 작은 control 간 | 8px |
| form row 간 | 12px |
| 관련 control group 간 | 16px |
| section 간 | 24px |
| page 좌우 margin | 24px |
| 대형 section 구분 | 32px |

---

# 6. Typography

폰트 크기는 화면별로 임의 생성하지 않는다.

권장 계층:

```text
Page Title      22~24px / Semibold
Section Title   16~18px / Semibold
Body            13~14px / Regular
Secondary       12~13px / Regular
Caption         11~12px / Regular
```

### 규칙

- 한 페이지에서 제목 크기를 여러 종류로 난립시키지 않는다.
- 굵기는 강조에만 사용한다.
- 설명 텍스트는 primary text보다 한 단계 낮은 명도로 표현한다.
- 버튼 텍스트에 불필요한 bold를 남발하지 않는다.
- 긴 설명은 QLabel 하나에 길게 넣기보다 title + secondary text 형태를 우선한다.

폰트 family는 OS 친화적인 fallback을 사용한다.

예:

```text
Pretendard
Segoe UI
Apple SD Gothic Neo
Malgun Gothic
sans-serif
```

단, 특정 폰트를 앱에 강제로 포함하지 않아도 된다.

---

# 7. Color 규칙

색상은 의미 기반 semantic token으로 관리한다.

```text
primary
background
surface
surface_alt
border
text_primary
text_secondary
success
warning
error
```

## 금지

다음과 같은 코드를 페이지마다 반복하지 않는다.

```python
button.setStyleSheet("background: #3874f2; ...")
label.setStyleSheet("color: #aaa;")
```

대신 theme 또는 component 계층에서 정의한다.

### Accent

한 화면에서 기본 accent는 하나만 사용한다.

예외:

- success
- warning
- error
- 도메인 상태 표현

Brand color가 있다면 primary accent로 사용할 수 있지만, 모든 요소를 해당 색으로 칠하지 않는다.

---

# 8. Light / Dark Theme

가능하면 OS 테마와 연동한다.

QFluentWidgets 사용 시 기본 방향:

```python
setTheme(Theme.AUTO)
```

필요하면 `darkdetect` 또는 Qt의 `colorSchemeChanged`를 이용해 동기화한다.

`ktrain`과 같이 theme 동기화 코드는 별도 모듈로 둔다.

```text
ui/theme.py
```

### 필수 확인

다크 모드에서:

- text contrast
- disabled text
- table header
- input border
- selected row
- checkbox
- list widget
- error/warning status

라이트 모드에서도 동일하게 확인한다.

---

# 9. QSS 사용 규칙

QSS는 **최후의 보정 수단**이다.

QFluentWidgets가 제공하는 component를 QSS로 다시 그리지 않는다.

## 허용

- Qt 기본 위젯과 Fluent 위젯 사이의 시각적 차이 보정
- 특정 native widget의 dark mode 대비 보정
- 라이브러리에서 제공하지 않는 최소한의 상태 표현
- 프로젝트 전체에 적용되는 공통 token 기반 스타일

## 금지

페이지마다 다음과 같은 방식:

```python
widget.setStyleSheet(...)
button.setStyleSheet(...)
label.setStyleSheet(...)
```

특히 조건문에 따라 inline QSS 문자열을 계속 생성하지 않는다.

불가피하다면 공통 helper로 이동한다.

---

# 10. Component 선택 원칙

가능하면 Fluent component를 우선 사용한다.

예:

```text
PushButton
PrimaryPushButton
ToolButton
LineEdit
SearchLineEdit
ComboBox
SpinBox
SwitchButton
CheckBox
ProgressBar
ProgressRing
InfoBar
MessageBox
CardWidget
SimpleCardWidget
SettingCard
HeaderCardWidget
```

기본 Qt widget을 써야 할 이유가 없다면 직접 `QPushButton` 등을 꾸며 재구현하지 않는다.

---

# 11. Button 규칙

버튼은 중요도에 따라 구분한다.

## Primary

화면의 핵심 행동.

예:

```text
검색
변환 시작
저장
실행
적용
```

한 화면 또는 한 section에서 primary action은 원칙적으로 하나만 둔다.

## Secondary

보조 행동.

```text
취소
폴더 열기
초기화
새로고침
추가 설정
```

## Destructive

삭제, 초기화, 데이터 제거 등.

일반 primary 색상을 사용하지 않는다.

필요하면 확인 절차를 둔다.

### 금지

한 줄에 다음처럼 모든 버튼이 동일 강조도를 갖게 하지 않는다.

```text
[검색] [저장] [복사] [초기화] [삭제] [폴더열기]
```

---

# 12. Form 규칙

Form은 정렬이 가장 중요하다.

권장:

```text
Label              Input
설명                 helper text
```

또는 좁은 화면에서는:

```text
Label
Input
helper text
```

### 규칙

- 같은 그룹의 label 폭을 통일한다.
- input 높이를 통일한다.
- 동일 종류 input 폭을 가급적 통일한다.
- placeholder를 label 대용으로 사용하지 않는다.
- 단위를 input 밖에 명확하게 표시한다.
- 숫자값은 가능하면 SpinBox 계열을 사용한다.
- 경로 입력은 LineEdit + Browse button 패턴을 사용한다.

---

# 13. Card 사용 규칙

Card는 관련 기능을 묶을 때만 사용한다.

좋은 예:

```text
[검색 조건]
출발역
도착역
날짜
인원
```

나쁜 예:

```text
카드
 └─ 카드
     └─ 카드
         └─ 버튼
```

페이지 전체를 여러 개의 떠 있는 card로 쪼개지 않는다.

### Card 판단 기준

다음 중 하나에 해당할 때 사용:

- 하나의 설정 그룹
- 명확한 독립 기능
- 별도 상태를 가진 작업 영역
- 요약 정보

단순한 section 제목과 2~3개 control뿐이면 card 없이 section layout을 우선한다.

---

# 14. Table / List

업무용 앱에서는 테이블 가독성이 매우 중요하다.

### 기본 규칙

- row height 통일
- header 정렬 통일
- 필요 없는 vertical grid 최소화
- 핵심 열만 강조
- 숫자는 우측 정렬 고려
- 상태 열은 icon/badge/text 조합 사용
- action button을 모든 셀에 과도하게 넣지 않는다

빈 테이블에는 빈 공간만 보여주지 않는다.

예:

```text
검색 결과가 없습니다.
조건을 변경한 뒤 다시 검색해 주세요.
```

Empty state component 사용을 우선한다.

---

# 15. Feedback / Notification

## 성공 / 경고 / 오류

일반적인 작업 결과는 `InfoBar` 사용을 우선한다.

예:

```python
InfoBar.success(...)
InfoBar.warning(...)
InfoBar.error(...)
InfoBar.info(...)
```

Modal dialog는 사용자의 작업을 반드시 차단해야 하는 경우만 사용한다.

### MessageBox 적합

- 저장하지 않고 종료
- 진행 중 작업 취소
- 데이터 삭제
- 되돌릴 수 없는 작업
- 반드시 선택이 필요한 상황

### InfoBar 적합

- 저장 완료
- 복사 완료
- 검색 실패
- 네트워크 오류
- 업데이트 완료
- 설정 적용 완료

---

# 16. Loading / Busy State

시간이 걸리는 작업은 반드시 상태를 표현한다.

필요에 따라:

```text
ProgressBar
ProgressRing
버튼 disabled
취소 버튼
상태 설명
```

작업 중 UI 전체를 무조건 disable 하지 않는다.

정말 필요한 영역만 잠근다.

### 긴 작업

UI thread에서 실행하지 않는다.

```text
QThread
QObject worker
Qt signal/slot
```

등 기존 프로젝트 패턴을 따른다.

---

# 17. 페이지 상태 설계

모든 주요 페이지는 최소한 다음 상태를 고려한다.

```text
initial
loading
populated
empty
error
busy
disabled
```

예:

```text
검색 페이지

initial
→ 검색 조건 입력

loading
→ ProgressRing + "검색 중"

populated
→ 결과 테이블

empty
→ EmptyState

error
→ InfoBar + 재시도 가능 상태
```

정상 성공 화면만 구현하고 나머지를 방치하지 않는다.

---

# 18. Dialog 규칙

Dialog는 최대한 짧고 목적이 명확해야 한다.

구조:

```text
Title

설명

content

Cancel | Primary Action
```

### 금지

- Dialog 안에 또 Dialog를 여는 구조
- 모든 설정을 modal에 몰아넣기
- 긴 로그를 MessageBox에 출력
- 단순 알림을 modal로 표시

---

# 19. Icon 규칙

QFluentWidgets의 `FluentIcon`을 우선한다.

```python
from qfluentwidgets import FluentIcon as FIF
```

예:

```text
FIF.HOME
FIF.SEARCH
FIF.SETTING
FIF.UPDATE
FIF.FOLDER
FIF.SAVE
FIF.DELETE
```

### 금지

```text
🔍
⚙️
📁
✅
❌
```

emoji를 앱의 정식 UI icon으로 사용하지 않는다.

텍스트 문맥에서 보조적으로 쓰는 것은 별개다.

---

# 20. Responsive Window

고정 해상도를 전제로 하지 않는다.

`ktrain`처럼 화면 가용 영역에 맞춰 초기 창 크기를 결정하는 패턴을 권장한다.

예:

```python
screen = QGuiApplication.primaryScreen()
available = screen.availableGeometry()
```

### 최소 요구

- 100% scaling
- 125%
- 150%

에서 UI가 깨지지 않아야 한다.

가능하면 1920×1080 이하 환경에서도 사용할 수 있어야 한다.

절대 좌표 기반 배치를 사용하지 않는다.

---

# 21. Layout 규칙

다음 순서로 사용을 우선한다.

```text
QVBoxLayout
QHBoxLayout
QGridLayout
QFormLayout
```

절대 위치:

```python
widget.move(...)
widget.setGeometry(...)
```

는 특별한 UI가 아니라면 사용하지 않는다.

### stretch 활용

빈 공간을 임의 margin으로 채우지 말고:

```python
layout.addStretch()
```

를 적절히 사용한다.

---

# 22. Scroll

페이지 내용이 창보다 길어질 가능성이 있으면 ScrollArea를 고려한다.

설정 화면, 긴 Form, 다수 Section에서는 특히 중요하다.

단, table 자체와 page scroll을 중첩해서 사용해 UX를 악화시키지 않는다.

---

# 23. Settings 페이지

설정은 일반 form보다 `SettingCard` 계열을 우선 검토한다.

예:

```text
일반
 ├─ 자동 업데이트
 ├─ 시작 시 실행
 └─ 기본 폴더

화면
 ├─ 테마
 └─ 언어

고급
 └─ 로그 설정
```

카테고리를 나눠 한 화면에 모든 설정을 평면 배치하지 않는다.

---

# 24. 재사용 컴포넌트

다음 패턴이 2회 이상 등장하면 공통 component화를 검토한다.

```text
파일 선택 row
폴더 선택 row
상태 badge
empty state
section header
progress panel
log viewer
path input
search toolbar
result toolbar
confirmation dialog
```

### 원칙

"코드를 줄이기 위한 추상화"보다  
"디자인과 동작을 동일하게 유지하기 위한 추상화"를 우선한다.

---

# 25. 비즈니스 로직과 UI 분리

페이지 class는 비즈니스 로직을 최소화한다.

좋은 구조:

```text
UI
↓ signal
Controller / Service
↓
Core
↓
result
↓ signal
UI
```

UI 파일이 API 호출, scraping, DB query, 파일 parsing까지 직접 수행하면 분리를 검토한다.

단순 앱에서는 불필요한 MVC/MVVM 과설계를 하지 않는다.

---

# 26. 기존 UI 리팩터링 절차

기존 UI를 개선할 때 무작정 전체 파일을 다시 작성하지 않는다.

다음 순서로 진행한다.

## Phase 1 — Audit

먼저 확인:

```text
현재 MainWindow
Navigation 방식
페이지 목록
중복 widget
inline QSS
custom color
custom button
dialog
table
loading state
dark/light 처리
window size
DPI 처리
```

## Phase 2 — Design Map

기존 기능을 다음과 같이 매핑한다.

```text
현재 UI
→ 유지
→ Fluent component로 교체
→ 공통 component화
→ 제거
```

## Phase 3 — Foundation

먼저 구축:

```text
theme
design tokens
MainWindow
Navigation
공통 component
```

## Phase 4 — Page Migration

페이지 단위로 변경한다.

한 번에 모든 화면을 전면 변경하지 않는다.

## Phase 5 — Cleanup

마지막에:

```text
unused QSS
unused widget
legacy component
duplicate color
duplicate spacing
dead code
```

를 정리한다.

---

# 27. KTrain과 동일 계열로 반드시 유지할 요소

다음 특징은 선택적 참고사항이 아니라 KTrain 호환 UI의 기본 계약으로 유지한다.

## 27.1 Fluent Navigation

`MSFluentWindow` / `FluentWindow` 기반 navigation.

## 27.2 단순한 페이지 구성

각 주요 기능을 별도 page로 분리한다.

## 27.3 시스템 테마 연동

다크/라이트를 앱에서 임의 강제하지 않는다.

## 27.4 InfoBar

작업 결과 알림은 화면 흐름을 깨지 않는 방식으로 제공한다.

## 27.5 Theme 모듈 분리

```text
theme.py
```

에서 공통 테마 로직을 관리한다.

## 27.6 최소 QSS

Fluent component가 이미 제공하는 스타일을 다시 CSS처럼 덮어쓰지 않는다.

## 27.7 Desktop density

웹앱처럼 과도하게 큰 padding을 적용하지 않는다.

---

# 28. 절대 금지 패턴

다음 패턴을 새로 만들지 않는다.

```python
button.setStyleSheet(...)
button2.setStyleSheet(...)
button3.setStyleSheet(...)
```

```python
widget.setGeometry(20, 30, 300, 50)
```

```text
화면마다 다른 button height
화면마다 다른 border radius
임의 hex color 반복
emoji icon
모든 기능을 하나의 거대한 MainWindow.py에 구현
UI thread에서 긴 작업
성공 메시지를 전부 QMessageBox로 표시
빈 결과를 빈 테이블로만 표현
hover animation 과다
shadow 과다
card nesting
```

---

# 29. 에이전트 작업 전 필수 확인

UI 작업을 시작하기 전에 다음 파일을 먼저 확인한다.

```text
README
requirements / pyproject
main entry
MainWindow
현재 theme
현재 UI components
대상 page
worker/service 구조
tests
packaging 설정
```

프로젝트 전체 구조를 파악하기 전에 UI 파일 하나만 보고 전면 재작성하지 않는다.

---

# 30. 에이전트 구현 규칙

에이전트는 작업 시 다음 순서를 따른다.

```text
1. 현재 UI 구조 분석
2. 기존 기능 목록 작성
3. 변경할 UI 영역 정의
4. 공통 component 재사용 가능성 확인
5. theme/token 적용
6. page 단위 구현
7. signal/slot 연결 검증
8. loading/error/empty 상태 검증
9. dark/light 검증
10. DPI/window resize 검증
11. 테스트 실행
12. dead UI code 제거
```

---

# 31. 기능 보존 원칙

UI 리팩터링 중 다음을 임의 변경하지 않는다.

```text
파일 처리 결과
API 요청 방식
DB schema
업데이트 로직
저장 형식
사용자 설정 key
CLI interface
worker 동작
기존 단축키
```

UI 개선 작업과 기능 변경을 분리한다.

기능 변경이 필요하면 이유를 명시하고 별도 변경으로 취급한다.

---

# 32. 테스트 기준

가능하면 다음을 확인한다.

## Startup

```text
앱 실행 성공
MainWindow 표시
Navigation 정상
기본 페이지 정상
```

## Interaction

```text
버튼 동작
입력
파일 선택
dialog
page 이동
```

## State

```text
loading
success
empty
error
cancel
```

## Theme

```text
light
dark
```

## Window

```text
resize
minimum size
high DPI
```

---

# 33. UI 완료 조건

다음 조건을 만족해야 UI 작업 완료로 판단한다.

- [ ] 기존 핵심 기능이 유지된다.
- [ ] Navigation 구조가 일관된다.
- [ ] spacing scale이 통일되어 있다.
- [ ] button hierarchy가 명확하다.
- [ ] inline `setStyleSheet()` 남용이 없다.
- [ ] 임의 hex color가 페이지 코드에 흩어져 있지 않다.
- [ ] dark/light mode가 정상이다.
- [ ] loading 상태가 존재한다.
- [ ] empty 상태가 존재한다.
- [ ] error 상태가 존재한다.
- [ ] 긴 작업이 UI thread를 막지 않는다.
- [ ] dialog와 InfoBar 용도가 구분되어 있다.
- [ ] 주요 화면에서 resize 시 layout이 깨지지 않는다.
- [ ] 125~150% DPI에서도 사용 가능하다.
- [ ] 중복 UI component가 정리되어 있다.
- [ ] legacy QSS와 dead UI code가 제거되었다.
- [ ] 테스트 또는 smoke test를 통과한다.

---

# 34. Agent용 최종 지시

UI 구현/리팩터링 시 아래 지시를 기본값으로 적용한다.

```text
이 프로젝트의 Qt 데스크톱 UI는 twbeatles/ktrain을 Canonical Reference로 한다.

단순히 유사한 색상이나 Fluent 느낌만 내지 말고,
MainWindow 구조, Navigation, Page Margin, HeaderCardWidget,
PrimaryPushButton/PushButton hierarchy, Settings Pivot,
InfoBar, Theme.AUTO, OS Light/Dark 연동, HiDPI 처리까지
KTrain과 동일 제품군 수준으로 구현한다.

UI 전면 재구축에서는 특별한 기술적 제약이 없는 한
PySide6 + PySide6-Fluent-Widgets를 사용한다.

MainWindow는 MSFluentWindow 또는 FluentWindow를 사용한다.
자체 Sidebar를 새로 만들지 않는다.

기본 창은 1100x800, 최소 640x560, 화면 margin 40을 기준으로 한다.
일반 페이지는 24px margin,
조건/결과형 작업 페이지는 16px margin,
기본 spacing은 8px을 사용한다.

조건/결과 화면은 QSplitter + HeaderCardWidget을 우선하며,
Card view margin은 12/8/12/12,
조건 패널 최소 폭 400px,
결과 패널 최소 폭 360px을 기본으로 한다.

Settings는 ScrollArea + Pivot + QStackedWidget으로 구현하고,
각 설정 Tab은 24px margin을 사용한다.

핵심 행동은 PrimaryPushButton,
보조 행동은 PushButton을 사용한다.
일반 성공/경고/오류는 InfoBarPosition.TOP을 사용하고,
사용자 결정을 요구하는 경우에만 MessageBox를 사용한다.

OS 다크/라이트 테마에 자동 연동하고 Mica는 기본 비활성화한다.
페이지별 setStyleSheet()를 남발하지 않는다.
Native Qt Widget 보정은 theme.py 한 곳에서 관리한다.

긴 작업은 UI thread에서 실행하지 않고 QObject Worker + QThread 패턴을 사용한다.
작업 상태는 ProgressRing + BodyLabel로 표시한다.

기존 비즈니스 로직, 데이터 형식, 설정 key, DB schema, API 동작은
UI 개편을 이유로 임의 변경하지 않는다.

최종 UI가 KTrain과 나란히 실행했을 때
같은 개발자가 만든 동일 제품군 앱처럼 보이지 않으면
UI 작업을 완료로 간주하지 않는다.
```

---

# 35. 변경 결과 보고 형식

에이전트는 작업 완료 후 최소한 다음 형식으로 보고한다.

```markdown
## UI 변경 요약

### 변경한 화면
- ...

### 공통 컴포넌트
- ...

### Theme / Style 변경
- ...

### 기존 기능 보존 여부
- ...

### 제거한 Legacy UI
- ...

### 테스트
- ...

### 남은 UI 개선 후보
- ...
```

---

## 적용 원칙 요약

```text
ktrain = 스타일 기준점
QFluentWidgets = 기본 컴포넌트
Theme = 중앙 관리
Spacing = 4/8/12/16/24/32
Navigation = 일관되게
Primary action = 제한적으로
InfoBar > 단순 MessageBox
QSS = 최소화
UI와 Core = 분리
상태 설계 = initial/loading/empty/error/success
Dark/Light/DPI = 기본 요구사항
```

이 규칙을 프로젝트 전체 UI의 기본 설계 계약(Design Contract)으로 간주한다.
