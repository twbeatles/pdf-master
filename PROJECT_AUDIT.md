# Project Audit

> 감사 기준일: **2026-07-15**  
> 대상 버전: **PDF Master v4.5.6**  
> 범위: 기능 구현 관점 (버그·검증·상태/비동기·보안·문서 정합·테스트 공백)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP/`codegraph explore`, 보조 파일 열람·grep, 테스트 수집 카운트  
>
> **후속 구현 (2026-07-15):** 본 리포트 1~3단계 권장 항목 중 코드로 실현 가능한 항목을 반영함.  
> OCR 엔진·미리보기 드래그 교정 UX는 제품 설계 후 별도 착수(의도적 미구현 유지).

---

## 1. Executive Summary

PDF Master v4.5.6은 **PyQt6 UI + `WorkerThread` 백그라운드 처리 + domain별 `worker_ops` + `worker_runtime` 계약(preflight/dispatch/atomic I/O)** 구조가 잘 정리된 데스크톱 PDF 편집기입니다. v4.5.5~4.5.6 안정화와 **2026-07-15 감사 후속 구현**으로 **전체 위험도는 Low**에 가깝게 낮아졌습니다.

### 구현 상태 (2026-07-15 후속)

| 우선순위 | 이슈 | 상태 |
|----------|------|------|
| High | AI 취소 무시 / finished 시그널 | **해결** — `cancel_check` + stream/handler re-raise |
| High | 암호화 PDF AI 무조건 거부 | **해결** — preview `passwords`로 임시 복호 경로 |
| Medium | blank-page 렌더 실패 오판 | **해결** — 예외 시 페이지 유지 |
| Medium | visual compare silent fail | **해결** — `visual_error` + `visual_error_count` |
| Medium | redact_area 확인 없음 | **해결** — 확인 다이얼로그 |
| Low | 문서 기준선 / Unknown task i18n / batch permissions | **해결** |

**테스트 기준선:** `python -m pytest -q` → **222 collected / 221 passed / 1 opt-in Gemini smoke skipped** (2026-07-21 SOLID 분할 반영).

**잔여(제품 로드맵):** OCR 엔진, 미리보기 드래그 교정 UX, compare 리포트 UI 확장.

---

## 2. Project Understanding

### 2.1 목적

- 올인원 PDF 편집 데스크톱 앱: 병합/변환/페이지 편집/보안/주석/추출/배치/AI(Gemini)
- 스택: Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai`, PyInstaller

### 2.2 아키텍처 (CodeGraph + 문서 교차)

```
main.py
  ├─ setup_logging / global_exception_handler (i18n)
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_undo / window_worker
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()
            ├─ busy 가드 + _pending_workers FIFO
            ├─ same-path preview 해제 / password 주입
            └─ WorkerThread (QThread)
                 └─ WorkerRuntimeMixin.run()
                      ├─ _normalize_mode_kwargs()
                      ├─ _preflight_inputs()  ← OperationSpec + PDF header/size
                      └─ handler in worker_ops/*
                           └─ signals → on_success / on_fail / on_cancelled
```

### 2.3 CodeGraph 기반 핵심 호출 관계

| 단계 | 심볼 | 위치 | 비고 |
|------|------|------|------|
| 진입 | `main()` | `main.py` | HiDPI, `--smoke`, `PDFMasterApp` |
| UI 게이트 | `run_worker` | `src/ui/main_window_worker.py` | CodeGraph: 다수 탭 액션 caller |
| 스레드 | `WorkerThread.run` | `src/core/worker.py` | Runtime mixin 위임 |
| 선검증 | `preflight_inputs` | `src/core/worker_runtime/preflight.py` | batch op 화이트리스트, search_term, required_* |
| 디스패치 | `OPERATION_SPECS` | `src/core/worker_runtime/dispatch.py` | 50+ mode 계약 |
| PDF open | `_open_pdf_document` | `src/core/worker_runtime/mixin.py` | `passwords` 맵 + authenticate |
| 완료/실패 | `on_success` / `on_fail` / `on_cancelled` | `main_window_worker.py` | Undo 스냅샷, preview 복원, pending 재실행 |
| 종료 | `_shutdown_worker_for_close` | `main_window.py` | cancel → 3s wait → 강제 종료 확인 |

### 2.4 안정화 메커니즘 (문서 ↔ 코드 대체로 일치)

- Same-path 저장 전 preview 해제 + 완료 후 복원
- Undo: `before_backup_path` / `after_backup_path` 스냅샷
- 취소 롤백: `created_output_paths` + `OperationSpec.cancel_cleanup`
- Atomic I/O: `_atomic_pdf_save` / text / binary
- AI 클래스 캐시: upload/text/chat session은 **클래스 변수**로 인스턴스 간 공유
- 첨부 추출: 파일명 정규화 + `output_dir` 하위 강제 (`io.py`)

### 2.5 README / CLAUDE.md vs 구현 정합성

| 문서 주장 | 실제 | 판정 |
|-----------|------|------|
| v4.5.6 deep compress / cleanup_ops / visual compare / redact_area 등 | `transform/`+facade, `cleanup/`+facade, `compare/`+facade, UI 탭 빌더 존재 | **일치** |
| SOLID 도메인 패키지 + thin facade (2026-07-21) | `worker_ops/{annotation,extract,cleanup,page,transform,compare}/`, `_settings_impl` 등 | **일치** |
| 미리보기 `zoomable_preview` / Qt 인쇄 | preview 위젯 + 인쇄 경로 | **일치** |
| Worker preflight + shared `pdf_validation` | `preflight.py` → `validate_pdf_file` | **일치** |
| 배치 미지원 op fail-fast | `batch_ops` + preflight 화이트리스트 | **일치** |
| `_pending_workers` FIFO / busy 단축키 비활성 | `lifecycle.set_ui_busy`, `run_worker` | **일치** |
| pytest 222 / 221 pass / 1 skip | 전체 suite 통과 확인 (2026-07-21 SOLID 분할 후) | **일치** |
| OCR 미구현 | 코드/로드맵에 후속 과제 | **일치 (의도적)** |
| GEMINI.md 테스트 기준선 | README와 동일 219 기준으로 동기화 | **일치** |

---

## 3. High-Risk Issues

> **참고:** 아래 항목은 감사 시점의 발견 기록입니다. 2026-07-15 후속으로 **해결된 항목**은 Executive Summary 표와 §7.1을 우선 참고하세요.

### 3.1 AI Worker 취소가 완료 경로를 막지 못함

* **위치:** `src/core/worker_ops/ai_ops.py` (`ai_summarize` / `ai_ask_question` / `ai_extract_keywords`), `src/core/ai/generation.py` (`_stream_generate_content`), `src/core/worker_runtime/mixin.py` (`run`)
* **문제:**
  1. AI 핸들러는 `_check_cancelled()`를 호출하지 않는다.
  2. 스트리밍 루프(`generate_content_stream`)에도 취소 체크가 없다.
  3. 취소 후에도 핸들러가 끝까지 가면 `finished_signal.emit(...)`이 그대로 호출된다. `run()`은 취소 시 로그만 생략할 뿐 finished를 막지 않는다.
* **영향:** 사용자가 오버레이에서 취소해도 네트워크/토큰 비용이 계속 들고, 완료 후 **성공 UI(요약/채팅 반영)** 가 뜰 수 있다. 취소 UX와 실제 상태가 어긋난다.
* **근거:**
  - `ai_ops.py` 전 구간: cancel 체크 없음, 성공 시 무조건 `finished_signal.emit`
  - `generation.py` 114–123: stream chunk 루프에 중단 조건 없음
  - `WorkerThread.cancel()`은 `_cancel_requested`만 세팅
* **권장 수정 방향:**
  - stream/generate 사이에 cancel 콜백 또는 `_check_cancelled()` 주입
  - AI 핸들러 종료 직전 cancel이면 `CancelledError` 또는 `cancelled_signal` 경로
  - (선택) SDK 요청 타임아웃/abort 연동
* **우선순위:** **High**

---

### 3.2 암호화 PDF AI 거부 — preview password 계약 미사용

* **위치:** `src/core/worker_ops/ai_ops.py` (세 모드 모두), `src/core/worker_runtime/preflight.py` `is_pdf_encrypted`, `src/ui/window_worker/undo.py` `_augment_worker_passwords_from_preview`
* **문제:** AI 핸들러는 `_is_pdf_encrypted(file_path)`가 True이면 **비밀번호 보유 여부와 무관하게** 즉시 오류로 종료한다. 반면 일반 Worker 경로는 `_open_pdf_document` + `passwords` 맵으로 preview 세션 암호를 재사용한다. UI도 `run_worker`에서 password를 kwargs에 주입한다.
* **영향:** 미리보기에서 연 암호화 PDF라도 요약/채팅/키워드가 불가. README “암호화 PDF는 일부 작업에서 복호화 필요”와 부분 일치하나, **이미 인증된 세션을 버리는 점**은 기능 gap.
* **근거:**
  - `ai_ops.py` 28–30, 87–89, 133–135: encrypted early return
  - `is_pdf_encrypted`: `doc.is_encrypted`만 확인 (authenticate 없음)
  - `_augment_worker_passwords_from_preview`: passwords 주입은 되지만 AI가 사용하지 않음
* **권장 수정 방향:**
  - AI 전 단계에서 `_open_pdf_document` 또는 authenticate 후 임시 복호/추출 경로
  - File API 업로드 전 암호 해제된 임시 파일 사용 시 삭제 보장
  - UI에 “암호 PDF는 미리보기 인증 후 AI 가능” 문구 또는 실패 메시지 개선
* **우선순위:** **High**

---

### 3.3 `remove_blank_pages` — 렌더 실패를 빈 페이지로 취급

* **위치:** `src/core/worker_ops/cleanup/helpers.py` (`cleanup_ops` facade re-export) / `_is_blank_page`
* **문제:** 텍스트·이미지·드로잉이 없을 때 저해상도 pixmap으로 판별하는데, **예외 시 `return True`(빈 페이지)** 이다. 손상 페이지·렌더 실패·메모리 압박 시 정상 페이지가 삭제 후보가 될 수 있다.
* **영향:** 대용량/스캔/특수 콘텐츠 PDF에서 의도치 않은 페이지 손실 위험.
* **근거:**

```python
# cleanup/helpers.py _is_blank_page
try:
    pix = page.get_pixmap(...)
    ...
except Exception:
    return True
```

* **권장 수정 방향:** 예외 시 **False(유지)** 또는 “판정 불가”로 keep; 옵션으로 공격적/보수적 모드 분리; 회귀 테스트(렌더 mock 실패 → 페이지 유지)
* **우선순위:** **Medium** (데이터 손실 가능성이라 상위에 가깝게 취급 권장)

---

### 3.4 visual compare 예외를 “차이 없음”으로 흡수

* **위치:** `src/core/worker_ops/compare_ops.py` / `_legacy_compare_pdfs` 내 `_pixel_diff_ratio` 호출부
* **문제:** visual 비교 중 예외가 나면 `logger.debug` 후 `visual_ratio=0`, `visual_diff=False`로 둔다. 페이지가 실제로 달라도 리포트에 안 잡힐 수 있다.
* **영향:** 스캔본/이미지 PDF 비교의 **신뢰성 false negative**. 보안·교정 워크플로에서 위험.
* **근거:**

```python
# compare_ops.py ~164-171
except Exception as exc:
    logger.debug("visual compare failed page %s: %s", index + 1, exc)
    visual_ratio = 0.0
    visual_diff = False
```

* **권장 수정 방향:** 페이지 status를 `visual_error`로 기록; 요약 다이얼로그에 실패 페이지 수 표시; 전체 실패 시 warning 완료 메시지
* **우선순위:** **Medium**

---

### 3.5 영역 교정(`redact_area`) — 파괴적 작업인데 확인 단계 없음

* **위치:** UI `src/ui/tabs_advanced/actions_markup.py` `action_redact_area` vs `action_redact_text`
* **문제:** `redact_text`는 경고 확인 후 실행하지만, `redact_area`는 좌표 파싱 후 바로 저장 대화상자 → Worker 실행. 교정은 영구 삭제다.
* **영향:** 잘못된 좌표/페이지로 비가역 데이터 손실. Undo는 백업 스냅샷으로 가능하나 UX 안전장치 불균형.
* **근거:** `action_redact_text`에 `QMessageBox.warning` 확인 있음; `action_redact_area`에는 없음
* **권장 수정 방향:** 동일 확인 다이얼로그; (추정 개선) 미리보기 좌표 오버레이 선택 UX
* **우선순위:** **Medium**

---

### 3.6 AI/장시간 작업 중 취소 외 세부 이슈 (배치 내부 루프)

* **위치:** `src/core/worker_ops/batch_ops.py` watermark/rotate 분기
* **문제:** 파일 단위 `_check_cancelled()`는 있으나, 페이지 루프 내부에는 없음. 초대형 단일 PDF 배치 시 취소 지연.
* **영향:** 응답성 저하 (기능 오류보다는 UX). compress 이미지 최적화 경로는 cancel 콜백이 있음.
* **근거:** watermark `for page in doc:` 내부에 cancel 없음; file loop 시작에만 존재
* **권장 수정 방향:** 페이지 루프에 `_check_cancelled()` 추가
* **우선순위:** **Low–Medium**

---

### 3.7 문서 기준선 불일치 (기능 자체보다 운영 리스크)

* **위치:** `GEMINI.md`, `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md`, 구 `PROJECT_AUDIT.md` 잔존 수치
* **문제:** README/CLAUDE는 **211 collected**를 쓰는데 GEMINI는 **192**, 구 감사는 **179/192**가 남아 있다. `PROJECT_AUDIT.md` 자체가 “1–2단계 완료·위험도 Low”로 고정되어 v4.5.6 신규 리스크를 가린다.
* **영향:** 신규 기여자/CI 기대치 혼선, 감사 문서 SSOT 붕괴
* **권장 수정 방향:** 유지 문서의 pytest 기준선을 한곳(README 또는 CLAUDE) 기준으로 동기화; 구 감사는 archive 섹션으로 분리
* **우선순위:** **Low**

---

### 3.8 Unknown task 메시지 하드코딩 (i18n)

* **위치:** `src/core/worker_runtime/mixin.py` `run()` else 분기
* **문제:** `error_msg = f"Unknown task: {self.mode}"` 영어 고정. 전역 예외 핸들러 i18n은 반영됨.
* **영향:** 영어/한국어 UI 불일치 (발생 빈도는 낮음 — 레지스트리 밖 mode)
* **권장 수정 방향:** `_get_msg("err_unknown_task", mode)`
* **우선순위:** **Low**

---

### 3.9 배치 encrypt vs 단일 protect 권한 계약 차이 (의도 가능)

* **위치:** `batch_ops.py` encrypt 분기 vs `security_ops.protect` + `_resolve_permissions`
* **문제:** 배치는 owner/user 동일 비밀번호 + 고정 permission(print/copy/accessibility). 단일 protect는 UI 권한 체크박스 + owner/user 분리 가능.
* **영향:** 배치로 만든 암호 PDF 권한 모델이 단일 작업과 다를 수 있음 (보안 정책 기대 불일치)
* **권장 수정 방향:** 의도라면 README/툴팁 명시; 아니면 protect와 동일 kwargs 계약
* **우선순위:** **Low** (의도 유지 가능)

---

## 4. Potential Functional Gaps

### 4.1 확인된 gap (추정 아님)

| 항목 | 설명 |
|------|------|
| OCR | 의도적 미구현. 텍스트 없는 스캔본 추출/검색/AI fallback 품질 한계 |
| AI cancel | 3.1 — 취소가 완료 결과를 막지 못함 |
| AI + 암호 PDF | 3.2 — preview password 미사용 hard reject |
| 기본 compare 모드 | UI 콤보 기본값이 text; visual은 사용자가 선택해야 함 (기능은 존재) |
| visual 샘플링 | `_pixel_diff_ratio`가 바이트 step 샘플링 → 국소 차이 누락 가능 (한계) |
| `auto_bookmarks` 휴리스틱 | 폰트 크기 기반; 다단/한글 제목 오탐·미탐 가능 |
| `redact_area` UX | 수동 좌표 입력만; 미리보기 드래그 선택 없음 |
| 추출 결과 하드코딩 한글 | `get_bookmarks`/`search_text` 출력 본문에 한국어 고정 문자열 |
| `_pending_workers` 상한 없음 | 이론상 무한 큐 (실사용에서는 낮음) |
| 종료 시 pending 큐 | close는 실행 중 worker만 정리; 대기 큐는 앱 종료로 소멸 (의도적일 수 있음) |

### 4.2 추정 gap

| 항목 | 설명 |
|------|------|
| **추정** — 썸네일 로더 | `ThumbnailLoaderThread`는 `_is_cancelled`만 사용. 대용량 PDF 전환 시 이전 배치 잔여 시그널이 잠깐 섞일 여지 (sender 가드 여부는 grid 쪽 추가 확인 필요) |
| **추정** — settings 저장 경합 | `_save_chat_histories` 즉시 저장 vs `_schedule_settings_save` 400ms debounce가 같은 `self.settings` dict를 쓰므로, 극단적 연속 조작 시 last-write-wins |
| **추정** — sanitize 완전성 | JS/OpenAction/일부 이름 트리 제거는 best-effort. “포렌식급 위생”은 아님 |
| **추정** — `set_bookmarks` 입력 | 구조 검증 약함 → 잘못된 toc가 PyMuPDF 예외로 실패할 수 있음 |
| **추정** — Linux/macOS | 앱은 Windows 중심(Segoe UI, dist exe). 소스 실행은 가능하나 인쇄/keyring/경로 케이스는 테스트 얇을 수 있음 |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (기능 신뢰성)

1. **AI 취소 계약:** stream/generate 중 cancel 체크 + 취소 시 `finished_signal` 금지 / `cancelled_signal` 경로
2. **AI 암호 PDF:** preview `passwords`로 open/authenticate 후 처리; 실패 메시지로 “미리보기에서 먼저 잠금 해제” 안내
3. **`_is_blank_page` 예외 시 유지(False):** 데이터 손실 방지 + 단위 테스트

### 2단계 — 안정성 개선

1. visual compare 예외 → `visual_error` status + UI 요약 반영
2. `redact_area` 확인 다이얼로그 (redact_text와 동일 정책)
3. batch watermark/rotate 페이지 루프 cancel 체크
4. `auto_bookmarks` 헤딩 스캔 루프에 cancel 체크
5. 유지 문서(GEMINI.md 등) pytest 기준선 동기화

### 3단계 — 구조·제품 개선

1. OCR 옵션 설계 (엔진/extra/패키징) — 로드맵 항목
2. compare 리포트 UI 확장 (페이지별 visual_error, 샘플 히트맵)
3. redact 좌표를 미리보기에서 지정하는 UX
4. Worker cancel domain checklist 전수(남은 짧은 핸들러 포함)
5. 추출 텍스트 결과 i18n 또는 locale-neutral 포맷
6. (선택) batch protect를 단일 protect 권한 모델과 통합

---

## 6. Test Recommendations

### 6.1 신규 권장 테스트

| 테스트 | 검증 목표 |
|--------|-----------|
| `test_ai_ops_cancel_mid_stream.py` | cancel 후 `finished_signal` 미발생 / `cancelled_signal` 또는 결과 미반영 |
| `test_ai_ops_encrypted_with_password.py` | passwords 맵 있으면 AI 진행(또는 명시적 복호 경로); 없으면 기존 오류 |
| `test_remove_blank_pages_render_failure_keeps_page.py` | pixmap 예외 시 페이지 유지 |
| `test_compare_visual_error_status.py` | visual 경로 예외 시 identical로 삼키지 않음 |
| `test_redact_area_ui_confirm.py` | (UI) 확인 No면 Worker 미기동 — 패턴은 redact_text와 동일 |
| `test_batch_watermark_cancel_mid_pages.py` | 대형 문서 페이지 루프 중 취소 |

### 6.2 기존 테스트 보강

| 영역 | 현황 | 보강 |
|------|------|------|
| `test_compare_scanned_pdf_limitation.py` | 기본(text) 모드 한계 스냅샷 | visual 모드에서 픽셀 차이가 잡히는지 **긍정 케이스** 추가 |
| `test_worker_pymupdf_extras.py` | cleanup/redact 등 존재 | blank-page 오판, sanitize best-effort 경계 |
| `test_ai_service_cache.py` | fake SDK 강함 | cancel 콜백 / stream 중단 계약 |
| 문서 검증 | `test_validation_docs_config.py` | GEMINI 등 기준선 숫자 드리프트 탐지 강화 |

### 6.3 검증 커맨드 (유지)

```powershell
python -m pyright
python -m pytest -q
python main.py --smoke
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
```

예상: **222 collected / 221 passed / 1 opt-in Gemini smoke skipped** (환경·의존성 동일 시, 2026-07-21 기준).

---

## 7. Appendix

### 7.1 이전 감사(2026-06-24) 이슈 상태

| 이슈 | 상태 |
|------|------|
| 배치 미지원 operation 묵시 복사 | **해결** (`batch_ops` + preflight) |
| `remove_annotations` 취소 없음 | **해결** |
| `set_ui_busy` 단축키 미차단 | **해결** (`lifecycle.py`) |
| `run_worker` wait(500) | **해결** (3s + 큐잉) |
| 단일 `_pending_worker` 덮어쓰기 | **해결** (`_pending_workers` FIFO) |
| 빈 `search_term` Worker 허용 | **해결** |
| `global_exception_handler` i18n | **해결** |
| compare 텍스트-only / visual silent fail | **개선** (visual/both UI + `visual_error` 상태; 기본 모드는 text 유지) |
| AI cancel / 암호 PDF / blank-page / redact confirm | **해결** (2026-07-15) |

### 7.2 CodeGraph 참고

- 인덱스: 프로젝트 루트 `.codegraph/` (약 212 files)
- MCP: `codegraph_explore` — entry/worker/security/cleanup 쿼리 사용
- CLI: `codegraph explore "..."` 로 runtime/preflight/cleanup 교차 확인
- 일부 “no covering tests found” 표시는 인덱스/동적 dispatch 한계로 **과소 탐지** 가능 (예: `run_worker`는 별도 테스트 존재)

### 7.3 감사 한계

- 전체 `pytest` 실행·PyInstaller smoke는 이번 세션에서 **전수 재실행하지 않음** (수집 카운트와 코드 정적 근거 중심)
- 네트워크 의존 Gemini live smoke는 opt-in 범위로 제외
- OCR/패키징 전략 같은 제품 결정은 로드맵 수준으로만 기록

---

*작성: 2026-07-15 — 기능 구현 감사. 코드 변경 없음. 이전 구현 완료 이슈와 신규 잔여 리스크를 분리 기록함.*
