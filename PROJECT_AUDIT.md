# Project Audit

> 감사 기준일: **2026-07-22**  
> 대상 버전: **PDF Master v4.5.6**  
> 범위: 기능 구현 관점 (버그·검증·상태/비동기·보안·문서 정합·테스트 공백)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP (`codegraph_explore`), 보조 파일 열람·grep, pytest 수집  
>
> **후속 구현 (2026-07-22):** 1·2단계 + 구현 가능한 3단계 일부를 코드에 반영.  
> OCR·드래그 교정 UX·compare 인터랙티브 리포트·SDK-level AI abort는 제품 로드맵으로 유지.

---

## 1. Executive Summary

PDF Master v4.5.6은 **PyQt6 UI + `WorkerThread` + `worker_runtime`(preflight/dispatch/atomic I/O) + 도메인별 `worker_ops`** 로 기능 경계가 잘 나뉜 데스크톱 PDF 편집기입니다. v4.5.5~4.5.6 안정화와 **2026-07-15 감사 후속 구현**, **2026-07-21 SOLID 코드 분할**, **2026-07-22 감사 후속 구현** 이후 이전에 지적된 High급 결함과 잔여 Medium 이슈 다수가 **코드상 해결된 상태**입니다.

### 전체 위험도

| 구분 | 평가 |
|------|------|
| **전체 위험도** | **Low** (2026-07-22 후속 반영 후) |
| Critical | **없음** (코드 근거 기준) |
| High (잔여) | **없음** |
| 문서 정합 | README / CLAUDE / 구현 대체로 **일치** |
| 테스트 기준선 | **230 collected / 229 passed / 1 opt-in Gemini smoke skipped** (`tests/test_audit_2026_07_22_followup.py` 추가) |

### 2026-07-22 후속 구현 상태

| 우선순위 | 이슈 | 상태 |
|----------|------|------|
| Medium | 썸네일 sender 가드 | **해결** — `_is_active_loader_sender` |
| Medium | AI temp orphan | **해결** — `src/core/temp_cleanup.py` + 기동/종료/취소 스윕 |
| Medium | cleanup 확인 다이얼로그 | **해결** — blank/dedupe/sanitize |
| Medium | AI cancel 응답성 | **개선** — retry sleep 분할 + Cancelled 비재시도 (SDK abort는 로드맵) |
| Low–Medium | 강제 종료 temp | **해결** — terminate 후 `include_in_progress` 스윕 |
| Low | 취소 mtime 휴리스틱 | **해결** — `created_output_paths`만 삭제 |
| Low | list_annotations 계약 | **해결** — `output_kind=text` |
| Low | 배치 encrypt UX | **해결** — 툴팁·안내 문구 |
| 3단계 | chat session single-flight | **해결** — per-key create lock |

### 핵심 잔여 리스크 (요약)

1. **AI 취소는 cooperative** — stream 청크·핸들러 경계에서는 막히지만, `upload` / non-stream `generate_content` / `retry sleep` 중에는 즉시 중단 불가.
2. **암호 PDF AI 경로의 임시 평문 파일** — 미리보기 암호로 복호 후 `tempfile`에 비암호화 PDF를 기록. 정상 종료 시 삭제하나 강제 종료·크래시 시 잔존 가능.
3. **썸네일 `_on_thumbnail_ready`에 sender 가드 부재** — complete 핸들러와 비대칭. 빠른 PDF 전환 시 잔여 시그널 혼선 가능성.
4. **파괴적 cleanup UI 확인 불균형** — redact는 확인, blank/dedupe/sanitize 등은 저장 대화만으로 진행.
5. **제품 갭(의도적)** — OCR 미구현, redact 드래그 UX 없음, compare 리포트 UI 확장 여지, 배치 암호 권한 UI 미노출.

2026-07-15 감사의 High 항목은 본 감사에서 **재현되지 않음**(해결 확인). 아래 §3은 **현재 잔여** 이슈 중심입니다.

---

## 2. Project Understanding

### 2.1 목적 (README / CLAUDE)

- 올인원 PDF 편집 데스크톱 앱: 병합·변환·페이지 편집·보안·주석·추출·배치·AI(Gemini)
- 스택: Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai` / `keyring`, PyInstaller
- 배포: Windows EXE (`dist/PDF_Master_v4.5.6.exe`), 소스는 크로스 실행 가능하나 폰트·인쇄·패키징은 Windows 중심

### 2.2 아키텍처 (CodeGraph + 문서)

```
main.py
  ├─ setup_logging / global_exception_handler (i18n)
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_undo / window_worker
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()          # 66+ UI callers (CodeGraph)
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
| UI 게이트 | `run_worker` | `src/ui/main_window_worker.py` | 탭 액션 다수 caller |
| 스레드 | `WorkerThread.run` | `src/core/worker.py` | Runtime mixin 위임 |
| 선검증 | `preflight_inputs` | `src/core/worker_runtime/preflight.py` | batch 화이트리스트, search_term, required_* |
| 디스패치 | `OPERATION_SPECS` | `src/core/worker_runtime/dispatch.py` | 50+ mode 계약 |
| PDF open | `_open_pdf_document` | `src/core/worker_runtime/mixin.py` | `passwords` 맵 + authenticate |
| AI | `ai_summarize` 등 | `src/core/worker_ops/ai_ops.py` | `cancel_check` + 임시 복호 |
| 취소 정리 | `_cleanup_cancelled_worker` | `src/ui/window_worker/lifecycle.py` | `created_output_paths` rollback |
| 종료 | `_shutdown_worker_for_close` | `src/ui/main_window.py` | cancel → 3s wait → 강제 종료 확인 |

### 2.4 안정화 메커니즘 (문서 ↔ 코드 일치)

- Same-path 저장 전 preview 해제 + 완료 후 복원 (`window_worker/same_path.py`)
- Undo: `before_backup_path` / `after_backup_path` 스냅샷
- 취소 롤백: `created_output_paths` + `OperationSpec.cancel_cleanup`
- Atomic I/O: `_atomic_pdf_save` / text / binary (`worker_runtime/io.py`)
- 첨부 추출: 파일명 정규화 + `output_dir` 하위 강제
- AI 캐시: upload/text/chat session은 **클래스 변수 + lock**
- 설정: JSON atomic write (`os.replace`), API 키 keyring 우선 + 동의 기반 파일 폴백
- SOLID 분할: `worker_ops/{annotation,extract,cleanup,page,transform,compare}/` + thin facade

### 2.5 README / CLAUDE.md vs 구현 정합성

| 문서 주장 | 실제 | 판정 |
|-----------|------|------|
| v4.5.6 deep compress / cleanup / visual compare / redact_area | 도메인 패키지 + UI 빌더 존재 | **일치** |
| SOLID 도메인 패키지 (2026-07-21) | facade + 구현 패키지 구조 | **일치** |
| 미리보기 `zoomable_preview` / Qt 인쇄 | preview 위젯 + 인쇄 경로 | **일치** |
| Worker preflight + shared `pdf_validation` | `preflight.py` → `validate_pdf_file` | **일치** |
| 배치 미지원 op fail-fast | preflight + `batch_ops` 화이트리스트 | **일치** |
| `_pending_workers` FIFO / busy 단축키 비활성 | lifecycle + `set_ui_busy` | **일치** |
| AI cancel / 암호 PDF unlock (2026-07-15 후속) | `ai_ops` cancel_check + temp unlock | **일치** |
| blank-page 보수 판정 | `_is_blank_page` 예외 시 `False` | **일치** |
| visual_error | compare `status: visual_error` + i18n | **일치** |
| OCR 미구현 | 코드/로드맵에 의도적 후속 | **일치** |
| pytest 230 / 229 / 1 skip | 2026-07-22 후속 테스트 반영 | **일치** |

### 2.6 2026-07-15 High 이슈 해결 확인

| 과거 이슈 | 현재 코드 근거 | 상태 |
|-----------|----------------|------|
| AI 취소 무시 / finished 경로 | `cancel_check` + `_reraise_if_cancelled` + stream 루프 체크 | **해결** |
| 암호 PDF AI hard reject | `_prepare_ai_pdf_path` + `_open_pdf_document` 임시 복호 | **해결** |
| blank 렌더 실패 → 삭제 | `except: return False` (유지) | **해결** |
| visual silent identical | `visual_error` status | **해결** |
| redact_area 확인 없음 | `QMessageBox.warning` Yes/No | **해결** |
| pending 큐 무한 | `_MAX_PENDING_WORKERS = 8` | **해결** |
| Unknown task 하드코딩 | `_get_msg("err_unknown_task", ...)` | **해결** |
| batch encrypt 권한 | `_resolve_permissions` + owner/user kwargs | **Worker 해결** (UI는 옵션 미노출) |

---

## 3. High-Risk Issues

> 감사 시점 발견 기록. **2026-07-22 후속으로 상당수 해결** — Executive Summary 표 참고.  
> 아래 중 **잔여**는 SDK-level AI abort 등 로드맵 항목. 추정은 §4로 분리.

---

### 3.1 AI 취소가 네트워크 블로킹 구간을 끊지 못함 (**부분 해결**)

* **위치:**  
  - `src/core/ai/generation.py` — `_upload_pdf_file`, `_generate_content`, `_stream_generate_content`  
  - `src/core/ai/errors.py` — `retry_with_backoff`  
  - `src/core/worker_ops/ai_ops.py` — `cancel_check=self._check_cancelled`
* **문제:**  
  취소는 **cooperative**이다. stream은 청크 사이에서 `_run_cancel_check`를 호출하지만,  
  1) `files_api.upload(file=...)`,  
  2) non-stream `generate_content(...)`,  
  3) `retry_with_backoff`의 `time.sleep(delay)`  
  구간에는 취소 플래그를 읽지 않는다. SDK 요청 abort도 없다.
* **영향:** 사용자가 오버레이에서 취소해도 진행 중인 HTTP/업로드가 끝날 때까지 대기·토큰 비용이 발생할 수 있다. finished 오발화 자체는 re-raise로 막는 구조이나 **응답성·비용** 이슈가 남는다.
* **근거:**  
  - `generation.py` 117–118: cancel 체크 → 즉시 `upload` (업로드 중 체크 없음)  
  - `generation.py` 164–168: `generate_content` 호출이 단일 블로킹  
  - `errors.py` 55–57: 재시도 시 `time.sleep`만 수행, cancel_check 인자 없음  
  - stream 루프(137–142)는 청크 사이 체크 **있음**
* **권장 수정 방향:**  
  - retry sleep을 짧은 구간으로 쪼개 cancel_check → **2026-07-22 반영**  
  - upload/generate를 별도 future + timeout/cancel 토큰 검토 (SDK 지원 범위 내) → **잔여 로드맵**  
  - 취소 시 UI에 “요청 중단 대기 중…” 상태 표시 → **잔여**
* **우선순위:** **Medium** (잔여: SDK abort) → 현재 실사용 영향 **Low–Medium**

---

### 3.2 암호 PDF AI 처리 시 디스크에 평문 임시 파일 (**개선**)

* **위치:** `src/core/worker_ops/ai_ops.py` — `_prepare_ai_pdf_path`, `_cleanup_ai_temp_path`
* **문제:** 암호화 PDF는 인증 후 `tempfile.mkstemp(prefix="pdf_master_ai_")`에 **비암호화 PDF**를 저장한 뒤 File API/텍스트 추출에 사용한다. `finally`에서 삭제하지만, 프로세스 `terminate`/크래시/권한 오류 시 평문 잔존 가능.
* **영향:** 민감 문서 사용 시 로컬 temp 노출. (Gemini File API 업로드 자체도 클라우드 전송 — 제품 특성이지만 로컬 평문은 별도 리스크)
* **근거:**

```python
# ai_ops.py
fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="pdf_master_ai_")
...
doc.save(temp_path, encryption=encrypt_none, ...)
# finally: _cleanup_ai_temp_path(temp_path)
```

* **권장 수정 방향:**  
  - 가능하면 메모리 버퍼/NamedTemporaryFile(delete_on_close) + 제한 ACL → **잔여**  
  - 앱 기동·종료 시 `pdf_master_ai_*` orphan 정리 → **2026-07-22 `temp_cleanup` 반영**  
  - 강제 종료 시 정리 시도 로그 → **2026-07-22 반영**
* **우선순위:** **Medium** → orphan 스윕 후 **Low–Medium**

---

### 3.3 썸네일 ready 슬롯에 sender 가드 부재 (**해결**)

* **위치:** `src/ui/thumbnail/grid.py` — `_on_thumbnail_ready` vs `_on_loading_complete`
* **문제:** `_on_loading_complete`는 `sender is not self._loader_thread`이면 무시한다. `_on_thumbnail_ready`는 인덱스 범위만 검사하고 **sender/loader 검증이 없다**. cleanup 시 disconnect를 시도하지만, disconnect 실패·큐잉된 시그널·대기 스레드가 남아 있으면 다른 PDF 로드 직후 잘못된 썸네일이 그려질 수 있다.
* **영향:** 대용량 PDF 간 빠른 전환 시 썸네일 깜빡임·오배치 (기능 오류 UX). 데이터 손실은 아님.
* **근거:**

```python
# _on_thumbnail_ready: sender 검사 없음
if index < len(self._thumbnails):
    self._thumbnails[index].set_pixmap(pixmap)
...
# _on_loading_complete: sender 검사 있음
if self._loader_thread and sender is not None and sender is not self._loader_thread:
    return
```

* **권장 수정 방향:** `_on_thumbnail_ready`에도 동일 sender 가드 → **2026-07-22 `_is_active_loader_sender` 반영**
* **우선순위:** **Medium** → **해결**

---

### 3.4 파괴적 cleanup 작업의 UI 확인 불균형 (**해결**)

* **위치:**  
  - 확인 있음: `src/ui/tabs_advanced/actions_markup.py` — `action_redact_area` / `action_redact_text`  
  - 확인 없음: `src/ui/tabs_advanced/actions_edit.py` — `action_remove_blank_pages`, `action_dedupe_pages`, `action_sanitize_pdf`
* **문제:** redact는 영구 삭제 경고 후 진행한다. blank 제거·중복 제거·sanitize는 파일 선택 후 저장 경로만 고르면 바로 Worker가 돈다. blank/dedupe는 휴리스틱 기반이라 오판 시 페이지 유실 체감이 크다 (출력은 별도 파일이라도 사용자 기대와 다를 수 있음).
* **영향:** 의도치 않은 대량 페이지 제거·메타/첨부 스크럽. Undo는 same-path 변형에 한해 스냅샷 가능.
* **근거:** `action_redact_*`의 `QMessageBox.warning` vs cleanup 액션의 즉시 `run_worker`
* **권장 수정 방향:** 제거 예상 페이지 수 미리보기 또는 확인 다이얼로그 → **2026-07-22 확인 다이얼로그 반영**; dry-run 카운트는 잔여
* **우선순위:** **Medium** → **해결** (dry-run은 로드맵)

---

### 3.5 강제 종료 시 Worker `terminate()` 잔여 위험 (**개선**)

* **위치:** `src/ui/main_window.py` — `_shutdown_worker_for_close`
* **문제:** cancel 후 3초 내 미종료 시 사용자 확인 뒤 `worker.terminate()`를 호출한다. QThread terminate는 자원 정리·atomic save·AI temp 삭제를 보장하지 않는다.
* **영향:** 미완성 출력, orphan temp(`pdf_master_ai_*`, `.pdf_master_*.tmp*`), 드물게 파일 잠금. 사용자가 명시 선택하는 경로라 Critical은 아님.
* **근거:** `worker.terminate(); worker.wait(1000)` 분기
* **권장 수정 방향:** terminate 전/후 temp glob 정리 → **2026-07-22 반영**; cooperative cancel 대기 옵션화는 잔여
* **우선순위:** **Low–Medium** → **Low**

---

### 3.6 취소 롤백의 mtime 휴리스틱 폴백 (**해결**)

* **위치:** `src/ui/window_worker/lifecycle.py` — `_cleanup_cancelled_worker`
* **문제:** 단일 파일 출력 취소 시 `created_output_paths`에 없으면 **mtime < 5초**인 파일을 삭제 후보로 본다. atomic 경로가 정상 추적되면 안전하지만, 추적 누락 + 기존 파일 덮어쓰기 경계에서는 오판 여지가 이론상 존재한다 (pre-existed 가드가 있어 완화됨).
* **영향:** 추적 누락 시 잘못된 삭제 또는 미삭제. 실사용 빈도는 낮음.
* **근거:**

```python
if not should_remove:
    try:
        should_remove = time.time() - os.path.getmtime(output_path_abs) < 5
    except Exception:
        should_remove = False
```

* **권장 수정 방향:** 휴리스틱 제거 → **2026-07-22 반영** (`created_output_paths`만 삭제)
* **우선순위:** **Low** → **해결**

---

### 3.7 `list_annotations` 계약 이중성 (memory vs output_path 필수) (**해결**)

* **위치:** `src/core/worker_runtime/dispatch.py` — `list_annotations` OperationSpec  
  UI: `action_list_annotations`는 항상 `output_path` 전달
* **문제:** `output_kind="memory"`이면서 `required_any_kwargs=(("output_path",),)`이다. UI 경로는 파일 저장을 강제하므로 동작은 하지만, 스펙만 보면 “메모리 결과인데 파일 필수”로 혼동된다. 향후 UI 없는 호출/테스트에서 preflight 실패 가능.
* **영향:** API/테스트 계약 혼란. 런타임 사용자 경로는 현재 정상.
* **근거:** dispatch 스펙 + `actions_markup.action_list_annotations`의 save dialog
* **권장 수정 방향:** `output_kind="text"`로 정리 → **2026-07-22 반영**
* **우선순위:** **Low** → **해결**

---

### 3.8 배치 암호화 UI가 단일 protect 권한 모델을 노출하지 않음 (**문서화**)

* **위치:**  
  - Worker: `batch_ops.py` encrypt 분기 — `permissions` / `owner_password` / `user_password` 지원  
  - UI: `tabs_basic/batch.py` `action_batch` — `option`(비밀번호 문자열)만 전달
* **문제:** Worker는 protect와 정렬됐으나 UI는 권한 체크박스·owner/user 분리를 제공하지 않는다. 배치 결과는 기본 print/copy/accessibility 권한 + 동일 owner/user 비밀번호.
* **영향:** 보안 정책이 엄격한 사용자는 단일 탭과 다른 결과물 기대 불일치. 기능 버그라기보다 **제품 갭**.
* **근거:** `action_batch` kwargs vs `batch_ops` encrypt kwargs
* **권장 수정 방향:** README/툴팁에 “기본 권한만 적용” 명시 → **2026-07-22 반영**; 배치 권한 UI는 로드맵
* **우선순위:** **Low** (UI 갭은 의도적 유지 가능)

---

## 4. Potential Functional Gaps

### 4.1 확인된 gap (추정 아님)

| 항목 | 설명 |
|------|------|
| OCR | 의도적 미구현. 스캔본 텍스트 추출/검색/AI fallback 품질 한계 (로드맵) |
| AI 즉시 abort | §3.1 — cooperative only |
| 암호 PDF AI 평문 temp | §3.2 |
| redact 좌표 UX | 수동 텍스트 좌표 입력만; 미리보기 드래그 영역 선택 없음 |
| compare 리포트 UI | 완료 요약 다이얼로그 + 선택적 visual PDF. 페이지별 인터랙티브 리포트 없음 |
| visual 샘플링 | `_pixel_diff_ratio` 바이트 step 샘플링 → 국소 차이 누락 가능 (한계) |
| `auto_bookmarks` | 폰트 크기 휴리스틱; 다단/한글 제목 오탐·미탐 가능 |
| 배치 작업 종류 | compress/watermark/encrypt/rotate만 (preflight 고정) |
| 종료 시 pending 큐 | close 시 `_pending_workers = []`로 폐기 (의도적) |
| Windows 기본 폰트 | `main.py` `Segoe UI` — 비 Windows 환경에서 폴백 의존 |

### 4.2 추정 gap

| 항목 | 설명 |
|------|------|
| **추정** — AI chat 세션 이중 생성 | `_get_or_create_chat`이 lock 밖에서 upload/create. UI는 단일 Worker라 실사용 레이스는 낮음. 클래스 캐시 공유 시 이론적 중복 업로드 가능 |
| **추정** — settings last-write-wins | `_save_chat_histories` 즉시 저장과 `_schedule_settings_save` debounce가 같은 `self.settings` dict를 쓰므로, 외부에서 파일을 동시에 쓰면 덮어쓰기 가능 (단일 UI 스레드에서는 완화) |
| **추정** — sanitize 완전성 | JS/OpenAction/이름 트리 제거는 best-effort. 포렌식급 위생 아님 |
| **추정** — passwords kwargs 로깅 | debug 로그에 kwargs 덤프 시 비밀번호 노출 가능 (현재 확인된 기본 로그 포맷은 mode 중심) |
| **추정** — Linux/macOS 인쇄·keyring | 소스 실행 가능하나 테스트·패키징 커버리지 얇을 수 있음 |
| **추정** — 대용량 AI PDF | File API 업로드 + 30k 텍스트 제한 메타 표시는 있으나, 초대형 업로드 시간/취소 UX는 §3.1과 결합 |

### 4.3 의도적으로 유지되는 제품 한계

- AI 요약 최대 30,000자, 렌더 8,000px, 파일 2GB
- 암호화 PDF는 작업별 암호 세션 재사용 (미리보기 인증 경로)
- Gemini 전용 AI (다른 LLM 미지원)

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (기능 신뢰성·보안 체감)

1. **썸네일 sender 가드** — `_on_thumbnail_ready`에 `_on_loading_complete`와 동일 검사  
2. **AI temp orphan 정리** — 기동/종료 시 `pdf_master_ai_*` 스윕; 가능하면 더 안전한 temp 수명  
3. **cleanup 확인 다이얼로그** — blank/dedupe/sanitize에 redact급 경고 (또는 dry-run 카운트)

### 2단계 — 안정성 개선

1. **AI cancel 응답성** — retry sleep 분할 + cancel_check; 업로드 전후 체크 강화  
2. **강제 종료 후 잔여 파일 정리** — terminate 경로 temp/atomic 잔재 스캔  
3. **취소 롤백 mtime 휴리스틱 축소** — `created_output_paths` 누락 모드 전수 점검  
4. **`list_annotations` OperationSpec 정리** — output_kind/required 계약 일치  
5. **배치 encrypt UI 문서화 또는 권한 UI 추가**

### 3단계 — 구조·제품 개선

1. OCR optional extra 설계 (패키징·라이선스 포함)  
2. compare 인터랙티브 리포트 UI (`visual_error_count` 활용)  
3. 미리보기 드래그 기반 `redact_area`  
4. AI 요청 abort 토큰/SDK 수준 취소  
5. (선택) chat session 생성 전 구간을 lock + double-check  
6. 비 Windows 런타임 스모크 (폰트·인쇄·keyring)

---

## 6. Test Recommendations

### 6.1 신규·보강 권장 테스트

| 테스트 | 검증 목표 |
|--------|-----------|
| `test_thumbnail_ready_sender_guard` | 이전 loader 시그널이 새 PDF 그리드에 pixmap을 쓰지 않음 |
| `test_ai_temp_cleanup_on_cancel` | 암호 PDF AI 취소/실패 후 `pdf_master_ai_*` 미잔존 |
| `test_ai_retry_respects_cancel` | retry sleep 중/후 cancel 시 finished 미발생 (구현 후) |
| `test_cleanup_confirm_ui_hooks` | blank/dedupe/sanitize 액션이 확인 다이얼로그를 거침 (구현 후) |
| `test_list_annotations_spec_contract` | preflight: output_path 있을 때만 통과 vs memory-only 의도 문서화 |
| `test_batch_encrypt_default_permissions` | UI 경로(권한 미지정) 기본 마스크가 print/copy/accessibility |
| `test_force_close_temp_sweep` | terminate 시나리오 후 temp orphan 정리 (구현 후) |
| `test_chat_session_single_flight` | 동시 `_get_or_create_chat` 시 업로드 1회 (추정 이슈 회귀) |

### 6.2 기존 회귀 (유지 필수)

| 영역 | 대표 테스트 |
|------|-------------|
| AI cancel / 암호 | `tests/test_ai_ops_cancel_and_encrypted.py` |
| blank / visual_error / queue | `tests/test_audit_followup_stability.py` |
| preflight / batch fail-fast | `tests/test_worker_preflight.py`, `test_worker_batch_*` |
| 첨부 경로 탈출 | `tests/test_worker_attachment_extract_security.py` |
| 취소·롤백 | `tests/test_worker_cancel_cleanup.py`, `test_worker_cancel_regression.py` |
| same-path preview | `tests/test_same_path_preview_restore.py` |
| 구조/facade | `tests/test_worker_structure_budget.py` |

### 6.3 검증 명령 (문서 기준선)

```bash
pip install -e .[dev]
python -m pyright
python -m pytest -q
python main.py --smoke
# 선택: PDF_MASTER_GEMINI_FILE_API_SMOKE=1 + GEMINI_API_KEY
```

문서 기준: **230 collected / 229 passed / 1 opt-in Gemini smoke skipped**.

---

## 7. Appendix

### 7.1 이전 감사(2026-07-15) 대비 상태

| 우선순위 | 이슈 | 2026-07-22 상태 |
|----------|------|-----------------|
| High | AI 취소 / finished | **해결 확인** |
| High | 암호 PDF AI 거부 | **해결 확인** (잔여: 평문 temp §3.2) |
| Medium | blank 오판 | **해결 확인** |
| Medium | visual silent fail | **해결 확인** |
| Medium | redact_area 확인 | **해결 확인** |
| Low | pending 상한 / unknown task i18n | **해결 확인** |

### 7.2 강점 (감사 중 확인)

- OperationSpec 중심 preflight·dispatch·undo·same-path 계약이 일관적  
- atomic save + created_output_paths 기반 취소 정리  
- 첨부 경로 정규화 및 공통 경로 탈출 차단  
- AI 결과 meta(source/truncated) UI 표기  
- SOLID 분할 후에도 public mode/import facade 유지 및 구조 예산 테스트  
- i18n 카탈로그 + 하드코딩 스모크 테스트 존재

### 7.3 분석 방법 메모

- 우선: CodeGraph `codegraph_explore` (entry/worker/AI/security/preview/lifecycle/compare)  
- 보조: grep (`_check_cancelled` 분포), 핵심 파일 구간 교차 확인  
- 본 감사는 **구현 수정 없이** 리포트만 산출

---

*이 문서는 PDF Master v4.5.6 코드 기준 기능 구현 감사입니다. (2026-07-22)*
