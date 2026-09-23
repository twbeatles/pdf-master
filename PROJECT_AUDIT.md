# Project Audit

> 감사 기준일: **2026-09-23**
> 대상 버전: **PDF Master v4.5.7** (`src/core/_constants_impl/values.py:5`)
> 성격: **기능 감사 Track A (SSOT)** — 품질/아키텍처 부채는 `PROJECT_AUDIT_QUALITY.md` (Track B)에 위임
> 원칙: 코드 수정 없음, 감사 리포트만 작성. 이슈는 반증 검증을 통과한 `Confirmed` 또는 근거가 강한 `Likely`만 기록.

## 1. Executive Summary

* 프로젝트 전체 상태: **양호**. PyQt6 UI + `WorkerThread` 작업 계층 + PyMuPDF 도메인 모듈 + 설정/AI 캐시 계층이 분리되어 있고, `OperationSpec` 디스패치·preflight·원자 저장·취소 정리·회귀 테스트가 촘촘하다.
* 전체 위험도: **Low–Medium**. 데이터 손실/파괴 경로에서 Critical/High에 해당하는 확인된 문제를 찾지 못했다. 남은 것은 릴리스 운영(매니페스트 게시 경쟁)과 업데이트 다운로드 재시도 같은 **운영 안정성** 문제다.
* 가장 중요한 문제 3개:
  1. 릴리스 매니페스트 게시 단계에 재시도가 없음 — 동시 푸시 시 에셋은 있는데 `updates/latest.json`이 뒤처질 수 있음 ([ISSUE-001]).
  2. 시작 시 자동 업데이트 확인 실패가 조용히 버려짐 — 사용자는 다음 수동 확인까지 모름 ([ISSUE-002]).
  3. 업데이트 다운로드는 단일 시도·이어받기 없음 — 저속 네트워크에서 대용량 EXE 재시도가 처음부터 다시 받음 ([ISSUE-003]).
* 데이터 손상/손실 가능성 평가: **낮음**. 동일 경로 저장 전 미리보기 해제·저장 후 복원, 원자 저장(`os.replace` + tmp), 취소 시 `created_output_paths`만 롤백, 첨부 추출 경로 안전화, 배치 암호 권한 해석, AI 임시 복호화 파일 ACL+정리가 모두 코드로 확인된다.
* 가장 먼저 수정해야 할 영역: **릴리스/업데이트 운영 경로** (게시 재시도 → 다운로드 재시도 → 조용한 실패 표면화 순).

## 2. Project Understanding

README/CLAUDE와 CodeGraph 탐색을 바탕으로 정리했다.

* 프로젝트 목적: PyQt6 기반 올인원 PDF 데스크톱 유틸리티 (병합·분할·회전·변환·주석·양식·보안·추출·정리·비교·AI 요약/채팅/키워드).
* 주요 entrypoint:
  * `main.py` → `PDFMasterApp` (QApplication 조립, `--smoke`, `--apply-update` 분기).
  * `src/ui/main_window_worker.py:50 run_worker()` — 약 69개 UI 호출자가 모든 Worker 작업을 여기로 보냄.
  * `src/core/worker.py:16 WorkerThread` — `WorkerRuntimeMixin.run()` → `OperationSpec` 디스패치 → `worker_ops` 도메인 핸들러 (약 122개 참조).
  * `src/ui/update_mixin.py` — 서명 업데이트 확인/다운로드/적용 UI 흐름.
* 핵심 모듈:
  * `src/core/worker_runtime/` — payload·progress·files·access·run 믹스인 + `dispatch.py`(`OperationSpec`) + `preflight.py`(`parse_page_range`, `validate_pdf_file`).
  * `src/core/worker_ops/{annotation,extract,cleanup,page,transform,compare,form,compose,security,batch,ai}/` — 도메인 패키지 + 얇은 `*_ops.py` 파사드.
  * `src/core/ai/` — client·config·cache·session·generation·service·errors 분리; 업로드/채팅/텍스트 캐시 포함.
  * `src/core/update_manifest.py` + `src/core/update_installer.py` — Ed25519 서명 검증·HTTPS 강제·해시/크기 검증·스테이징·교체·smoke·롤백.
  * `src/core/{pdf_validation,settings,undo_manager,temp_cleanup}.py` — 크기/헤더 검증, 홈 JSON 원자 저장, 스냅샷 undo, 고아 임시파일 스윕.
* 데이터 저장 방식: 설정은 사용자 홈 JSON 임시파일+`os.replace`; AI 채팅 기록은 `v2:{mtime_ns}:{정규화경로}` 키; AI 업로드/채팅/텍스트는 프로세스 내 LRU; 업데이트 결과는 `LOCALAPPDATA/PDFMaster/updates/last-update-result.json`에 한 번 소비.
* 외부 의존성: PyQt6, PyMuPDF(fitz, optional 경계 `optional_deps.py`), `cryptography`(매니페스트 서명), `google-genai`(optional AI), `keyring`(optional API 키), PyInstaller(배포).
* 핵심 실행 흐름:
  * `UI 액션 → run_worker(mode, output_path, **kwargs) → _prepare_preview_for_same_path_output → _augment_worker_passwords_from_preview → WorkerThread.run → _preflight_inputs → OperationSpec handler → atomic save → finished/error/cancelled 시그널 → preview 복원·undo 스냅샷`
  * `기동 → UpdateMixin(Windows만, idle 단일 비행) → download/verify manifest(별도 스레드) → _offer_update(모달 1회) → _download_update(진행률) → stage_update(고유 스테이징명) → launch_update_helper → 종료 → helper: 대기→백업→교체→smoke→성공 시 재기동/실패 시 롤백+결과 JSON → 다음 기동에서 1회 소비·표시`

## 3. Audit Coverage & Limitations

* 직접 확인한 주요 모듈: `main.py`, `worker.py`, `worker_runtime/{dispatch,preflight,mixin_files,io}`, `extract/attachments.py`, `batch/ops.py`, `security/ops.py`, `ai/{cache,handlers,prepare,temp_acl}`, `update_{mixin,manifest,installer}`, `window_worker/lifecycle.py`, `pdf_validation.py`, `_constants_impl/values.py`, `pdf_master.spec`, `.github/workflows/release.yml`, `scripts/build_update_manifest.py`.
* CodeGraph로 분석·추출한 관계:
  * `WorkerThread` → 122개 참조 (`main_window_worker.py` 중심), `run_worker` → 69개 UI 호출자, `OperationSpec` 디스패치, `_enqueue_pending_worker`/`_run_pending_worker` 대기열, `AIService summarize/chat/upload cache`, `UpdateMixin/apply_update/stage_update/manifest signature`, `pdf_validation/parse_page_range/attachment/permissions`.
* 실행한 테스트:
  * `python -m pytest -q` → **exit 0** (약 330개 테스트, 1 skip — opt-in Gemini File API smoke).
  * `python -m pyright src/core src/ui` → **0 errors, 0 warnings**.
* 확인할 수 없었던 환경/행위/비즈니스: 실제 GitHub Release 태그 푸시 E2E (에셋 게시→매니페스트 커밋→클라이언트 stage→교체→smoke→재기동→롤백), 저속 네트워크 대용량 다운로드, 장시간 실행 메모리 프로파일, macOS/Linux 번들 경로 (제품이 Windows 우선이므로 설계상 범위 밖).
* CodeGraph 또는 분석의 한계: 정적 호출 그래프는 `OperationSpec` 문자열 디스패치·Qt 시그널 경계·런타임 kwargs 정규화의 실제 분기를 완전히 따라가지 못하므로, 해당 경계는 파일 직접 열람과 테스트 실행으로 보완했다.

## 4. High-Risk Issues

> Critical/High에 해당하는 확인된 문제는 없다. 아래는 반증을 통과한 Medium 1건 + Low 3건이다.

### [ISSUE-001] 매니페스트 게시 단계의 동시 푸시 재시도 없음

* **위치:** `.github/workflows/release.yml:82-98` (`Publish update manifest`).
* **우선순위:** Medium
* **신뢰도:** Likely
* **문제:** 게시 잡은 `git pull --rebase origin main` 후 `git push`를 1회만 시도한다. 두 태그 릴리스가 겹치거나, 게시 중 main에 다른 푸시가 들어가면 push가 거부되고 매니페스트 커밋이 누락된다.
* **발생 조건:** 동일 시간대 2개 이상 릴리스/매니페스트 게시, 또는 게시–푸시 사이 main 갱신.
* **영향:** Release 에셋은 존재하는데 `updates/latest.json`이 이전 버전에 머물러 설치된 앱이 새 릴리스를 발견하지 못한다. 데이터 손실은 없다.
* **근거:** 해당 단계에 재시도 루프·원자적 게시 대체 수단이 없음. 태그→main 포함 검사는 `fetch-depth: 0`으로 이미 교정되어 이 경로만 남았다.
* **반증 확인:** 단일 메인테이너·순차 릴리스가 일반적이라 경쟁 윈도우가 좁고, 실패 시 워크플로가 fail-fast로 드러나 수동 재실행으로 복구 가능하다. 서명·해시·버전 검사가 어긋난 게시를 막으므로 잘못된 매니페스트가 나갈 가능성은 낮다.
* **검출/영향 범위:** 릴리스 워크플로 → `updates/latest.json` → 전체 설치 기반의 업데이트 발견. CodeGraph상 클라이언트 호출자는 `UpdateMixin.check_for_updates` 단일 경로.
* **권장 수정 방향:** 게시 단계에 `pull --rebase + push` 재시도(예: 3회, 지수 백오프), 또는 매니페스트 게시를 독립 잡/재실행 가능 단계로 분리.
* **필요한 추가 테스트:** 동일 베이스에서 두 게시 잡이 경합하는 시뮬레이션에서 재시도 후 단일 매니페스트 커밋으로 수렴하는지 검증.

### [ISSUE-002] 시작 시 자동 업데이트 확인 실패가 조용히 버려짐

* **위치:** `src/ui/update_mixin.py:43-56`.
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** `silent=True` 자동 확인에서 네트워크·서명·파싱 예외는 로그만 남기고 어떤 시그널도 방출하지 않는다. 상태는 `idle`로 복귀한다.
* **발생 조건:** 기동 2초 후 자동 확인이 실패하는 모든 경우 (오프라인, DNS, 5xx, 손상된 매니페스트).
* **영향:** 사용자는 실패를 알 수 없고 다음 수동 확인 때까지 업데이트 존재를 모른다. 기능 손상·데이터 영향 없음.
* **근거:** `except Exception` 분기에서 `if not silent` 조건으로 `failed` 방출이 막혀 있음.
* **반증 확인:** 의도된 조용한 기동(토스트 스팸 방지)이며, 수동 확인은 실패를 정상 표시하고 로그에 전체 스택이 남는다. 상태 머신이 `idle`로 복귀하므로 이후 확인이 막히지 않는다.
* **검출/영향 범위:** `UpdateMixin` 단일 경로. 다른 작업 흐름과 공유 상태 없음.
* **권장 수정 방향:** 상태바 1줄· Ferramenta: 상태바 1회성 힌트 또는 다음 수동 확인 시 마지막 실패 원인 노출. 동작 변경 없이 관측성만 추가.
* **필요한 추가 테스트:** 모의 `download_release_manifest` 실패 주입 시 silent 모드에서 상태가 `idle`로 복귀하고, 수동 모드에서 `failed`가 방출되는지 검증.

### [ISSUE-003] 업데이트 다운로드 단일 시도·이어받기 없음

* **위치:** `src/core/update_installer.py:54-73` (`stage_update`).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** 다운로드는 `urlopen(timeout=30)` 1회 시도이며 재시도·구간 재개가 없다. 실패 시 스테이징 파일을 삭제하고 예외를 올린다.
* **발생 조건:** 저속·불안정 네트워크에서 30–40MB EXE 수신 중 타임아웃·절단.
* **영향:** 처음부터 다시 받아야 한다. 무결성(크기·SHA-256)·HTTPS 리다이렉트 검사가 통과하지 못하면 저장하지 않으므로 손상 설치 위험은 없다.
* **근거:** 재시도 루프·Range 요청이 없고, 호출자 `_download_update`도 1회 호출 후 실패 시그널만 보낸다.
* **반증 확인:** 서명된 매니페스트의 크기·해시 검사가 손상 파일을 차단하고, 진행률 콜백·고유 스테이징명·실패 정리·24시간 helper 정리가 갖춰져 부분 파일이 남지 않는다. 사용자는 다시 확인을 눌러 복구할 수 있다.
* **검출/영향 범위:** `UpdateMixin._download_update → stage_update` 단일 경로.
* **권장 수정 방향:** 일시적 네트워크 오류에 한해 2–3회 재시도(백오프). 구간 재개는 매니페스트 크기 고정과 충돌하므로 우선순위 낮음.
* **필요한 추가 테스트:** 첫 N 바이트 후 절단되는 모의 응답에서 재시도 후 크기·해시 검증 통과 및 실패 정리(잔여 파일 없음) 검증.

### [ISSUE-004] 작업 실행 중 새 요청의 모달 확인이 UI 스레드를 막음

* **위치:** `src/ui/main_window_worker.py:53-66` (`run_worker`).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** Worker 실행 중 새 작업을 요청하면 `QMessageBox.question`(대기열 추가 여부)을 모달로 띄운다. 사용자가 답할 때까지 메인 윈도우와 상호작용할 수 없다.
* **발생 조건:** 장시간 작업 중 다른 탭 액션을 누른 경우.
* **영향:** UX 정체. 대기열 자체는 FIFO·상한 8·민감값 미저장으로 안전하므로 데이터 영향 없음.
* **근거:** 해당 분기가 모달 다이얼로그이며, `_enqueue_pending_worker`는 그 뒤에 호출된다.
* **반증 확인:** 의도된 확인(무심코 쌓이는 대기열 방지)이고, `wait(3000)` 후 defer 경로와 큐 풀 토스트가 폭주를 막는다. 취소·완료 경로는 그대로 동작한다.
* **검출/영향 범위:** 69개 `run_worker` 호출자 전체에 공통 적용. 개별 탭 수정 없이 중앙에서 개선 가능.
* **권장 수정 방향:** 모달 대신 비모달 토스트+대기열 자동 추가/실행 중 표시로 전환 (동작 변경이므로 별도 스펙으로 분리).
* **필요한 추가 테스트:** 실행 중 요청 시 모달 없이 1개가 큐에 들어가고, 완료 후 자동 실행되며, 8개 초과 시 거부 토스트가 나오는지 검증.

## 5. Potential Functional Gaps

* **Confirmed Gap:** 업데이트 E2E 자동 테스트 부재. `tests/test_update_manifest.py`(서명 수락·변조 거부·동일 버전)와 `tests/test_update_installer.py`(교체 경로 중심)는 있으나, stage→교체→smoke→재기동 및 고의 실패 롤백의 자동 E2E는 없다.
* **Confirmed Gap:** 매니페스트 만료 정책(`scripts/build_update_manifest.py:23`, 365일)이 앱 내 어디에도 표면화되지 않는다. 1년 무릴리스 시 정상 앱이 "만료" 실패를 맞으며, 만료 임박 경고·재발행 절차 안내가 없다.
* **Confirmed Gap:** 조용한 확인 실패에 백오프·다음 재시도 시점이 없다. 매 기동 1회 + 수동 확인만 존재한다.
* **Likely Gap:** 비-Windows에서는 업데이트 확인 자체가 비활성화(설계상 Windows 우선)되므로, 향후 타 플랫폼 번들을 내면 별도 배포 채널 스펙이 필요하다. 현재 README 배포 대상이 Windows라 당장은 공백이 아니다.
* 추정 항은 없다. (추정은 현재 버그처럼 표현하지 않는다.)

## 6. Documentation Mismatches

* `pdf_master.spec:482` 주석 예시가 `dist/PDF_Master_v4.5.6.exe`로 고정되어 있다. 실제 EXE명은 `values.py`의 `VERSION`(현재 4.5.7)에서 동적 생성(`pdf_master.spec:38-42,463`)되므로 동작 불일치는 없으나 주석이 구버전을 가리킨다.
* `CLAUDE.md`의 Spec Kit 안내가 `.specify/`·`specs/001-pdf-master-release-ux` 활성 기능을 전제하지만, 현재 트리에는 해당 디렉터리가 없다. 워크플로 문서와 실제 트리가 어긋나므로, 스펙 기반 작업을 하기 전에 포인터를 정리해야 한다.
* 과거 감사에서 지적된 "버전 3중복·shallow checkout·업데이트 무방비" 서술은 현재 코드와 불일치한다(해결됨): spec은 단일 소스(`APP_VERSION`), 워크플로는 `fetch-depth: 0` + `VERSION` 대조, 업데이터는 단일 비행 상태머신·win32 가드·백그라운드 다운로드·고유 스테이징·결과 JSON·smoke+롤백을 갖췄다. 본 감사서가 최신 상태이며, 구문은 인용 시 주의가 필요하다.
* 위를 제외하고 README의 업데이트 절(서명·해시 검증 후 교체, smoke 실패 시 롤백, `vX.Y.Z` 규칙, `PM_UPDATE_*` 시크릿)은 코드와 일치한다.

## 7. Recommended Fix Plan

> 실제 코드 수정은 하지 않는다. 우선순위별 방향만 제시한다.

### Phase 1 — Immediate (릴리스 운영 신뢰)

1. 매니페스트 게시 단계에 `pull --rebase + push` 재시도(3회·백오프) 또는 독립 재실행 잡 분리 ([ISSUE-001]).
2. 업데이트 다운로드에 일시 오류 재시도 2–3회 추가; 실패 정리는 현행 유지 ([ISSUE-003]).
3. 만료 정책 문서화: 릴리스 체크리스트에 365일 만료·재발행 절차 명시, 만료 30일 전 CI 경고 검토.

### Phase 2 — Stability (관측성·입력·복구)

1. silent 확인 실패의 상태바 1회성 힌트 + 수동 확인 시 마지막 실패 원인 노출 ([ISSUE-002]).
2. 실행 중 요청 UX를 모달에서 비모달 대기열 안내로 전환하는 별도 스펙 작성 ([ISSUE-004]).
3. 업데이트 E2E 시나리오를 Windows CI 또는 수동 릴리스 게이트에 편입 (stage→교체→smoke→재기동, 고의 실패 롤백).

### Phase 3 — Structural (구조·테스트 용이성)

1. `UpdateMixin`(상태/UI)과 네트워크·설치 로직의 경계를 thin service로 분리해 단위 테스트 가능 영역 확대.
2. 버전·에셋명·매니페스트 메타데이터 생성을 단일 빌드 메타데이터로 묶는 스크립트 유지 (현재 spec 단일 소스는 유지, 주석만 정리).
3. `.specify` 포인터 또는 CLAUDE.md 스펙 안내 중 하나를 현재 트리에 맞게 정리.

## 8. Test Recommendations

| 대상 | 입력 조건 | 기대 결과 |
|------|-----------|-----------|
| 매니페스트 게시 경쟁 | 동일 베이스에서 2개 게시 잡 동시 실행 | 재시도 후 단일 `latest.json` 커밋으로 수렴, 에셋과 버전 일치 |
| silent 확인 실패 | 모의 다운로드 예외 + `silent=True/False` | silent는 로그+`idle` 복귀, 수동은 `failed` 방출 |
| 다운로드 절단 | N 바이트 후 절단되는 모의 응답 | 재시도 후 크기·SHA-256 통과, 실패 시 잔여 스테이징 없음 |
| 실행 중 요청 UX | Worker 실행 중 2번째 `run_worker` | 모달 없이 큐 1건 적재→완료 후 자동 실행, 9번째 요청 거부 토스트 |
| 만료 매니페스트 | `expires_at` 과거 서명 매니페스트 | `Manifest is expired` 거부, UI 실패 표시 |
| 첨부 경로 안전 | `../`·절대경로·예약어 파일명 포함 PDF | 모두 `output_dir` 하위로 정규화 저장, 중복명 일련화 |
| 동일 경로 저장 | 미리보기 문서에 덮어쓰기 | 저장 전 미리보기 해제→저장 후 뷰 상태 복원, 실패 시 원본 유지 |
| 취소 롤백 | 대용량 분할/추출 중 취소 | `created_output_paths`만 삭제, 사전 존재 파일 보존 |
| AI 암호 PDF | 암호 PDF + 미리보기 인증 세션 | 임시 복호화본으로 처리 후 삭제, ACL 실패 시 메타에 명시 |
| 버전 단일 소스 | `values.VERSION` 변경 | spec EXE명·워크플로 대조·매니페스트 URL이 동일 버전 추종 |

## 9. Final Assessment

| 구분 | 평가 | 근거 |
|------|------|------|
| Functional Correctness | Acceptable | 핵심 흐름 보호됨. 남은 것은 운영 경로의 재시도·관측성 수준 |
| Runtime Stability | Acceptable | 단일 비행·대기열 상한·민감값 scrub·취소 정리가 확인됨 |
| Data Integrity | Good | 원자 저장·동일 경로 복원·첨부 경로 안전화·해시/크기 검증이 촘촘함 |
| Error Resilience | Acceptable | 실패가 드러나고 복구 가능. silent 실패와 단일 시도 다운로드만 약함 |
| Cross-platform Robustness | Acceptable | Windows 우선 설계와 일치. win32 가드가 명시적이나 타 플랫폼 채널 스펙은 없음 |
| Test Confidence | Good | `pytest` exit 0(약 330/1 skip), `pyright` 0 errors. 업데이트 E2E만 공백 |

**먼저 수정할 문제 3개:** 매니페스트 게시 재시도 ([ISSUE-001]) → 다운로드 재시도 ([ISSUE-003]) → 조용한 확인 실패 표면화 ([ISSUE-002]).
