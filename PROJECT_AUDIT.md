# Project Audit

> 대상: PDF Master (커밋 상태 기준, `VERSION = "4.5.19"`)
> 일자: 2026-11-24 / 아래 Follow-up에 기록된 대로 제안 사항을 모두 반영했다.
> 이전 `PROJECT_AUDIT.md`가 존재했으나, 본 문서는 이번에 직접 확인한 내용으로 새로 작성했다.

## 0. Follow-up — 조치 상태 (2026-11-24)

* ISSUE-001 해결: 모델 목록 새로고침을 데몬 스레드 + Signal 방식으로 변경 (`model_choice._refresh_ai_models` 분리: `_fetch_model_choices`/`_apply_model_choices`/`_on_model_refresh_finished`). 회귀 테스트 `tests/test_ai_model_refresh.py` 3건.
* ISSUE-002 해결: 채팅 전송 히스토리 상한 (`MAX_CHAT_CONTEXT_ENTRIES=20`, `MAX_CHAT_CONTEXT_CHARS=20000`, 최신분 유지) + 400 계열 non-retryable 분류. 회귀 테스트 `tests/test_ai_chat_context.py` 5건.
* ISSUE-004 해결: 복원 실패 시 `UndoRestoreError` 전파 → `UndoManager`가 스택 원복, UI는 상태 표시만. 회귀 테스트 `tests/test_undo_restore_failure.py` 3건.
* ISSUE-003 해결: 시작 시 `last_output_dir` orphan 스윕 (`sweep_output_dir_orphans`). 회귀 테스트 `tests/test_output_orphan_sweep.py` 2건.
* CI 게이트 추가: `checks.yml`에 `full-checks` 작업 (ruff + pyright + 전체 pytest). 단, 전체 pytest/ruff/pyright 0-error를 먼저 달성한 뒤 추가했다.
* `tm.get` KeyError 통일 (worker `get_message`와 동일). 테스트 1건 추가.
* 문서 버전 표기 동기화: README/README_EN/CLAUDE/GEMINI의 `4.5.18` 표기를 `4.5.19`로 갱신 (이력 섹션·since 표기는 유지).
* 검토 후 유지 결정 (코드 변경 없음): 배치 취소 시 완성 출력물 삭제 (테스트로 고정된 의도된 동작), `validate_api_key` 공개 유지 (CLAUDE/GEMINI 문서화 계약), 장시간 네이티브 저장의 취소 지연 (구조적 한계).
* Phase 3에서 제거한 데드코드: `WorkerRuntimeAccessMixin._init_ai_service` (호출처 없음 확인 후 삭제).

검증: 전체 453 passed + 1 skipped, `ruff check src tests main.py` clean, `pyright` 0 errors.

## 1. Executive Summary

* **프로젝트 전체 상태**: 양호. 핵심 데이터 경로(원자 저장·백업·복구·서명 업데이트)가 견고하게 설계되어 있고, 테스트 스위트 439건이 통과한다.
* **전체 위험도**: 낮음. Critical/High에 해당하는 실제 문제를 찾지 못했다. 남은 것은 복구 가능한 수준의 Medium 2건, Low 2건이다.
* **가장 중요한 문제 3개**:
  1. [ISSUE-001] AI 모델 목록 새로고침이 UI 스레드에서 동기 네트워크 호출 → 느린 네트워크에서 UI 프리즈 (Medium/Likely)
  2. [ISSUE-002] AI 채팅 전체 히스토리 무제한 전송 → 초대형 대화에서 실패 가능, 토큰 가드 없음 (Medium/Likely)
  3. [ISSUE-004] Undo 복원 실패가 성공으로 기록됨 (스택 이동 + 성공 토스트) (Low/Likely)
* **데이터 손상/유실 가능성 여부**: 직접적인 데이터 손실 경로는 찾지 못했다. 모든 파일 쓰기는 동일 디렉터리 임시 파일 + `os.replace` 원자 교체이며, 동일 경로 덮어쓰기는 미리보기 문서를 먼저 닫고, 실패·취소·종료 경로마다 복원/롤백/정리가 있다. 자동 업데이트도 서명 검증 + smoke 검증 + `.bak` 롤백이 있다.
* **가장 먼저 수정해야 할 영역**: AI 모델 새로고침의 백그라운드화 (ISSUE-001) — 유일하게 사용자 체감 장애(프리즈)로 직결되는 항목이다.

## 2. Project Understanding

* **프로젝트 목적**: PySide6 기반 올인원 PDF 데스크톱 앱 (병합·편집·보안·마크업·추출·AI 요약/채팅·자동 업데이트).
* **주요 entrypoint**: [main.py](D:\twbeatles-repos\pdf-master\main.py) (`main()` → 단일 인스턴스 락 → 스플래시 → `PDFMasterApp`), `--apply-update` (업데이트 헬퍼 모드), `--smoke` (패키지 검증).
* **핵심 모듈**:
  - `src/core/worker_runtime/` — 작업 공통 런타임 (dispatch → preflight → handler → 에러 매핑, 원자 저장, 취소)
  - `src/core/worker_ops/` — 도메인별 실제 구현 (page/transform/annotation/extract/cleanup/compare/form/compose/security/batch/ai)
  - `src/core/ai/` — Gemini 서비스 (모델 레지스트리·폴백·세션 캐시·File API 업로드)
  - `src/core/update_installer.py` + `update_manifest.py` + `update_service.py` — 서명 업데이트 (Ed25519, HTTPS 강제, sha256/size 검증, smoke 후 교체, `.bak` 롤백)
  - `src/ui/main_window_worker.py` + `window_worker/` — 워커 스레드 수명주기 (FIFO 대기 큐 상한 8, 취소 정리, undo 등록, same-path 복원)
  - `src/ui/window_undo/` — 스냅샷 기반 Undo/Redo (before/after 백업 복사)
  - `src/core/_settings_impl/` + `keyring` — 설정/채팅 기록 영속화 (원자 쓰기, API 키는 keyring 우선)
* **데이터 저장 방식**: 로컬 JSON 설정 파일 (원자 교체), 채팅 기록 JSON, undo 백업 사본 (시스템 temp), 원격 Gemini File API (세션 캐시, 인메모리).
* **외부 의존성**: PySide6 6.12, PyMuPDF, `google-genai>=3.6.1` (optional), `cryptography` (Ed25519 검증), keyring (optional), Tesseract (optional, OCR).
* **핵심 실행 흐름**:

  `UI 액션 → run_worker(mode, kwargs) → WorkerThread → _normalize_mode_kwargs → preflight_inputs(검증) → handler → 원자 저장 → result_payload → on_success/on_fail/on_cancelled → 미리보기 복원/undo 등록/정리`

  AI 흐름: `UI → run_worker(ai_*) → AIService(모델 결정·폴백) → File API 업로드 또는 로컬 텍스트 추출 → generate_content[_stream]/chats → 구조화 파싱 → meta(모델명 포함) → 결과 표시`

  업데이트 흐름: `기동 2초 후 silent 확인 → Ed25519 매니페스트 검증 → 사용자 동의 → 스테이징(sha256/size 검증, 3회 재시도) → 헬퍼 Popen → 앱 종료 → smoke 검증 → 교체/롤백 → 결과 파일`

## 3. Audit Coverage & Limitations

* **실제 확인한 주요 모듈**: `main.py` 전체, `update_installer.py` 전체, `update_manifest.py` 전체, `update_mixin.py` 전체, `worker_runtime/{mixin_run,preflight,normalize,io,mixin_access,mixin_files,save_profiles,dispatch(일부)}`, `_undo_impl/manager.py`, `window_undo/{backup,cleanup,history,mixin}.py`, `window_worker/{lifecycle,helpers,undo,success,fail,same_path}.py`, `main_window_worker.py`, `main_window.py::closeEvent`, `worker_ops/{security/ops,batch/ops,ai/prepare}.py`, `ai/{errors}.py`, `worker_runtime/messages.py`, `i18n.py`, `pdf_validation.py`, `temp_cleanup.py`, `_settings_impl/{api_key,persistence}.py`, `.github/workflows/checks.yml`.
* **호출 관계 분석 방식**: CodeGraph MCP·CLI가 이 환경에 없다 (전용 도구 미제공, `codegraph` 명령 없음 — `.codegraph/` 디렉터리만 존재). 그래서 `muse.search`(regex) + 파일 직접 열람으로 caller/callee를 추적했다. 본 문서에 "CodeGraph로 확인"이라고 쓰지 않았다.
* **실행한 테스트** (모두 통과):
  - `tests/test_worker_cancel_cleanup.py`, `test_update_manifest.py`, `test_update_installer.py`, `test_undo_backup_flow.py`, `test_i18n_ui_hardcoded_smoke.py`, `test_worker_dispatch_registry.py` — 29건 통과
  - 전체 스위트: **439 passed, 1 skipped** (opt-in Gemini live smoke 1건 skip; 코드 변경 없이 감사 직전 상태 기준)
  - 직접 실행 프로브: `tm.get` 미등록 키 폴백(키 그대로 반환), 서식 인자 전달 확인
* **확인하지 못한 환경/외부 서비스**: 실제 Gemini API 호출 (키 없음 — 모의 클라이언트 테스트로 대체됨), 실제 서명 업데이트 E2E (단위 테스트로 대체), macOS/Linux 실기기 동작, 대용량(수백 MB) PDF 수동 시나리오.
* **분석상의 한계**: 정적 추적 + 기존 테스트에 의존하므로, UI 스레드 블로킹 시간 같은 런타임 정량은 측정하지 않았다 (해당 항목은 Likely로만 분류). 테스트 프로세스 종료 시점에 이 환경에서 `-1073740791` 종료 코드가 간헐·재현성 있게 관찰됐는데, 변경 없는 원본 트리에서도 동일해 앱 동작이 아닌 테스트 환경 teardown 문제로 판단하고 이슈에서 제외했다.

## 4. High-Risk Issues

### [ISSUE-001] AI 모델 목록 새로고침이 UI 스레드에서 동기 네트워크 호출

* **위치:** [src/ui/tabs_ai/setup.py](D:\twbeatles-repos\pdf-master\src\ui\tabs_ai\setup.py) (`btn_refresh_models.clicked` 연결) → [src/ui/tabs_ai/model_choice.py](D:\twbeatles-repos\pdf-master\src\ui\tabs_ai\model_choice.py) (`_refresh_ai_models`) → [src/core/ai/service.py](D:\twbeatles-repos\pdf-master\src\core\ai\service.py) (`refresh_models` → `client.models.list()`)
* **우선순위:** Medium
* **신뢰도:** Likely (호출 체인은 코드로 확정, 블로킹 시간은 미측정)
* **문제:** 새로고침 버튼 핸들러가 GUI 스레드에서 `models.list()` 네트워크 호출을 직접 수행한다. SDK 타임아웃(30s) + 내부 재시도가 겹치면 UI가 수십 초 프리즈된다.
* **발생 조건:** AI 탭에서 "모델 목록 새로고침" 클릭 + 느리거나 끊긴 네트워크.
* **영향:** UI 응답 없음 (프리즈). 데이터 손실·오작동은 없다 (실패 시 카탈로그 유지).
* **근거:** `clicked.connect(self._refresh_ai_models)` — 슬롯이 GUI 스레드에서 실행되고, 함수 내에 스레드·디바운스·타임아웃 단축이 없다.
* **반증 확인:** `check_for_updates` 같은 다른 네트워크 경로는 데몬 스레드 + Signal로 분리되어 있어, 이 경로만 분리되지 않은 것이 대조된다. `AIService` 생성자 자체는 오프라인이라 문제없다.
* **호출/영향 범위:** 호출자 `setup_ai_tab` 1곳. 영향은 AI 탭 새로고침 버튼 1개 기능으로 한정.
* **권장 수정 방향:** 새로고침을 백그라운드 스레드(QTimer/Worker 또는 `threading` + Signal)로 이동 + 진행 표시, 또는 원격 조회를 제거하고 카탈로그만 사용.
* **필요한 회귀 테스트:** `models.list`를 30초 sleep하는 모의 클라이언트로 `_refresh_ai_models` 호출 시 UI 스레드가 1초 내 반환하는지 (QTest + 타이머), 실패 시 콤보가 카탈로그 상태로 유지되는지.

### [ISSUE-002] AI 채팅 전체 히스토리 무제한 전송 (토큰 가드 없음)

* **위치:** [src/core/ai/service.py](D:\twbeatles-repos\pdf-master\src\core\ai\service.py) (`ask_about_pdf` → `_history_to_contents(conversation_history or [])` 전체 전달)
* **우선순위:** Medium
* **신뢰도:** Likely (전송 코드는 확정, 400 재현은 라이브 키 없이 불가)
* **문제:** 대화 기록이 개수 상한(40개)만 있고 토큰/문자 상한이 없어, 긴 답변이 누적되면 컨텍스트 초과로 `INVALID_ARGUMENT`(400) 실패가 날 수 있다. chat 경로는 retry 래퍼가 없어 즉시 실패한다 (낭비 재시도는 없지만 복구 수단도 없음).
* **발생 조건:** 한 PDF에 대한 장문 질의응답을 40개 가까이 누적한 채팅.
* **영향:** 해당 질문 실패 + 사용자 재시도 유도 없음. 데이터 손실 없음.
* **근거:** `_history_to_contents`가 슬라이싱 없이 전부 변환하고, 길이·토큰 검사가 어디에도 없다 (`_trim_chat_histories`는 개수만 제한).
* **반증 확인:** 요약/키워드 경로는 `MAX_TEXT_LENGTH`(30,000자) 캡이 있어 400이 희박하고, `_generate_content`의 retry는 400을 재시도하긴 하나(낭비) 요약 입력이 캡되므로 실질 타격이 작다. 즉 문제는 채팅 경로에 국한된다.
* **호출/영향 범위:** `ask_about_pdf` ← `ai_ask_question` 워커 ← 채팅 UI. 요약·키워드에는 영향 없음.
* **권장 수정 방향:** 최근 N개/문자 상한으로 히스토리 슬라이싱 (잘린 경우 meta에 표기), 400 계열을 non-retryable로 분류.
* **필요한 회귀 테스트:** 40개 × 장문 히스토리 + 모의 400 응답 → (a) 전송 전 슬라이싱되어 호출 히스토리 길이가 상한 이하인지, (b) 400 발생 시 재시도 없이 1회만 호출되고 명확한 에러 메시지가 전달되는지.

### [ISSUE-003] 출력 디렉터리의 원자 저장 orphan 임시 파일 미스윕

* **위치:** [src/core/worker_runtime/io.py](D:\twbeatles-repos\pdf-master\src\core\worker_runtime/io.py) (`atomic_*` — `mkstemp(dir=out_dir, prefix=".pdf_master_")`) vs [src/core/temp_cleanup.py](D:\twbeatles-repos\pdf-master\src\core\temp_cleanup.py) (시스템 temp만 스윕)
* **우선순위:** Low
* **신뢰도:** Likely (경로 불일치는 코드로 확정, 발생은 crash/kill 조건부)
* **문제:** 원자 저장용 임시 파일이 출력 디렉터리에 만들어지는데, orphan 스윕은 시스템 temp 디렉터리만 본다. 저장 중 프로세스 crash/강제종료 시 `.pdf_master_*.tmp.pdf` 등이 사용자 출력 폴더에 영구 잔존한다.
* **발생 조건:** `os.replace` 이전 시점의 crash/kill (정상 취소 경로는 finally에서 정리됨을 확인).
* **영향:** 쓰레기 파일 누적. 데이터 손상 없음 (원본은 replace 전까지 untouched).
* **근거:** `io.py`의 4개 `mkstemp`가 전부 `dir=out_dir`이고, `cleanup_pdf_master_temp_files`의 glob 대상은 `tempfile.gettempdir()`뿐이다.
* **반증 확인:** 정상 완료·취소·종료 경로는 모두 정리된다 (finally 절, `_cleanup_cancelled_worker`, closeEvent 스윕). 즉 순수 비정상 종료 경로만의 문제다.
* **호출/영향 범위:** 모든 파일 출력 모드 공통 (`atomic_pdf/text/binary/pixmap_save`).
* **권장 수정 방향:** 시작 시 `last_output_dir`/최근 출력 디렉터리에도 동일 접두사 스윕을 적용하거나, orphan 감지 시 로그로 안내.
* **필요한 회귀 테스트:** `mkstemp` 후 `replace` 전 예외 주입 → orphan 파일 생성 확인 → 스윕 함수 호출 후 제거되는지.

### [ISSUE-004] Undo 복원 실패가 성공으로 기록됨

* **위치:** [src/ui/window_undo/backup.py](D:\twbeatles-repos\pdf-master\src\ui\window_undo\backup.py) (`_restore_from_backup`, `_redo_from_output`) + [src/core/_undo_impl/manager.py](D:\twbeatles-repos\pdf-master\src\core\_undo_impl\manager.py) (`undo`/`redo`)
* **우선순위:** Low
* **신뢰도:** Likely (실패 삼킴은 코드로 확정, 트리거는 외부 개입 조건부)
* **문제:** 백업이 없거나 복원 복사가 실패하면 경고 다이얼로그만 띄우고 `return`한다 (예외 없음). `UndoManager`는 콜백이 raise해야 스택을 되돌리므로, 복원이 안 됐는데도 기록이 redo 스택으로 이동하고 성공 토스트(`history.py`)까지 표시될 수 있다.
* **발생 조건:** 백업 파일의 외부 삭제·백신 격리·권한 변경 후 undo/redo. (3종 cleanup은 스택内 백업을 보호하므로 내부 경로로는 발생하지 않음을 확인.)
* **영향:** 상태 표시 불일치. 원본을 잘못된 내용으로 덮지 않으므로 데이터 손상 없음.
* **근거:** `_restore_from_backup`의 `return` 3곳 모두 raise 없음 + `manager.undo()`의 스택 복구가 `except` 블록에만 있음.
* **반증 확인:** 200MB 초과 원본은 `_create_backup_for_undo`가 `""`를 반환하고 `_pending_undo` 자체가 등록되지 않아 이 경로에 닿지 않는다. 즉 도달 경로는 외부 개입으로 한정된다.
* **호출/영향 범위:** `_undo_action`/`_redo_action` ← undo/redo 버튼·단축키.
* **권장 수정 방향:** 복원 실패 시 `False`/예외를 반환하고, `_undo_action`에서 실패를 감지해 스택 이동 없이 에러만 표시.
* **필요한 회귀 테스트:** 백업 파일을 삭제한 뒤 undo → 스택 길이 불변 + 에러 다이얼로그 표시 + redo 스택에 추가되지 않음.

## 5. Potential Functional Gaps

* **Confirmed Gap — 전체 테스트 스위트가 CI에 없었다 (조치됨).** 감사 시점의 [checks.yml](D:\twbeatles-repos\pdf-master\.github\workflows\checks.yml)은 테마 회귀 + 앱 smoke + 매니페스트 만료 게이트만 실행했다. Follow-up에서 `full-checks` 작업 (ruff + pyright + 전체 pytest)을 추가했다.
* **Confirmed behavior (버그 아님, UX 트레이드오프)** — 취소 시 해당 실행에서 만든 *완성된* 출력물도 삭제된다 (`test_cancel_cleanup_*` 3건이 의도된 동작으로 고정, CLAUDE.md에도 명시). 배치 작업처럼 부분 완료물이 유의미한 모드에서는 사용자가 "취소 = 지금까지 한 것은 유지"를 기대할 수 있어, 모드별 정책 분리(배치는 유지 등)를 검토할余地가 있다.
* **Likely Gap — 재시작 시 원격 Gemini File API 고아 파일.** 업로드 캐시가 인메모리라서 앱 재시작 후 이전 세션의 원격 파일 삭제를 시도할 수 없다. 48시간 자동 만료가 있어 실해는 작다. (종료 시 `shutdown_executor`가 정상 경로를 정리하는 것은 확인.)
* **추정 — 장시간 네이티브 저장 중 취소 지연.** `doc.save()` 같은 긴 네이티브 호출 사이에는 `cancel_check`가 끼어들 수 없어, 초대형 PDF 저장 중 취소가 수 초 지연될 수 있다. 구조적 한계이며 종료-강제종료 경로가 별도로 있다.
* **추정 — `tm.get`의 서식 예외 처리 비대칭.** worker용 `get_message`는 `IndexError, KeyError`를 모두 잡지만, UI용 `tm.get`은 `IndexError`만 잡는다. 현재 명명 플레이스홀더(`{n}`, `{total}`) 사용처 2곳은 인자 없이 호출되는 표시용 리터럴이라 무해함을 확인했으나, 향후 인자 전달 실수 시 크래시가 된다.

## 6. Documentation Mismatches

* **버전 표기 불일치 (조치됨):** 감사 시점에 README/CLAUDE/GEMINI의 `v4.5.18` vs 코드 `4.5.19` 불일치를 확인했고, Follow-up에서 표기를 `4.5.19`로 동기화했다 (이력 섹션·since 표기는 유지). 기능 영향 없음.
* **AGENTS.md 없음:** 작업 지시에 언급됐으나 파일이 없고, 저장소 어디에서도 참조하지 않는다. 필요한 파일이 아니므로 문제 아님.
* **그 외 불일치 없음:** CLAUDE.md의 Current Behavior Notes를 표본 대조했다 (원자 저장, 취소 정리 범위, undo 스냅샷 방식, 대기 큐 상한 8, 채팅 single-flight, 업데이트 smoke+롤백). 모두 구현과 일치한다. README의 제한사항·업데이트 동작 설명도 코드와 일치한다.

## 7. Recommended Fix Plan

### Phase 1 — Immediate

* ISSUE-001: 모델 새로고침 백그라운드화 (유일한 체감 장애 경로).
* ISSUE-002: 채팅 히스토리 상한 + 400 non-retryable (실패 조건 제거가 목적).
* CI에 `pytest -q`(전체) + `ruff check` + `pyright` 게이트 추가 (가장 싼 회귀 방지책).

### Phase 2 — Stability

* ISSUE-004: undo 복원 실패의 명시적 에러 전파.
* ISSUE-003: 출력 디렉터리 orphan 스윕.
* `tm.get`의 `KeyError` 처리 통일 (worker `get_message`와 동일 수준).
* 배치 취소 정책 검토 (완성 출력물 유지 옵션).

### Phase 3 — Structural

* `validate_api_key` 등 미사용 공개 메서드 정리 또는 UI 검증 플로우에 연결 (현재 호출처 없음 — 데드 표면 축소).
* `_init_ai_service`(호출처 없음) 같은 미사용 헬퍼 정리.
* 장시간 네이티브 호출(`doc.save`, 대용량 렌더)의 취소响应 구조 검토.

## 8. Test Recommendations

* **ISSUE-001 (Integration):** `models.list`를 30초 블로킹하는 모의 클라이언트로 새로고침 버튼 클릭 → 1초 내 슬롯 반환 + 완료 후 콤보 갱신 + 실패 시 기존 목록 유지. 기대: UI 스레드 블로킹 없음.
* **ISSUE-002 (Unit):** 40개 × 5KB 히스토리로 `_history_to_contents` 호출 → 전송 길이가 상한 이하로 잘리는지. 모의 400 응답 → `generate_content` 재호출 횟수 1회 + 사용자 메시지 명확 전달.
* **ISSUE-003 (Integration):** `os.replace` 직전 예외 주입으로 orphan 생성 → 스윕 후 `.pdf_master_*` 잔존 0건.
* **ISSUE-004 (Unit):** 백업 삭제 상태에서 `undo()` → `can_undo` 유지 + redo 스택 길이 0 + 에러 경로 도달.
* **업데이트 (Integration, 기존 테스트 보완):** 만료된 매니페스트 → `NoUpdateAvailableError`가 아닌 만료 에러로 실패하고 silent 확인에서 상태바 힌트만 표시되는지 (현재 단위 테스트는 서명/검증 중심).
* **취소 의미 (Regression, 기존 유지):** 배치 5/10 완료 후 취소 → 현행 정책이면 완성물 삭제됨을 명시적으로 고정 (정책 변경 시 이 테스트가 먼저 깨지도록).
* **보안 (Unit):** `..`, 절대경로, `C:` 드라이브 표기, 예약어(`CON` 등), 제어문자, NUL 바이트를 파일명으로 주입 → 출력이 `output_dir` 하위로 강제되고 예외 없이 거부·대체되는지 (현행 `commonpath` 검사의 경계 케이스 고정 목적).
* **플랫폼 (Manual):** OneDrive/네트워크 드라이브 출력 + 백신 실시간 감시 환경에서 대용량 저장·undo·업데이트 교체 — 자동화 불가 영역이므로 릴리스 체크리스트에 수동 항목으로.

## 9. Final Assessment

| 항목 | 평가 | 근거 |
|------|------|------|
| Functional Correctness | Good | 핵심 흐름(검증→실행→원자 저장→복원) 전 구간 방어적. High 이상 실제 결함 없음 |
| Runtime Stability | Acceptable | 단일 워커 + FIFO 큐로 race 원천 차단, 종료 정리 철저. 단 ISSUE-001(UI 프리즈) 1건 |
| Data Integrity | Good | 원자 교체, same-path 미리보기 close, undo 스냅샷, 업데이트 smoke+롤백 완비 |
| Error Resilience | Acceptable | 매핑·폴백·재시도 체계적. 단 채팅 400 대응(ISSUE-002)과 undo 실패 기록(ISSUE-004) 보완 필요 |
| Cross-platform Robustness | Acceptable | 크로스 드라이브 교체·인코딩·경로 traversal 대응 확인. 단 자동 업데이트 Windows 전용(문서화됨), macOS/Linux 실측 없음 |
| Test Confidence | Needs Work | 439건 통과는 확인했으나 CI가 전체 스위트를 실행하지 않아 회귀 방지 구멍 존재 |

**실제로 먼저 수정할 문제 3개:**

1. AI 모델 목록 새로고침의 백그라운드화 (ISSUE-001)
2. CI에 전체 테스트 + ruff + pyright 게이트 추가 (§5 Confirmed Gap)
3. 채팅 히스토리 상한 + 400 non-retryable 분류 (ISSUE-002)
