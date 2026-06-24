# Project Audit

> 감사 기준일: 2026-06-24  
> 구현 완료일: 2026-06-24  
> 대상 버전: PDF Master v4.5.5  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP, 보조 grep·파일 열람, `python -m pytest -q`

---

## 구현 상태 (2026-06-24)

본 리포트 **1~2단계 권장 수정**은 코드에 반영되었습니다.

| 우선순위 | 이슈 | 상태 |
|----------|------|------|
| High | 배치 미지원 `operation` 묵시 복사 | **해결** — `batch_ops.py` + `preflight.py` fail-fast |
| Medium | `remove_annotations` 취소 체크 없음 | **해결** — page loop `_check_cancelled()` |
| Medium | `set_ui_busy` 범위 제한 | **해결** — 단축키 + 파일 열기 메뉴 포함 |
| Medium | `run_worker` 500ms `wait` 경합 | **해결** — 3s wait + running 시 큐잉 |
| Medium | 단일 `_pending_worker` 덮어쓰기 | **해결** — `_pending_workers` FIFO 큐 |
| Medium | `compare_pdfs` 텍스트-only 한계 | **문서화/스냅샷** — OCR은 3단계(미구현) |
| Low | `global_exception_handler` i18n | **해결** — `tm.get()` 적용 |
| Low | 배치 encrypt owner/user 동일 비밀번호 | **의도 유지** — `protect()`와 동일 계약 |

**3단계(미착수):** Compare OCR/렌더링 옵션, Worker cancel domain checklist 전수 점검, 암호화 PDF AI password UI 문서화.

테스트 기준선: `python -m pytest -q` → **192 collected / 191 passed / 1 skipped(opt-in Gemini smoke)**.

---

## 1. Executive Summary

PDF Master v4.5.5는 **PyQt6 UI + WorkerThread 백그라운드 처리 + domain별 `worker_ops`** 구조가 잘 정리된 데스크톱 PDF 편집기입니다. v4.5.5 감사 후속(2026-05-13~22)과 2026-06-24 본 리포트 후속 구현으로 preflight 계약, atomic save, same-path preview 복원, Undo 스냅샷, Worker 큐/취소, 배치 fail-fast 등이 보강되어 **전체 위험도는 Low** 로 평가합니다.

2026-06-24 감사 시점의 잔여 리스크였던 배치 묵시 복사, Worker 큐 덮어쓰기, `set_ui_busy` 범위, `remove_annotations` 취소, 빈 `search_term` 허용, 전역 예외 i18n은 **구현 완료**되었습니다.

남은 제품/구조 과제는 다음에 집중됩니다.

1. **기능 한계 문서화** — 텍스트 기반 비교, OCR 미구현 (`test_compare_scanned_pdf_limitation.py`로 한계 스냅샷 유지)
2. **3단계 구조 개선** — Compare OCR/렌더링, Worker cancel checklist 통일, 암호화 PDF AI password UI 계약
3. **추정 gap 모니터링** — 썸네일 로더 취소, `chat_histories` 저장 경합, WSL/Windows CodeGraph lock

테스트 기준선은 `python -m pytest -q` → **192 collected / 191 passed / 1 skipped(opt-in Gemini smoke)** 입니다.

---

## 2. Project Understanding

### 2.1 프로젝트 목적

- **올인원 PDF 편집 데스크톱 앱** (병합, 변환, 페이지 편집, 보안, 주석, 추출, AI 요약/채팅/키워드)
- Python 3.10+, PyQt6, PyMuPDF(fitz), optional Gemini (`google-genai`)

### 2.2 아키텍처 개요

```
main.py
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_undo
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()
            └─ WorkerThread (QThread)
                 ├─ WorkerRuntimeMixin.run()
                 │    ├─ _normalize_mode_kwargs()
                 │    ├─ _preflight_inputs()  ← dispatch OperationSpec 계약
                 │    └─ handler() in worker_ops/*
                 └─ signals → on_success / on_fail / on_cancelled
```

### 2.3 CodeGraph 기반 핵심 실행 흐름

| 단계 | 심볼 | 파일 | 설명 |
|------|------|------|------|
| 진입 | `main()` | `main.py` | 로깅, HiDPI, `--smoke`, `PDFMasterApp` 실행 |
| UI 액션 | `run_worker()` | `src/ui/main_window_worker.py:38` | 58+ 탭 액션에서 호출 (CodeGraph callers) |
| 스레드 | `WorkerThread.run()` | `src/core/worker.py:45` | `WorkerRuntimeMixin.run()` 위임 |
| 선검증 | `preflight_inputs()` | `src/core/worker_runtime/preflight.py:126` | PDF/header/크기, `required_kwargs`, `required_any_kwargs` |
| 디스패치 | `OPERATION_SPECS` | `src/core/worker_runtime/dispatch.py` | 50+ mode 계약(undo, cancel_cleanup, output_kind) |
| 완료 | `on_success/on_fail/on_cancelled` | `src/ui/main_window_worker.py` | Undo 등록, preview 복원, pending worker 재실행 |
| 종료 | `_shutdown_worker_for_close()` | `src/ui/main_window.py:38` | cooperative cancel → 3s wait → 강제 종료 확인 |

### 2.4 주요 안정화 메커니즘 (문서·코드 일치)

- **Same-path 저장**: `_prepare_preview_for_same_path_output` → worker → `_restore_preview_after_same_path_output` (`src/ui/window_worker/same_path.py`)
- **Undo**: before/after 백업 스냅샷 (`undo_manager.py` + `on_success` 등록)
- **취소 롤백**: `created_output_paths` + `cancel_cleanup` 정책 (`src/ui/window_worker/lifecycle.py`)
- **Atomic I/O**: `_atomic_pdf_save` / `_atomic_text_save` / `_atomic_binary_save` (`src/core/worker_runtime/io.py`)
- **AI 캐시/세션**: `AICacheMixin` — upload cache, chat session, mtime 기반 키 (`src/core/ai/cache.py`, `session.py`)

### 2.5 README/CLAUDE.md vs 실제 구현 정합성

| 문서 주장 | 실제 | 판정 |
|-----------|------|------|
| 미리보기는 `zoomable_preview.py` 경유 | `window_preview/*` + `ZoomablePreviewWidget` | 일치 |
| Worker preflight + `pdf_validation.py` 공유 | `preflight.py` → `validate_pdf_file()` | 일치 |
| Undo 스냅샷 복원 | `on_success`에서 backup push, `_restore_from_backup` | 일치 |
| 192 tests / 191 passed | 로컬 `pytest -q` 동일 (1 Gemini smoke skip) | 일치 |
| OCR / 풍부한 compare UI | 코드·로드맵에 “미구현” 명시 | 일치 (의도적 미구현) |
| 언어 변경 후 재시작 필요 | `window_core/menu.py` 재시작 안내 유지 | 일치 |

---

## 3. High-Risk Issues

### 3.1 배치 모드 미지원 operation 묵시 폴백

* **위치:** `src/core/worker_ops/batch_ops.py` / `WorkerBatchOpsMixin.batch()`
* **문제:** `operation`이 `compress|watermark|encrypt|rotate`가 아니면 `else` 분기에서 **원본을 그대로 복사 저장**합니다. 오류 없이 “성공”으로 집계됩니다.
* **영향:** 잘못된 배치 설정 시 사용자는 작업이 적용됐다고 믿지만 실제로는 단순 복사본만 생성됩니다.
* **근거:**

```86:88:src/core/worker_ops/batch_ops.py
                else:
                    self._atomic_pdf_save(doc, out_path)
                success_count += 1
```

* **권장 수정 방향:** `else`에서 `error_signal` 또는 파일별 `failed_files`로 처리; preflight에서 `operation` 화이트리스트 검증 추가.
* **우선순위:** **High**

---

### 3.2 `remove_annotations` 취소 응답성 부재

* **위치:** `src/core/worker_ops/annotation_ops.py` / `WorkerAnnotationOpsMixin.remove_annotations()`
* **문제:** 페이지별 주석 삭제 루프에 `_check_cancelled()`가 없습니다. 대용량 주석 문서에서 취소가 늦게 반영됩니다.
* **영향:** 취소 후에도 CPU 시간 소모, 완료 직전 취소 시 출력 파일이 이미 저장될 수 있음.
* **근거:**

```176:182:src/core/worker_ops/annotation_ops.py
            for page in doc:
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    page.delete_annot(annot)
```

  (`get_pdf_info`, `search_text`, `extract_tables`, `list_annotations`는 2026-05-22에 취소 체크가 추가됨 — `remove_annotations`는 제외)
* **권장 수정 방향:** 페이지 루프·내부 annot 루프 시작 시 `_check_cancelled()` 호출; 회귀 테스트 추가.
* **우선순위:** **Medium**

---

### 3.3 `set_ui_busy` 적용 범위가 제한적

* **위치:** `src/ui/window_worker/lifecycle.py` / `set_ui_busy()`
* **문제:** busy 상태에서 **`tabs`와 `btn_open_folder`만** 비활성화합니다. 메뉴바 단축키(`Ctrl+O`, `Ctrl+Z`), 툴바, progress overlay 외부 위젯은 그대로 동작할 수 있습니다.
* **영향:** 작업 중 중복 `run_worker` 호출 가능성(내부적으로 `isRunning()` 가드가 있으나 UX 혼란·대기 큐 덮어쓰기 유발).
* **근거:**

```115:117:src/ui/window_worker/lifecycle.py
def set_ui_busy(self, busy):
    self.tabs.setEnabled(not busy)
    self.btn_open_folder.setEnabled(not busy)
```

* **권장 수정 방향:** 메뉴 액션/단축키 일괄 disable, 또는 `run_worker` 진입 전 중앙 `WorkerGate`로 모든 액션 차단.
* **우선순위:** **Medium**

---

### 3.4 Worker 정리 시 500ms `wait` 경합

* **위치:** `src/ui/main_window_worker.py` / `run_worker()`
* **문제:** 기존 worker가 `isRunning()`이면 `wait(500)` 후 `_finalize_worker()`합니다. 500ms 내 종료되지 않으면 **아직 실행 중인 스레드를 finalize** 할 수 있습니다.
* **영향:** stale signal, 드물게 이중 완료 핸들러, 리소스 경합.
* **근거:**

```59:62:src/ui/main_window_worker.py
        if self.worker:
            if self.worker.isRunning():
                self.worker.wait(500)
            self._finalize_worker()
```

  (종료 시에는 `main_window.py`에서 3000ms + 사용자 확인 후 `terminate()` — 더 안전)
* **권장 수정 방향:** `wait()`를 충분히 길게 하거나, 완료 시그널 기반으로만 finalize; running 중이면 큐잉만 허용.
* **우선순위:** **Medium**

---

### 3.5 단일 `_pending_worker` 큐 — 마지막 요청만 보존

* **위치:** `src/ui/main_window_worker.py` / `run_worker()`, `_run_pending_worker()`
* **문제:** 작업 중 “예”를 여러 번 누르면 `_pending_worker`가 **매번 덮어쓰기**됩니다. FIFO 큐가 아닙니다.
* **영향:** 사용자가 의도한 두 번째 대기 작업이 유실될 수 있음.
* **근거:** `self._pending_worker = {"mode": ..., ...}` 단일 dict 할당 (line 49-53); `_run_pending_worker`는 1건만 pop.
* **권장 수정 방향:** `list` 큐로 변경하거나, 덮어쓰기 시 토스트/확인 표시.
* **우선순위:** **Medium**

---

### 3.6 배치 암호화 시 user/owner 동일 비밀번호

* **위치:** `src/core/worker_ops/batch_ops.py` / `batch()` encrypt 분기
* **문제:** `owner_pw`와 `user_pw`에 동일 `option`을 설정합니다. 의도적일 수 있으나, 단일 파일 `protect` UI와 권한 정책이 다를 수 있습니다.
* **영향:** 배치 암호화 결과물의 권한 모델이 단일 protect 작업과 미묘하게 다를 수 있음.
* **근거:**

```72:80:src/core/worker_ops/batch_ops.py
                elif operation == "encrypt" and option:
                    perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
                    self._atomic_pdf_save(
                        doc, out_path,
                        encryption=FITZ_PDF_ENCRYPT_AES_256,
                        owner_pw=option, user_pw=option,
```

* **권장 수정 방향:** 단일 `protect` 모드와 동일 kwargs 계약으로 통일; 문서화.
* **우선순위:** **Low**

---

### 3.7 전역 예외 핸들러 i18n 미적용

* **위치:** `main.py` / `global_exception_handler()`
* **문제:** 처리되지 않은 예외 메시지 박스가 **한국어 하드코딩**입니다. `language=en` 설정과 불일치합니다.
* **영향:** 영어 UI 사용자에게 한국어 크래시 대화상자 표시.
* **근거:**

```62:66:main.py
        QMessageBox.critical(
            None,
            "오류 발생",
            f"예상치 못한 오류가 발생했습니다.\n\n{exc_value}\n\n상세 로그: {LOG_FILE}"
        )
```

* **권장 수정 방향:** `tm.get(...)` 또는 최소 en/ko 분기.
* **우선순위:** **Low**

---

### 3.8 `compare_pdfs` — 텍스트 레이어만 비교

* **위치:** `src/core/worker_ops/compare_ops.py` / `_legacy_compare_pdfs()`
* **문제:** `page.get_text()` 문자열 diff만 수행합니다. 스캔 PDF·이미지 기반 PDF는 “동일”로 판정될 수 있습니다.
* **영향:** 시각적으로 다른 문서가 동일하다고 보고됨 (기능적 false negative).
* **근거:** line 118-121 text equality early-continue; OCR 미구현은 README/로드맵과 일치.
* **권장 수정 방향:** 제품 로드맵대로 OCR/렌더링 기반 비교 옵션 추가; 현재는 UI에 “텍스트 비교” 한계 명시.
* **우선순위:** **Medium** (제품 한계로 문서화됨, 구현 gap)

---

## 4. Potential Functional Gaps

### 4.1 확인된 gap (추정 아님)

| 항목 | 설명 |
|------|------|
| OCR 엔진 | README/로드맵에 후속 과제로만 존재, 코드 없음 |
| Compare 리포트 UI 확장 | 완료 요약 다이얼로그 + optional visual diff PDF까지만 구현 |
| Worker 직접 호출 시 빈 `search_term` | UI(`action_search_text`)는 검증하지만 Worker `search_text()`는 빈 문자열 허용 |
| `fill_form` / `get_bookmarks` / `extract_links` | page loop 취소 체크 패턴이 extract 계열과不完全 일치 가능 (grep상 `_check_cancelled` 호출 없음) |
| 배치 워터마크 `option` 누락 | `watermark` 분기는 `option` 없으면 아무 것도 안 하고 복사에 가까운 저장 가능 |
| AI 암호화 PDF | `ai_ops`에서 `is_pdf_encrypted` 시 조기 종료 — preview 비밀번호를 Worker에 넘기지 않으면 AI 불가 (의도적일 수 있음) |

### 4.2 추정 gap

| 항목 | 설명 |
|------|------|
| **추정** — WSL/Windows 이중 환경 | CodeGraph 주석(`directory.d.ts`)처럼 동일 워크트리에서 WSL+Windows가 `.codegraph/`를 공유하면 인덱스/데몬 lock 충돌 가능. `CODEGRAPH_DIR` 분리 필요. |
| **추정** — 대용량 배치 취소 | 배치는 `_atomic_pdf_save`로 path 추적은 되나, 수백 파일 처리 중 취소 시 부분 성공 파일이 출력 폴더에 남음(의도된 `created_outputs` 정책이나 UX 혼란 가능). |
| **추정** — 썸네일 로더 취소 | `ThumbnailLoaderThread`는 `_is_cancelled` 플래그만 사용, `QThread.requestInterruption` 미연동. |
| **추정** — `chat_histories` 동시 쓰기 | 빠른 연속 AI 채팅 시 settings 저장 타이머(400ms)와의 경합으로 마지막 메시지 유실 가능성(낮음). |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 ✅ (2026-06-24 완료)

1. ~~`batch()` unknown `operation` 묵시 복사 제거~~ → `batch_ops.py` + `preflight.py`
2. ~~`remove_annotations` 취소 체크 추가 + 테스트~~ → `annotation_ops.py` + `test_worker_remove_annotations_cancel.py`
3. ~~배치 `watermark`/`encrypt`에서 `option` 누락 시 명시적 실패 처리~~ → `test_worker_batch_missing_option.py`

### 2단계 — 안정성 개선 ✅ (2026-06-24 완료)

1. ~~`set_ui_busy` 범위 확대(메뉴/단축키/핵심 액션)~~ → `lifecycle.py`, `shortcuts.py`, `menu.py`
2. ~~`run_worker`의 `wait(500)` → 시그널 기반 정리 또는 대기 큐~~ → 3s wait + running 시 큐잉
3. ~~`_pending_worker`를 list 큐로 확장~~ → `_pending_workers` FIFO
4. ~~Worker 레벨 입력 검증 보강 (`search_term`, `operation` 등)~~ → `extract_ops.py`, `preflight.py`, `dispatch.py`
5. ~~`global_exception_handler` i18n~~ → `main.py` + i18n catalogs

### 3단계 — 구조·제품 개선 (미착수)

1. Compare: OCR/렌더링 기반 옵션 (로드맵 착수 전 설계 문서)
2. Worker cancel 정책을 domain checklist로 통일 (`form_ops`, `annotation_ops` 전수 점검)
3. 암호화 PDF — AI/배치/고급 추출에서 preview password 재사용 계약 UI 문서화
4. CodeGraph/개발 환경: `scripts/codegraph_repair.ps1` 정기 실행 가이드 (이미 추가됨)

---

## 6. Test Recommendations

### 6.1 추가 권장 테스트 ✅ (2026-06-24 반영)

| 테스트 | 검증 목표 | 상태 |
|--------|-----------|------|
| `test_worker_batch_unknown_operation.py` | 잘못된 `operation`이 silent copy 되지 않음 | 추가됨 |
| `test_worker_batch_missing_option.py` | watermark/encrypt에 `option` 없을 때 실패 | 추가됨 |
| `test_worker_remove_annotations_cancel.py` | annot 삭제 루프 중 취소 시 출력 미생성 | 추가됨 |
| `test_run_worker_pending_queue.py` | 연속 큐잉 시 요청 유실 없음 | 추가됨 |
| `test_set_ui_busy_shortcuts.py` | busy 중 단축키/메뉴 비활성화 | 추가됨 |
| `test_worker_search_text_empty_term.py` | Worker 경계에서 빈 검색어 reject | 추가됨 |
| `test_fill_form_cancel_regression.py` | 양식 채우기 page loop 취소 | 기존 `test_worker_cancel_regression.py`로 충족 |
| `test_compare_scanned_pdf_limitation.py` | 이미지-only PDF “동일” 스냅샷 | 추가됨 |

### 6.2 기존 테스트 보강

| 영역 | 현황 | 보강 |
|------|------|------|
| `run_worker` UI 흐름 | CodeGraph: direct unit test 없음 | `on_success`/`on_fail` payload 분기 통합 테스트 |
| `preflight_inputs` | 구조 테스트 있음 | mode별 negative case 표 확장 |
| AI File API | fake SDK 테스트 강함 | 암호화 PDF + password mapping 시나리오 |
| Encoding audit | `agent-tools/` 등 임시 파일에 민감 | `.gitignore` 또는 audit exclude에 `agent-tools/` 추가 검토 |

### 6.3 검증 기준선 (유지)

```powershell
python -m pyright
python -m pytest -q
python main.py --smoke
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/codegraph_repair.ps1
```

---

## 부록: 감사 시 수행한 환경 조치

CodeGraph MCP 안정화를 위해 다음을 적용했습니다 (감사 범위 외이나 재현성에 영향).

- CodeGraph **v1.0.1 → v1.1.0** 업그레이드
- `codegraph index -f` 전체 재인덱싱
- `scripts/codegraph_repair.ps1`, `scripts/codegraph.ps1`, `.grok/config.toml` 추가
- 손상된 `daemon.pid` 이력(`EISDIR`) 정리 및 `daemon.log` 초기화

---

*초기 작성(2026-06-24)은 분석·보고만 수행했습니다. 동일 날짜에 1~2단계 권장 수정과 신규 테스트 13건이 코드에 반영되었습니다. 이전 감사 문서 `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md`의 F-01~F-04는 “이미 해결됨”으로 간주합니다.*