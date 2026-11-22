# Project Audit — UI·Interaction·Lifecycle Scope (Scope 2)

> 감사 기준일: **2026-11-22**
> 대상 버전: **PDF Master v4.5.18** (`src/core/_constants_impl/values.py`)
> 성격: **기능 구현·런타임 안정성 One-Shot 감사 (Scope 2)** — 코드 수정 없이 리포트만 작성한다.
> 범위: 전회 감사(`PROJECT_AUDIT.md`, 런타임 코어·업데이트·compare·AI·preflight·문서)와 겹치지 않는 **사용자 인터랙션 레이어 + 나머지 Worker 도메인 + 앱 수명주기**.
> 원칙: 이슈는 반증 검증을 통과한 `Confirmed` 또는 근거가 강한 `Likely`만 기록. 단순 스타일·취향은 제외.

## 1. Executive Summary

* 프로젝트 전체 상태: **양호**. 탭 액션의 입력 검증(파일·범위·선택·옵션 누락 가드), 취소 체크포인트, 원자 저장, 미리보기 동기화, 종료 정리(worker·백업·orphan temp·AI 캐시·설정 저장 순서)가 촘촘하다.
* 전체 위험도: **Low–Medium.** 데이터 손실/파괴에 해당하는 Critical/High 문제는 확인하지 못했다.
* 가장 중요한 문제 3개:
  1. `split_by_pages` 범위 모드의 범위 초과 clamp가 마지막 페이지를 날조 — 존재하지 않는 범위 입력에 "성공"으로 마지막 쪽을 저장 ([S2-ISSUE-001]).
  2. Undo 백업(PDF 전체 사본)이 `%TEMP%`에 ACL 제한 없이 보관 — AI 임시 평문 파일에는 적용된 chmod/icacls가 Undo 사본에는 없음 ([S2-ISSUE-002]).
  3. `duplicate_page` 횟수 무검증 — 0/음수는 "0번 복제 성공", 거대값은 장시간 hang ([S2-ISSUE-003]).
* 데이터 손상/유실 가능성 평가: **낮음.** 지적 사항은 모두 fail-open이 아니라 "잘못된 성공 메시지·부분 결과" 또는 "방어 심화" 수준이며, 원자 저장·취소 롤백·입력 검증 골격은 유지된다.
* 가장 먼저 수정해야 할 영역: **분할 clamp → 복제 횟수 가드 → Undo ACL 순.**

## 2. Project Understanding

README/CLAUDE 및 CodeGraph 탐색을 바탕으로 정리했다.

* 프로젝트 목적: PySide6 기반 올인원 PDF 데스크톱 유틸리티 (본 범위는 탭 UI·썸네일·미리보기·Undo·수명주기).
* 주요 entrypoint:
  * `src/ui/main_window.py:309 closeEvent` → worker 정리 → 대기 큐 폐기 → 미리보기 해제 → undo 백업 정리 → orphan temp 스윕 → AI 정리 → 채팅/설정 저장.
  * 탭 액션 (`tabs_basic/*`, `tabs_advanced/actions_*`, `tabs_ai/actions.py`, `tabs_settings`) → 입력 검증·다이얼로그 → `run_worker` (Scope 1에서 감사).
  * `src/ui/thumbnail/grid*.py` (로더 스레드 + LRU + 선택 모델) ↔ `tabs_basic/page.py` 회전/선택 연동 ↔ AI 탭 썸네일.
  * `src/ui/preview_widget/*` (문서·탐색·검색·인쇄·영역선택·텍스트배치·큐고스트) + `window_preview/*` (파일 감시·포커스·전체화면·인쇄·업데이트).
* 핵심 모듈:
  * `src/ui/window_undo/{backup,cleanup,history}.py` — 스냅샷 백업·용량/시간 정리·Undo/Redo 콜백.
  * `src/core/worker_ops/page/{split_delete,mutate,reorder_rotate}.py` — 분할·삭제·회전·삽입·복제·번호.
  * `src/core/worker_ops/{transform,extract,cleanup,form}/` — 크기/자르기·추출/검색·정리·양식.
  * `src/core/temp_cleanup.py` — orphan temp 스윕 (AI 평문·atomic 잔존).
  * `src/core/worker_ops/ai/temp_acl.py` — 임시 평문 파일 권한 제한 (chmod 0o600 + icacls).
* 데이터 저장 방식: 설정 홈 JSON 원자 저장 + debounce(`_schedule_settings_save` 400ms) + 종료 시 flush; 최근 파일(`recent_files`, `RECENT_FILES_MAX` 상한·dedup·존재 확인); 채팅 기록 v2 키 (Scope 1).
* 외부 의존성: PySide6 (QPdfDocument/QPdfView/파일 감시자/인쇄), PyMuPDF (fitz, `optional_deps` 경계), Tesseract(선택 OCR).
* 핵심 실행 흐름:

`탭 액션 입력 검증 → _choose_save_file/_choose_output_directory(last_output_dir 기억) → run_worker → (Scope 1) → on_success/on_fail/on_cancelled → 미리보기 복원·undo 등록·토스트/모달`

`미리보기 파일 변경 감지 → 250ms single-shot 재시도(최대 10회) → 뷰 상태 복원 리로드`

`종료 → 실행 중 worker cooperative cancel(3s)→모달→terminate → 큐 폐기 → 미리보기 해제 → 미사용 undo 정리 → temp 스윕(include_in_progress) → AI 정리 → 채팅/설정 저장`

## 3. Audit Coverage & Limitations

* 직접 확인한 주요 모듈: `thumbnail/{grid,grid_loading,grid_layout,grid_selection,loader,document,pixmap_lru}`, `preview_widget/{document_api,navigation,search_panel,interaction_queue,interaction_region}`, `window_preview/{document,update,navigation,focus}`, `window_undo/{backup,cleanup,history,mixin}`, `window_core/state.py`, `main_window.py` closeEvent, `tabs_basic/{page,batch,convert}`, `tabs_advanced/actions_edit.py`, `worker_ops/page/{split_delete,mutate}`, `transform/geometry.py`, `cleanup/{blank_dedupe,sanitize_nup,bookmark_ops}`, `form/ops.py`, `security/ops.py`, `ai/temp_acl.py`, `temp_cleanup.py`.
* CodeGraph로 분석·추출한 관계:
  * `load_pdf` → 6개 호출자 / `ThumbnailGridWidget` → 13개 호출자 / `_is_active_loader_sender` 잔여 시그널 가드.
  * `set_ui_busy` → 14개 구현 디스패치 / 썸네일 선택(단일/확장·active/selected 분리).
  * `closeEvent` 7단계 종료 순서 / `_shutdown_worker_for_close` cooperative→모달→terminate.
  * `fetch-depth` 대상 아님 — 이하 파일 직접 열람으로 보완.
* 실행한 테스트: 본 감사 단계에서는 코드 흐름·기존 테스트 대조 중심 (수정 후 `pytest`·`pyright` 전체 실행 예정).
* 확인할 수 없었던 환경/행위: 실제 다중 사용자 PC에서의 temp 파일 가시성, 1000쪽 초과 대용량 문서의 분할 체감, macOS/Linux 파일 감시자·인쇄 동작 (Windows 우선 설계).
* CodeGraph 또는 분석상의 한계: 인덱스-엔진 버전 경고 하에 동작. Qt 시그널 경계·런타임 디스패치는 파일 직접 열람으로 보완했다.

## 4. High-Risk Issues

> Critical/High에 해당하는 문제는 없다. 아래는 반증을 통과한 Medium 1건 + Low 3건이다 (신뢰도 전부 `Confirmed`).

### [S2-ISSUE-001] `split_by_pages` 범위 초과 시 마지막 페이지 날조

* **위치:** `src/core/worker_ops/page/split_delete.py:129-140`.
* **우선순위:** Medium
* **신뢰도:** Confirmed
* **문제:** 범위 모드에서 `start`·`end`가 전체 쪽수를 넘으면 `min()`으로 clamp한다. `"99-200"`을 10쪽 문서에 넣으면 10쪽이 통째로 저장되고 `msg_split_done` 성공이 나간다. `parse_page_range` 계열(무효 토큰 hard-fail)과 정반대 관대함이다.
* **발생 조건:** 범위를 잘못 입력한 모든 경우 (오타·다른 문서 기준 범위 재사용). 현실적이다.
* **영향:** 존재하지 않는 범위에 대한 "성공" + 예상 밖 1쪽 PDF 생성. 입력 원본은 불변, 출력은 신규 파일이라 덮어쓰기 손상은 없다.
* **근거:** 129-138행 직접 열람. `start > page_count and end > page_count` → 둘 다 `page_count`로 고정 → `insert_pdf(from_page=9, to_page=9)`. `count==0` 에러 분기(164-165행)는 이 경우에 닿지 않는다.
* **반증 확인:** 부분 겹침(`"8-15"` on 10쪽 → 8~10쪽)은 편의상 clamp가 정당하므로 유지한다. 문제되는 것은 **범위 전체가 문서 밖에 있을 때**뿐이다. 호출 UI(`actions_edit.py:18-21`)는 빈 문자열만 막고 범위 타당성은 검사하지 않으며, worker preflight도 `split_by_pages`의 `ranges` 값을 검사하지 않는다(`required_kwargs=("output_dir",)`만). `split`(parse_page_range 사용)과 대조하면 엄격도 비대칭이 명확하다.
* **호출/영향 범위:** `split_by_pages` 단일 핸들러 → `_atomic_pdf_save` → 신규 `_part_N.pdf`. 기존 테스트는 `each` 모드만 커버해 clamp 의존 없음.
* **권장 수정 방향:** `start > page_count`면 해당 파트 skip(warning 로그) — 부분 겹침 clamp는 유지. 전부 skip되면 기존 `err_split_no_valid_ranges`로 종료.
* **필요한 회귀 테스트:** (a) 10쪽 문서에 `"99-200"` → 에러 + 출력물 없음, (b) `"8-15"` → 8~10쪽 1파일 성공 유지.

### [S2-ISSUE-002] Undo 백업 사본에 권한 제한 없음 (AI temp와 비대칭)

* **위치:** `src/ui/window_undo/backup.py:13-43` (`shutil.copy2` 후 제한 없음), `src/ui/main_window.py:129-131` (`pdf_master_undo` 디렉터리 생성 시 제한 없음).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** Undo 백업은 **PDF 전체 사본**을 `%TEMP%/pdf_master_undo/undo_<hex>_<원본명>`으로 보관하는데, AI 임시 평문 파일에 적용되는 `chmod 0o600` + icacls 상속 제거가 없다. 같은 "임시 평문 PDF"인데 보호 수준이 다르다.
* **발생 조건:** Undo 대상 작업이 실행될 때마다 (일상적). 악용에는 동일 PC의 다른 사용자 권한 상승(또는 ACL 오구성)이 필요하므로 현실성은 낮다.
* **영향:** 보호 심화(gap) 수준. Windows 기본 `%TEMP%`는 사용자별로 격리되어 있어 당장 노출되지는 않는다.
* **근거:** 코드 대조 — `ai/temp_acl.py::_restrict_temp_file_permissions` (chmod+icacls, 실패 시 메타 경고) vs `backup.py` (제한 없음). 파일명에 원본 파일명이 그대로 들어가 temp 목록에서 문서명이 노출되는 것도 확인했다.
* **반증 확인:** `%TEMP%` 사용자 격리, 500MB 용량 캡·24h age 정리·종료 시 미사용 정리로 잔존 창구가 제한됨을 확인했다. 그래서 Low다. `temp_cleanup.py`가 undo 파일을 스윕하지 않는 점(접두사 `undo_` 미포함)도 확인 — undo 정리는 자체 함수들이 담당하므로 orphan은 아니다.
* **호출/영향 범위:** `_create_backup_for_undo` (run_worker undo 스냅샷 + `_register_undo_action` — 후자는 데드코드, S2-ISSUE-004) → `%TEMP%/pdf_master_undo/`.
* **권장 수정 방향:** `temp_cleanup.py`에 core helper로 권한 제한 로직을 두고 `ai/temp_acl.py`는 facade로 유지한 뒤, undo 백업 디렉터리 생성 시 + `copy2` 직후에 best-effort 적용 (실패 시 로그, AI temp와 동일 수준).
* **필요한 회귀 테스트:** 백업 생성 후 POSIX에서 mode `0o600` 확인 (Windows는 best-effort 미검증 + 로그 확인).

### [S2-ISSUE-003] `duplicate_page` 횟수 무검증

* **위치:** `src/core/worker_ops/page/mutate.py:208-230` (`count = _as_int(...)`, 범위 검사 없음).
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** `count=0`·음수면 루프를 건너뛰고 사본 저장 후 `"0번 복제"` 성공 메시지가 나간다. 거대값(예: 수백만)은 페이지당 `fullcopy_page` 반복으로 장시간 hang (취소는 가능).
* **발생 조건:** 직접 호출·malformed kwargs. UI 스핀박스(1~100)는 막으므로 정상 경로는 안전하다.
* **영향:** 오해성 성공 메시지 / 장시간 작업. 원본·출력 무결성 자체는 깨지지 않는다.
* **근거:** 213행·220-227행 직접 열람. `count=0`이면 `range(0)` 스킵 → `_atomic_pdf_save` → `msg_page_duplicated(..., 0)`. preflight에 `duplicate_page`별 검증 없음.
* **반증 확인:** UI 계약(스핀박스 1~100)이 정상 경로를 막고, 취소 체크포인트가 매 반복마다 있어 hang에서 탈출 가능함을 확인했다.
* **호출/영향 범위:** `duplicate_page` 단일 핸들러. `insert_blank_page`(위치 범위 검사 있음, 153-159행)와 대조된다.
* **권장 수정 방향:** `count` 1~100 (UI 계약과 동일) 외에는 명시 에러. 진행률 0-나눗셈은 `count>=1` 보장 후라 안전해진다.
* **필요한 회귀 테스트:** `count` = 0·-3·101 → 명시 에러 + 출력물 없음, `count` = 3 → 3쪽 복제 성공.

### [S2-ISSUE-004] 호출되지 않는 `_register_undo_action` 이중 등록 경로 (데드코드)

* **위치:** `src/ui/window_undo/history.py:36-54`, 배선 `src/ui/window_undo/mixin.py:8,17`.
* **우선순위:** Low
* **신뢰도:** Confirmed
* **문제:** undo 등록 로직이 두 벌 존재한다. 실제 사용 경로는 `window_worker/success.py::apply_undo_registration` + `_pending_undo`이고, `history._register_undo_action`은 mixin에 배선만 되어 있고 **호출자가 0명**이다 (repo 전체 검색 확인). 방치 시 향후 호출자가 생기면 before/after 스냅샷 중복 생성·정책 불일치(대용량 스킵 안내 등 success 경로와 다름) 위험이 있다.
* **발생 조건:** 없음 (현재 미도달).
* **영향:** 없음. 구조 부채 정리 대상이다.
* **근거:** repo 전체 `_register_undo_action` 참조 = 정의+mixin 배선 2곳. monkeypatch 계약 SSOT·structure budget 테스트가 이 심볼을 고정하지 않음을 확인했다.
* **반증 확인:** production risk가 아니므로 이슈가 아니라 구조 정리로 분류한다. 삭제해도 동작 불변이 구조상 자명하다.
* **호출/영향 범위:** `window_undo` 패키지 내부. 삭제 후 mixin 표면 축소.
* **권장 수정 방향:** 정의 + mixin 배선 제거. `apply_undo_registration`을 유일 등록 경로로 남긴다.
* **필요한 회귀 테스트:** 기존 undo 테스트 그대로 (동작 불변). 별도 신규 테스트 불필요.

## 5. Potential Functional Gaps

* **Confirmed Gap:** `resize_pages`는 0쪽 문서 입력 시 빈 `new_doc` 저장에서 `ValueError: cannot save with zero pages`로 끝나며 명시 가드가 없다 (images_to_pdf와 동형 — Scope 1에서 해당 패턴을 수정한 바 있다). 다만 0쪽 PDF 파일 자체가 사실상 도달 불가하므로 이슈로 올리지 않는다.
* **Likely Gap:** 썸네일 LRU 무효화 키 비교가 비정규 경로 문자열(`load_pdf`의 `prev_path != pdf_path`)이라, 같은 파일의 다른 표기(대소문자·구분자) 재선택 시 LRU 전체를 비운다. 성능 영향만 있고 정확성 영향은 없다.
* 추정 항은 없다. (추정은 현재 버그처럼 표현하지 않는다.)

## 6. Documentation Mismatches

* 본 범위에서 README/CLAUDE/GEMINI와 실제 구현이 어긋나는 신규 불일치는 없다 (Scope 1에서 버전·바인딩 표기를 정정한 상태).
* `split_by_pages`의 관대 clamp와 `parse_page_range`의 엄격 hard-fail이 같은 "범위 입력"에 대해 문서화되지 않은 채 공존한다 — S2-ISSUE-001 수정으로 엄격 쪽에 맞춘다.

## 7. Recommended Fix Plan

> 실제 코드 수정은 하지 않는다 (본 문서는 감사 기록). 수정은 후속 구현 단계에서 수행한다.

### Phase 1 — Immediate

1. `split_by_pages` 전체-범위-밖 파트 skip ([S2-ISSUE-001]). 부분 겹침 clamp 유지.
2. `duplicate_page` 횟수 1~100 명시 검증 ([S2-ISSUE-003]).

### Phase 2 — Stability

1. Undo 백업 ACL best-effort 적용 ([S2-ISSUE-002]). core helper + `ai/temp_acl` facade 유지.
2. 데드 `_register_undo_action` 제거 ([S2-ISSUE-004]).

### Phase 3 — Structural

1. LRU 키 정규화 (성능, 여유 시).
2. `resize_pages` 0쪽 가드 (도달 불가에 가까우므로 최하위).

## 8. Test Recommendations

| 대상 | 입력 조건 | 기대 결과 |
|------|-----------|-----------|
| 분할 범위 밖 | 10쪽 문서에 `"99-200"` | `err_split_no_valid_ranges` + 출력물 없음 |
| 분할 부분 겹침 | 10쪽 문서에 `"8-15"` | 8~10쪽 1파일 성공 유지 |
| 복제 횟수 | `count` 0·-3·101 | 명시 에러 + 출력물 없음 |
| 복제 정상 | `count` 3 | 3쪽 복제 + 성공 메시지 |
| Undo ACL | 백업 생성 직후 | POSIX mode `0o600` (Windows는 미검증 + 로그) |
| Undo 데드코드 | 삭제 후 전체 suite | 기존 undo 테스트 전부 통과 |

## 9. Final Assessment

| 구분 | 평가 | 근거 |
|------|------|------|
| Functional Correctness | Acceptable | 분할 clamp·복제 횟수 2건이 감점 요인. 나머지는 검증 촘촘 |
| Runtime Stability | Good | 종료 순서·취소·busy 가드·로더 sender 가드가 확인됨 |
| Data Integrity | Good | 원자 저장·롤백·입력 검증 골격 유지. 확인된 손실 경로 없음 |
| Error Resilience | Acceptable | 관대 파싱 지점(분할 clamp)이 실패를 성공으로 포장하는 1건 |
| Cross-platform Robustness | Acceptable | Windows 우선 설계와 일치. ACL은 best-effort로 양 OS 커버 |
| Test Confidence | Good | 기존 회귀 커버 존재. 신규 4건 추가 예정 |

**먼저 수정할 문제 3개:** `split_by_pages` 범위 밖 skip ([S2-ISSUE-001]) → `duplicate_page` 횟수 검증 ([S2-ISSUE-003]) → Undo 백업 ACL ([S2-ISSUE-002]).

## 10. Follow-up — 조치 적용 기록 (2026-11-22)

> 본 감사서 §4·§7 제안의 코드 반영 기록. 감사 본문(§1~§9)은 감사 시점 스냅샷으로 유지한다.

* [S2-ISSUE-001] `split_by_pages` 범위 모드에서 `start > page_count`인 파트는 skip(warning 로그) — 부분 겹침 clamp는 유지. 전부 skip되면 기존 `err_split_no_valid_ranges`로 종료.
* [S2-ISSUE-003] `duplicate_page` 횟수를 1~100(UI 스핀박스 계약)으로 제한, 범위 밖은 `err_duplicate_count_invalid` (KO/EN/FALLBACK 키 추가).
* [S2-ISSUE-002] `temp_cleanup.py`에 `restrict_temp_file_permissions` core helper를 두고 `ai/temp_acl.py`는 facade로 유지. Undo 백업 디렉터리 생성 시 + `copy2` 직후에 best-effort 적용 (실패 시 warning 로그, AI temp와 동일 수준).
* [S2-ISSUE-004] 데드 `_register_undo_action` 정의 + mixin 배선 제거 (유일 등록 경로는 `apply_undo_registration`).
* 신규 회귀: `tests/test_audit_2026_11_22_scope2_followup.py` 6건.
* 검증: `python -m pyright src/core src/ui` → **0 errors**, `ruff check` → 통과, `python -m pytest -q` → 제품 실패 0건 (잔여 FAILED 1건은 깨진 system-python env의 `qframelesswindow` 부재, 코드 무관 + teardown AV 1회 관측).
