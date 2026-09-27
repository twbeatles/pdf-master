# Fluent Redesign 설계안 (pdf-master)

> SSOT: `DESKTOP_UI_DESIGN_RULES.md` (§0~§35). 본 문서는 규칙을 복제하지 않고
> pdf-master 적용점·토큰·이식·단계만 정의한다. 중복 규칙 문서 신설 금지.

## 0. 전제

- Qt 바인딩은 **PyQt6 유지** (§1.1). `PySide6-Fluent-Widgets` 혼합 금지.
- Fluent는 선택 extra: `pip install -e ".[fluent]"` (`PyQt6-Fluent-Widgets>=1.6`, `darkdetect>=1.8`).
  미설치면 `src/ui/fluent_theme.py` 브리지가 no-op — 기존 QSS/동작 그대로.
- 우선순위: 기능 무손실 > 규칙 통일 > 장식 (§0). Worker mode/kwargs·public import 불변.

## 1. 현행 구조

- `PDFMasterApp(QMainWindow)`: 헤더 + `QSplitter`(좌 탭/우 미리보기) + 상태바.
- 최상위 8탭: 병합·변환·페이지·순서변경·편집/보안·배치·고급·AI.
  고급 내부 4서브탭: 편집/추출/마크업/기타 (`tabs_advanced/tab_builders/`).
- 각 탭 content는 `setup_*` 팩토리 반환 위젯 — 셸 교체 시 그대로 이식 가능.
- 미리보기 `ZoomablePreviewWidget` (QPdfDocument/QPdfView), 썸네일 `ThumbnailGridWidget` — Fluent 래핑만, QPdf 경로 유지.

## 2. 목표 네비게이션 (탭 정리) — P2 적용됨

- 최상위 `QTabWidget` → `TabShell` (`src/ui/tab_shell.py`): Fluent 설치 시
  `SegmentedWidget`(메인 8탭) / `Pivot`(고급 4서브탭) + `QStackedWidget`,
  미설치 시 `QTabWidget` 폴백. QTabWidget 표면(`addTab`/`setCurrentIndex`/
  `count`/`widget`/`setCurrentWidget`/`currentWidget`/`indexOf`/`setEnabled`)
  호환으로 호출부·단축키(Ctrl+1..8)·테스트 스텁 무손실.
- `MSFluentWindow` 미사용 결정: 고정 크롬이 splitter/미리보기/포커스·전체화면
  구조와 충돌. 셀렉터+스택 조합으로 Fluent 내비게이션을 구현.
- 탭 추가는 `add_tab()` 공용 헬퍼로 — 테스트 스텁의 순수 QTabWidget에 `icon=`
  키워드가 들어가면 `TypeError`이므로 직접 `addTab(..., icon=)` 호출 금지.
- 아이콘: PASTE/SYNC/CUT/MOVE/CERTIFICATE/LAYOUT/SETTING/ROBOT (메인),
  EDIT/DOWNLOAD/BRUSH/MENU (서브). emoji 라벨 제거 (§18·§19).
  폴백 경로에서는 `FluentIcon.icon()` → `QTabWidget.setTabIcon`으로 표시.
- 화면당 accent(Primary) 버튼 1개, Destructive 분리, 확인 절차 유지 (§11).

## 3. 토큰 (`src/ui/design_tokens.py`)

- spacing은 4/8/12/16/24/32만: 아이콘-텍스트 8, form row 12, group 16, section 24, page margin 24 (§5·§21).
- 컨트롤 높이 32/36/40. card 중첩·전면 card·gradient/shadow/glass 금지, 단일 section은 card 생략 (§13).
- 타이포: Page 22 Semibold / Section 16 / Body 13 / Secondary 12 / Caption 11,
  fallback `Pretendard → Segoe UI → Apple SD → Malgun Gothic → sans-serif` (§6).
  현행 `Segoe UI 9pt`와 시각 동등 — 무단 확대 금지.
- 색: `primary #4f8cff` 유지 (SRT `#E4002B` 등 도메인색 복제 금지 §0).
  semantic token만 사용: background/surface/border/text/success/warning/error (§7).
- 윈도우: 기본 1200x850 / 최소 950x700을 `availableGeometry`로 클램프 (§20).
  `move`/`setGeometry` 절대좌표 금지. `stretch`로 여백 흡수 (§21).

## 4. srtgo 이식점 (`src/ui/fluent_theme.py`, `main.py`)

- `setTheme(Theme.AUTO)` + `darkdetect` + `colorSchemeChanged` 즉시반영 + 3초 폴링 (§8, `ktrain/gui/theme.py` 계승).
- `settings` 수동 전환은 `sync_fluent_theme()`로 브리지 — 기존 QSS 적용 뒤에 호출, 충돌 없이 병행.
- Mica는 `setMicaEffectEnabled(False)` 강제. 라이트는 플랫폼 기본, 다크만 최소 보정 (§9, 신규 QSS 파일 신설 금지).
- HiDPI: `QT_ENABLE_HIGHDPI_SCALING/AUTO_SCALE=1` 유지 + `PassThrough` rounding (§20).
- 피드백: 비차단은 `InfoBar`, 차단은 `MessageBox` (§15). 로딩은 기존 overlay + 영역잠금 + 취소 유지 (§16).
- 인라인 `setStyleSheet` 신규 금지 — 공통 helper 경유 최후 보정만 (§9).

## 5. Fluent 의존성·패키징

- `pyproject.toml`: `[project.optional-dependencies] fluent`.
- `pdf_master.spec`: `qfluentwidgets`/`qframelesswindow`/`darkdetect`를 `_module_exists` 가드로 collect.
  설치 시 EXE 용량 증가 감안 (현 30~40MB 기준).
- 라이선스 고지: Fluent는 GPLv3(+상업 옵션). pdf-master는 PyQt6로 이미 GPL 의무가 있어
  두 번째 GPLv3 권리자 추가로 배포 방식을 결정해야 한다.

## 6. 마이그레이션 단계 (P0–P4 완료)

- P0 결정: extra 설치·동작 확인 (`.[fluent]` 설치 환경에서 `--smoke`).
- P1 토대: 토큰·브리지·HiDPI·창 클램프·spec·문서·회귀 테스트.
- P2 셸 교체: `TabShell` 도입, `setup_*` content 그대로 페이지 이식 (import·mode/kwargs 불변).
- P3 컴포넌트 치환: `fluent_widgets` 별칭으로 import 한 줄 교체 + 역할별
  `PrimaryButton`(action/accent)`/DangerButton`(red 계열)`/WarningButton`/
  `EditableComboBox`(setEditable) 지정. `QMessageBox`·`QGroupBox`·미리보기/
  썸네일은 네이티브 유지 (API 상이·계약 표면).
- P4 정리: Fluent 활성 시 스코프드 네이티브 시트(`theme/native.py`)만 적용,
  glass gradient 평탄화. i18n 스모크, `package_smoke.ps1`.

## 8. 실측 경계 (P2–P4 검증에서 확정)

- 전역 레거시 QSS + Fluent 누적 시 `app.setStyleSheet`에서 access violation.
  타입 셀렉터가 Fluent 서브클래스/내부 Qt 자식을 관통하는 것이 원인으로 추정.
  대응: Fluent 활성 경로에서는 레거시 시트를 적용하지 않음 (`_apply_theme` 분기).
- `FileSelectorWidget` 버튼은 Qt 유지: Fluent 버튼 + deleteLater + 전역 재폴리시
  누적 조합에서 동일 크래시 재현. `test_fluent_shell_boundary.py`로 클래스 고정.
- 인스턴스 QSS에 `QPushButton` 등 타입 셀렉터를 쓰는 경우, 대상이 Fluent
  위젯이면 안 됨 (서브클래스 매칭으로 내부까지 오염). Destructive는 Qt
  `DangerButton`/`WarningButton` + ID 규칙으로 표현.
- 테스트에서 `_qapp()` 반환 참조를 버리면 QApplication이 즉시 수거되어 다음
  QWidget 생성에서 fatal. `app = _qapp()` 형태로 유지할 것.

## 7. 완료 조건 (§29·§32·§33)

- `python -m pyright` 0 errors, `python -m pytest -q` (Fluent 유무 양쪽).
- 100%·125%·150% 리사이즈, 1920x1080 이하 무파손, dark/light 대비·가독성.
- i18n 하드코딩 스모크, Worker 전 모드 성공/실패/취소 경로 무손실.
