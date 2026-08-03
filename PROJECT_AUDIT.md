# Project Audit

> 감사 기준일: **2026-08-03**  
> 대상 버전: **PDF Master v4.5.6**  
> 초점: **2026-08-03 미리보기 포커스/전체화면 + 텍스트 상자 편집기 고도화** (Phase 1–3)  
> 범위: 기능 구현 관점 (예외·검증·상태/비동기·경로·설정·보안·문서 정합·테스트)  
> 분석 수단: `README.md`, `CLAUDE.md`, CodeGraph MCP (`codegraph_explore`), 보조 파일 열람·grep  
> **SSOT:** 본 파일 (`PROJECT_AUDIT.md`)이 현행 기능 감사 문서  

---

## 0. Implementation Follow-up (2026-08-03)

감사 §5 권고 반영 상태.

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| High §3.1 | 실패/취소 시 textbox post 플래그 리셋 | **해결** — `_clear_textbox_post_flags` on fail/cancel/success |
| High §3.2 | busy 시 포커스 바·전체화면 삽입 버튼 비활성 | **해결** — `set_ui_busy` + `set_actions_enabled` |
| High §3.3 | 큐 항목 `file_path` 고정 + 커밋 경로 검증 | **해결** |
| High §3.4 | `replace_text_in_rect` redact 실패 hard-fail | **해결** — `err_textbox_redact_failed` |
| Medium §3.5 | 인라인 편집 FocusOut 정책 | **해결** — arm 디바운스 + reason 필터 |
| Medium §3.6 | 영역 추출 암호 세션 | **부분** — preview password 전달 (Worker 이관은 잔여) |
| Medium §3.7 | 호스트 F11 = 메인 순환 | **해결** — `layoutCycleExitRequested` |
| Medium §3.8 | same-path 확인 다이얼로그 | **해결** |
| Medium §3.9 | README/단축키 동기화 | **해결** |
| Low §3.10 | insert_textboxes 부분 실패 보고 | **해결** — `msg_textboxes_inserted_partial` |
| 3단계 | 큐 다중 박스 오버레이 미리보기 | **해결** — `QueueGhostOverlay` + `set_queue_ghost_boxes` |
| 3단계 | 텍스트 상자 세션 단일 객체화 | **해결** — `TextboxEditorSession` |
| 3단계 | 영역 텍스트 추출 Worker | **해결** — `extract_text_in_rect` (memory payload) |

**검증:** `python -m pytest -q` (opt-in Gemini smoke skip 가능). 회귀: `tests/test_textbox_audit_followup.py` 등.

### SOLID 분할 (2026-08-03, 후속)

| 영역 | 구조 | facade 유지 |
|------|------|-------------|
| UI 마크업 액션 | `tabs_advanced/markup_actions/{annotations,redact,shapes_links,textbox,deps}.py` | `actions_markup.py` |
| Worker 주석 마크업 | `annotation/highlight_markup.py` + `annotation/textbox.py` | `annotation/markup.py` |
| 미리보기 위젯 | `preview_widget/{document_api,navigation,zoom,search_panel,theme_api,interaction_overlays}.py` | `widget.py` 합성 클래스 |

원칙: move-only 본문, public import/mode 불변, structure budget 게이트 확장.

---

## 1. Executive Summary

PDF Master는 **PyQt6 UI → `run_worker` → `WorkerThread` / `worker_runtime` → `worker_ops`** 로 명확히 분리된 올인원 PDF 편집 앱이다. 2026-08-03에 추가된 **미리보기 포커스·전체화면**, **텍스트 상자 편집기형 UX**(리사이즈·인라인 편집·same-path·큐·영역 교체)는 기존 Worker 계약(`insert_textbox` same_path_safe/Undo) 위에 얹혀 있어 골격은 건전하다.

다만 신규 기능 경계에서 **상태 플래그가 실패 경로에서 정리되지 않는 문제**, **전체화면 호스트가 busy 가드 밖**, **큐와 현재 파일 경로 불일치**, **영역 교체의 “지우고 쓰기” 실패 시 이중 기록 위험**, **README/단축키 문서 공백**이 확인된다. Critical 급 원격 보안 구멍은 없고, 사용자 데이터 손실·중복 실행 관점의 **High/Medium** 이슈가 핵심이다.

### 전체 위험도

| 구분 | 평가 |
|------|------|
| **전체 위험도** | **Medium** (신규 UX 경계; 코어 Worker 골격은 양호) |
| Critical | **없음** |
| High | 실패 시 텍스트상자 post-flag 잔존, 전체화면 중 busy 우회 가능, 큐–파일 경로 드리프트, 영역 교체 redact 실패 후 덮어쓰기 |
| Medium | 인라인 편집 FocusOut, UI 스레드 fitz 추출, F11 순환 불일치, 문서 미반영 |
| Low | reparent 레이아웃 취약성, 부분 실패 침묵, 테스트 갭 |

### 핵심 문제 (요약)

1. **`_textbox_clear_queue_after_success` / `_textbox_reopen_placement_after_success`가 성공 훅에서만 소비** — 실패·취소 시 잔존 → 다음 성공 작업에 부작용.  
2. **`PreviewFullscreenHost` 배치/삽입 버튼이 `set_ui_busy` 대상이 아님** — Worker 실행 중 중복 `run_worker` 가능.  
3. **다중 박스 큐는 항목에 `file_path`를 저장하지 않음** — 커밋 시 현재 선택 PDF에 적용 → 잘못된 문서에 삽입 가능.  
4. **`replace_text_in_rect`는 redact 실패를 로그만 하고 insert 계속** — “교체”가 “추가”로 변질 가능.  
5. **README/단축키 표에 F11·전체화면·same-path·큐·교체 미기재** — CLAUDE Current Behavior와 제품 문서 불일치.

---

## 2. Project Understanding

### 2.1 목적 (README / CLAUDE)

| 항목 | 내용 |
|------|------|
| 제품 | 올인원 PDF 편집 데스크톱 앱 (병합·변환·페이지·보안·주석·추출·배치·AI) |
| 스택 | Python 3.10+, PyQt6, PyMuPDF(`fitz`), optional `google-genai` / `keyring`, PyInstaller |
| 버전 | v4.5.6 |
| 배포 | Windows EXE 중심, 소스는 크로스 실행 가능 |

### 2.2 아키텍처 개요

```
main.py
  └─ PDFMasterApp (믹스인 조립)
       ├─ window_core / window_preview / window_worker / window_undo
       ├─ tabs_basic / tabs_advanced / tabs_ai
       └─ MainWindowWorkerMixin.run_worker()
            ├─ busy 가드 + _pending_workers FIFO
            ├─ same-path 시 미리보기 close → Worker → restore
            └─ WorkerThread → worker_runtime preflight/dispatch
                 └─ worker_ops (annotation/markup: insert_textbox*)
```

### 2.3 2026-08-03 신규 기능 실행 흐름 (CodeGraph)

**미리보기 레이아웃**

| 단계 | 심볼 / 위치 | 동작 |
|------|-------------|------|
| 포커스 | `window_preview/focus.py` `_set_preview_focus_mode` | 좌측 탭 숨김 + 스플리터 확장, 설정 저장 |
| F11 순환 | `_toggle_preview_focus_mode` | 일반 → 포커스 → 전체화면 → 일반 |
| 전체화면 | `_enter_preview_fullscreen` + `PreviewFullscreenHost` | `preview_image` reparent → `showFullScreen` |
| 복귀 | `_exit_preview_fullscreen` | detach → 패널 레이아웃 재삽입; `_preview_fullscreen_exiting` 재진입 가드 |
| Esc | `_on_preview_focus_escape` | 인라인 편집 → 배치 → 영역선택 → 전체화면 → 포커스 |

**텍스트 상자**

| 단계 | 심볼 / 위치 | 동작 |
|------|-------------|------|
| 배치 UI | `TextPlacementOverlay` + `ZoomablePreviewWidget.set_text_placement_mode` | 이동·8핸들 리사이즈·클릭 배치·너지·더블클릭 인라인 편집 |
| 삽입 | `action_insert_textbox` | same-path 옵션 또는 저장 다이얼로그 → `run_worker("insert_textbox")` |
| 성공 후 | `on_success` → `_on_textbox_worker_success` | 큐 비우기 / 연속 배치 `QTimer.singleShot(150, …)` |
| 큐 | `action_textbox_queue_*` + Worker `insert_textboxes` | 메모리 큐 → 일괄 삽입 |
| 교체 | `replace_text_in_rect` | 영역 redact 후 `insert_textbox` 계열 쓰기 |

**설정**

- `preview_focus_mode`, `splitter_sizes_before_focus` — `_settings_impl` 기본값·정규화.
- 포커스 중 스플리터 드래그는 `_save_splitter_state`에서 일반 비율 덮어쓰기 방지.

### 2.4 이전 감사 잔여 (2026-07-27 기준, 신규 범위 외)

- AI SDK-level HTTP abort, OCR optional extra 등 로드맵 잔여.  
- 암호 PDF AI UI·merge 0페이지·PROJECT_AUDIT SSOT 게이트는 당시 후속으로 반영된 상태.

---

## 3. High-Risk Issues

### 3.1 텍스트 상자 성공 전용 플래그가 실패·취소 시 잔존

* **위치:**  
  - `src/ui/tabs_advanced/actions_markup.py` — `action_insert_textbox` / `action_textbox_queue_commit` / `action_replace_text_in_rect` (`_textbox_reopen_placement_after_success`, `_textbox_clear_queue_after_success`)  
  - `src/ui/main_window_worker.py` — `on_success` (후크 호출) vs `on_fail` / `on_cancelled` (후크 없음)
* **문제:** 큐 커밋·연속 배치 플래그가 **성공 경로에서만** 소비된다. Worker 실패·취소 시 플래그가 남은 채 다음 성공 작업에 적용될 수 있다.
* **영향:**  
  - 실패한 큐 커밋 이후 단건 삽입 성공 시 **의도치 않은 큐 삭제**.  
  - keep-placing이 다음 성공 작업 후 예기치 않게 배치 모드를 재개.
* **근거:**  
  - 설정: `actions_markup.py` 약 904, 959–960, 1023행.  
  - 소비: `main_window_worker.py` `on_success` 262–269행 + `_on_textbox_worker_success`.  
  - `on_fail` 335+ / cancel 경로는 해당 플래그를 건드리지 않음.
* **권장 수정 방향:** `on_fail` / `on_cancelled`에서도 플래그 리셋; 또는 `run_worker` 시작 시 요청 단위 컨텍스트 객체로 묶어 해당 job 완료 시에만 처리.
* **우선순위:** **High**

---

### 3.2 전체화면 호스트가 UI busy 가드 밖 — 중복 실행

* **위치:**  
  - `src/ui/window_worker/lifecycle.py` — `set_ui_busy` (tabs / `_app_shortcuts` / Open 메뉴만)  
  - `src/ui/window_preview/fullscreen_host.py` — `btn_place` / `btn_insert`  
  - `src/ui/window_preview/panel.py` — 포커스 바 버튼 (tabs 비활성 시 좌측은 막히나, 포커스 중 미리보기 패널은 우측에 남음)
* **문제:** Worker 실행 중 메인 탭·단축키는 비활성화되지만, **전체화면 창의 배치/삽입 버튼**은 활성 상태다. 포커스 바 버튼도 우측 패널에 있으면 busy 중에도 클릭 가능할 수 있다(좌측 탭 비활성과 별개).
* **영향:** `run_worker` 재진입 → 대기 큐 적재 또는 사용자 혼란; same-path 연속 쓰기의 레이스 체감.
* **근거:** `set_ui_busy`가 tabs/`_app_shortcuts`/`_menu_open_action`만 제어. Fullscreen host는 별도 `QMainWindow`로 시그널을 `action_*`에 직결.
* **권장 수정 방향:** busy 시 `PreviewFullscreenHost` 버튼 비활성; 또는 `run_worker` 진입을 단일 게이트로 유지하되 호스트 UI에 busy 미러링. 포커스 바 버튼도 동일.
* **우선순위:** **High**

---

### 3.3 다중 박스 큐와 대상 PDF 경로 불일치

* **위치:**  
  - `actions_markup.py` — `action_textbox_queue_add` (큐 항목에 page/rect/style만 저장)  
  - `action_textbox_queue_commit` (커밋 시 `sel_textbox.get_path()` 사용)
* **문제:** 큐에 쌓을 때 **파일 경로를 고정하지 않는다**. 큐잉 후 파일 선택기를 바꾸면 다른 PDF에 좌표가 적용된다.
* **영향:** 잘못된 문서에 텍스트 일괄 삽입; 페이지 수 부족 시 Worker `err_page_out_of_range`로 전체 실패(부분 저장 없음).
* **근거:** 큐 아이템 구조는 page_num/rect/text/style; commit은 현재 `path`만 사용 (CodeGraph `action_textbox_queue_commit`).
* **권장 수정 방향:** 큐 항목에 `file_path` 저장 + 커밋 시 불일치 거부; 또는 큐잉 중 파일 선택 변경 시 큐 무효화 확인 다이얼로그.
* **우선순위:** **High**

---

### 3.4 `replace_text_in_rect` — redact 실패 후 insert 계속

* **위치:** `src/core/worker_ops/annotation/markup.py` — `replace_text_in_rect` (약 333–341행)
* **문제:** `add_redact_annot` / `apply_redactions` 예외를 로깅만 하고 **새 텍스트 삽입을 계속**한다. 사용자 확인 문구는 “지우고 덮어쓰기”인데 결과는 기존 텍스트 위에 추가될 수 있다.
* **영향:** 민감 정보 제거 실패 인지 불가; 레이아웃/내용 이중 표시.
* **근거:** `except Exception: logger.warning(...); # 교정 실패 시에도 덮어쓰기 시도` 후 `_write_textbox_content`.
* **권장 수정 방향:** redact 실패 시 `error_signal`로 중단; 또는 명시적 “insert-only 폴백” 플래그와 사용자 경고. 성공 시 교체 여부를 payload로 보고.
* **우선순위:** **High**

---

### 3.5 인라인 편집 `FocusOut` 즉시 커밋

* **위치:** `src/ui/preview_widget/text_placement.py` — `TextPlacementOverlay.eventFilter` (`FocusOut` → `_finish_inline_edit(commit=True)`)
* **문제:** 포커스 이탈 시 무조건 커밋. Qt에서 `setFocus` 직후 순간적 FocusOut, 또는 IME/다른 창 클릭 시 편집이 조기 종료되거나 빈 커밋이 발생할 수 있다. (추정 포함: 플랫폼·IME 의존)
* **영향:** 편집 중 텍스트 유실 체감, 불필요한 `textEdited` → 본문 필드 덮어쓰기.
* **근거:** FocusOut 분기에서 `reason`/`PopupFocusReason` 필터 없음; `_start_inline_edit`가 `setFocus` 직후 show.
* **권장 수정 방향:** `QEvent.FocusOut` 시 `reason` 검사, 짧은 디바운스, 또는 명시 버튼(완료)만 커밋 + Esc 취소 유지.
* **우선순위:** **Medium**

---

### 3.6 영역 교체 시 UI 스레드 동기 `fitz.open`

* **위치:** `actions_markup.py` — `_extract_text_in_rect_sync` (region `textbox_replace` 콜백에서 호출)
* **문제:** 미리보기 드래그 완료 직후 **UI 스레드에서 PDF를 열어** 클립 텍스트를 추출한다. 대용량·네트워크 드라이브 PDF에서 UI 스톨 가능.
* **영향:** 드래그 UX 멈춤; 암호 PDF·잠금 파일에서 예외 삼킴 → 빈 본문(조용한 실패).
* **근거:** `fitz.open(path)` + `page.get_text(..., clip=...)` 동기 호출; 예외 시 `""` 반환.
* **권장 수정 방향:** Worker 모드로 추출 이전; 또는 이미 로드된 preview 문서/캐시 재사용; 암호 세션 연동.
* **우선순위:** **Medium**

---

### 3.7 전체화면 창 F11 vs 메인 F11 순환 의미 불일치

* **위치:**  
  - `focus.py` `_toggle_preview_focus_mode` — 전체화면 중 F11 → exit + **포커스 해제(일반)**  
  - `fullscreen_host.py` — 호스트 내부 F11/Esc → `close` → `hostClosing` → `_exit_preview_fullscreen(restore_focus=True)` → **포커스 유지**
* **문제:** 같은 F11이라도 **포커스 소유 창에 따라** 결과가 다르다 (일반 복귀 vs 포커스 잔류).
* **영향:** “F11 한 번 더 = 일반” 학습 모델 붕괴; 지원/문서와 어긋남.
* **근거:** CodeGraph `focus.py` 105–107행 vs `fullscreen_host.py` F11 → `self.close` + hostClosing `restore_focus=True`.
* **권장 수정 방향:** 호스트 F11도 메인 순환과 동일하게 “exit fullscreen + exit focus”; 또는 호스트에서 메인 `_toggle` 호출.
* **우선순위:** **Medium**

---

### 3.8 same-path 적용에 확인 다이얼로그 없음

* **위치:** `actions_markup.py` — `_textbox_resolve_output_path` + 체크박스 `chk_tb_same_path`
* **문제:** “원본에 바로 적용”이 켜진 채 삽입/큐/교체 시 **추가 확인 없이** 원본 PDF를 덮어쓴다. Undo는 가능하나 백업 실패 시 위험.
* **영향:** 실수 클릭 시 원본 즉시 변경; 교체 모드는 파괴적(redact).
* **근거:** same-path 시 path 그대로 반환; `replace`만 확인 다이얼로그 있음. 단건 insert same-path는 확인 없음.
* **권장 수정 방향:** same-path 첫 적용 또는 세션당 확인; 교체+same-path는 이중 확인 유지.
* **우선순위:** **Medium**

---

### 3.9 README / 단축키 표 vs CLAUDE·구현 불일치

* **위치:** `README.md` (기능·단축키 절), `CLAUDE.md` Current Behavior Notes (2026-08-03 항목 있음)
* **문제:** README UI/UX·단축키에 **F11/Ctrl+F11, 포커스/전체화면, same-path, 큐, 영역 교체, 인라인 편집**이 없다. 텍스트 상자는 “드래그 위치 지정” 수준만 기술.
* **영향:** 사용자 발견성 저하; 검증 문서 게이트는 SSOT 존재만 검사하므로 README 기능 공백이 테스트에 안 잡힘.
* **근거:** README 단축키 표 218–233행에 F11 없음; `F11|전체화면|insert_textboxes` grep 0건. CLAUDE L14에 상세 기술.
* **권장 수정 방향:** README/README_EN 단축키·고급 편집·변경 이력 동기화.
* **우선순위:** **Medium**

---

### 3.10 `insert_textboxes` 부분 실패 침묵

* **위치:** `markup.py` `insert_textboxes` — 빈 rect/`ok=False` 시 `continue`, 마지막에 `wrote_count`만 보고
* **문제:** 일부 박스 실패 시 어떤 인덱스가 빠졌는지 UI/메시지에 없음. 페이지 범위 오류만 hard-fail.
* **영향:** “N개 삽입”이 큐 길이보다 작아도 원인 불명.
* **근거:** `if fitz_rect.is_empty: continue`, `if ok: wrote_count += 1`.
* **권장 수정 방향:** 실패 인덱스 목록을 payload/메시지에 포함; 0개일 때만 에러(현재).
* **우선순위:** **Low–Medium**

---

### 3.11 전역 Esc 단축키와 폼 입력 충돌 가능

* **위치:** `window_core/shortcuts.py` — `QShortcut(Qt.Key.Key_Escape, self, _on_preview_focus_escape)`
* **문제:** 메인 윈도우 Esc가 배치/포커스 해제에 연결됨. 포커스 모드가 아닐 때는 no-op에 가깝지만, **포커스 모드 + 다른 위젯 입력 중 Esc**가 레이아웃을 접을 수 있다.
* **영향:** 의도치 않은 포커스 종료.
* **근거:** Esc 핸들러가 배치 없으면 포커스 해제. Application/Window shortcut context 기본값.
* **권장 수정 방향:** 포커스가 미리보기/오버레이일 때만 처리; 또는 `WidgetWithChildrenShortcut` 범위 축소.
* **우선순위:** **Low–Medium**

---

## 4. Potential Functional Gaps

| 항목 | 설명 | 구분 |
|------|------|------|
| 큐 항목 시각적 미리보기 | 목록 텍스트만 있고 페이지 썸네일/오버레이 다중 박스 표시 없음 | 기능 갭 |
| 암호 PDF + 영역 추출 | `_extract_text_in_rect_sync`가 preview 암호 세션을 재사용하지 않음 → 추출 실패 가능 | **추정**(암호 파일에서 빈 문자열) |
| 전체화면 중 검색/인쇄 | 호스트 툴바에 검색·인쇄 없음; 위젯 내장 툴바는 유지되나 포커스 전환 UX 미검증 | **추정** |
| keep-placing 후 좌표 리셋 | 성공 후 같은 자리에 재배치 → 의도적일 수 있으나 “다음 위치” 프리셋 없음 | 기능 갭 / **추정** |
| 인라인 편집 중 페이지 전환 | 페이지 변경 시 오버레이 좌표 동기화는 refresh 경로에 의존; 편집 중 페이지 이동 시 박스/페이지 불일치 가능 | **추정** |
| `insert_textboxes` 진행률 UI | progress emit은 있으나 큐 크기·실패 요약 다이얼로그 없음 | 기능 갭 |
| OCR/스캔 PDF 교체 | 영역 교체는 텍스트 레이어 전제; 스캔본은 redact+빈 추출 | 알려진 제품 한계 (기존 OCR 로드맵) |
| 다중 모니터 전체화면 | `showFullScreen` 기본 스크린; 모니터 선택 없음 | **추정** 갭 |
| 설정에 전체화면 복원 안 함 | 기동 시 포커스만 복원 — 의도적 | 문서화 필요 |

---

## 5. Recommended Fix Plan

### 1단계 — 즉시 수정 (데이터 무결성·중복 실행)

1. **실패/취소 시 텍스트상자 플래그 리셋** (`_textbox_*_after_success` clear in `on_fail` / `on_cancelled`).  
2. **busy 시 전체화면·포커스 바 삽입/배치 버튼 비활성** (또는 액션 진입 가드 강화).  
3. **`replace_text_in_rect` redact 실패 시 hard-fail** (또는 명시적 폴백 + 사용자 경고).  
4. **큐 항목에 `file_path` 고정 + 커밋 시 경로 검증**.

### 2단계 — 안정성 개선

5. 인라인 편집 FocusOut 정책 개선 (reason/디바운스).  
6. 영역 텍스트 추출을 Worker/preview 세션으로 이전.  
7. 호스트 F11을 메인 순환과 일치.  
8. same-path 확인 다이얼로그(특히 교체·첫 적용).  
9. `insert_textboxes` 부분 실패 보고.

### 3단계 — 구조·문서·UX

10. README/README_EN 단축키·기능·변경 이력 동기화.  
11. 큐 다중 박스 미리보기 오버레이(선택).  
12. 텍스트 상자 편집 “세션” 상태를 단일 객체로 묶어 Worker 완료 콜백과 연결.  
13. (로드맵) OCR·기존 텍스트 블록 리스트 선택 교체.

---

## 6. Test Recommendations

### 6.1 즉시 추가 권장

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_textbox_flags_cleared_on_fail` | 큐 커밋 실패/에러 시그널 후 `_textbox_clear_queue_after_success` / reopen 플래그가 False |
| `test_textbox_flags_cleared_on_cancel` | 취소 경로 동일 |
| `test_queue_commit_rejects_path_mismatch` | 큐잉 path ≠ 현재 path 시 거부 (구현 후) |
| `test_replace_text_redact_failure_aborts` | redact mock 실패 시 insert 미호출 / error_signal |
| `test_fullscreen_busy_disables_insert` | busy 중 호스트 insert가 no-op 또는 비활성 (구현 후) |
| `test_f11_cycle_consistency` | 전체화면 종료 후 레이아웃 모드가 토글 정의와 일치 |

### 6.2 보강 권장

| 테스트 | 검증 내용 |
|--------|-----------|
| 인라인 편집 | 더블클릭 → textEdited → 본문 필드 동기 (dummy overlay) |
| keep-placing | 성공 후 `action_start_textbox_region_select` 예약 호출 (QTimer mock) |
| same-path insert | preview prepare/restore 호출 여부 (기존 same-path 테스트 패턴 재사용) |
| reparent | enter/exit fullscreen 후 `preview_image` parent가 panel (Qt 통합, skip if headless) |
| 좌표 매핑 | 리사이즈 후 spinbox 동기 (기존 drag flow 확장) |
| 문서 게이트 | README에 `F11` 또는 “포커스 모드” 키워드 포함 여부를 optional 스모크로 (문서 수정 후) |

### 6.3 기존 커버리지 (양호)

- `tests/test_text_placement_overlay.py` — 핸들/리사이즈 단위  
- `tests/test_preview_focus_mode.py` — 포커스 토글·Esc 순서  
- `tests/test_textbox_queue_and_replace.py` — 큐 추가/same-path/Worker 일괄·교체 happy path  
- `tests/test_textbox_drag_ui_flow.py` — 배치 필드 동기  
- `tests/test_worker_param_compat.py` — 단건 `insert_textbox`  

**갭:** 실패 경로 플래그, busy×fullscreen, 경로 드리프트, redact 실패 — 현재 테스트가 happy path 중심.

---

## 부록 A. 문서·구현 정합 체크리스트

| 출처 | 상태 |
|------|------|
| CLAUDE.md 2026-08-03 노트 | 구현과 **대체로 일치** |
| README 텍스트 상자 / 미리보기 UX | **부분 일치** (드래그만; 포커스·전체화면·큐·same-path·교체 없음) |
| README 단축키 | **F11 / Ctrl+F11 누락** |
| PROJECT_AUDIT SSOT 게이트 | 파일 존재·docs 참조 유지 필요 (본 개정 후 계속 SSOT) |

---

## 부록 B. CodeGraph blast radius (신규 심볼)

| 심볼 | 비고 |
|------|------|
| `insert_textboxes` / `replace_text_in_rect` | UI 1 caller + 전용 테스트 |
| `action_insert_textbox` | mixin 노출; CodeGraph 기준 전용 UI 플로우 테스트 약함 |
| `TextPlacementOverlay` | widget/__init__ 경유; 인라인 편집 단위 테스트 없음 |
| `_toggle_preview_focus_mode` / fullscreen host | focus 단위 테스트 일부; reparent 통합 테스트 없음 |

---

*이 문서는 2026-08-03 코드 스냅샷 기준 기능 감사이다. 구현 수정은 포함하지 않는다.*
