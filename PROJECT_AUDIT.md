# Project Audit

> 감사 기준일: **2026-07-27**  
> 후속 구현: **2026-07-27** (1·2단계 + 3단계 일부)  
> 대상 버전: **PDF Master v4.5.6**  
> 범위: 기능 구현 관점 (검증·예외·상태/비동기·보안·경로·설정·문서 정합·테스트)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP (`codegraph_explore`), 보조 파일 열람·grep, `pytest` 실행  
> **SSOT:** 본 파일 (`PROJECT_AUDIT.md`)이 현행 기능 감사 문서

---

## 0. Implementation Follow-up (2026-07-27)

감사 권고에 대한 구현 반영 상태.

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| High §3.1 | 문서 SSOT → `PROJECT_AUDIT.md`, validation 테스트 이전 | **해결** |
| High §3.2 | 암호 PDF AI UI — preview 인증 후 Worker 진행 (옵션 A) | **해결** |
| Medium §3.5 | merge 0페이지 시 error (빈 PDF 미저장) | **해결** |
| Medium §3.3 | chat `_get_or_create_chat`에 `cancel_check` 전파 | **해결** |
| Medium | 취소 시 AI 네트워크 대기 안내 UI | **해결** |
| Medium §3.4 | AI temp `chmod 0o600` best-effort | **해결** |
| Low §3.7 | 배치 encrypt 권한 체크박스 UI | **해결** |
| 3단계 | blank/dedupe dry-run 예상 개수 확인 다이얼로그 | **해결** |
| 3단계 | compare 페이지 상세 행 확대 | **해결** |
| 3단계 | AI Client `http_options.timeout` best-effort | **부분** |
| 3단계 | OCR 엔진 optional extra | **잔여 로드맵** |
| 3단계 | 미리보기 드래그 `redact_area` | **해결** (2026-07-27) — `RegionSelectOverlay` + 좌표 매핑 + 고급 탭 연동 |
| 3단계 | SDK-level HTTP abort (요청 중 강제 중단) | **잔여 로드맵** |

**검증 (구현 후):** `python -m pyright` → 0 errors; `python -m pytest -q` → pass (opt-in Gemini smoke skip).

---

## 1. Executive Summary

PDF Master v4.5.6은 **PyQt6 UI → `run_worker` → `WorkerThread`/`worker_runtime`(preflight·dispatch·atomic I/O) → 도메인 `worker_ops`** 구조가 명확한 올인원 PDF 편집 앱입니다. 2026-07-27 감사 후속으로 High 2건(문서 게이트·암호 PDF AI UI)과 주요 Medium 항목을 코드에 반영했습니다.

### 전체 위험도

| 구분 | 평가 |
|------|------|
| **전체 위험도** | **Low–Medium** (후속 반영 후; 네트워크 AI cancel·OCR 등은 잔여) |
| Critical | **없음** |
| High (잔여) | **없음** (게이트·암호 AI UI 계약 정리) |
| Medium 잔여 | AI cooperative cancel(네트워크 블로킹), 평문 temp 본질, OCR 미구현 |
| 문서 정합 | `PROJECT_AUDIT.md` SSOT |
| 테스트 | 게이트 통과 목표; opt-in Gemini smoke 1건 skip 가능 |

### 감사 당시 핵심 문제 (구현 전 스냅샷)

1. **품질 게이트 실패** — legacy FUNCTIONAL audit / roadmap 삭제 → validation 테스트 실패 (**해결**)
2. **암호 PDF AI UI 차단 vs Worker 지원** (**해결** — preview 세션 재사용)
3. **AI 취소 cooperative** — chat upload cancel 미연결은 **개선**, SDK abort는 **잔여**
4. **2026-07-22 후속** 다수는 유지

---

## 2. Project Understanding

### 2.1 목적 (README / CLAUDE)

| 항목 | 내용 |
|------|------|
| 제품 | 올인원 PDF 편집 데스크톱 앱 (병합·변환·페이지·보안·주석·추출·배치·AI) |
| 스택 | Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai` / `keyring`, PyInstaller |
| 버전 | v4.5.6 |
| 배포 | Windows EXE 중심 (`dist/PDF_Master_v4.5.6.exe`), 소스는 크로스 실행 가능하나 폰트·인쇄·패키징은 Windows 중심 |

### 2.2 아키텍처 (CodeGraph + 문서)

```
main.py
  ├─ setup_logging / global_exception_handler (i18n)
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_undo / window_worker
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()          # CodeGraph: 66+ UI callers
            ├─ busy 가드 + _pending_workers FIFO (상한 8)
            ├─ same-path preview 해제 / passwords 주입
            └─ WorkerThread (QThread)
                 └─ WorkerRuntimeMixin.run()
                      ├─ _normalize_mode_kwargs()
                      ├─ _preflight_inputs()           # OperationSpec + PDF header/size
                      └─ handler in worker_ops/*
                           └─ signals → on_success / on_fail / on_cancelled
```

### 2.3 CodeGraph 기반 핵심 호출 관계

| 단계 | 심볼 | 위치 | 비고 |
|------|------|------|------|
| 진입 | `main()` | `main.py` | HiDPI, `--smoke`, `PDFMasterApp` |
| UI 게이트 | `run_worker` | `src/ui/main_window_worker.py` | 탭 액션 다수 caller; busy 시 대기 큐 |
| 스레드 | `WorkerThread` | `src/core/worker.py` | Runtime mixin 위임 |
| 선검증 | `preflight_inputs` | `src/core/worker_runtime/preflight.py` | batch 화이트리스트, search_term, required_* |
| 디스패치 | `OperationSpec` / `OPERATION_SPECS` | `src/core/worker_runtime/dispatch.py` | 50+ mode 계약 |
| PDF open | `_open_pdf_document` | `src/core/worker_runtime/mixin.py` | `passwords` 맵 + authenticate |
| AI | `ai_summarize` 등 | `src/core/worker_ops/ai_ops.py` | `cancel_check` + 임시 복호 |
| 취소 정리 | `_cleanup_cancelled_worker` | `src/ui/window_worker/lifecycle.py` | `created_output_paths` only |
| 종료 | `_shutdown_worker_for_close` | `src/ui/main_window.py` | cancel → 3s → 강제 terminate + temp 스윕 |

### 2.4 안정화 메커니즘 (문서 ↔ 코드 일치 확인)

| 메커니즘 | 상태 |
|----------|------|
| Same-path 저장 전 preview 해제 + 완료 후 복원 | **일치** |
| Undo 스냅샷 (`before`/`after` backup) | **일치** |
| Atomic I/O + `created_output_paths` 취소 롤백 | **일치** (mtime 휴리스틱 제거됨) |
| 첨부 추출 경로 정규화 + `output_dir` 하위 강제 | **일치** |
| AI 캐시 클래스 변수 + lock / chat single-flight | **일치** |
| 설정 JSON atomic write, API 키 keyring 우선 + 동의 기반 파일 폴백 | **일치** |
| SOLID 도메인 패키지 + thin facade | **일치** |
| 썸네일 `_is_active_loader_sender` | **일치** (ready/progress/complete 공통) |
| temp orphan 스윕 (`temp_cleanup`) | **일치** (기동/취소/강제종료) |

### 2.5 README / CLAUDE.md vs 구현 정합성

| 문서 주장 | 실제 | 판정 |
|-----------|------|------|
| v4.5.6 deep compress / cleanup / visual compare / redact_area | 도메인 패키지 + UI 존재 | **일치** |
| SOLID 도메인 패키지 | facade + 구현 패키지 | **일치** |
| zoomable_preview / Qt 인쇄 | preview 위젯 경로 | **일치** |
| Worker preflight + shared `pdf_validation` | `preflight.py` → `validate_pdf_file` | **일치** |
| 배치 미지원 op fail-fast | preflight + `batch_ops` | **일치** |
| pending FIFO / busy 단축키 비활성 | lifecycle + `set_ui_busy` | **일치** |
| **암호화 PDF AI: preview 암호 재사용** | Worker/테스트만 지원, **AI UI는 암호 PDF 차단** | **불일치** |
| pytest **230 / 229 passed / 1 skip** | 실측 **230 / 228 passed / 1 skip / 2 failed** | **불일치** |
| `legacy FUNCTIONAL audit document`가 현행 감사 문서 | 파일 **삭제됨** (git status `D`) | **불일치** |
| OCR 미구현 | 의도적 후속 | **일치** |

### 2.6 과거 High 이슈 재검증 (2026-07-15 → 현재)

| 과거 이슈 | 현재 코드 근거 | 상태 |
|-----------|----------------|------|
| AI 취소 무시 / finished 경로 | `cancel_check` + `_reraise_if_cancelled` + stream 체크 | **해결** (네트워크 블로킹은 잔여) |
| 암호 PDF AI hard reject (Worker) | `_prepare_ai_pdf_path` + passwords | **Worker 해결 / UI 미연결** |
| blank 렌더 실패 → 삭제 | 예외 시 페이지 유지 | **해결** |
| visual silent identical | `visual_error` status | **해결** |
| redact_area 확인 없음 | `QMessageBox.warning` Yes/No | **해결** |
| pending 큐 무한 | `_MAX_PENDING_WORKERS = 8` | **해결** |
| 썸네일 ready sender 가드 | `_is_active_loader_sender` | **해결** |
| 취소 mtime 휴리스틱 | `created_output_paths`만 삭제 | **해결** |

---

## 3. High-Risk Issues

> 실제 코드·테스트 실행 근거가 있는 항목만 수록. 추정은 §4.

---

### 3.1 유지 문서·감사 파일 삭제와 pytest 품질 게이트 실패

* **위치:**  
  - 삭제됨(git status): `legacy FUNCTIONAL audit document`, `PROJECT_ANALYSIS_AND_FEATURE_ROADMAP.md`  
  - `tests/test_validation_docs_config.py` — `test_docs_reference_validation_manifest_and_commands`, `test_maintained_docs_do_not_reference_missing_functional_audits`  
  - `CLAUDE.md` (FUNCTIONAL audit을 “current repo-local audit document”로 기술)  
  - `README.md` / `README_EN.md` / `CLAUDE.md` / `GEMINI.md` — pytest 기준선 수치
* **문제:**  
  1) `FUNCTIONAL_IMPLEMENTATION_AUDIT_*.md` glob 결과가 비어 `assert audit_files` 실패.  
  2) 유지 문서 목록에 포함된 `PROJECT_ANALYSIS_AND_FEATURE_ROADMAP.md`가 없어 `read_text` → `FileNotFoundError`.  
  3) 유지 문서가 “229 passed”를 주장하나 현재 워크트리는 **2 failed**.
* **영향:** CI/로컬 검증이 깨진 상태. 신규 회귀를 “전원 통과”로 오인할 위험. 감사 SSOT 경로가 이중화·단절됨(`PROJECT_AUDIT.md` vs 삭제된 FUNCTIONAL audit).
* **근거:**  
  - 2026-07-27 실행: `python -m pytest -q` → 2 failed (위 테스트명).  
  - `test_validation_docs_config.py` L5–6, L62–64, L74–81.  
  - git status 스냅샷: 두 md 파일 `D`.
* **권장 수정 방향:**  
  - (A) FUNCTIONAL audit을 복원하거나, 테스트를 `PROJECT_AUDIT.md` 단일 SSOT로 이전.  
  - roadmap 파일을 복원하거나 maintained_docs 목록에서 제거.  
  - README/CLAUDE/GEMINI 기준선을 실측 수치로 갱신.
* **우선순위:** **High**

---

### 3.2 암호 PDF AI: UI 차단 vs Worker 지원 vs 문서 서술 불일치

* **위치:**  
  - UI: `src/ui/tabs_ai/actions.py` — `action_ai_summarize`, `_ask_ai_question`, `_extract_keywords`  
  - Worker: `src/core/worker_ops/ai_ops.py` — `_prepare_ai_pdf_path`  
  - 회귀: `tests/test_ai_ops_cancel_and_encrypted.py` — `test_ai_summarize_encrypted_with_password_unlocks`  
  - 문서: `CLAUDE.md` 2026-07-15 Addendum (암호화 PDF AI unlock)
* **문제:**  
  AI 탭은 세 기능 모두에서:

```python
if is_pdf_encrypted(path):
    return QMessageBox.warning(..., tm.get("err_pdf_encrypted", ...))
```

  로 암호 PDF를 **미리보기 인증 여부와 무관하게** 거부한다.  
  반면 Worker는 `passwords` 맵으로 인증 후 `pdf_master_ai_*` 임시 평문 PDF를 만들고 File API/추출에 쓰며, 단위 테스트도 이를 검증한다. `run_worker`의 `_augment_worker_passwords_from_preview`는 AI UI가 먼저 return하므로 **실사용 경로에 도달하지 않는다**.
* **영향:**  
  - 문서/로드맵이 약속한 “암호 PDF AI”를 사용자가 쓸 수 없음.  
  - Worker·테스트 커버 범위와 제품 UX 불일치 → 향후 수정 시 회귀 방향 혼선.  
  - 의도적 안전장치(평문 temp 회피)라면 문서·Worker 공개 경로를 정리해야 함.
* **근거:** `tabs_ai/actions.py` L80–81, L117–118, L198–199; `ai_ops.py` L18–44; CLAUDE Addendum; worker 테스트 존재.
* **권장 수정 방향:**  
  - **옵션 A (기능 완성):** AI 액션에서 `_ensure_preview_ready`/password 세션을 재사용하고 UI 차단 제거 → Worker unlock 경로와 정렬.  
  - **옵션 B (의도적 비활성):** Worker unlock·관련 문서/테스트를 “내부/비UI”로 명확히 하고 CLAUDE 서술을 “UI 미지원”으로 수정.
* **우선순위:** **High** (제품 계약·보안 기대치 모두 영향)

---

### 3.3 AI 취소가 네트워크 블로킹 구간을 끊지 못함

* **위치:**  
  - `src/core/ai/generation.py` — `_upload_pdf_file`, `_generate_content`, `_stream_generate_content`  
  - `src/core/ai/errors.py` — `retry_with_backoff` / `_interruptible_sleep`  
  - `src/core/ai/session.py` — `_get_or_create_chat`
* **문제:** 취소는 cooperative이다.  
  - stream: 청크 사이 `_run_cancel_check` **있음**.  
  - retry sleep: 0.2s 슬라이스 + cancel_check **있음** (2026-07-22 개선).  
  - `files_api.upload(file=...)` 호출 중: 체크 없음.  
  - non-stream `generate_content(...)`: 단일 블로킹.  
  - `_get_or_create_chat`의 `_upload_pdf_file(pdf_path)`: **`cancel_check` 인자 자체를 전달하지 않음**.
* **영향:** 사용자가 오버레이에서 취소해도 업로드/생성 완료까지 UI busy·토큰/네트워크 비용이 남을 수 있다. finished 오발화는 `_reraise_if_cancelled`로 막는 구조이나 **응답성** 문제는 잔존.
* **근거:** `generation.py` L117–118, L164–168; `session.py` L56; `errors.py` L46–107.
* **권장 수정 방향:**  
  - chat 생성 경로에 `cancel_check` 전파.  
  - 취소 중 UI 상태 “요청 중단 대기 중…”.  
  - SDK 수준 abort/timeout (로드맵).
* **우선순위:** **Medium**

---

### 3.4 암호 PDF AI 임시 평문 파일 (Worker 경로)

* **위치:** `src/core/worker_ops/ai_ops.py` — `_prepare_ai_pdf_path`, `_cleanup_ai_temp_path`; `src/core/temp_cleanup.py`
* **문제:** 암호화 PDF는 인증 후 `tempfile.mkstemp(prefix="pdf_master_ai_")`에 **비암호화 PDF**를 기록한다. `finally` 삭제 + age 기반 orphan 스윕이 있으나, 프로세스 kill·디스크 오류·동시성 edge에서는 평문 잔존 가능.
* **영향:** 민감 문서 로컬 temp 노출. (Gemini 업로드는 별도 클라우드 리스크.) UI가 암호 PDF를 막는 현재 상태에서는 사용자 노출 빈도는 낮지만, Worker/테스트·향후 UI 연결 시 재부각.
* **근거:** `ai_ops.py` L36–44, L63–78; `temp_cleanup.py` L13–60.
* **권장 수정 방향:** 제한 ACL/NamedTemporaryFile 수명 강화, 가능하면 메모리 경로; UI 연결 시 사용자 고지.
* **우선순위:** **Medium** (UI 연결 시 상향)

---

### 3.5 병합 시 전 파일 스킵이면 빈 PDF를 성공 저장

* **위치:** `src/core/worker_ops/compose_ops.py` — `merge`
* **문제:** 개별 파일 open/암호/손상 시 `skipped_count`만 올리고 계속 진행한다. 유효 페이지를 하나도 넣지 못해도 `_atomic_pdf_save` 후 `finished_signal`(성공)을 낸다. 메시지는 “merged 0 + skipped N” 형태가 될 수 있으나 **실패 시그널이 아니다**.
* **영향:** 암호-only 목록·전부 손상 입력 시 빈/무의미 PDF가 “완료”로 저장됨. 사용자가 성공으로 오인.
* **근거:**

```python
# compose_ops.merge
doc = self._open_pdf_document(path)
if doc.is_encrypted:
    skipped_count += 1
    ...
    continue
...
self._atomic_pdf_save(doc_merged, output_path)
result_msg = self._get_msg("msg_merge_done", len(valid_files) - skipped_count)
```

  (현 PyMuPDF에서 authenticate 성공 시 `is_encrypted`가 False가 되는 것을 로컬에서 확인 — 암호 미해결 파일은 exception 경로로 skip.)
* **권장 수정 방향:** 병합 페이지 수 0이면 `error_signal`로 종료하고 출력 미생성(또는 생성 파일 롤백).
* **우선순위:** **Medium**

---

### 3.6 강제 종료 시 `QThread.terminate()` 잔여 위험 (완화됨)

* **위치:** `src/ui/main_window.py` — `_shutdown_worker_for_close`
* **문제:** cancel 3초 초과 시 사용자 확인 후 `worker.terminate()` 호출. 원자 저장·AI temp 삭제는 스레드 협력 없이는 보장 불가. 이후 `cleanup_pdf_master_temp_files(include_in_progress=True)`로 **완화**.
* **영향:** 드묾. 미완성 출력·파일 잠금 가능. 사용자 명시 선택 경로.
* **근거:** `main_window.py` L38–69.
* **권장 수정 방향:** cooperative 대기 옵션 연장; terminate 전 출력 경로 목록 로깅.
* **우선순위:** **Low–Medium**

---

### 3.7 배치 암호화 UI가 단일 탭 권한 모델을 노출하지 않음

* **위치:** Worker `batch_ops.py` (permissions/owner/user kwargs 지원) vs UI `tabs_basic/batch.py` (비밀번호 문자열만)
* **문제:** 배치 결과는 기본 print/copy/accessibility 권한 + owner/user 동일 비밀번호. 단일 Security 탭과 기대 불일치 가능. 2026-07-22에 툴팁/안내 문구는 반영됨.
* **영향:** 보안 정책 엄격 사용자의 결과물 기대 불일치. 기능 버그보다 **제품 갭**.
* **근거:** batch UI kwargs vs `batch_ops` encrypt 분기; i18n `tip_batch_encrypt_permissions`.
* **권장 수정 방향:** 배치 권한 UI 추가 또는 README에 한계를 더 명시.
* **우선순위:** **Low**

---

## 4. Potential Functional Gaps

### 4.1 확인된 gap (추정 아님)

| 항목 | 설명 |
|------|------|
| OCR | 의도적 미구현. 스캔본 텍스트/검색/AI fallback 품질 한계 |
| AI 즉시 abort | §3.3 |
| 암호 PDF AI UI | §3.2 — Worker 있음 / UI 없음 |
| redact 좌표 UX | 수동 텍스트 좌표; 미리보기 드래그 영역 선택 없음 |
| compare 리포트 UI | 요약 다이얼로그 + 선택적 visual PDF. 페이지별 인터랙티브 리포트 없음 |
| visual 샘플링 | 픽셀 step 샘플링 → 국소 차이 누락 가능 |
| `auto_bookmarks` | 폰트 크기 휴리스틱; 다단/한글 제목 오탐·미탐 가능 |
| 배치 작업 종류 | compress/watermark/encrypt/rotate만 (preflight 고정) |
| 종료 시 pending 큐 | close 시 `_pending_workers` 폐기 (의도적) |
| Windows 기본 폰트 | `Segoe UI` — 비 Windows 폴백 의존 |
| 문서 SSOT | FUNCTIONAL audit 삭제 후 테스트·CLAUDE 미갱신 (§3.1) |

### 4.2 추정 gap

| 항목 | 설명 |
|------|------|
| **추정** — settings last-write-wins | 채팅 즉시 저장과 debounce settings save가 같은 dict를 공유; 단일 UI 스레드에서는 완화, 외부 파일 동시 편집 시 덮어쓰기 가능 |
| **추정** — sanitize 완전성 | JS/OpenAction 등 best-effort. 포렌식급 위생 아님 |
| **추정** — passwords/api_key kwargs 수명 | Worker kwargs에 평문 보관. 기본 로그는 mode 중심이나 디버그 확장 시 유출 여지 |
| **추정** — Linux/macOS 인쇄·keyring | 소스 실행 가능하나 패키징/테스트 커버리지 얇을 수 있음 |
| **추정** — 대용량 AI 업로드 | File API + 30k 텍스트 제한 meta는 있으나 장시간 업로드+취소 UX는 §3.3과 결합 |
| **추정** — merge skip 사유 미구분 | 암호/손상/기타를 사용자에게 파일 단위로 보여주지 않음 |

### 4.3 의도적 제품 한계

- AI 요약 최대 30,000자, 렌더 8,000px, 파일 2GB  
- Gemini 전용 AI  
- 페이지 대상 작업의 엄격 페이지 리졸버 (`-1` last-page는 서명 계열 예약)

### 4.4 강점 (감사 중 확인)

- OperationSpec 중심 preflight·dispatch·undo·same-path 계약  
- atomic save + created_output_paths 취소 정리  
- 첨부 경로 탈출 차단 테스트  
- AI meta(source/truncated) UI  
- SOLID 분할 후 public facade·구조 예산 테스트  
- i18n 카탈로그 + 하드코딩 스모크  
- 2026-07-22 후속 회귀 테스트 존재

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 (품질 게이트·계약 정합)

1. **문서/테스트 게이트 복구 (§3.1)**  
   - `FUNCTIONAL_IMPLEMENTATION_AUDIT_*.md` 복원 **또는** `test_validation_docs_config.py`를 `PROJECT_AUDIT.md` 기준으로 이전.  
   - `PROJECT_ANALYSIS_AND_FEATURE_ROADMAP.md` 복원 또는 maintained 목록 제거.  
   - README/CLAUDE/GEMINI pytest 기준선 실측 반영.  
   - 목표: `python -m pytest -q` 실패 0.
2. **암호 PDF AI 계약 결정 (§3.2)**  
   - UI 연결(옵션 A) 또는 문서·Worker 경로 정리(옵션 B) 중 하나를 명시적으로 택함.
3. **merge 0페이지 성공 저장 차단 (§3.5)**  
   - 유효 페이지 없으면 error + 출력 미생성.

### 2단계 — 안정성

1. chat `_get_or_create_chat`에 `cancel_check` 전파 (§3.3).  
2. AI 취소 중 UI “중단 대기” 상태.  
3. AI 평문 temp 수명/ACL 강화 + UI 연결 시 고지 (§3.4).  
4. 강제 종료 경로 로깅·대기 옵션 다듬기 (§3.6).  
5. 배치 encrypt 권한 UI 또는 문서 강화 (§3.7).

### 3단계 — 구조·제품

1. OCR optional extra 설계  
2. compare 인터랙티브 리포트  
3. 미리보기 드래그 `redact_area`  
4. SDK-level AI abort  
5. 비 Windows 런타임 스모크 (폰트·인쇄·keyring)  
6. cleanup dry-run 카운트(예상 제거 페이지 수)

---

## 6. Test Recommendations

### 6.1 즉시 필요한 테스트/수정

| 항목 | 목적 |
|------|------|
| `test_validation_docs_config` 수리 | 삭제 파일·SSOT 정책과 테스트 정합 |
| UI 암호 PDF AI 회귀 | `action_ai_summarize` 등이 preview 암호 후 진행 **또는** 차단이 문서와 일치함을 고정 |
| `test_merge_all_skipped_emits_error` | 전 파일 skip 시 finished 금지·출력 없음 |
| `test_chat_upload_respects_cancel_check` | `_get_or_create_chat` → upload에 cancel 전파 후 검증 |

### 6.2 보강 권장

| 테스트 | 검증 목표 |
|--------|-----------|
| `test_ai_retry_interruptible_sleep` | retry 중 cancel 시 finished 미발생 (이미 일부 존재 시 확장) |
| `test_ai_temp_cleanup_on_cancel` | 암호 PDF AI 취소 후 `pdf_master_ai_*` 미잔존 |
| `test_batch_encrypt_default_permissions` | UI 미지정 시 기본 권한 마스크 |
| `test_force_close_temp_sweep` | terminate 후 orphan 스윕 |
| `test_docs_pytest_baseline_matches_ci` | README 수치와 실제 collect/pass 정책 동기화 (하드코딩 수치 지양 권장) |

### 6.3 기존 회귀 (유지 필수)

| 영역 | 대표 테스트 |
|------|-------------|
| AI cancel / 암호 Worker | `tests/test_ai_ops_cancel_and_encrypted.py` |
| blank / visual_error / queue | `tests/test_audit_followup_stability.py` |
| 2026-07-22 후속 | `tests/test_audit_2026_07_22_followup.py` |
| preflight / batch fail-fast | `tests/test_worker_preflight.py`, `test_worker_batch_*` |
| 첨부 경로 탈출 | `tests/test_worker_attachment_extract_security.py` |
| 취소·롤백 | `tests/test_worker_cancel_cleanup.py`, `test_worker_cancel_regression.py` |
| same-path preview | `tests/test_same_path_preview_restore.py` |
| 구조/facade | `tests/test_worker_structure_budget.py` |

### 6.4 검증 명령

```bash
pip install -e .[dev]
python -m pyright
python -m pytest -q
python main.py --smoke
# 선택: PDF_MASTER_GEMINI_FILE_API_SMOKE=1 + GEMINI_API_KEY
```

**실측 기준선 (2026-07-27):**  
`python -m pytest -q` → **230 collected / 228 passed / 1 opt-in Gemini smoke skipped / 2 failed**  
(`test_validation_docs_config` 2건 — §3.1)

문서에 적힌 “229 passed”는 **현재 워크트리에서 더 이상 유효하지 않음**.

---

## 7. Appendix

### 7.1 분석 방법

1. `README.md`, `CLAUDE.md` 정독 — 목적·아키텍처·Current Behavior·Addendum  
2. CodeGraph `codegraph_explore` — entry/`run_worker`/preflight/AI/security/cancel/lifecycle 호출 관계·blast radius  
3. 보조: 핵심 파일 구간 열람, `_check_cancelled`/암호/경로 패턴 grep  
4. `python -m pytest -q` 및 docs 실패 테스트 상세 실행  
5. PyMuPDF `is_encrypted` authenticate 전후 동작 로컬 확인 (merge 분기 해석용)

### 7.2 이전 감사 대비

| 시점 | 요약 |
|------|------|
| 2026-07-15 | High 다수 (AI cancel, 암호 AI Worker, visual silent 등) |
| 2026-07-22 | 후속 구현 후 잔여 Medium 중심, 문서상 Low |
| **2026-07-27** | 후속 구현은 대체로 유지. **문서/테스트 게이트 붕괴**와 **암호 AI UI 계약**이 신규 High. 전체 **Medium** |

### 7.3 비고

- 본 감사는 **구현 수정 없이** 리포트만 작성했다.  
- 과장 없이 코드·테스트 근거가 있는 문제와 추정을 분리했다.  
- `PROJECT_AUDIT.md`를 현행 기능 감사 SSOT로 쓸 경우, `tests/test_validation_docs_config.py`와 `CLAUDE.md`의 FUNCTIONAL audit 참조를 함께 정리하는 것이 1단계 필수다.

---

*이 문서는 PDF Master v4.5.6 코드 기준 기능 구현 감사입니다. (2026-07-27)*
