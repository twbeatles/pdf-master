# Project Audit — Quality Track (Architecture · Performance · Packaging · i18n · Tests)

> 감사 기준일: **2026-08-05**  
> 대상 버전: **PDF Master v4.5.6**  
> **범위(Track B):** 아키텍처·유지보수성·성능/메모리·패키징·i18n 산출물·테스트 공백·운영 품질  
> **비범위:** 기능 구현 fail-fast·취소·path traversal 등 → 기능 SSOT `PROJECT_AUDIT.md` (Track A)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP, 보조 파일 열람·grep·`pytest`/`pyright`  

---

## 0. Implementation Follow-up (2026-08-05)

| 항목 | 상태 | 근거 |
|------|------|------|
| §3.1 AI text cache clear + closeEvent shutdown | **해결** | `shutdown_executor` + `closeEvent` |
| §3.2 kwargs/pending scrub + AI api_key 재주입 | **해결** | `scrub_sensitive_worker_kwargs`, `copy_kwargs_for_pending` |
| §3.3 `get_pdf_info` i18n | **해결** | `pdf_info_*` 카탈로그 키 |
| §3.7 FITZ 미설치 기동 안내 | **해결** | `main.py` early dialog |
| §3.6 FALLBACK ⊆ catalog 스모크 | **해결** | `test_fallback_message_keys_subset_of_catalogs` |
| §3.8 Undo 대용량 스킵 | **해결** | `UNDO_BACKUP_MAX_SOURCE_BYTES` 200MB |
| §3.5 structure budget 본체 가드 | **해결** | ai 분할 후 facade 40줄 + 본체 상한 |
| §3.4 monkeypatch 계약 공식 어댑터 | **해결** | `src/ui/contracts/monkeypatch_surfaces.py` + 테스트 |
| §3.9 썸네일 LRU | **해결** | `ThumbnailPixmapLru` + 가시 영역 적중 시 재렌더 스킵 |
| AI ops 분할 | **해결** | `temp_acl` / `prepare` / `handlers` / thin `ops` |
| compare pixel helper 추출 | **해결** | `helpers.pixel_diff_ratio` |
| 대형 i18n 카탈로그 분할 | **잔여** (Low, 900줄 카탈로그) |
| text_placement 추가 분할 | **잔여** (Low) |

**회귀:**  
`tests/test_audit_2026_08_05_quality_followup.py`  
`tests/test_monkeypatch_contracts.py`  
`tests/test_thumbnail_pixmap_lru.py`

**구현 후 위험도:** **Low**

---

## 1. Executive Summary

기능 감사(Track A) 후 코어 동작 위험도는 **Low**다. Track B 권고의 **1–2단계 핵심 항목은 구현 반영**되었다. 잔여는 구조 분할·썸네일 LRU 등 장기 과제다.

| 구분 | 평가 (구현 후) |
|------|------|
| **전체 위험도 (Track B)** | **Low–Medium** |
| Critical / High | **없음** |
| Medium 잔여 | monkeypatch 계약 고정 비용, 카탈로그/대형 ops 추가 분할 |
| Low 잔여 | 썸네일 LRU, HiDPI 추정 등 |

### 핵심 문제 (요약)

1. **`AIService.shutdown_executor`가 업로드/채팅만 비우고 `_text_cache`(추출 본문, 최대 16MB)는 남긴다** — 프로세스 수명 동안 PDF 본문이 메모리에 잔존. `closeEvent`도 명시 호출하지 않고 `atexit`에만 의존.  
2. **Worker·pending 큐가 `api_key` / `passwords` 를 kwargs dict로 장시간 보유** — finalize는 시그널 disconnect + `deleteLater`만 수행, 민감 필드 scrub 없음.  
3. **`get_pdf_info` 출력 본문이 한국어 리터럴 고정** — EN UI에서도 산출 TXT가 한글 섹션 헤더.  
4. **아키텍처: ToastWidget/`tabs_ai/actions` monkeypatch 계약**으로 facade 분리가 반쯤 멈춤 — 테스트·리팩터 비용이 구조에 고정됨.  
5. **품질 게이트는 강함** (`pyright` 0, `pytest` 0, structure budget) — 그러나 budget 밖 파일이 400–900줄대로 재비대화 중.

---

## 2. Project Understanding (Track B 관점)

### 2.1 목적·스택 (README / CLAUDE)

| 항목 | 내용 |
|------|------|
| 제품 | 올인원 PDF 편집 데스크톱 |
| 스택 | Python 3.10+, PyQt6, PyMuPDF, optional google-genai/keyring/OCR, PyInstaller |
| 검증 게이트 | pyright / pytest / smoke / package_smoke |
| 구조 정책 | SOLID 도메인 패키지 + public facade 불변 + structure budget 테스트 |

### 2.2 아키텍처 골격 (CodeGraph)

```
PDFMasterApp (8-way mixin)
  ├─ run_worker  (~69 UI callers)  → WorkerThread
  │     WorkerRuntimeMixin + WorkerPdfOpsMixin(10 domain mixins) + WorkerAiOpsMixin
  ├─ preview_widget mixins + thumbnail grid_* 
  └─ tabs_* actions (AI: monkeypatch-sensitive single file)
```

| 심볼 | CodeGraph 관찰 | Track B 함의 |
|------|----------------|--------------|
| `run_worker` | ~69 callers, ⚠️ covering tests 적음 | 회귀는 간접 테스트 의존 |
| `WorkerPdfOpsMixin` | 10개 도메인 합성 | MRO 깊음, 변경 blast radius 큼 |
| `ToastWidget` | 37 callers | UI 전역 의존 + monkeypatch 계약 |
| `AICacheMixin` | class-level LRU | 프로세스 전역 상태, 종료 경로 중요 |
| `resource_path` / frozen | main + path_utils | 패키징 경로 단일화됨 |
| facade line budgets | `test_worker_structure_budget` | shim은 얇게 유지, 본체는 budget 밖 |

### 2.3 현 품질 게이트 스냅샷

```text
python -m pytest -q     → exit 0 (opt-in Gemini smoke skip)
python -m pyright src/core src/ui → 0 errors
```

### 2.4 Track A와의 관계

| Track A (기능) | Track B (품질) |
|----------------|----------------|
| preflight, cancel, path safety, HTML escape | 아키텍처 부채, 메모리, 패키징, i18n 산출물, 테스트 공백 |
| 2026-08-05 residual **구현 완료** | 본 문서 이슈는 **미구현 권고** |

---

## 3. High-Risk Issues (품질·운영)

> Critical 없음. 기능 장애보다 **유지보수·프라이버시·다국어 산출물·구조 비용** 중심.

### 3.1 AI 텍스트 캐시가 종료 시 비워지지 않음

* **위치:** `src/core/ai/cache.py` → `AICacheMixin.shutdown_executor`  
  등록: `src/core/ai/service.py` `atexit.register(AIService.shutdown_executor)`  
  UI: `PDFMasterApp.closeEvent` — `shutdown_executor` **미호출**
* **문제:** `shutdown_executor`는 `_uploaded_file_cache`·`_chat_sessions`만 clear. **`_text_cache` / `_text_cache_bytes`는 유지.** 클래스 레벨 캐시 상한 `_TEXT_CACHE_MAX_BYTES = 16MB`.
* **영향:** 요약/폴백 추출한 PDF 본문이 앱 수명 동안 RAM 잔존. 공유 PC·메모리 덤프·장기 실행 시 프라이버시·메모리 압력. 원격 File API 삭제는 되나 **로컬 텍스트 사본은 남음**.
* **근거:** `shutdown_executor` 본문; `closeEvent`에 AI shutdown 없음; `atexit`만 등록.
* **권장 수정 방향:** `shutdown_executor`에서 text cache clear; `closeEvent`에서 best-effort `AIService.shutdown_executor()` 호출(이중 호출 안전).
* **우선순위:** **Medium**

---

### 3.2 Worker kwargs / pending 큐의 민감 파라미터 잔류

* **위치:**  
  - `src/core/worker.py` → `WorkerThread.kwargs`  
  - `src/ui/window_worker/lifecycle.py` → `_enqueue_pending_worker` (`"kwargs": dict(kwargs or {})`)  
  - `_finalize_worker` → disconnect + `deleteLater` only
* **문제:** AI 모드 `api_key`, 암호 PDF `passwords`/`password` 가 dict에 그대로 실려 스레드 수명·대기 큐에 복제된다. finalize 시 scrub 없음.
* **영향:** 메모리 잔존 시간 증가, 대기 큐 덤프/디버그 로그 시 유출 면적 확대. (디스크 로그에 직접 찍히는 코드는 이번 감사에서 **확인되지 않음**.)
* **근거:** `run_worker`가 kwargs 통째 전달; enqueue가 `dict` 복사; finalize가 키 삭제 없음.
* **권장 수정 방향:** finalize/cancel 시 `api_key`/`password(s)` 키 제거; pending 저장 시 민감 키 마스킹 또는 실행 직전 주입; 가능하면 keyring에서 실행 시점에만 로드.
* **우선순위:** **Medium**

---

### 3.3 `get_pdf_info` 산출물 언어 하드코딩

* **위치:** `src/core/worker_ops/extract/text_info.py` → `get_pdf_info`
* **문제:** 출력 TXT 헤더·섹션이 `"# PDF 정보"`, `"## 기본 정보"`, `"페이지 수"` 등 **한국어 리터럴 고정**. Worker i18n/`_get_msg` 미사용.
* **영향:** EN UI 사용자도 한글 리포트 수신. i18n 정책(런타임 UI 카탈로그)과 산출물 정책 불일치.
* **근거:** `lines = [f"# PDF 정보: ...", "## 기본 정보", ...]` 직접 구성.
* **권장 수정 방향:** 카탈로그 키로 섹션 헤더 분리 또는 locale 분기; EN/KO 스냅샷 테스트.
* **우선순위:** **Medium**

---

### 3.4 Monkeypatch 계약으로 고정된 UI 분할 한계

* **위치:**  
  - `src/ui/main_window_worker.py` (ToastWidget / WorkerThread surface)  
  - `src/ui/tabs_ai/actions.py` (AI_AVAILABLE / `__module__` 계약, budget 320줄)  
  - `tests/test_worker_structure_budget.py` 주석
* **문제:** SOLID Round 2에서도 **의도적으로** 두 표면을 단일 파일·오버라이드에 고정. 헬퍼 분리(`success.py`/`fail.py`)는 됐으나 **테스트 계약을 바꾸지 않으면** 추가 분할 불가.
* **영향:** 신규 AI UI 기능이 `actions.py`에 몰림; worker 완료 경로 변경 시 monkeypatch 테스트 동시 수정 필수. 구조 개선 속도 제한.
* **근거:** structure budget 주석; CLAUDE “의도적 유지”; CodeGraph ToastWidget 37 callers.
* **권장 수정 방향:** monkeypatch 포인트를 thin adapter로 공식화(문서+fixtures); 계약 테스트 분리 후 본체 이전.
* **우선순위:** **Medium** (구조 부채, 즉시 장애 아님)

---

### 3.5 대형 모듈 재성장 (structure budget 사각)

* **위치(라인 수 상위, 근사):**  
  - `i18n_catalogs/ko_base.py` ~906 / `en_base.py` ~899  
  - `theme/dark.py` ~467, `preview_widget/text_placement.py` ~414  
  - `annotation/textbox.py` ~409, `compare/ops.py` ~396  
  - `worker_ops/ai/ops.py` ~352, `tabs_ai/actions.py` ~304  
* **문제:** facade budget 테스트는 **shim 경로만** 제한. 실제 복잡도 파일은 budget 밖이라 SOLID 이후 다시 비대화 가능.
* **영향:** 리뷰·충돌·회귀 비용 증가. textbox/compare/AI ops 변경 시 blast radius 큼.
* **권장 수정 방향:** 본체 파일 line budget 2차 정책(예: 450줄 경고); 카탈로그 도메인 분할(basic/ai/worker).
* **우선순위:** **Medium–Low**

---

### 3.6 Worker FALLBACK_MESSAGES 이중 소스 드리프트

* **위치:** `src/core/worker_runtime/messages.py` → `FALLBACK_MESSAGES` (한국어 고정 대량)  
  정상 경로: `tm.get` via i18n catalogs
* **문제:** i18n 실패 시에만 쓰이지만, **신규 키를 카탈로그만 추가하고 FALLBACK을 안 맞추면** 폴백 시 raw key 노출 또는 구식 문구. 반대로 FALLBACK만 갱신하면 EN 환경 폴백이 한글.
* **영향:** 희귀 경로(i18n import 실패·테스트 고립) UX 저하; 유지보수 이중 부담.
* **권장 수정 방향:** FALLBACK을 최소 에러 키만 유지하거나 EN 단일 폴백으로 통일; 키 존재 스모크 테스트 확장.
* **우선순위:** **Low–Medium**

---

### 3.7 PyMuPDF 미설치 시 기동 UX 공백

* **위치:** `src/core/optional_deps.py` → `FITZ_AVAILABLE` / `_MissingFitzProxy`  
  `main.py` — FITZ 사전 검사 없음
* **문제:** 앱은 기동 가능하나 첫 PDF 작업에서 `ModuleNotFoundError` 성격의 proxy 예외. 사용자 친화 안내 다이얼로그 없음.
* **영향:** dev/부분 설치 환경에서 불친절 실패. 정식 EXE에는 fitz 포함 가정.
* **권장 수정 방향:** `main()`에서 `FITZ_AVAILABLE` False면 모달 안내 후 종료 또는 읽기 전용 배너.
* **우선순위:** **Low** (배포 EXE 경로에서는 낮음)

---

### 3.8 Undo 대용량 백업 I/O 비용

* **위치:** `run_worker` → `_create_backup_for_undo` (full file copy)  
  한도: `UNDO_BACKUP_MAX_SIZE_MB`, age cleanup
* **문제:** 수 GB PDF 연속 편집 시 temp 디스크·시작 정리 비용. 한도·정리는 있으나 **복사 자체 비용**은 큼.
* **영향:** 대용량 문서 UX 지연; temp 디스크 압박 (한도 초과 시 오래된 백업 삭제).
* **권장 수정 방향:** 대용량 시 undo 스킵+경고, hardlink/reflink 가능 시 사용, 사용자 설정 “Undo 비활성”.
* **우선순위:** **Low–Medium** (추정 부하, 코드상 전체 복사 확인)

---

### 3.9 (Low) 썸네일 pixmap 메모리 · 배치 크기

* **위치:** `ThumbnailLoaderThread` — 페이지별 `QPixmap` emit, batch `_MAX_BATCH_SIZE=64`
* **문제:** 페이지 많은 PDF에서 썸네일 위젯·pixmap 누적. loader wait는 1s로 개선됨.
* **영향:** 저메모리 환경 스크롤 시 압력. (추정: 실제 OOM 재현은 미실시)
* **권장 수정 방향:** LRU 타일 캐시, 화면 밖 pixmap 해제 정책.
* **우선순위:** **Low** (추정 포함)

---

## 4. Potential Functional / Quality Gaps

### 4.1 확인된 갭

| 갭 | 설명 |
|----|------|
| closeEvent ↔ AI shutdown 비연동 | atexit 의존, text cache 미청소 (§3.1) |
| 민감 kwargs scrub 부재 | (§3.2) |
| 정보 추출 리포트 i18n | (§3.3) |
| structure budget 본체 미적용 | (§3.5) |
| FALLBACK vs catalog 이중 관리 | (§3.6) |
| CodeGraph “no covering tests” hot path | `run_worker`, `set_ui_busy`, `preflight_inputs`, `build_safe_attachment_output_path` 등은 간접 테스트 위주 |

### 4.2 추정 갭

| 갭 | 설명 |
|----|------|
| **(추정)** 일부 extract 리포트도 한글 하드코딩 | bookmarks/search 리포트 키는 FALLBACK에 한글 — catalog 경로면 OK, 폴백 시 EN 깨짐 |
| **(추정)** QPdfDocument + fitz 이중 오픈 | preview(Qt)와 Worker(fitz) 동시 오픈으로 파일 잠금/Windows 공유 위반 엣지 |
| **(추정)** 패키징 후 OCR/Tesseract | EXE에 Tesseract 미포함 — OCR은 시스템 의존(문서화됨) |
| **(추정)** HiDPI/멀티모니터 영역 선택 | 매핑 테스트 있으나 전 환경 커버 미확인 |
| **(추정)** Linux/macOS 1급 지원 | 소스는 크로스, 패키징·smoke·explorer 폴더는 Windows 중심 |

### 4.3 Track A에서 이미 해결·잔존 한계 (재확인)

| 항목 | 상태 |
|------|------|
| 채팅 partial HTML escape | Track A 해결 |
| OCR 0성공 hard-fail | Track A 해결 |
| 첨부 path traversal | 양호 |
| AI HTTP abort | **의도적 한계** 잔존 |
| QThread.terminate | **의도적 최후 수단** 잔존 |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 (프라이버시·산출물 정확성)

1. `shutdown_executor`에서 `_text_cache` clear + `closeEvent`에서 호출.  
2. Worker finalize / cancel 시 `api_key`·`password(s)` scrub; pending 큐 저장 정책 재검토.  
3. `get_pdf_info` 섹션 문자열 i18n화.

### 2단계 — 안정성·운영

4. FITZ 미설치 기동 안내.  
5. FALLBACK_MESSAGES 축소 또는 EN 단일화 + 키 동기 스모크.  
6. Undo 대용량 정책(스킵 임계값).  
7. 패키징 문서에 OCR/Tesseract·optional extras 명시 재확인.

### 3단계 — 구조

8. monkeypatch 계약 공식 어댑터 + structure budget을 본체 모듈로 확장.  
9. `text_placement` / `compare/ops` / `ai/ops` / i18n catalog 2차 분할.  
10. `run_worker`·lifecycle 단위 테스트 fixture 공용화.  
11. 썸네일 LRU (여유 시).

---

## 6. Test Recommendations

### 6.1 즉시 추가

| 테스트 | 목적 |
|--------|------|
| `test_ai_shutdown_clears_text_cache` | shutdown 후 `_text_cache` empty |
| `test_close_event_calls_ai_shutdown` | Dummy app close → shutdown (mock) |
| `test_finalize_worker_scrubs_secrets` | kwargs에 api_key/passwords 없을 것 |
| `test_pending_worker_does_not_persist_api_key` | 또는 scrub 정책 문서화 후 검증 |
| `test_get_pdf_info_respects_locale` | EN locale 시 헤더 비한글 또는 키 기반 |

### 6.2 보강

| 테스트 | 목적 |
|--------|------|
| FALLBACK 키 ⊆ catalog 키 | 드리프트 방지 |
| structure budget 본체 후보 | textbox/compare/ai ops 상한 |
| `resource_path` frozen 분기 | monkeypatch `sys.frozen` |
| FITZ_AVAILABLE False 기동 | 스모크 메시지 |

### 6.3 유지

- `test_worker_structure_budget`, i18n smoke, AI cache, package smoke, Track A audit follow-ups

### 6.4 검증 커맨드

```bash
python -m pyright src/core src/ui
python -m pytest -q
python main.py --smoke
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
```

---

## 7. Appendix

### 7.1 상위 라인 수 (Track B 스냅샷)

| 대략 줄 수 | 파일 |
|-----------|------|
| ~900 | `i18n_catalogs/ko_base.py`, `en_base.py` |
| ~400+ | `theme/dark.py`, `text_placement.py`, `annotation/textbox.py`, `compare/ops.py` |
| ~300+ | `ai/ops.py`, `tabs_ai/actions.py`, `main_window.py` |

### 7.2 CodeGraph 무테스트 경고 (선별)

- `run_worker`, `set_ui_busy`, `preflight_inputs`, `resource_path`, `get_message`, `build_safe_attachment_output_path`  
→ 간접 커버 가능하나 **직접 단위 테스트 부재**로 리팩터 시 회귀 탐지 지연.

### 7.3 문서 위치

| 문서 | 역할 |
|------|------|
| `PROJECT_AUDIT.md` | **Track A** 기능 구현 감사 SSOT |
| `PROJECT_AUDIT_QUALITY.md` | **Track B** 품질·아키텍처 감사 (본 문서) |

### 7.4 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-08-05 | Track B 초판 — 기능 감사와 분리한 품질 재감사 |

---

*본 문서는 코드 변경 없이 작성되었다. 수정 시 §5 순서를 권장한다.*
