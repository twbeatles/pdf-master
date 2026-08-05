# Project Audit

> 감사 기준일: **2026-08-04** (구조 분할 후속: **2026-08-05**)  
> 대상 버전: **PDF Master v4.5.6**  
> 범위: 기능 구현 관점 (예외·검증·상태/비동기·경로·설정·보안·문서 정합·테스트)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP (`codegraph_explore`), 보조 파일 열람·grep·`pytest`  
> **SSOT:** 본 파일 (`PROJECT_AUDIT.md`)이 현행 기능 감사 문서  

---

## 0b. Structure Follow-up (2026-08-05 SOLID Round 2)

기능 동작 변경 없이 **코드 분할·Host 타입·facade 대칭** 후속. 상세 설계: `docs/superpowers/specs/2026-08-05-code-split-solid-round2-design.md`.

| 영역 | 상태 |
|------|------|
| Worker `ai`/`batch`/`compose`/`form`/`security` 패키지 + `*_ops.py` facade | **완료** |
| `_pdf_helpers_impl` + facade | **완료** |
| UI textbox_impl / tab section builders / thumbnail mixins / interaction split | **완료** |
| `PreviewWidgetHost` / `ThumbnailGridHost` | **완료** (`src/core`+`src/ui` pyright 0) |
| `main_window_worker` Toast/WorkerThread monkeypatch surface | **유지** (본문 helper 분리) |
| `tabs_ai/actions.py` 단일 파일 monkeypatch 계약 | **유지** |
| public import / mode / kwargs | **불변** |

**검증:** `python -m pytest -q` 통과 (opt-in Gemini smoke skip 가능); structure budget `tests/test_worker_structure_budget.py`.

---

## 0. Implementation Follow-up (2026-08-04)

감사 §3–§5 권고 반영 상태 (코드 수정 포함).

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| High §3.1 | 배치 워터마크 CJK + 공용 `_write_textbox_content` | **해결** — `batch_ops` + `text_needs_cjk` / font auto |
| High §3.2 | i18n 테마 QSS 한글 주석 → pytest 그린 | **해결** — theme QSS 주석 영문화 |
| Medium §3.3 | AI 스트림 취소 시 stream.close 시도 | **부분** — SDK HTTP abort 불가 한계 유지, 청크 경계 cancel + stream.close |
| Medium §3.4 | 채팅 HTML 이스케이프 | **해결** |
| Medium §3.5 | AI 평문 temp 권한 (chmod + Windows icacls) | **해결** (best-effort) |
| Medium §3.6 | 페이지 범위 무효 토큰 hard-fail | **해결** |
| Medium §3.7 | 강제 종료 위험 고지 i18n | **해결** |
| Medium §3.8 | 채팅 디스크 저장 opt-out (`save_chat_histories`) | **해결** — 환경설정 메뉴 |
| Medium §3.9 | textbox 페이지 밖 rect hard-fail | **해결** |
| Low–Med §3.10 | `is_pdf_encrypted` → `bool \| None` | **해결** |
| Low §3.11 | toast-only 알림 모드 | **해결** — `notify_mode` |
| Gap | redact_area 무효 rect 부분 보고 | **해결** |
| Gap | 취소 시 pending 큐 폐기 | **해결** — `clear_pending_on_cancel` 기본 True |
| Gap | 비교 스크롤 리포트 다이얼로그 | **해결** — `compare_report.py` |
| Gap | 배치 워터마크 fontsize/opacity UI | **해결** |
| Gap | OCR optional 경로 | **해결** — `extract_text(use_ocr=…)` + 변환 탭 체크박스 + `pyproject` ocr extra 표기 |
| 단일 WM CJK | 단일 워터마크 CJK 임베드 | **해결** |

**검증:** `python -m pytest -q` — 전부 통과 (opt-in Gemini smoke skip 가능). 회귀: `tests/test_audit_2026_08_04_followup.py`.

**잔여 (의도적 한계):** Gemini SDK 수준 HTTP abort 불가; OCR은 시스템 Tesseract + PyMuPDF `get_textpage_ocr` 의존(미설치 시 네이티브 폴백/안내).

---

## 1. Executive Summary

PDF Master는 **PyQt6 UI → `run_worker` → `WorkerThread` / `worker_runtime` → `worker_ops`** 로 책임이 분리된 올인원 PDF 편집 데스크톱 앱이다. Worker 모드는 `OperationSpec` 레지스트리(약 68개)로 계약화되어 있고, preflight·원자적 저장·취소 롤백·same-path 미리보기 해제·첨부 경로 고정·API 키 keyring 우선 등 **코어 골격은 성숙**하다.

2026-08-03 감사에서 High로 잡힌 텍스트 상자 플래그/busy 가드/큐 경로/redact hard-fail 등은 **코드상 후속 반영이 확인**된다. 이번 전수 감사에서 **원격 RCE·무인증 파일 탈출 같은 Critical 보안 구멍은 확인되지 않았다.**

다만 아래가 남아 있다.

| 구분 | 평가 |
|------|------|
| **전체 위험도** | **Medium** (코어 안정, 경계 기능·검증 게이트·취소/네트워크에 잔여 이슈) |
| Critical | **없음** |
| High | 배치 워터마크 CJK 미지원(한글 제품 회귀), 릴리스 검증 게이트(`pytest`) 1건 실패 |
| Medium | AI 취소의 HTTP 미중단, 채팅 HTML 미이스케이프, 평문 AI temp, 페이지 범위 침묵 무시, 종료 시 `QThread.terminate`, 채팅 기록 평문 설정 저장 등 |
| Low | 성공 toast+모달 이중 알림, Esc/포커스 잔여 UX, compare 리포트 UI 한계 |

### 핵심 문제 (요약)

1. **배치 워터마크가 `fontname="helv"` 고정** — 한글/CJK 워터마크가 비거나 깨질 수 있다 (단일 텍스트 워터마크·텍스트 상자 경로와 불일치).  
2. **`python -m pytest -q` 기준선이 현재 깨져 있다** — `test_i18n_ui_hardcoded_smoke`가 테마 QSS 한글 주석을 위반으로 잡음.  
3. **AI 작업 취소는 청크 경계/`cancel_check`에만 의존** — 진행 중 `generate_content` / 스트림 HTTP를 끊지 못해 네트워크 대기 체감이 남는다.  
4. **AI 채팅 UI가 사용자·모델 텍스트를 HTML로 그대로 `append`** — 마크업 주입·레이아웃 오염 가능.  
5. **암호화 PDF AI 경로의 임시 평문 PDF** — 기능상 필요하나 Windows temp ACL·잔존 파일이 보안 잔여 위험.

---

## 2. Project Understanding

### 2.1 목적 (README / CLAUDE)

| 항목 | 내용 |
|------|------|
| 제품 | 올인원 PDF 편집 데스크톱 (병합·변환·페이지·보안·주석·추출·배치·AI) |
| 스택 | Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai` / `keyring`, PyInstaller |
| 버전 | v4.5.6 |
| 배포 | Windows EXE 중심 (`dist/PDF_Master_v4.5.6.exe`), 소스는 크로스 실행 가능 |
| 검증 SSOT | `PROJECT_AUDIT.md` + `python -m pyright` / `pytest` / `main.py --smoke` / `package_smoke.ps1` |

### 2.2 아키텍처 개요

```
main.py
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_worker / window_undo
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()   ← UI 진입 단일 게이트 (~69 callers)
            ├─ busy 가드 + _pending_workers FIFO (상한 8)
            ├─ same-path 시 미리보기 close → Worker → restore
            ├─ preview passwords 주입 (_augment_worker_passwords_from_preview)
            └─ WorkerThread.run → worker_runtime
                 ├─ normalize kwargs → preflight_inputs → handler dispatch
                 └─ worker_ops/*
                      annotation / extract / cleanup / page / transform / compare
                      compose / security / batch / form / ai
```

### 2.3 CodeGraph 기반 실행 흐름·영향 범위

| 심볼 | 역할 | 영향 범위 (CodeGraph) |
|------|------|------------------------|
| `run_worker` (`main_window_worker.py`) | 모든 탭 작업 진입, 큐·Undo 스냅샷·시그널 연결 | 다수 UI 탭 actions (merge/convert/markup/AI 등) |
| `WorkerThread.run` → `WorkerRuntimeMixin.run` | preflight + handler 호출 + 예외→error/cancelled 매핑 | 전 Worker 모드 |
| `set_ui_busy` (`lifecycle.py`) | 탭·단축키·Open·텍스트상자/포커스/전체화면 버튼 비활성 | 중복 `run_worker` 방지 |
| `insert_textbox` / `insert_textboxes` / `replace_text_in_rect` | 위치 텍스트·큐·영역 교체 | UI markup + 배치 워터마크(간접) + 테스트 회귀 |
| `redact_area` | 좌표 교정 | Advanced UI + `test_worker_pymupdf_extras` |
| `ask_about_pdf` / AI ops | Gemini File API·스트림·cancel_check | `ai_ops` + AI 탭 |
| `WorkerExtractAttachmentsMixin` | 첨부 추출 경로 고정 | extract facade |

**동적 경계:** 모드 문자열 → `OPERATION_SPECS` → handler 메서드명 디스패치. UI 시그널은 Qt 런타임 연결.

### 2.4 안정화되어 확인된 계약 (이번 감사에서 재검증)

| 영역 | 상태 | 근거 |
|------|------|------|
| 텍스트상자 실패/취소 시 post 플래그 클리어 | 해결 | `on_fail` / `on_cancelled` → `_clear_textbox_post_flags` |
| busy 시 전체화면·포커스 바 삽입 버튼 | 해결 | `set_ui_busy` → `set_actions_enabled` / 버튼 목록 |
| 큐 `file_path` 고정·경로 불일치 거부 | 해결 | `textbox_session.py` + `markup_actions/textbox.py` |
| `replace_text_in_rect` redact 실패 hard-fail | 해결 | `textbox.py` `err_textbox_redact_failed` |
| 부분 큐 실패 메시지 | 해결 | `msg_textboxes_inserted_partial` |
| 원자적 저장 | 양호 | `atomic_*_save` + same-dir `os.replace` |
| 첨부 path traversal | 양호 | `build_safe_attachment_output_path` |
| API 키 파일 폴백 동의 | 양호 | `set_api_key(..., allow_file_fallback=)` |
| 설정 JSON 원자 저장·손상 백업 | 양호 | `_settings_impl/persistence.py` |
| README 단축키 F11/Ctrl+F11 | 문서 정합 | README 단축키 표에 반영됨 |

### 2.5 검증 실행 스냅샷 (감사 시점)

```text
python -m pytest -q
→ 1 failed: tests/test_i18n_ui_hardcoded_smoke.py::test_no_hardcoded_korean_string_literals_in_runtime_ui_files
→ 원인: src/ui/theme/dark.py · light.py QSS 문자열 내 한글 CSS 주석
→ opt-in Gemini smoke 1건 skip 가능 (기존 정책)
```

---

## 3. High-Risk Issues

### 3.1 배치 워터마크가 Base-14 `helv` 고정 — 한글 워터마크 실패

* **위치:** `src/core/worker_ops/batch_ops.py` — `WorkerBatchOpsMixin.batch` (`operation == "watermark"`)  
* **문제:** 페이지마다 `page.insert_textbox(..., fontname="helv", ...)` 만 호출한다. 단일 파일 워터마크/텍스트 상자 경로는 CJK 임베드·폰트 해석(`_resolve_textbox_fontname` 등)을 쓰지만, **배치 경로는 그 로직을 재사용하지 않는다.**  
* **영향:** 한국어(및 기타 비라틴) 워터마크 배치 시 글자가 비거나 대체 실패 → “성공 카운트”는 올라가지만 **시각적으로 워터마크가 없는 PDF**가 나올 수 있다.  
* **근거:** `batch_ops.py` 워터마크 분기 `fontname="helv"` 하드코딩; 단일 경로 `annotation/textbox.py` 는 CJK/`insert_font` 처리.  
* **권장 수정 방향:** 배치 워터마크를 `insert_textbox`/`_write_textbox_content` 공용 헬퍼로 통합하거나, 텍스트 샘플에 따라 CJK 폰트 임베드. 회귀 테스트에 한글 워터마크 배치 1건 추가.  
* **우선순위:** **High**

---

### 3.2 릴리스 검증 게이트 실패 — i18n UI 하드코딩 스모크

* **위치:**  
  - 테스트: `tests/test_i18n_ui_hardcoded_smoke.py`  
  - 위반 파일: `src/ui/theme/dark.py`, `src/ui/theme/light.py` (QSS 삼중따옴표 문자열 내부 한글 주석)  
* **문제:** 런타임 UI 문자열 스모크가 **스타일시트 주석의 한글**까지 상수 문자열로 탐지한다. `styles.py` 만 제외 목록에 있고 `theme/*` 는 제외되지 않았다.  
* **영향:** README/CLAUDE가 가리키는 `python -m pytest -q` 기준선이 **현재 실패**한다. 기능 회귀가 아니어도 릴리스·CI 게이트가 막힌다.  
* **근거:** 감사 시점 `pytest` 1 failed; AST Constant 값이 멀티라인 QSS 전체를 잡고 lineno=3 으로 보고.  
* **권장 수정 방향:** (A) QSS 주석 영문화 또는 제거, 또는 (B) `theme/dark.py`·`light.py`를 allowlist에 추가하되 “주석만” 허용 정책을 문서화. 수정 후 전체 pytest 재확인.  
* **우선순위:** **High** (품질 게이트 / 문서 정합)

---

### 3.3 AI 취소가 SDK HTTP 요청을 중단하지 못함

* **위치:**  
  - `src/core/ai/generation.py` — `_stream_generate_content` / `_generate_content`  
  - `src/core/worker_ops/ai_ops.py` — `cancel_check=self._check_cancelled`  
  - UI: `lifecycle._on_worker_cancelled` (AI 모드 시 네트워크 대기 문구)  
* **문제:** 스트림은 **청크 사이**에서만 `cancel_check`를 호출한다. non-stream `generate_content` 는 호출 **전후**만 검사한다. HTTP 소켓 abort / client close 가 없다.  
* **영향:** 사용자가 취소해도 네트워크·타임아웃 동안 Worker/오버레이가 남을 수 있다. cooperative cancel 설계와 사용자 기대(“즉시 중단”) 간 갭. CLAUDE/로드맵에도 SDK-level abort 잔여로 기재.  
* **근거:** `for chunk in generate_content_stream(...): self._run_cancel_check(...)` 패턴; 스트림 iterator 자체를 끊는 코드 없음.  
* **권장 수정 방향:** SDK/HTTP 클라이언트 레벨 취소 토큰 조사 후 연동; 불가 시 타임아웃 단축 + UI에 “네트워크 응답 대기 중” 고지 강화 + 강제 종료 시 temp 정리(이미 일부 존재).  
* **우선순위:** **Medium** (기능 갭 + UX; 데이터 손상 직접 원인은 아님)

---

### 3.4 AI 채팅 히스토리 HTML 미이스케이프

* **위치:** `src/ui/tabs_ai/actions.py` — 질문/응답 `txt_chat_history.append(f"... {question}")` / assistant 동일; `_load_chat_history_for_path`  
* **문제:** `QTextEdit.append` 는 rich text로 HTML을 해석할 수 있다. 사용자 입력·모델 출력의 `<`, `>` 등을 이스케이프하지 않는다.  
* **영향:** 악의적/우연한 HTML 태그로 UI 레이아웃 붕괴, 가짜 포맷 표시. 데스크톱이라 전형적 웹 XSS 수준은 아니나 **표시 무결성** 문제.  
* **근거:** `actions.py` 약 157–158, 193–195행 패턴; `html.escape` 사용 흔적 없음.  
* **권장 수정 방향:** `html.escape(content, quote=True)` 후 append; 또는 plain text 전용 API. 저장 형식은 plain 유지.  
* **우선순위:** **Medium**

---

### 3.5 암호화 PDF AI 처리 시 임시 평문 PDF

* **위치:** `src/core/worker_ops/ai_ops.py` — `_prepare_ai_pdf_path` (`pdf_master_ai_*` + `PDF_ENCRYPT_NONE` 저장)  
* **문제:** File API/텍스트 추출을 위해 **복호화된 임시 파일을 디스크에 생성**한다. POSIX는 `chmod 0o600` best-effort, Windows ACL 강화는 없다. 취소·종료 시 `temp_cleanup` 스윕이 있으나 크래시 타이밍 잔존 가능.  
* **영향:** 공유 PC·포렌식·백업 대상 temp에 민감 PDF 평문 잔존 위험. 기능 동작에는 필요.  
* **근거:** `mkstemp(prefix="pdf_master_ai_")` + `doc.save(..., encryption=ENCRYPT_NONE)`; finally/`_cleanup_ai_temp_path` 삭제.  
* **권장 수정 방향:** Windows 사용자-only ACL; 가능하면 메모리/스트림 업로드 경로; 종료·취소·예외 경로 삭제 이중화(이미 상당 부분 있음) 점검.  
* **우선순위:** **Medium**

---

### 3.6 페이지 범위 파서가 잘못된 토큰을 침묵 무시

* **위치:** `src/core/worker_runtime/preflight.py` — `parse_page_range`  
* **문제:** `ValueError` 토큰은 로그만 남기고 `continue`. 범위 밖 숫자는 건너뛴다. 전부 무효면 빈 리스트가 상위 모드로 전달될 수 있다(모드별 후속 처리에 의존).  
* **영향:** 사용자가 `1-3, foo, 99` 입력 시 **일부만 적용**되거나 예상과 다른 결과. 검증 실패로 보이지 않음.  
* **근거:** `except ValueError: logger.warning(...); continue` 및 범위 필터.  
* **권장 수정 방향:** 무효 토큰이 하나라도 있으면 preflight/UI에서 hard-fail 또는 경고 다이얼로그; “적용된 페이지만 진행” 시 명시 확인.  
* **우선순위:** **Medium**

---

### 3.7 앱 종료 시 `QThread.terminate()` 강제 종료

* **위치:** `src/ui/main_window.py` — `_shutdown_worker_for_close`  
* **문제:** cooperative cancel + 3초 `wait` 후에도 실행 중이면 사용자 확인 후 `worker.terminate()`. Qt/`QThread.terminate` 는 네이티브 스레드 강제 종료로 **파이썬/네이티브 락·부분 I/O 상태 불명**.  
* **영향:** 드물게 프로세스 불안정, temp 잔존(스윕으로 완화), 강제 종료 직후 파일 핸들 이슈. 원자적 `os.replace` 전 단계면 원본 보존 가능성은 높음.  
* **근거:** `worker.terminate(); worker.wait(1000)` + temp cleanup.  
* **권장 수정 방향:** terminate 전 AI/네트워크 경로 우선 완화; 가능하면 process 격리 Worker(장기); 단기에는 same-path 작업 중 강제 종료 경고 문구 강화.  
* **우선순위:** **Medium**

---

### 3.8 채팅 기록이 설정 JSON에 평문 저장

* **위치:** `src/ui/tabs_ai/storage.py` + `~/.pdf_master_settings.json` (`chat_histories`)  
* **문제:** PDF 관련 Q&A 본문이 설정 파일에 평문으로 직렬화된다. trim 정책은 있으나 암호화 없음.  
* **영향:** 동일 사용자 프로필 접근 가능 시 민감 문서 내용 유출. API 키보다는 낮은 민감도일 수 있으나 문서 내용 자체가 민감할 수 있음.  
* **근거:** `_save_chat_histories` → `settings["chat_histories"]` → `save_settings`.  
* **권장 수정 방향:** 선택적 “채팅 저장 안 함”; OS 사용자 디렉터리 권한 고지; 장기적으로 DPAPI/keyring 연동 또는 분리 파일+권한.  
* **우선순위:** **Medium** (프라이버시)

---

### 3.9 `insert_textbox` 페이지 밖 rect 침묵 폴백

* **위치:** `src/core/worker_ops/annotation/textbox.py` — `insert_textbox`  
* **문제:** 페이지와 교집합이 비면 **(50,50) 근처 기본 박스로 폴백**해 삽입한다. 사용자 지정 좌표와 다른 위치에 텍스트가 생긴다.  
* **영향:** 드래그/좌표 입력 오류 시 “성공”이지만 위치가 어긋남 — 교정·정밀 배치 UX에서 신뢰 저하.  
* **근거:** `if fitz_rect.is_empty ...: fitz_rect = fitz.Rect(50, 50, ...)`  
* **권장 수정 방향:** hard-fail + `err_textbox_rect_outside_page`; 또는 UI 단계에서 클램프 고지.  
* **우선순위:** **Medium**

---

### 3.10 `is_pdf_encrypted` 예외 시 False

* **위치:** `src/core/worker_runtime/preflight.py` — `is_pdf_encrypted`  
* **문제:** `fitz.open` 실패 시 `False` 반환. 손상·잠금 파일을 “비암호화”로 오인할 수 있다.  
* **영향:** AI/UI 분기에서 암호 프롬프트 대신 다른 오류 경로로 가서 메시지가 모호해질 수 있음.  
* **근거:** `except Exception: return False`  
* **권장 수정 방향:** 예외 시 `None`/재raise 또는 호출측에서 손상 PDF 검증과 분리.  
* **우선순위:** **Low–Medium**

---

### 3.11 성공 시 toast + 모달 이중 알림 (기능 피로)

* **위치:** `src/ui/main_window_worker.py` — `on_success`  
* **문제:** 거의 모든 성공 경로에서 `ToastWidget` 후 `QMessageBox.information` 을 띄운다(일부 custom_dialog 제외).  
* **영향:** 연속 작업·큐 처리 시 클릭 피로, 자동화 체감 저하. 데이터 오류는 아님.  
* **근거:** toast 후 `if not custom_dialog_shown: QMessageBox.information(...)`.  
* **권장 수정 방향:** 설정 옵션 “간단 알림(toast only)” 또는 모드별 정책.  
* **우선순위:** **Low**

---

## 4. Potential Functional Gaps

| 항목 | 설명 | 구분 |
|------|------|------|
| OCR / 스캔 PDF 텍스트 작업 | 하이라이트·검색·영역 교체·텍스트 compare는 텍스트 레이어 전제. README 로드맵·CLAUDE와 동일 | 알려진 제품 한계 |
| Compare 인터랙티브 리포트 UI | 결과는 `QMessageBox` 요약 중심. 대용량 diff 가독성·탐색 약함 | 기능 갭 |
| SDK-level AI HTTP abort | §3.3 과 동일 | 로드맵 잔여 |
| 배치 워터마크 옵션 빈약 | 위치·회전·불투명도·폰트가 단일 보안 탭 워터마크와 비대칭 | 기능 갭 (**추정:** UI 옵션이 배치 kwargs로 안 넘어갈 수 있음 — 코드상 option 문자열+고정 스타일만 사용) |
| 취소 후 pending 큐 자동 실행 | 현재 작업 취소 후에도 `_run_pending_worker` 가 대기 작업을 이어 실행. 종료 시에만 큐 폐기 | UX 정책 갭 (**의도일 수 있음**) |
| `same_path_restore` 정책명 | cancel_cleanup 값이 “복원”처럼 읽히나 실제 lifecycle은 **기존 출력 보존·created 삭제** 중심 | 명명/문서 갭 |
| `redact_area` 일부 무효 rect 스킵 | 전부 무효면 에러, 일부만 무효면 침묵 스킵 후 나머지 적용 | 검증 갭 |
| 썸네일 로더 실패 UX | 예외 시 로그만, 사용자 토스트 없음 | UX 갭 |
| 다중 모니터 전체화면 선택 | `showFullScreen` 기본 스크린 (**추정**) | 추정 갭 |
| 인라인 편집 중 페이지 전환 | refresh 의존; 편집 중 페이지 이동 시 박스 불일치 가능 (**추정**) | 추정 |
| 미리보기 외부 변경 reload vs Worker 쓰기 | same-path는 미리보기 close로 완화. 다른 경로 동시 쓰기 시 레이스 **추정** | 추정 |
| macOS/Linux 1급 지원 | README는 Windows EXE 중심. 소스 실행은 가능하나 패키징·키링·경로 검증 범위는 Windows 편향 | 플랫폼 갭 |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 (데이터 무결성·검증 게이트·한글 핵심 경로)

1. **배치 워터마크 CJK/공용 텍스트 삽입 경로 통합** (§3.1) + 한글 배치 회귀 테스트.  
2. **i18n UI 스모크 실패 해소** (§3.2) — 테마 QSS 주석 정리 또는 allowlist; `pytest -q` 그린 복구.  
3. (여력 시) **`insert_textbox` 페이지 밖 rect hard-fail** (§3.9) — 잘못된 위치 “성공” 방지.

### 2단계 — 안정성·보안·입력 검증

4. AI 채팅 **HTML 이스케이프** (§3.4).  
5. 페이지 범위 **무효 토큰 hard-fail/경고** (§3.6); `redact_area` 부분 무효 보고.  
6. AI temp **Windows ACL·삭제 경로 재점검** (§3.5).  
7. `is_pdf_encrypted` 예외 의미 분리 (§3.10).  
8. 종료 강제 terminate 경고/정책 문서화 및 가능 시 완화 (§3.7).  
9. 채팅 저장 opt-out 또는 민감 고지 (§3.8).

### 3단계 — 구조·제품 로드맵

10. AI SDK/HTTP **진짜 abort** (§3.3).  
11. Compare 리포트 전용 뷰어(페이지 네비·필터).  
12. OCR optional extra (패키징 설계 후).  
13. 성공 알림 정책(toast-only 옵션) (§3.11).  
14. 배치 워터마크 UI 옵션을 단일 워터마크와 패리티.  
15. cancel 시 pending 큐 폐기 여부 사용자 선택.

---

## 6. Test Recommendations

### 6.1 즉시 추가·수정

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_batch_watermark_cjk` | 한글 워터마크 배치 후 페이지 텍스트/렌더에 글리프 존재 (또는 font embed) |
| `test_i18n_theme_qss_allowlist` / 수정 후 기존 스모크 | theme QSS 주석 정책 확정 후 `test_i18n_ui_hardcoded_smoke` 그린 |
| `test_chat_history_html_escaped` | `<b>x</b>` 질문이 태그로 해석되지 않고 이스케이프되어 표시 |
| `test_parse_page_range_invalid_token_rejected` | (정책 변경 후) `1, foo` preflight/handler 실패 |
| `test_insert_textbox_outside_page_fails` | (정책 변경 후) 페이지 밖 rect → error_signal, 파일 미변경 |

### 6.2 보강 권장

| 테스트 | 검증 내용 |
|--------|-----------|
| AI cancel mid-stream | fake SDK generator 중간에 cancel → `CancelledError`, finished 미발행 (기존 cancel 테스트 확장) |
| AI encrypted temp cleanup | 성공/실패/취소 후 `pdf_master_ai_*` 부재 |
| Force close while worker | `_shutdown_worker_for_close` 분기 (기존 `test_close_shutdown_flow` 확장) |
| Pending queue after cancel | 취소 후 대기 작업 실행/폐기 정책 고정 후 회귀 |
| redact_area partial invalid | 일부 잘못된 rect 스킵 시 payload/메시지 |
| 암호 PDF 배치 | 암호 없는 배치 파일이 failed_files에 사유 포함 |

### 6.3 기존 커버리지 (양호)

- Worker preflight / cancel / batch fail-fast / attachment path / same-path restore  
- AI cache·encrypted unlock·chat cancel_check 전파  
- 텍스트 상자 큐·교체·감사 후속 (`test_textbox_audit_followup.py` 등)  
- 구조 예산·i18n 키 양언어·encoding audit  

**갭:** 배치 CJK, 채팅 HTML, 페이지 범위 엄격 검증, 테마 파일 i18n 스모크 정책, AI HTTP abort(통합은 mock 한계).

---

## 부록 A. 문서·구현 정합

| 출처 | 상태 |
|------|------|
| CLAUDE.md Current Behavior / 아키텍처 | 구현과 **일치** (SOLID Round 1–2, textbox, focus, cancel 정책, Host 타입) |
| README / README_EN 변경 이력 | **2026-08-05 SOLID Round 2** 반영 |
| GEMINI.md / `pdf_master.spec` 주석 | Round 2 패키지·검증 경로 반영 |
| README/CLAUDE `pytest -q` 그린 기준선 | **정합** — 2026-08-04 §3.2 테마 QSS 이슈 해결 후 그린 유지 |
| OCR 경로 | optional `use_ocr` 구현 반영; SDK-level AI HTTP abort는 잔여 |
| `cancel_cleanup=same_path_restore` 명칭 | 문서/스펙 이름이 “복원”을 암시하나 구현은 보존 중심 — **부분 불일치** |
| `.gitignore` `specs/` | 루트 전용 `/specs/` 로 수정 — `docs/superpowers/specs/` 설계 문서 추적 가능 |

---

## 부록 B. 이전 감사(2026-08-03) 후속 상태

| 당시 이슈 | 상태 |
|-----------|------|
| 텍스트상자 post 플래그 실패 잔존 | **해결** |
| 전체화면 busy 우회 | **해결** |
| 큐 file_path 드리프트 | **해결** |
| replace redact 실패 후 insert | **해결** |
| FocusOut / F11 / same-path 확인 / 부분 실패 메시지 / 큐 고스트 | **해결 또는 개선** |
| 영역 추출 Worker | **해결** (`extract_text_in_rect`) |

---

## 부록 C. CodeGraph blast radius 요약

| 심볼 | 비고 |
|------|------|
| `run_worker` | UI 전역 게이트; 변경 시 전 탭 회귀 필요 |
| `WorkerRuntimeMixin.run` / preflight | 전 모드 공통 실패 경로 |
| `batch` | 4 operation; 워터마크 경로가 단일 삽입 스택과 분리된 것이 핵심 리스크 |
| `ai_ops` / `generation` | 취소·temp·File API 보안 경계 |
| `atomic_pdf_save` | same-path·취소 롤백 신뢰의 중심 |

---

*이 문서는 2026-08-04 코드 스냅샷 기준 기능 감사이다. 구현 수정은 포함하지 않는다.*
