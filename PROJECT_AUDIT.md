# Project Audit

> 감사 기준일: **2026-11-22**
> 대상 버전: **PDF Master v4.5.18** (`src/core/_constants_impl/values.py`)
> 성격: **기능 구현·런타임 안정성 One-Shot 감사** — 코드 수정 없이 리포트만 작성. 품질/아키텍처 부채는 `PROJECT_AUDIT_QUALITY.md` (Track B)에 위임
> 이전 감사: `PROJECT_AUDIT.md` (2026-09-23, v4.5.7 기준)의 ISSUE-001~004는 본 감사에서 코드로 재확인한 결과 **모두 해결됨** (§4 하단 참조)

## 1. Executive Summary

* 프로젝트 전체 상태: **양호하나 회귀 신호 3건이 현재 트리에서 재현된다.** UI → `run_worker` → `WorkerThread` → `OperationSpec` 디스패치 → 원자 저장·취소 정리라는 핵심 골격은 견고하고, 2026-09-23 감사의 릴리스/업데이트 4건은 코드로 해결 확인했다. 그러나 (a) Fluent 바인딩 하드 기동 게이트가 깨진 의존성 환경에서 앱 전체를 멈추고, (b) `compare_pdfs` 텍스트 경로의 페이지 단위 예외가 시각 경로와 달리 격리되지 않아 기존 회귀 테스트 1건이 실패하며, (c) 페이지 범위 1000건 상한이 조용히 잘라내는 동작이 테스트에 못박혀 있다.
* 전체 위험도: **Medium.** 데이터 손실/파괴에 해당하는 Critical/High 문제는 확인하지 못했다. 남은 것은 기동 불가(환경 의존), 특정 입력에서의 기능 실패, 조용한 부분 실행이다.
* 가장 중요한 문제 3개:
  1. Fluent 바인딩 문제 시 앱 전체 기동 실패 — 장식용 테마 의존성이 하드 게이트이며, 존재하는 QTabWidget 폴백까지 도달하지 못함 ([ISSUE-001], 기동 경로에서 실제 재현).
  2. `compare_pdfs` 텍스트 추출 경로 무방비 — 페이지 `get_text()` 예외가 리포트 없이 작업 전체를 실패로 끝냄. 설치된 PyMuPDF 1.28.2에서 기존 테스트가 그대로 실패함 ([ISSUE-002]).
  3. `parse_page_range` 1000건 조용 절단 — 1000쪽 초과 문서에서 split/delete가 경고 없이 일부만 수행될 수 있음 ([ISSUE-003]).
* 데이터 손상/유실 가능성 평가: **낮음.** 동일 경로 저장 전 미리보기 해제·복원(`window_worker/same_path.py`), 원자 저장(`worker_runtime/io.py: atomic_*` + `os.replace`), 취소 시 `created_output_paths`만 롤백, 첨부 경로 안전화, 배치 암호 권한 해석, AI 임시 복호 파일 ACL+정리를 모두 코드로 확인했다.
* 가장 먼저 수정해야 할 영역: **기동 게이트 완화(Fluent) → compare 텍스트 경로 격리 → 범위 절단 경고 순.**

## 2. Project Understanding

README/CLAUDE 및 CodeGraph 탐색을 바탕으로 정리했다.

* 프로젝트 목적: PySide6 기반 올인원 PDF 데스크톱 유틸리티 (병합·분할·회전·변환·주석·양식·보안·추출·정리·비교·AI 요약/채팅/키워드). 문서 일부는 구 바인딩명(PyQt6)으로 남았으나 실제 코드는 PySide6이다 (§6).
* 주요 entrypoint:
  * `main.py` → `PDFMasterApp` (QApplication 조립, `--smoke`·`--apply-update` 분기, 단일 인스턴스 `QLockFile`).
  * `src/ui/main_window_worker.py:50 run_worker()` — CodeGraph 기준 **69개 UI 호출자**가 모든 Worker 작업을 여기로 보냄.
  * `src/core/worker.py:16 WorkerThread` — CodeGraph 기준 **122개 참조**. `WorkerRuntimeMixin.run()` → `OperationSpec` 디스패치 → `worker_ops` 도메인 핸들러.
  * `src/ui/update_mixin.py` — 서명 업데이트 확인/다운로드/적용 UI 흐름 (Windows 전용).
* 핵심 모듈:
  * `src/core/worker_runtime/` — payload·progress·files·access·run 믹스인 + `dispatch.py`(`OperationSpec`) + `preflight.py`(`parse_page_range`, 크기/헤더 검증).
  * `src/core/worker_ops/{annotation,extract,cleanup,page,transform,compare,form,compose,security,batch,ai}/` — 도메인 패키지 + 얇은 `*_ops.py` 파사드.
  * `src/core/ai/` — client·config·cache·session·generation·service·errors 분리; 업로드/채팅/텍스트 프로세스 내 LRU 캐시.
  * `src/core/update_manifest.py` + `src/core/update_installer.py` — Ed25519 서명 검증·HTTPS 강제·해시/크기 검증·스테이징·교체·smoke·롤백.
  * `src/core/{pdf_validation,settings,temp_cleanup}.py` — 크기/헤더 공용 검증, 홈 JSON 원자 저장, 스냅샷 undo, 고아 임시파일 스윕.
* 데이터 저장 방식: 설정은 사용자 홈 JSON 임시파일+`os.replace` 원자 저장; AI 채팅 기록은 `v2:{mtime_ns}:{정규화경로}` 키; AI 업로드/채팅/텍스트는 프로세스 내 LRU; 업데이트 결과는 `LOCALAPPDATA/PDFMaster/updates/last-update-result.json` 1회 소비.
* 외부 의존성: PySide6, PyMuPDF (optional 경계 `optional_deps.py`), `PySide6-Fluent-Widgets` + `darkdetect` (실질 하드 기동 게이트 — [ISSUE-001]), `cryptography`(매니페스트 서명), `google-genai`(optional AI), `keyring`(optional API 키), Tesseract(선택 OCR, 시스템 바이너리), PyInstaller(배포).
* 핵심 실행 흐름:

`UI 액션 → run_worker(mode, output_path, **kwargs) → same-path 미리보기 해제·preview passwords 주입·undo 스냅샷 → WorkerThread.run → _normalize_mode_kwargs → _preflight_inputs → OperationSpec handler → atomic save → finished/error/cancelled 시그널 → preview 복원·undo 등록`

`기동 → UpdateMixin(Windows만, idle 단일 비행) → download/verify manifest(별도 스레드) → _offer_update(모달 1회) → _download_update → stage_update(고유 스테이징명·재시도) → launch_update_helper → 종료 → helper: 대기→중단 복구→백업 이동→교체 이동→smoke(clean env)→성공 시 재기동/실패 시 롤백+결과 JSON → 다음 기동에서 1회 소비·표시`

## 3. Audit Coverage & Limitations

* 직접 확인한 주요 모듈: `main.py`, `worker.py`, `worker_runtime/{dispatch,preflight,normalize,mixin_access,mixin_run,mixin_files,io,messages}`, `window_worker/{lifecycle,same_path,undo,success,helpers}`, `window_undo/{backup,history}`, `compose/ops.py`, `batch/ops.py`, `security/ops.py`, `extract/{attachments,text_info}.py`, `compare/ops.py`, `annotation/textbox_impl/{single,batch,extract}.py`, `ai/{cache,prepare,temp_acl}`, `update_{mixin,manifest,installer}`, `window_preview/document.py`, `_settings_impl/{persistence,api_key}`, `fluent_theme.py`, `tab_shell` 설계 문서, `.github/workflows/release.yml`, `scripts/check_update_manifest_expiry.py`, `pdf_master.spec` + `pdf-master.spec`.
* CodeGraph로 분석·추출한 호출 관계 (MCP `codegraph_explore` 6회):
  * `run_worker` → 69개 호출자 / `WorkerThread` → 122개 참조 / `OperationSpec` 디스패치 / `_enqueue_pending_worker`·`_run_pending_worker` 대기열.
  * same-path 저장·복원 ↔ undo 백업 등록(`apply_undo_registration`이 성공 시 `after_backup` 채움 — 결함 없음으로 반증).
  * AI 임시 복호(`_prepare_ai_pdf_path`) ↔ ACL(`temp_acl`) ↔ orphan 스윕(`temp_cleanup`).
  * preflight ↔ `required_kwargs`/`required_any_kwargs` ↔ batch/merge/images 검증 분기.
  * 미리보기 파일 감시자(`_watch_preview_file`·디렉터리 감시 병행) ↔ 외부 변경 재시도(최대 10회·250ms).
  * 설정 저장/채팅 기록/`clear_pending_on_cancel` ↔ 종료 시 저장 순서.
* 실행한 테스트:
  * `python -m pytest --collect-only` → **416 collected.**
  * `python -m pytest -q` (system python 3.15.2, PySide6 6.12.0, PyMuPDF 1.28.2): 1회차 완주 **4 failed** — `test_advanced_pages_follow_explicit_theme_with_dark_os_palette`, `test_check_manifest_expiry_states`, `test_compare_visual_error_not_silent`, `test_main_smoke_exits_successfully` (상세 §4). 2·3회차는 동일 4건 FAILED 출력 후 teardown 과정에서 access violation (`exit=-1073741819`)으로 최종 counts 라인 없이 종료.
  * `python -m pyright src/core src/ui` → **0 errors, 0 warnings, 0 informations.**
  * 목표 프로브: 빈 `fitz` 문서 `save` → `ValueError: cannot save with zero pages` ([ISSUE-005] 근거). 작업 트리는 전후 `git status` clean 유지 (프로브 잔존물 제거 확인).
* 확인하지 못한 환경/외부 서비스: 실제 GitHub Release 태그 푸시 E2E, 저속 네트워크 대용량 다운로드, 장시간 메모리 프로파일, macOS/Linux 번들, Gemini File API 실연동 (opt-in smoke skip — `tests/test_ai_service_gemini_smoke.py`, 1 skip 확인), 깨끗한 `pip install -e .[dev]` 격리 env (이 머신의 `.venv`에는 pytest 미설치, `.venv-fluent`는 존재하지 않는 Python 3.14를 가리켜 깨짐 — 의존성 추가 설치는 감사 제약상 수행하지 않음).
* CodeGraph 또는 분석상의 한계: CodeGraph 인덱스가 추출 엔진보다 구버전이라는 경고(`v1.6.2 extraction 27` vs `v1.6.4 extraction 29`)와 함께 동작했다. 정적 호출 그래프는 `OperationSpec` 문자열 디스패치·Qt 시그널 경계·런타임 kwargs 정규화를 완전히 따라가지 못하므로 해당 경계는 파일 직접 열람·프로브·테스트 실행으로 보완했다. 2차 전체 실행의 teardown AV로 최종 pass counts 라인을 확보하지 못해, 통과 수는 "416 − 실패 − 스킵" 형태가 아닌 관측 서술로만 기재한다.

## 4. High-Risk Issues

> Critical/High에 해당하는 문제는 확인하지 못했다. 아래는 반증을 통과한 Medium 3건 + Low 3건이며, 신뢰도는 전부 `Confirmed`다.

### [ISSUE-001] Fluent 바인딩 문제 시 앱 전체 기동 실패 (장식 의존성의 하드 게이트)

* **위치:** `main.py:295-299` (`setup_app_theme(app)` 실패 시 `raise RuntimeError`), `src/ui/fluent_theme.py:113-152` (`is_fluent_available`/`setup_app_theme`).
* **우선순위:** Medium
* **신뢰도:** Confirmed
* **문제:** `is_fluent_available()`은 qfluentwidgets 미설치뿐 아니라 **임의의 import/초기화 예외까지 전부 `False`로 반환**하고, `main()`은 그 즉시 기동을 중단한다. `TabShell`의 QTabWidget 폴백(설계 `docs/fluent-redesign-design.md` §2, CLAUDE "미설치면 QTabWidget 폴백")은 `PDFMasterApp` 생성 이전에 raise되므로 **프로덕션 경로에서 도달 불가**하다.
* **발생 조건:** qfluentwidgets 또는 전이 의존성(`qframelesswindow` 등)이 깨진/어긋난 모든 환경. pip 의존성 드리프트로 현실적으로 도달 가능하다.
* **영향:** 테마 장식 문제와 무관한 핵심 PDF 기능 전체를 사용할 수 없다. 데이터 손상은 없다.
* **근거:** 코드 경로 + 실제 재현. 본 감사 환경의 system python은 `qfluentwidgets`는 설치됐으나 `qframelesswindow`가 없어(`ModuleNotFoundError: No module named 'qframelesswindow'`) `python main.py --smoke`가 `RuntimeError: PySide6 Fluent UI is unavailable`로 exit 1이 된다. 동일 원인으로 `test_main_smoke_exits_successfully`·`test_advanced_pages_follow_explicit_theme_with_dark_os_palette`가 실패한다.
* **반증 확인:** 의도적 결정이라는 점을 확인했다. `DESKTOP_UI_DESIGN_RULES.md`가 Fluent를 강제하고, 릴리스 preflight(`release.yml`)도 `is_fluent_available()`를 assert한다. 그러나 (1) 그 preflight는 깨끗한 CI env에서만 동작하고 사용자 env 드리프트는 막지 못하며, (2) 폴백 코드가 있으면서도 기동 게이트가 먼저 차단하므로 폴백은 테스트 전용 사각(死角) 코드가 된다. 어느 쪽도 "깨진 전이 의존성에서 앱이 뜬다"를 보장하지 못한다.
* **호출/영향 범위:** CodeGraph 기준 `main()` 단일 진입점 → 앱 전체. `TabShell._use_fluent`(smoke가 assert) 이하 모든 UI가 영향권이지만, 정작 폴백 분기는 미도달이다.
* **권장 수정 방향:** `setup_app_theme` 실패 시 raise 대신 경고 로그 + Qt 폴백 기동으로 전환하고, 기동 게이트는 "Fluent **혼합(섞임) 설치** 감지" 같은 실제 위험에만 유지한다. 또는 `is_fluent_available()`를 `False` 사유별로 구분(미설치=폴백 기동, 깨진 설치=경고 후 폴백 기동)한다.
* **필요한 회귀 테스트:** (a) qfluentwidgets import를 강제로 실패시킨 offscreen 기동에서 `--smoke`가 exit 0이고 `window.tabs._use_fluent is False`인지, (b) 혼합 설치(PyQt6 잔재)에서는 기존처럼 거부되는지.

### [ISSUE-002] `compare_pdfs` 텍스트 경로의 페이지 단위 예외가 격리되지 않음

* **위치:** `src/core/worker_ops/compare/ops.py:89-90` (`text1 = page1.get_text()` / `text2 = ...`, 어떤 try도 없음). 같은 파일의 시각 경로는 `_measure_visual_diff` 내부에서 예외를 잡아 `visual_error` 상태로 격리한다(105-117행).
* **우선순위:** Medium
* **신뢰도:** Confirmed
* **문제:** 텍스트 추출이 한 페이지라도 raise하면 `_legacy_compare_pdfs` 전체가 중단되고 `run()`의 generic 핸들러로 빠져 **리포트 파일 없이 에러 종료**한다. `visual_error`처럼 "해당 페이지만 표시 후 계속"이 아니다.
* **발생 조건:** 손상된 Content Stream 등 `get_text()`가 raise하는 PDF. 설치된 PyMuPDF 1.28.2에서는 `get_text` 내부가 `Matrix(1, 1)`를 사용하므로, `Matrix` 주입 실패만으로도 재현된다 — 기존 테스트가 그 경로로 실패 중이다.
* **영향:** 비교 기능 전체 실패 + 리포트 미생성. 입력 파일은 건드리지 않고(읽기 전용 + `_atomic_text_save` 미도달) 데이터 손상은 없다.
* **근거:** 코드(89-90행 무방비 vs 96-103행 방비) + 실패 테스트. `tests/test_audit_followup_stability.py::test_compare_visual_error_not_silent`는 `fitz.Matrix`를 실패 주입했을 때 `visual_error` 격리를 기대하지만, 1.28.2의 `get_text`가 같은 `Matrix`를 먼저 타서 89행에서 전파되어 테스트가 실패한다. `pyproject.toml`이 `PyMuPDF>=1.28`로 상한이 없으므로, 이런 내부 구현 드리프트는 지원 설치 범위 안에서 반복 가능하다.
* **반증 확인:** 상위 보호로 `run()` generic 핸들러가 프로세스 크래시를 막고 입력 파일을 보호하는 점은 확인했다. 그러나 요구되는 계약("페이지 단위 오류 격리", 테스트가 명시)은 깨져 있고, 실패 시 사용자가 얻는 것은 페이지별 원인이 아닌 통째 에러뿐이다. `do_text or do_visual` 조건(89행) 때문에 `compare_mode="visual"`에서도 텍스트 추출이 수행되어, visual 전용 비교조차 텍스트 경로 장애에 끌려간다.
* **호출/영향 범위:** `compare_pdfs`(유일 진입, `ops.py:207-209`) → `_legacy_compare_pdfs` → `_diff_page_texts`·`_collect_page_diff_blocks`·`_write_visual_diff_pdf`·`_finish_compare` 전체가 미실행. UI `compare_report` 대화상자(`window_worker/success.py:182-190`)도 열리지 않는다.
* **권장 수정 방향:** 89-90행을 페이지 루프 내 try로 감싸 텍스트 실패 페이지를 `visual_error`와 동형인 `text_error` 상태로 기록하고 계속 진행한다. `_collect_page_diff_blocks` 호출부(159-160행)도 같은 가드로 묶는다.
* **필요한 회귀 테스트:** (a) `get_text`가 특정 페이지만 raise하는 스텁에서 리포트 생성 + 해당 페이지 `text_error` 기록 + 나머지는 정상 비교, (b) `compare_mode="visual"`에서 텍스트 경로 장애가 발생해도 visual 비교가 완료되는지.

### [ISSUE-003] `parse_page_range` 1000건 상한 조용 절단

* **위치:** `src/core/worker_runtime/preflight.py:47-52, 61-66` (`MAX_PAGE_RANGE_LENGTH = 1000`, `src/core/_constants_impl/values.py:88`), `logger.warning` 후 에러 없이 부분 목록 반환.
* **우선순위:** Medium
* **신뢰도:** Confirmed
* **문제:** 범위 파싱이 상한에 닿으면 **에러 시그널 없이 조용히 앞에서 1000건만 반환**한다. 호출자(`split`, `delete_pages` 등)는 잘린 목록을 정상 입력으로 받아 실행하므로, 1000쪽 초과 문서에서 "1-2000" 같은 입력이 경고 없이 일부만 처리될 수 있다.
* **발생 조건:** 1000쪽 초과 PDF에 1000건을 넘는 범위 지정 (매뉴얼·도면집 등 현실적).
* **영향:** 사용자 의도와 다른 부분 실행 (삭제/분할 범위 축소). 미리보기로 결과 확인은 가능하고, 상한 자체는 OOM 방지 의도이므로 데이터 파괴는 아니다.
* **근거:** 코드 + 테스트가 상한을 의도로 못박음 (`tests/test_worker_page_range.py:31-33`: `"1-2000"` → `len(pages) == 1000` assert). 즉 절단은 버그가 아니라 **통보 없는 사양**이다. 무효 토큰은 hard-fail(`err_invalid_page_range`, 73-82행)인데 분량 초과만 silent라는 비대칭이 문제의 핵심이다.
* **반증 확인:** 상한 자체의 정당성(OOM/행 방지)은 인정한다. 그러나 무효 입력에는 에러를 주는 같은 함수가, 더 위험한(부분 실행) 경우에 로그 한 줄로 끝나는 것은 보호 장치가 아니다. 로그는 일반 사용자에게 도달하지 않는다.
* **호출/영향 범위:** `_parse_page_range` → `mixin_progress` 경유 모든 범위 입력 모드(`split`, `delete_pages`, `copy_page_between_docs`, `extract` 계열). CodeGraph상 `_normalize_mode_kwargs` 호출자 9곳과 교차한다.
* **권장 수정 방향:** 상한 도달 시 `err_... truncated` 계열 에러 또는 확인 가능한 경고 payload를 반환하고, UI에는 "앞 1000페이지만 적용됨" 명시 후 진행/중단 선택을 준다. 최소한 잘린 결과 메시지에 적용 건수를 표기한다.
* **필요한 회귀 테스트:** (a) 5000쪽 문서 mock에 "1-2000" 입력 시 상한 도달이 에러/경고로 표면화되는지, (b) 정확히 1000건 입력은 기존처럼 통과하는지.

### [ISSUE-004] 만료 검사 스크립트의 day 경계 off-by-one (CI 게이트 + 테스트 red)

* **위치:** `scripts/check_update_manifest_expiry.py:44` (`int(total_seconds() // 86400)` floor), `.github/workflows/update-manifest-expiry.yml` (해당 스크립트 사용 CI).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** 남은 일수를 floor로 계산해 **최대 하루 적게 보고**한다. 테스트가 작성한 "10일 후 만료" 픽스처가 "9 days"로 보고되어 `tests/test_audit_2026_09_23_followup.py::test_check_manifest_expiry_states`가 실패한다 (`assert '10' in message` vs `'expires in 9 days ...'`).
* **발생 조건:** 항상 (floor는 만료 시각의 초 단위 잔여를 버린다). `warn_days=30` 경계에서는 경고가 최대 24시간 일찍 울린다.
* **영향:** CI 만료 경고의 메시지가 실제와 하루 어긋남 + repo 테스트 1건 red. 보수적 방향(일찍 경고)이라 릴리스 누락 위험은 없다.
* **근거:** 실패 테스트 로그 원문 + 코드 1행. 결정적(deterministic) 실패이며 flake가 아니다.
* **반증 확인:** 분기가 틀리는 경우는 없다 (`days_left <= warn_days`에 floor를 쓰면 경고가 늦어지지 않는다). 사용자·릴리스 영향이 없다는 점도 확인했다. 그러나 "CI 게이트 스크립트 + 그 스크립트를 검증하는 테스트가 함께 틀린 값을 두고 불일치"하므로, 게이트 자체의 신뢰가 깎인다.
* **호출/영향 범위:** 스크립트 단일 경로 → 만료 감시 CI → `updates/latest.json` 재발행 판단. 클라이언트 런타임과는 무관.
* **권장 수정 방향:** 올림(`-(-total // 86400)`)으로 일치시키거나, 테스트를 floor 의미에 맞게 고친다. 어느 쪽이든 "스크립트 동작 = 테스트 기대" 단일 진실로 맞춘다.
* **필요한 회귀 테스트:** 기존 테스트 그대로 (현재 실패가 곧 회귀 신호). 경계값 추가: 정확히 30일·30일+1초·이미 만료.

### [ISSUE-005] `images_to_pdf`에 빈 입력 명시 가드 부재 (`merge`와 비대칭)

* **위치:** `src/core/worker_ops/compose/ops.py:72-99` (`images_to_pdf`), 대조 `merge:22-24` (`if not files: err_no_files_selected`).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** `images_to_pdf`는 handler 진입부에 빈 입력 검사가 없다. `files` 키 누락 시 `_as_list(None)` → `[]` → 루프 스킵 → 빈 문서 `save` → `ValueError: cannot save with zero pages`(프로브로 확인)가 generic 핸들러로 빠져 **`err_operation_failed` 통 에러**가 된다. `merge`처럼 `err_no_files_selected`/`err_output_path_missing` 명시 분기가 없다.
* **발생 조건:** `files` 없이(또는 전부 비문자열로) `images_to_pdf`를 직접 호출한 경우. UI(`tabs_basic/convert.py:221-223`)는 파일 목록을 넘기므로 통상은 preflight(`files` present-but-empty → `err_input_file_missing`)가 막는다.
* **영향:** 원인 불명의 통 에러 메시지. 빈 PDF가 저장되는 일은 없다(`save`가 raise하므로 fail-closed).
* **근거:** 코드 대조 + `.venv` python 프로브 (`fitz.open()` 빈 문서 `save` → `ValueError`). preflight의 `files` 루프(`preflight.py:260-290`)는 키가 없을 때 `continue`로 건너뛰므로 이 틈을 메우지 못한다.
* **반증 확인:** UI 경로·일반 preflight 경로가 막고 있고, 최악의 경우에도 저장물이 생기지 않는 점은 확인했다. 그래서 Low다.
* **호출/영향 범위:** `images_to_pdf` 단일 핸들러. `merge`·`batch`(preflight+handler 이중 검사)와 대조된다.
* **권장 수정 방향:** `merge`와 동일한 진입 가드(`files` 비어 있으면 `err_no_files_selected`, `output_path` 없으면 `err_output_path_missing`)를 핸들러에 추가한다.
* **필요한 회귀 테스트:** `files` 누락/`[]`/`[None, ""]` + `output_path` 누락 조합에서 명시 에러 키가 나가고 출력물이 생기지 않는지.

### [ISSUE-006] `run_worker`의 도달 불가 `wait(3000)` 분기 (죽은 방어 코드)

* **위치:** `src/ui/main_window_worker.py:52-67` (실행 중이면 큐에 넣고 `return`) vs `:69-80` (`if self.worker: if isRunning: wait(3000)...`).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** 52행이 `worker.isRunning()`이면 항상 return하므로, 70행의 `isRunning()` 검사는 같은 스레드에서 참이 될 수 없고 `wait(3000)`·지연 큐 분기는 **도달 불가**하다. 방어처럼 보이지만 실행되지 않는 코드다.
* **발생 조건:** 없음 (정적 도달 불가. 동일 UI 스레드에서 52행과 70행 사이에 이벤트 루프 재진입이 없으므로 TOCTOU도 성립하지 않는다).
* **영향:** 런타임 영향 없음. 그러나 "이전 worker가 3초 안에 안 끝나면 대기열로"라는 읽히는 동작이 실제로는 없으므로, 유지보수자의 오해를 유발한다.
* **근거:** 49-80행 직접 열람. 2026-09-23 감사의 ISSUE-004(모달 제거→자동 큐)는 52-67행으로 해결 확인됐고, 69-80행은 그 이전 로직의 잔재다.
* **반증 확인:** 삭제해도 동작이 변하지 않음을 구조상 확인했다. `_finalize_worker()`(80행)는 여전히 finished worker 정리에 필요하다.
* **호출/영향 범위:** 69개 `run_worker` 호출자 전체에 공통. 동작 변경 없이 정리 가능하다.
* **권장 수정 방향:** 69-79행의 안쪽 `isRunning` 분기를 제거하고 주석으로 "실행 중은 위에서 이미 큐잉됨"을 명시한다.
* **필요한 회귀 테스트:** 기존 `test_run_worker_pending_queue.py`·`test_audit_2026_09_23_followup.py` 큐 테스트 그대로 (동작 불변 확인).

> 2026-09-23 감사 ISSUE-001~004 해결 확인 (본 감사에서 코드 재검증):
>
> * 001 매니페스트 게시 재시도 → 해결: `.github/workflows/release.yml`에 `pull --rebase + push` 최대 3회·지수 백오프(5s·10s) 루프 + `fail_on_unmatched_files` + `merge-base --is-ancestor` 검사 확인.
> * 002 조용한 확인 실패 → 해결: `update_mixin.py:94-121` 상태바 1회성 힌트 + `_last_update_check_error` + 5분 뒤 1회 자동 재시도 확인.
> * 003 다운로드 재시도 → 해결: `update_installer.py:64-147` `STAGE_UPDATE_MAX_RETRIES=3`, `_is_transient_stage_error`가 `OSError/TimeoutError/ConnectionError`를 재시도하고 서명/HTTPS 정책 오류를 제외함 확인.
> * 004 실행 중 모달 → 해결: `main_window_worker.py:52-67` FIFO 자동 큐 + 비모달 토스트 확인 (단, [ISSUE-006] 잔재 분기 남음).

## 5. Potential Functional Gaps

* **Confirmed Gap:** 깨끗한 env 게이트를 이 머신에서 재현할 수 없다. 문서상 게이트(`pip install -e .[dev]`)와 달리, 이 머신의 `.venv`에는 pytest가 없고 `.venv-fluent`는 존재하지 않는 Python 3.14를 가리켜 깨져 있으며, system python의 `qfluentwidgets`는 전이 의존성(`qframelesswindow`) 누락으로 깨져 있다. 감사 제약(불필요한 의존성 설치 금지)상 복구하지 않았으므로, 본 감사의 테스트 실패 2건(env 2건 제외)은 **깨진 env가 아닌 깨끗한 env에서 재확인해야 한다.**
* **Confirmed Gap:** `fitz` 별칭 deprecation. 실행 중 `PyMuPDF` 1.28.2가 `UserWarning: The 'fitz' API is deprecated ... use 'import pymupdf'`를 방출한다(테스트 출력에서 관측). 호출은 `src/core/optional_deps.py`로 중앙화되어 있어 마이그레이션 지점은 단일화되어 있으나, 향후 제거 시 전 기능이 한 번에 깨진다. 영향은 없으나(경고のみ) 시점이 외부에 달려 있다.
* **Confirmed Gap:** 업데이트 경로는 Windows 전용 설계(`sys.platform != "win32"`면 확인 비활성, `update_mixin.py:124`) + 릴리스/스모크 CI가 Windows 러너다. 타 플랫폼 번들을 내면 배포 채널 스펙이 새로 필요하다. 현재 README 배포 대상이 Windows이므로 당장은 공백이 아니다.
* **Likely Gap:** `QFileSystemWatcher` 파일+디렉터리 이중 감시(`window_preview/document.py:50-66`)는 원자 교체 흐름을 커버하지만, 미리보기와 같은 디렉터리에 batch 출력이 쏟아지면 디렉터리 변경 이벤트마다 재로드 스케줄이 돈다. 250ms single-shot으로 합쳐지므로 폭주는 아니나, 대량 batch 중 미리보기 깜빡임/재렌더 비용이 있다.
* 추정 항 (현재 버그처럼 표현하지 않는다):
  * 추정: 장시간 AI 스트리밍 중 네트워크 단절은 SDK 레벨 abort 없이 워커 취소(`CancelledError` 재전파)에 의존한다 — 구조상 fail-closed이나, 소켓 타임아웃까지 UI가 "대기 중"으로 보이는 구간이 있을 수 있다. 품질 감사에서도 의도적 한계로 기록된 영역이다.
  * 추정: 종료 시 실행 중 worker 강제 종료(`main_window.py:66-84` `QThread.terminate`)는 원자 저장 이후를 가정한다. 저장 중 terminate 타이밍과 겹치면 백업/교체 중간 상태가 될 수 있으나, smoke 실패 시 롤백(`update_installer`)과 달리 일반 작업 경로의 강제 종료 후 무결성 검사는 없다. 재현 조건이 극히 좁아 이슈로 올리지 않는다.

## 6. Documentation Mismatches

* README 머리(`README.md:1` `# PDF Master v4.5.9`)와 코드 버전(`values.py` `VERSION = "4.5.18"`) 불일치. 본문(133행 `dist/PDF_Master_v4.5.18.exe`, 변경 이력 v4.5.10~v4.5.18)은 4.5.18을 따르므로 **머리만 stale**하다.
* 바인딩 표기 불일치 (동작 영향 없으나 기여자가 잘못 설치할 수 있음): `README.md:3` "PyQt6 기반" + PyQt6 배지, `README.md:147-148` "PySide6-Fluent-Widgets와 혼합" 주의 문구, `README.md:318` "기본 의존성 `PyQt6-Fluent-Widgets`" vs 실제 `pyproject.toml:14-15` `PySide6==6.12.0` + `PySide6-Fluent-Widgets==1.11.3` 및 코드 전체 `PySide6` import + 릴리스 preflight의 PySide6 바인딩 assert. `CLAUDE.md:56/61` 표("PyQt6"), `CLAUDE.md/typings` 언급의 "PyQt6 스텁", `GEMINI.md:463` "v4.5.8 기준", `PROJECT_AUDIT_QUALITY.md:66` "Python 3.10+, PyQt6"도 같은 계열 stale이다.
* `pdf-master.spec`(하이픈, 1.2KB, `name='pdf-master'`, datas 없음)가 `pdf_master.spec`(언더스코어, 20KB, 릴리스 실제 사용)과 공존한다. `pyinstaller pdf-master.spec`을 실행하면 Fluent 에셋·버전 동기화 없는 미니멀 EXE가 나온다. 빌드 문서(`pdf_master.spec` 사용으로 명시)와 코드는 일치하므로, 문제는 방치된 유사 파일명이다.
* 작업 지시 문서인 `AGENTS.md`가 저장소에 존재하지 않는다 (`Test-Path AGENTS.md` → False). CLAUDE.md/GEMINI.md는 있으나 에이전트 공통 진입점 파일은 없다. 런타임 영향은 없다.
* 위를 제외하고 README의 업데이트 절(서명·해시 검증 후 교체, smoke 실패 시 롤백, `vX.Y.Z` 규칙), `pyproject.toml` 명령(`pip install -e .[dev]`, `python -m pyright`, `python -m pytest -q`, `python -m build`, `python -m PyInstaller pdf_master.spec --clean`, `main.py --smoke`, `scripts/package_smoke.ps1`)은 코드와 일치한다. `tests/test_validation_docs_config.py`의 문서 계약(필수 문자열·레거시 감사 참조 금지)은 본 감사서도 준수한다.

## 7. Recommended Fix Plan

> 실제 코드 수정은 하지 않는다. 우선순위별 방향만 제시한다.

### Phase 1 — Immediate

1. Fluent 기동 하드 게이트 완화 ([ISSUE-001]). `setup_app_theme` 실패를 raise가 아닌 경고+Qt 폴백 기동으로 바꾸고, 혼합 설치 같은 실제 위험만 거부한다. TabShell 폴백을 프로덕션에서 도달 가능하게 한다.
2. `compare_pdfs` 텍스트 경로 페이지 격리 ([ISSUE-002]). `get_text` 실패 페이지를 `text_error` 상태로 기록하고 계속 진행 (`visual_error`와 동형).
3. 만료 스크립트 day 경계 단일화 ([ISSUE-004]). 올림/내림 중 하나로 스크립트와 테스트를 일치시킨다 — CI 게이트 신뢰 회복이 목적이다.

### Phase 2 — Stability

1. `parse_page_range` 상한 도달 표면화 ([ISSUE-003]). 에러 또는 "앞 1000건만 적용" 명시 후 진행/중단 선택.
2. `images_to_pdf` 진입 가드를 `merge`와 대칭으로 ([ISSUE-005]).
3. `run_worker` 도달 불가 분기 제거 ([ISSUE-006]). 동작 불변 정리 + 주석.
4. 테스트 env 게이트 문서화: `pip install -e .[dev]` 깨끗한 env에서만 `pytest`/`--smoke`를 판정으로 인정하고, 드리프트된 env(system python) 결과와 구분한다. `.venv-fluent` 깨진 참조 정리.

### Phase 3 — Structural

1. `fitz` → `pymupdf` import 마이그레이션 (`optional_deps.py` 단일 지점). 경고 제거 + 향후 제거 대비.
2. 버전·바인딩 문서 단일 소스화: README 머리 버전, CLAUDE/GEMINI 버전 표기, PyQt6 잔재, `pdf-master.spec` 잔재 정리. `AGENTS.md` 필요 여부를 결정 (없으면 작업 지시에서 제외).
3. 미리보기-배치 출력 동일 디렉터리 재로드 strobe 검토 (gap 항목): 대량 batch 중 불필요한 재렌더를 디바운스/발생원 필터로 줄인다.
4. 강제 종료 후 무결성 확인(추정 항)을 스모크 수준에서라도 정의한다 — 현재는 업데이트 경로에만 smoke+롤백이 있다.

## 8. Test Recommendations

| 대상 | 입력 조건 | 기대 결과 |
|------|-----------|-----------|
| Fluent 폴백 기동 | qfluentwidgets import 실패 주입 + offscreen `--smoke` | exit 0, `tabs._use_fluent is False`, 경고 로그 존재 |
| Fluent 혼합 설치 거부 | PyQt6 잔재 바인딩 조건 | 기존처럼 기동 거부 유지 (폴백 대상 아님) |
| compare 텍스트 격리 | 특정 페이지만 `get_text` raise + `compare_mode="both"` | 리포트 생성, 해당 페이지만 `text_error`, 나머지 정상 비교 |
| compare visual 독립성 | `compare_mode="visual"` + 텍스트 경로 장애 주입 | visual 비교 완료, 리포트의 visual 결과 정상 |
| 범위 상한 표면화 | 5000쪽 mock에 `"1-2000"` | 상한 도달이 에러/경고로 표면화, 조용한 1000건 저장 금지 |
| 범위 정상 통과 | 정확히 1000건 입력 | 기존처럼 통과 (회귀 방지) |
| 만료 경계 | 만료 = now+30일 / +30일 1초 / 과거 | 코드·메시지·테스트 기대 일치 (올림/내림 단일 규칙) |
| images 빈 입력 | `files` 누락·`[]`·`[None,""]`, `output_path` 누락 조합 | `err_no_files_selected` 등 명시 키, 출력물 없음 |
| 대기열 불변 | 실행 중 2번째 `run_worker` + 9번째 요청 | 모달 없이 큐 적재→완료 후 자동 실행, 9번째 거부 토스트 (기존 테스트 유지) |
| 동일 경로 저장 | 미리보기 문서에 덮어쓰기 | 저장 전 미리보기 해제→뷰 상태 복원, 실패 시 원본 유지 |
| 취소 롤백 | 대용량 분할/추출 중 취소 | `created_output_paths`만 삭제, 사전 존재 파일 보존 |
| AI 암호 PDF | 암호 PDF + 미리보기 인증 세션 | 임시 복호본 처리 후 삭제, ACL 실패 시 메타 경고 |
| 첨부 경로 안전 | `../`·절대경로·예약어 파일명 포함 PDF | 모두 `output_dir` 하위 정규화 저장, 중복명 일련화 |
| 손상 PDF 비교 | Content Stream 손상 1쪽 포함 문서 쌍 | 해당 쪽만 오류 기록 후 리포트 완성 (신규, ISSUE-002) |
| 플랫폼 한계 | Windows 전용 업데이트 확인 (Linux/macOS) | 비활성 + 릴리스 페이지 안내 (설계 일치 확인) |

## 9. Final Assessment

| 구분 | 평가 | 근거 |
|------|------|------|
| Functional Correctness | Acceptable | 핵심 흐름 보호됨. compare 격리·범위 절단·빈 입력 가드의 비대칭 3건이 감점 요인 |
| Runtime Stability | Acceptable | 단일 비행·대기열 상한·민감값 scrub·취소 정리는 견고. Fluent 하드 게이트가 기동 안정성을 깎음 |
| Data Integrity | Good | 원자 저장·동일 경로 복원·첨부 경로 안전화·해시/크기 검증이 촘촘함. 확인된 손실 경로 없음 |
| Error Resilience | Acceptable | 실패가 드러나고 복구 가능. 텍스트 경로 무방비 + 만료 스크립트 경계가 감점 요인 |
| Cross-platform Robustness | Acceptable | Windows 우선 설계와 일치. win32 가드가 명시적이나 타 플랫폼 채널 스펙은 없음 |
| Test Confidence | Needs Work | `pyright` 0 errors이나, `pytest` 4 failed(실제 2건 + env 2건) + teardown AV로 최종 counts 미확보. 깨끗한 env 재실행이 필요 |

**먼저 수정할 문제 3개:** Fluent 하드 기동 게이트 완화 ([ISSUE-001]) → `compare_pdfs` 텍스트 경로 페이지 격리 ([ISSUE-002]) → `parse_page_range` 상한 표면화 ([ISSUE-003]).

## 10. Follow-up — 조치 적용 기록 (2026-11-22)

> 본 감사서 §4·§6·§7 제안의 코드 반영 기록. 코드는 수정했고, 감사 본문(§1~§9)은 감사 시점 스냅샷으로 유지한다.

* [ISSUE-001] `main.py` 기동 게이트를 경고+Qt 폴백 계속 기동으로 변경, `--smoke`도 폴백을 정상으로 인정. 릴리스 preflight의 fluent assert(CI 패키징 게이트)는 유지.
* [ISSUE-002] 텍스트 추출·블록 수집을 `compare/text_diff.py` 단계 믹스인(`_extract_page_texts`·`_compute_page_text_diff`·`_text_error_result`)으로 격리. `ops.py`는 오케스트레이션만 남겨 구조 예산(240줄) 준수. `text_error` 상태·`text_error_count` payload·리포트/UI 요약·카탈로그 키(KO/EN) 추가, `dispatch` `result_payload_keys`·`results.py` 기본값 보정 포함.
* [ISSUE-003] 상한 초과(`> 1000`)를 `err_page_range_truncated` 에러로 표면화 (정확히 1000건은 기존처럼 통과). 카탈로그 키(KO/EN/FALLBACK) 추가, `test_worker_page_range.py` 기대값 갱신.
* [ISSUE-004] `check_update_manifest_expiry.py`를 올림(`ceil`)으로 변경. 기존 실패 테스트가 그대로 통과.
* [ISSUE-005] `images_to_pdf`에 `err_no_input_files`·`err_output_path_missing` 진입 가드 추가 (카탈로그 키 KO/EN/FALLBACK).
* [ISSUE-006] `run_worker` 도달 불가 `wait(3000)` 분기 제거 + 주석.
* 문서: README/README_EN 머리 버전(→4.5.18)·PySide6 표기·`PySide6-Fluent-Widgets` 패키지명 정정, CLAUDE/GEMINI 버전 표기(→4.5.18)·프레임워크 표기 정정, `PROJECT_AUDIT_QUALITY.md` 스택 표기 정정, 무참조 `pdf-master.spec` 삭제. `AGENTS.md`는 신규 생성하지 않기로 결정 (CLAUDE.md/GEMINI.md가 에이전트 진입점 역할을 이미 수행).
* `fitz`→`pymupdf`: 이미 `optional_deps._load_fitz_module`에서 canonical import로 중앙화되어 있었고 `test_optional_deps_fitz_alias`로 고정됨 — 추가 변경 없음. 테스트 파일들의 `import fitz` 잔재는 경고만 내보내므로 잔여 항목으로 남김.
* 신규 회귀: `tests/test_audit_2026_11_22_followup.py` 4건 (images 빈 입력 2건, compare 텍스트 격리 2건).
* 검증: `python -m pyright src/core src/ui` → **0 errors**; `python -m pytest -q` → 이전 실패 3건(만료·compare·smoke) 해소, 잔여 FAILED 1건은 깨진 system-python env 전용(`qframelesswindow` 부재, 코드 무관) + teardown AV 1회 관측(동일 env 상관). `tests/test_validation_docs_config.py` 통과로 감사서 계약 유지 확인.


