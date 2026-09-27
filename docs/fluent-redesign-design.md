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

## 9. 바인딩 가드·좀비 방지·스위트 안정화 (2026-09-27, §1.1)

- 환경 오염 실측: `PySide6-Fluent-Widgets`가 설치된 머신에서는 `qfluentwidgets`
  import가 PySide6 바인딩으로 동작해 PyQt6 부모 전달 시 `ValueError`, 부모 없이
  만들면 이종 바인딩 위젯이 된다. 같은 top-level 패키지를 공유하므로 두 변형
  동시 설치·순차 uninstall은 공유 파일 삭제/고스트 dist를 남긴다. 정화 절차:
  `pip install --force-reinstall --no-cache-dir PyQt6-Fluent-Widgets==<ver>
  PyQt6-Frameless-Window==<ver>` 후 dist 목록에 PySide6 변형이 없는지 확인.
  (한쪽만 uninstall하면 공유 `qfluentwidgets/`가 통째로 삭제되므로 금지.)
- 코드 가드(§1.1 혼합 금지의 실행 강제): `fluent_theme.is_fluent_available()`은
  spec 존재를 넘어 (1) `PySide6-Fluent-Widgets` dist 부재, (2)
  `PyQt6-Fluent-Widgets` dist 존재, (3) `NavigationInterface`·`Pivot`·
  `PushButton`이 `PyQt6.QtWidgets.QWidget` 서브클래스임을 확인한다. 불충족 시
  전부 Qt 폴백(QTabWidget/순정 위젯)으로 동작하므로 segfault 대신 기능 유지.
  `fluent_widgets`·`TabShell` 진입부가 같은 게이트를 공유한다. 회귀:
  `test_fluent_availability_rejects_pyside_variant`,
  `test_fluent_widget_aliases_are_pyqt6_backed`.
- 좀비 방지: `NavigationInterface` 생성자가 `NavigationPanel` 단계에서 예외를
  던지면 C++ 자식(부모 있음)이 살아남아 이후 resize에서 panel-less
  `AttributeError`를 이벤트 루프로 터뜨린다. `TabShell`은 부모 없이 생성 →
  `hasattr(panel)` 검증 → `setParent` 순서로 만든다. 회귀:
  `test_tab_shell_constructs_without_parented_zombie`.
- 스위트 규칙: 테스트별 `QApplication` 재생성은 Fluent C++ 싱글톤(Router 등)을
  삭제해 이후 Fluent 위젯 생성을 깨뜨린다. `tests/conftest.py`가 세션 전역
  QApplication 1개를 유지하고, autouse fixture가 테스트마다 전역 stylesheet을
  리셋한다. 개별 파일의 `_qapp()`는 `instance()`를 재사용하므로 안전하다.

## 10. Wave-2 컴포넌트·설정 탭 (2026-09-27)

- 별칭 추가: `PasswordLineEdit`(보기 버튼)·`SearchLineEdit`(검색/지우기 버튼,
  `searchSignal`/`clearSignal`)·`HeaderCardWidget`(`setTitle`+`viewLayout`)·
  `TitleLabel`/`BodyLabel`. 폴백은 Qt 서브클래스(Password echo 고정/clear 버튼/
  `QGroupBox+viewLayout`)로 동일 API 유지.
- 교체: API 키·복호화·보안 비밀번호 3곳 → `PasswordLineEdit` (setEchoMode 중복 제거).
  AI 질문·하이라이트 검색 → `SearchLineEdit` + `connect_search()` 헬퍼
  (폴백은 False, `returnPressed` 기존 연결 유지 — Enter 중복 발사 없음 확인).
  미리보기 검색(`PreviewSearchLineEdit`)은 Shift+Enter/Escape 커스텀 키 유지로 교체 제외.
- 버튼 objectName 정리: NATIVE 시트는 `#dangerBtn/#warningBtn/#toolbar*` ID 한정
  (베어 타입 셀렉터 0 — 주석 1건 제외). Fluent 버튼의 `actionBtn/secondaryBtn`은
  폴백 레거시 시트 전용 후크. 역할→이름 매핑 헬퍼 `set_button_role()` 추가.
- 설정 탭(9번째 메인탭, `SETTING`): `TabShell(mode="pivot")` 2섹션(외관/알림 및 기록)
  + `wrap_page()` HeaderCard. 환경설정 메뉴와 같은 settings 키를 공유하고 변경은
  기존 메뉴 핸들러(`_set_notify_mode/_toggle_*/_change_language`)에 위임하므로
  동작 계약 불변. 테마 변경은 `_apply_theme()` + 툴바 버튼 문구까지 갱신.
- 콤보 userData 계약: Fluent `ComboBox.addItem(text, icon, userData)` — 위치 인자
  2개 호출 36곳을 `userData=` 키워드로 전환. Qt에선 동작해도 Fluent에선 icon
  슬롯에 꽂혀 `currentData()`가 전부 기본값으로 무너지던 실측 버그. 구조 회귀
  테스트가 `cmb_*/combo.addItem` 위치 인자를 금지.
- 알림 헬퍼: `notify(parent, kind, title, content)` — Fluent `InfoBar`,
  폴백 `QMessageBox`. i18n 키 13종 추가(ko/en).
- 회귀: `tests/test_fluent_settings_tab.py` (별칭 베이스·`wrap_page`·
  `connect_search`·`notify` 무예외·섹션 스펙·핸들러 무효값 폴백·카탈로그 키).

## 7. 완료 조건 (§29·§32·§33)

- `python -m pyright` 0 errors, `python -m pytest -q` (Fluent 유무 양쪽).
- 100%·125%·150% 리사이즈, 1920x1080 이하 무파손, dark/light 대비·가독성.
- i18n 하드코딩 스모크, Worker 전 모드 성공/실패/취소 경로 무손실.
