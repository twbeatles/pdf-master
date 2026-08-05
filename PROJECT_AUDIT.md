# Project Audit

> 감사 기준일: **2026-08-05**  
> 대상 버전: **PDF Master v4.5.6**  
> 범위: 기능 구현 관점 (예외·검증·상태/비동기·경로·설정·보안·문서 정합·테스트)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP (`codegraph_explore`), 보조 파일 열람·grep·`pytest`  
> **SSOT:** 본 파일 (`PROJECT_AUDIT.md`)이 **기능 구현(Track A)** 감사 문서  
> **연관:** 품질·아키텍처·성능·패키징 재감사 → [`PROJECT_AUDIT_QUALITY.md`](PROJECT_AUDIT_QUALITY.md) (Track B)

---

## 0. Follow-up Status

| 시기 | 내용 | 상태 |
|------|------|------|
| 2026-08-04 | 배치 CJK, 페이지 범위 hard-fail, textbox 경계, chat 최종 HTML escape, ACL, OCR 경로, notify/save_chat 설정 등 | **해결** (`tests/test_audit_2026_08_04_followup.py`) |
| 2026-08-05 | SOLID Round 2 (Worker/UI 패키지 분할, Host 타입) | **완료** — public import·mode/kwargs 불변 |
| 2026-08-05 | **잔여 감사 이슈 구현** (§3.1–3.9) | **해결** (`tests/test_audit_2026_08_05_followup.py`) |

### 0b. 2026-08-05 Residual Implementation

| 항목 | 상태 |
|------|------|
| §3.1 채팅 partial HTML escape + cancel 중 partial 차단 | **해결** |
| §3.2 `_is_pdf_encrypted` → `bool \| None` 삼상 | **해결** |
| §3.3 OCR 0성공 hard-fail + 부분 폴백 메시지 | **해결** |
| §3.4 요약/채팅 공용 `_consume_stream_chunks` (cancel close) | **해결** |
| §3.5 강제 종료 mode 로그 + 스윕 removed 카운트 | **해결** |
| §3.6 채팅 디스크 저장 tip/toast 프라이버시 안내 | **해결** |
| §3.7 AI temp ACL 실패 meta·완료 메시지 가시화 | **해결** |
| §3.8 썸네일 로더 wait `THUMBNAIL_LOADER_WAIT_MS=1000` | **해결** |
| §3.9 첨부 `MAX_ATTACHMENT_SIZE` 100MB + preflight | **해결** |
| OCR 체크박스 `tip_extract_ocr` / CLAUDE bullet | **해결** |

**의도적 한계(잔존):** Gemini SDK HTTP abort 불가 — 청크 경계 cancel + `stream.close` best-effort.

**구현 후 검증:**

```text
python -m pyright (변경 모듈) → 0 errors
python -m pytest -q → exit 0 (opt-in Gemini smoke skip 가능)
```

---

## 1. Executive Summary

PDF Master는 **PyQt6 UI → `run_worker` → `WorkerThread` / `worker_runtime` → `worker_ops`** 구조의 올인원 PDF 편집 앱이다. preflight·원자적 저장·취소 롤백·첨부 경로 고정·keyring API 키 등 코어는 성숙하다. **Critical 보안 구멍은 확인되지 않았다.**

2026-08-05 감사에서 잡은 High/Medium 잔여 이슈는 **동일 일자 후속 구현으로 반영**되었다.

| 구분 | 평가 (구현 후) |
|------|------|
| **전체 위험도** | **Low** |
| Critical / High | **없음** |
| Medium (의도적 한계) | AI HTTP abort 불가, 강제 `terminate` 최후 수단, 채팅 평문 디스크(opt-out+안내) |
| Low | 첨부 메모리 적재(100MB 상한으로 완화) |

### 잔존 한계 (의도적)

1. AI 취소는 청크/`cancel_check` 경계 — SDK abort 없음.  
2. 종료 시 사용자 확인 후 `worker.terminate()` + temp 스윕.  
3. 채팅 디스크 평문 저장 기본 ON — 환경설정에서 해제 가능.

---

## 2. Project Understanding

### 2.1 목적 (README / CLAUDE)

| 항목 | 내용 |
|------|------|
| 제품 | 올인원 PDF 편집 데스크톱 (병합·변환·페이지·보안·주석·추출·배치·AI·미리보기) |
| 스택 | Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai` / `keyring` / OCR(Tesseract), PyInstaller |
| 버전 | v4.5.6 |
| 배포 | Windows EXE 중심 (`dist/PDF_Master_v4.5.6.exe`); 소스는 크로스 실행 가능 |
| 검증 | `pyright`, `pytest`, `main.py --smoke`, `scripts/package_smoke.ps1` |
| 기능 감사 SSOT | 본 `PROJECT_AUDIT.md` |

### 2.2 아키텍처 개요

```
main.py
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_worker / window_undo
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()   ← UI 진입 단일 게이트
            ├─ busy 가드 + _pending_workers FIFO (상한 8)
            ├─ same-path 시 미리보기 close → Worker → restore
            ├─ preview passwords 주입
            └─ WorkerThread.run → WorkerRuntimeMixin.run
                 ├─ normalize kwargs → preflight_inputs → handler dispatch
                 └─ worker_ops/*
                      annotation / extract / cleanup / page / transform / compare
                      compose / security / batch / form / ai
```

SOLID Round 2 이후 대형 파일은 도메인 패키지 + thin facade(`*_ops.py`, `zoomable_preview.py` 등)로 유지되며, **public import 경로·Worker mode 이름·kwargs 계약은 불변**이다.

### 2.3 주요 실행 흐름 (CodeGraph)

| 심볼 | 역할 | 영향 범위 (CodeGraph) |
|------|------|------------------------|
| `run_worker` (`main_window_worker.py`) | 탭 작업 진입, 큐·Undo 스냅샷·시그널 연결 | UI 탭 actions 다수 (~69 callers) |
| `WorkerThread` + `WorkerRuntimeMixin.run` | preflight + handler + CancelledError/예외 매핑 | 전 Worker 모드 |
| `OPERATION_SPECS` / `preflight_inputs` | 모드 계약·필수 kwargs·PDF/헤더 검증 | dispatch 전 fail-fast |
| `set_ui_busy` / `_enqueue_pending_worker` | busy 중 탭·단축키 비활성, 대기 큐 | 중복 실행·레이스 완화 |
| `on_success` / `on_fail` / `on_cancelled` | sender 가드, preview 복원, textbox/AI 플래그 클리어 | 전 UI 완료 경로 |
| `insert_textbox` / `insert_textboxes` / `replace_text_in_rect` | 위치 텍스트·큐·영역 교체 | Advanced UI + 배치 워터마크(간접) |
| `extract_attachments` + `build_safe_attachment_output_path` | 첨부 추출 경로 고정 | path traversal 방어 |
| `ask_about_pdf` / AI ops `_prepare_ai_pdf_path` | Gemini + 암호 PDF 임시 복호 | AI 탭 |
| `_shutdown_worker_for_close` | 종료 시 cancel → wait → 선택적 terminate | 앱 종료 안전성 |

**동적 경계:** mode 문자열 → `OPERATION_SPECS` → handler 메서드명 getattr. UI 시그널은 Qt 런타임 연결.

### 2.4 안정화되어 재확인된 계약

| 영역 | 상태 | 근거 |
|------|------|------|
| 원자적 PDF/바이너리 저장 | 양호 | `atomic_pdf_save` / `os.replace` + cancel 체크 |
| 첨부 path traversal | 양호 | `sanitize` + `commonpath` 강제 |
| API 키 keyring + 파일 폴백 동의 | 양호 | `set_api_key(..., allow_file_fallback=)` |
| 설정 JSON 원자 저장 | 양호 | `_settings_impl/persistence.py` |
| 배치 워터마크 CJK | 해결 | `text_needs_cjk` + `_write_textbox_content` |
| 페이지 범위 무효 토큰 | 해결 | hard-fail + 테스트 |
| textbox 페이지 밖 rect | 해결 | `err_textbox_rect_outside_page` |
| 채팅 **최종** HTML 이스케이프 | 해결 | `tabs_ai/actions.py`, `success.py` |
| 취소 시 pending 큐 폐기 | 해결 | `clear_pending_on_cancel` 기본 True |
| 썸네일 stale sender 가드 | 양호 | `_is_active_loader_sender` |
| Worker/UI 시그널 sender 가드 | 양호 | progress/success/fail/cancel/partial |

### 2.5 README / CLAUDE vs 구현 정합

| 항목 | 문서 | 구현 | 정합 |
|------|------|------|------|
| OCR 텍스트 추출 | README 표기 | `extract_text(use_ocr=…)` + Tesseract 의존 | **정합** (실패 UX는 §3.3 잔여) |
| F11 / Ctrl+F11 포커스·전체화면 | README 단축키 | `window_preview/focus.py` 등 | **정합** |
| 미리보기 드래그 교정/텍스트 상자 | README | region_select + text_placement | **정합** |
| 기능 감사 SSOT | README → `PROJECT_AUDIT.md` | 본 파일 | **정합** |
| CLAUDE 구 Addendum “OCR out of scope” | 일부 과거 문단 | OCR 경로 존재 | **구 문단 잔존** — Current Behavior/README 우선 |
| `_is_pdf_encrypted` 반환 타입 | `_typing.py` `bool\|None` | mixin은 `bool`만 | **타입/계약 불일치** (§3.2) |

---

## 3. High-Risk Issues

> Critical 없음. 아래는 **실제 코드 근거**가 있는 잔여 이슈만 수록.  
> 우선순위: Critical / High / Medium / Low

### 3.1 채팅 스트리밍 partial HTML 미이스케이프

* **위치:** `src/ui/main_window_worker.py` → `MainWindowWorkerMixin._on_partial_result`  
* **문제:** 채팅 스트림 중 partial 텍스트를 HTML 위젯에 **escape 없이** 삽입한다. 최종 성공 경로(`success.py`)와 히스토리 로드(`tabs_ai/actions.py`)는 `html.escape`를 사용한다.
* **영향:** 모델/스트림 청크에 `<`, `>`, 태그성 문자열이 포함되면 레이아웃 오염·의도치 않은 HTML 해석. (데스크톱 로컬 UI이므로 전형적 원격 XSS는 아니나, **스트리밍 UX와 최종 결과 불일치** 및 표시 깨짐.)
* **근거:**
  ```python
  # main_window_worker.py (partial — escape 없음)
  _replace_last_chat_block(
      self.txt_chat_history,
      f"<b>{tm.get('chat_assistant_prefix')}</b> {self._chat_partial_text}",
  )
  # success.py / actions.py — escape 있음
  _html.escape(answer, quote=True)
  html.escape(content, quote=True)
  ```
* **권장 수정 방향:** partial 누적본을 `html.escape(..., quote=True)` 후 표시. 공용 헬퍼로 성공/partial/히스토리 경로 통일.
* **우선순위:** **High**

---

### 3.2 Worker `_is_pdf_encrypted`가 `None`을 `False`로 붕괴

* **위치:**  
  - `src/core/worker_runtime/mixin.py` → `WorkerRuntimeMixin._is_pdf_encrypted`  
  - 소비: `src/core/worker_ops/ai/ops.py` → `_prepare_ai_pdf_path`  
  - 공용 함수: `src/core/worker_runtime/preflight.py` → `is_pdf_encrypted` (`bool | None`)  
  - 타입 계약: `src/core/_typing.py` (`bool | None` 선언)
* **문제:** 믹스인 구현이 `return is_pdf_encrypted(file_path) is True` 로 **`None`(probe 실패)을 `False`로 취급**한다. AI 준비 경로의 `if enc is None: … err_pdf_corrupted` 분기는 **도달 불가(dead branch)**.
* **영향:** 손상·권한·일시 열기 실패 PDF를 “비암호화”로 간주하고 AI File API/추출 경로에 넘김. 의도한 조기 fail-fast가 무력화되고, 오류 메시지가 모호해질 수 있다.
* **근거:**
  ```python
  # mixin.py
  def _is_pdf_encrypted(self, file_path: str) -> bool:
      return is_pdf_encrypted(file_path) is True

  # ai/ops.py
  enc = self._is_pdf_encrypted(file_path)
  if enc is False:
      return file_path, None
  if enc is None:  # 현재 구현에서는 도달 불가
      self.error_signal.emit(self._get_msg("err_pdf_corrupted"))
      return None, None
  ```
  테스트 `test_is_pdf_encrypted_unknown_returns_none`는 **공용 함수**만 검증하고 믹스인 래퍼는 미검증.
* **권장 수정 방향:** 믹스인이 `bool | None`을 그대로 반환. AI/기타 호출부 계약을 재정렬. 회귀 테스트에 믹스인 경로 추가.
* **우선순위:** **Medium**

---

### 3.3 OCR 전면 실패 시 hard-fail 경로 사문화

* **위치:** `src/core/worker_ops/extract/text_info.py` → `WorkerExtractTextInfoMixin.extract_text`
* **문제:** `use_ocr` 시 페이지 루프 진입 직후 `any_ocr_used = True`로 설정한다. 이후 `err_ocr_unavailable` 조건(`use_ocr and ocr_hard_fail and not any_ocr_used`)은 **논리적으로 도달 불가**. Tesseract/PyMuPDF OCR 부재 시에도 네이티브 폴백만 남기고 “완료”로 끝날 수 있다.
* **영향:** 사용자가 OCR을 켰는데 실제 OCR이 전혀 동작하지 않아도 성공으로 인지. 스캔본에서 빈/부실 텍스트 산출.
* **근거:**
  ```python
  if use_ocr:
      any_ocr_used = True  # 성공 전에 설정
      try:
          ...
      except Exception as exc:
          ocr_hard_fail = str(exc)
          text_chunks.append(page.get_text() or "")
  ...
  if use_ocr and ocr_hard_fail and not any_ocr_used:  # dead
      self.error_signal.emit(self._get_msg("err_ocr_unavailable", ...))
  ```
* **권장 수정 방향:** OCR **성공 페이지 수**를 별도 카운트. 0성공+하드 실패면 `err_ocr_unavailable` hard-fail 또는 명확한 “전부 폴백” 경고 payload/UI.
* **우선순위:** **Medium**

---

### 3.4 AI 작업 취소 — HTTP 미중단 + 채팅 스트림 close 부재

* **위치:**  
  - `src/core/ai/generation.py` → `_stream_generate_content` (청크 경계 cancel + `stream.close` 시도)  
  - `src/core/ai/service.py` → `ask_about_pdf` (`chat.send_message_stream` 루프, close 없음)  
  - `src/core/ai/generation.py` → `_generate_content` (호출 전후 cancel만)  
  - UI: `lifecycle.py` → `_on_worker_cancelled` (네트워크 취소 안내)
* **문제:** 취소는 cooperative `cancel_check`에만 의존. 진행 중 `generate_content` / stream 소비 중에는 즉시 끊기지 않는다. 요약 스트림은 cancel 시 `stream.close`를 best-effort로 시도하나, **채팅 `send_message_stream` 경로는 close 시도가 없다.**
* **영향:** 취소 후에도 네트워크·CPU 점유 지속, UI “취소 중” 체감 지연. (SDK 한계로 완전 해결은 어려움.)
* **근거:** generation.py 주석 `# 청크 경계에서만 취소 가능 — SDK HTTP abort 미지원`; chat 스트림 루프에 close 없음.
* **권장 수정 방향:** chat 스트림도 동일 close 패턴 적용; cancel 시 더 이상 partial UI 갱신 금지; (장기) SDK abort/timeout 옵션 조사.
* **우선순위:** **Medium** (의도적 한계 + 개선 여지)

---

### 3.5 앱 종료 시 `QThread.terminate()`

* **위치:** `src/ui/main_window.py` → `_shutdown_worker_for_close`
* **문제:** cancel 후 3초 대기 실패 시 사용자 확인 후 `worker.terminate()` + 1초 wait. 네이티브 강제 종료는 파일 핸들·Python 상태를 불명하게 남길 수 있다.
* **영향:** 드물지만 손상 출력·잠긴 파일·좀비 리소스. 현재는 i18n 위험 고지 + `cleanup_pdf_master_temp_files(include_in_progress=True)` 로 완화.
* **근거:** `worker.terminate()` 주석 및 temp 스윕 코드.
* **권장 수정 방향:** terminate 전 “출력 미보장” 강화 문구 유지; 가능하면 장시간 AI/배치만 terminate 허용; 강제 종료 후 추가 orphan 스윕 로그.
* **우선순위:** **Medium** (의도적 최후 수단, 잔여 위험)

---

### 3.6 채팅 히스토리 평문 설정 파일 저장

* **위치:** `src/ui/tabs_ai/storage.py` → `_save_chat_histories`  
  설정: `save_chat_histories` (기본 True)
* **문제:** PDF 경로 키와 질의/응답 본문이 `~/.pdf_master_settings.json`에 평문으로 남을 수 있다. opt-out 설정은 존재.
* **영향:** 공유 PC·백업·로그 유출 시 문서 내용 추론 가능. API 키와 별개 프라이버시 이슈.
* **근거:** `settings["chat_histories"] = self._chat_histories` 후 `save_settings`.
* **권장 수정 방향:** 기본값을 보수적으로 검토하거나, 저장 시 경고/마스킹/별도 암호화 파일. README에 저장 위치·opt-out 명시 강화.
* **우선순위:** **Medium** (설정으로 완화 가능)

---

### 3.7 암호화 PDF AI 임시 평문 파일

* **위치:** `src/core/worker_ops/ai/ops.py` → `_prepare_ai_pdf_path`, `_restrict_temp_file_permissions`, `_cleanup_ai_temp_path`  
  보조: `src/core/temp_cleanup.py`
* **문제:** File API용으로 비암호화 임시 PDF를 temp에 생성. chmod 0o600 + Windows icacls best-effort, 완료/취소/종료 시 스윕. 강제 종료·스윕 실패 시 평문 잔존 가능.
* **영향:** 민감 문서의 로컬 평문 사본 노출 창(시간 제한·ACL로 완화).
* **근거:** `tempfile.mkstemp(prefix="pdf_master_ai_")` + save ENCRYPT_NONE.
* **권장 수정 방향:** 현재 완화 유지; 실패 시 사용자 가시 경고; 가능하면 메모리 경로/짧은 삭제 정책 강화.
* **우선순위:** **Low–Medium** (기능 필수 + 잔여 위험)

---

### 3.8 (Low) 썸네일 로더 짧은 wait / 백그라운드 잔존

* **위치:** `src/ui/thumbnail/grid_loading.py` → `_cleanup_loader_thread` (wait 300ms)
* **문제:** 로더가 300ms 내 안 끝나면 백그라운드 정지로 두고 진행. sender 가드로 UI 오염은 막음.
* **영향:** 대용량 PDF 빠른 전환 시 짧은 중복 디스크 I/O·스레드 잔존. 기능 오류 가능성은 낮음.
* **권장 수정 방향:** wait 상한 조정 또는 finished 후 일괄 deleteLater 정책 문서화.
* **우선순위:** **Low**

---

### 3.9 (Low) 첨부 파일 전체 메모리 적재

* **위치:** `src/core/worker_ops/extract/attachments.py` → `add_attachment`
* **문제:** `open(attach_path, "rb").read()`로 전체를 메모리에 적재. preflight는 `MAX_FILE_SIZE`(2GB)까지 허용.
* **영향:** 초대형 첨부 시 메모리 압박·UI 정체.
* **권장 수정 방향:** 첨부 전용 더 낮은 상한 또는 스트리밍 embfile API 사용(지원 시).
* **우선순위:** **Low**

---

## 4. Potential Functional Gaps

> 확실하지 않은 항목은 **(추정)** 표기.

### 4.1 확인된 보완 지점

| 갭 | 설명 |
|----|------|
| Chat partial escape 통일 | §3.1 — 최종/히스토리와 partial 불일치 |
| 암호화 probe 삼상 논리 | §3.2 — AI 조기 실패 의도 미구현 |
| OCR 실패 UX | §3.3 — hard-fail/명확 경고 부족 |
| Chat 스트림 cancel close | §3.4 — 요약 스트림과 비대칭 |
| OCR 품질/엔진 안내 | README는 Tesseract 필요를 말하지만, UI에서 미설치 시 사전 점검(추정: 체크박스만 있을 수 있음) |
| 비교 리포트 고도화 | 스크롤 리포트는 존재; 인터랙티브 diff UI는 로드맵 잔여(문서/CLAUDE) |
| Gemini 실연동 테스트 | opt-in smoke 1건 — CI 기본 경로에서는 미실행 |

### 4.2 추정 갭

| 갭 | 설명 |
|----|------|
| **(추정)** 일부 Worker 모드의 page-loop cancel 밀도 불균일 | 주요 모드는 회귀 테스트가 있으나, 모든 핸들러 전수 cancel 체크는 이번 감사에서 미실시 |
| **(추정)** Undo 비대상 모드 사용자 기대 불일치 | 스냅샷 Undo 대상은 mutation PDF 모드 중심; 배치/디렉터리 출력 등은 의도적으로 제외됐을 가능성 |
| **(추정)** 미리보기 암호 세션 메모리 상주 | `_current_preview_password` 등 — 세션 중 메모리 노출은 일반적이나 화면 잠금 없는 공유 PC 리스크 |
| **(추정)** 다중 모니터/HiDPI 엣지 | 영역 선택 좌표 매핑 테스트는 있으나 전 환경 커버 미확인 |
| **(추정)** Linux/macOS 패키징 | 소스는 크로스, 공식 배포·smoke는 Windows 중심 |

### 4.3 의도적으로 제품 범위 밖(문서상)

- Gemini SDK-level HTTP abort  
- 완전 서버형 협업/클라우드 동기화  
- PDF→Word 등 제거된 변환 파이프라인  

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (기능 정확성·표시 안전)

1. **채팅 partial HTML escape** (§3.1)  
   - `_on_partial_result`에서 escape 적용, 성공/히스토리와 동일 헬퍼.  
2. **`_is_pdf_encrypted` 삼상 반환 복구** (§3.2)  
   - mixin → `bool | None`; AI 경로 dead branch 활성화; 타입 계약 일치.  
3. **OCR 성공 카운트 기반 hard-fail/경고** (§3.3)  
   - 0성공 시 `err_ocr_unavailable` 또는 UI 경고 payload.

### 2단계 — 안정성 개선

4. 채팅 `send_message_stream` cancel 시 close/partial 차단 정렬 (§3.4).  
5. 강제 종료 경로 문서·로그·스윕 강화 (§3.5).  
6. 채팅 디스크 저장 기본 정책/안내 강화 (§3.6).  
7. AI temp 생성 실패·스윕 실패 시 사용자 가시화 (§3.7).

### 3단계 — 구조 개선

8. AI cancel 추상화: “streamable generate” 단일 경로로 요약/채팅 통합.  
9. Worker 핸들러 cancel-checkpoint 린트/정적 규칙 또는 구조 테스트 확대.  
10. OCR optional extra·런타임 사전 점검 UI.  
11. CLAUDE 구 Addendum OCR 문구와 Current Behavior 정리(문서 전용).  
12. (여유 시) 첨부 스트리밍·용량 상한, 썸네일 로더 lifecycle 정리.

---

## 6. Test Recommendations

### 6.1 즉시 추가 권장

| 테스트 | 목적 |
|--------|------|
| `test_chat_partial_html_escaped` | `_on_partial_result`에 `<script>`/`<b>` 등 포함 시 escape 여부 (Dummy host + signal) |
| `test_worker_is_pdf_encrypted_propagates_none` | 믹스인/WorkerThread에서 손상·미존재 경로가 `None`/`err_pdf_corrupted`로 이어지는지 |
| `test_extract_text_ocr_unavailable_hard_fail` | `get_textpage_ocr` 부재/예외 시 hard-fail 또는 명시적 fallback 플래그 (mock page) |
| `test_ai_chat_stream_cancel_closes` | cancel_check 시 채팅 스트림 루프 종료·close 호출(fake stream) |

### 6.2 보강 권장

| 테스트 | 목적 |
|--------|------|
| `test_prepare_ai_pdf_path_probe_failure` | 암호화 probe 실패 시 임시 파일 미생성 |
| `test_save_chat_histories_opt_out_clears_disk` | `save_chat_histories=False` 시 디스크 키 비움 (기존 defaults 테스트 확장) |
| `test_ocr_partial_page_fallback_payload` | 일부 페이지만 OCR 실패 시 `ocr_fallback` meta |
| cancel 체크 구조 테스트 확대 | 신규 모드 page loop에 `_check_cancelled` 존재 여부 |

### 6.3 기존 강점 (유지)

- preflight / batch fail-fast / attachment path security  
- cancel cleanup (mtime 휴리스틱 제거)  
- textbox queue / redact hard-fail / region select  
- i18n hardcoded smoke / structure budget  
- audit follow-up: `tests/test_audit_2026_08_04_followup.py`, `tests/test_audit_2026_07_22_followup.py`  

### 6.4 검증 커맨드 (현행)

```bash
python -m pyright src/core src/ui
python -m pytest -q
python main.py --smoke
# 선택: PDF_MASTER_GEMINI_FILE_API_SMOKE=1 + GEMINI_API_KEY
# 선택: powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
```

---

## 7. Appendix

### 7.1 이번 감사에서 “문제 아님”으로 재확인

- 첨부 추출 path traversal 방어  
- API 키 평문 폴백 시 명시적 동의  
- Worker 완료/실패/취소 sender 가드  
- 취소 출력 롤백이 `created_output_paths`만 대상  
- 배치 미지원 operation silent copy 방지  
- 2026-08-04 목록의 CJK·페이지 범위·textbox 밖·notify_mode 등  

### 7.2 CodeGraph 활용 요약

- `run_worker` blast radius: UI 탭 전반 (~69 callers)  
- `WorkerThread` 테스트 커버: cancel/preflight/regression 다수  
- 동적 dispatch: mode → `OPERATION_SPECS` → getattr handler  
- AI 스트림 close는 getattr dynamic boundary  

### 7.3 변경 이력 (감사 문서)

| 날짜 | 내용 |
|------|------|
| 2026-08-04 | 이전 전수 감사 + 후속 수정 반영 표 |
| 2026-08-05 | SOLID Round 2 구조 후속; 잔여 이슈 재평가 |
| 2026-08-05 | **§3–§6 권고 구현 완료** — §0b 체크리스트·위험도 Low로 갱신 |

---

*§3 항목의 “문제” 서술은 감사 시점 근거로 유지한다. 현재 코드 상태는 §0 / §0b 및 회귀 테스트를 따른다.*
