# PDF 편집기 구현 리스크/개선 감사 보고서 (v4.5.4 유지보수 addendum 포함)

- 작성일: 2026-02-26
- 대상 저장소: `d:\twbeatles-repos\pdf-master`
- 기준 문서: [README.md](README.md), [CLAUDE.md](CLAUDE.md)
- 점검 범위: `F-01~F-07` (핵심 결함/정책/노출 항목)
- 점검 기준: 사용자 데이터 신뢰성, 보안, 기능 실패 가능성 우선

## 2026-03-09 유지보수 addendum

- 범위: 정적 타입 정합성, 인코딩 점검, 문서/spec/.gitignore 동기화
- 반영 결과:
  1. `pyrightconfig.json` 추가 후 저장소 전체 `pyright .` → `0 errors`
  2. `src/core/_typing.py`, `src/ui/_typing.py` 추가로 Worker/UI 믹스인 host 계약 명시
  3. UTF-8 decode 실패 `0`, U+FFFD(`�`) 검색 결과 `0`
  4. `pdf_master.spec`를 importlib 기반 optional Gemini SDK 로딩과 `_typing` 모듈 반영 상태로 갱신
  5. `.gitignore`에 Python 검사/커버리지/패키징 산출물 패턴 보강
  6. `pytest -q` 재검증 결과 `50 passed`

## 심각도 기준

- BLOCKER: 보안/데이터 손상/핵심 기능 전면 차단
- HIGH: 결과 정확성/기능 성공률에 직접 영향
- MEDIUM: 안정성/유지보수/정책 일관성 리스크
- LOW: 제품 정합성/노출 정책 리스크

## 공개 API/인터페이스 영향

- 시그니처 변경: 없음
- 동작 정책 변경:
  1. `copy_page_between_docs`: 무효 `page_range`는 묵시 폴백 없이 즉시 오류 반환
  2. `add_link(goto)`: Worker 경계에서 0-based 페이지 인덱스만 허용
  3. `extract_attachments`: 파일명 정규화 + 경로 탈출 차단 + 중복명 suffix 정책

## 상태 요약

| 항목 | 심각도 | 상태 |
|---|---|---|
| F-01 배치 워터마크 런타임 실패 | HIGH | 해결 |
| F-02 페이지 복사 무효 범위 묵시 폴백 | HIGH | 해결 |
| F-03 첨부 추출 경로 정규화 부재 | HIGH | 해결 |
| F-04 `fitz.open()` 정리 패턴 불균일 | MEDIUM | 해결 |
| F-05 링크 페이지 0/1-based 혼용 | MEDIUM | 해결 |
| F-06 테스트 커버리지 편중 | MEDIUM | 부분 완화(잔여) |
| F-07 구현 존재/UI 미노출 | LOW | 해결 |

---

## 확정 리스크 조치 내역

### F-01. 배치 워터마크 런타임 실패

- 심각도: HIGH
- 영향 범위: `batch(operation=watermark)` 결과 파일 생성 실패 가능
- 근거(파일:라인): `src/core/worker.py:566`, `src/core/worker.py:596`, `src/core/worker.py:631`
- 재현 시나리오: 단일 PDF + `operation=watermark` + 텍스트 옵션
- 원인(개선 전): `insert_text(..., align=1)` 사용으로 런타임 인자 오류
- 권장 수정: `insert_textbox` 기반 정렬 처리 + 파일별 실패 원인 요약
- 반영 결과: 적용 완료 (`insert_textbox` 전환, `failed_files` 요약 메시지 추가)
- 검증 테스트: `tests/test_worker_batch_watermark.py`

### F-02. 페이지 복사 무효 범위 입력 시 묵시 복사

- 심각도: HIGH
- 영향 범위: 사용자 의도와 다른 페이지가 출력될 가능성
- 근거(파일:라인): `src/core/worker_ops/pdf_ops.py:1416`, `src/core/worker_ops/pdf_ops.py:1434`, `src/core/worker_ops/pdf_ops.py:1446`
- 재현 시나리오: `copy_page_between_docs`에서 `page_range='abc'`
- 원인(개선 전): 파싱 실패 시 1페이지 폴백 경로 존재
- 권장 수정: 무효/누락 범위 hard-fail, 출력 파일 미생성 보장
- 반영 결과: 적용 완료 (`err_copy_pages_required`/`err_invalid_page_range`로 즉시 종료)
- 검증 테스트: `tests/test_worker_copy_page_range_strict.py`

### F-03. 첨부 추출 경로 정규화 부재

- 심각도: HIGH
- 영향 범위: 경로 탈출/덮어쓰기 위험
- 근거(파일:라인): `src/core/worker.py:172`, `src/core/worker.py:184`, `src/core/worker.py:946`, `src/core/worker.py:967`
- 재현 시나리오: 첨부명에 `../`, `..\`, 금지문자, 정규화 후 중복명 포함
- 원인(개선 전): 첨부명을 `output_dir`와 직접 결합
- 권장 수정: `basename` 강제, 위험문자 치환, 빈 이름 fallback, 중복 suffix, base-dir 검증
- 반영 결과: 적용 완료 (`_sanitize_attachment_filename`, `_build_safe_attachment_output_path` 도입)
- 검증 테스트: `tests/test_worker_attachment_extract_security.py`

### F-04. `fitz.open()` 리소스 정리 패턴 불균일

- 심각도: MEDIUM
- 영향 범위: 예외 경로에서 문서 핸들 정리 누락 가능성
- 근거(파일:라인):
  - `src/core/worker.py:639` (`get_pdf_info`)
  - `src/core/worker.py:689` (`get_bookmarks`)
  - `src/core/worker.py:714` (`set_bookmarks`)
  - `src/core/worker.py:731` (`search_text`)
  - `src/core/worker.py:768` (`extract_tables`)
  - `src/core/worker.py:806` (`decrypt_pdf`)
  - `src/core/worker.py:827` (`list_annotations`)
  - `src/core/worker.py:867` (`add_annotation`)
  - `src/core/worker.py:903` (`remove_annotations`)
  - `src/core/worker.py:926` (`add_attachment`)
  - `src/core/worker.py:946` (`extract_attachments`)
- 재현 시나리오: 각 메서드 내 예외 유도 시 자원 정리 경로 확인
- 원인(개선 전): `doc.close()` 보장 패턴 불일치
- 권장 수정: `try/finally`로 `fitz.open()` 자원 정리 통일
- 반영 결과: 적용 완료 (대상 메서드 전수 반영)
- 검증 테스트: `tests/test_worker_resource_management_structure.py`

### F-05. 링크 대상 페이지 인덱스 정책 혼용

- 심각도: MEDIUM
- 영향 범위: 링크 대상 페이지 오해/오동작 가능
- 근거(파일:라인): `src/core/worker_ops/pdf_ops.py:1264`, `src/core/worker_ops/pdf_ops.py:1313`, `src/core/worker_ops/pdf_ops.py:1315`, `src/ui/tabs_advanced/actions_markup.py:190`
- 재현 시나리오: UI에서 페이지 링크 입력 후 Worker 전달값/범위 오류 확인
- 원인(개선 전): Worker에서 0/1-based 혼용 허용
- 권장 수정: 정책 단일화(Worker는 0-based만 허용, UI에서 사전 정규화)
- 반영 결과: 적용 완료 (UI `-1` 정규화 + Worker strict 검증)
- 검증 테스트: `tests/test_link_index_policy.py`

### F-07. 구현은 있으나 UI 미노출 모드

- 심각도: LOW
- 영향 범위: 제품 기능 가시성과 문서 정합성 저하
- 근거(파일:라인):
  - `src/ui/tabs_advanced/builders.py:685` (`replace_page`/`set_bookmarks`/`add_annotation` 그룹)
  - `src/ui/tabs_advanced/actions_misc.py:117` (`action_replace_page`)
  - `src/ui/tabs_advanced/actions_misc.py:140` (`action_set_bookmarks`)
  - `src/ui/tabs_advanced/actions_markup.py:235` (`action_add_annotation_basic`)
  - `src/ui/main_window_worker.py:114`~`116` (mode 설명 매핑)
- 재현 시나리오: 고급 탭 Misc에서 각 기능 실행 시 Worker 모드 호출 확인
- 원인(개선 전): Worker 구현 대비 UI 액션/설명 미연결
- 권장 수정: 기본형 UI 노출 + i18n 키 + mode description 추가
- 반영 결과: 적용 완료
- 검증 테스트: `tests/test_advanced_new_modes_ui_flow.py`

---

## 잔여 리스크

### F-06. 테스트 커버리지 편중 (부분 완화)

- 심각도: MEDIUM
- 현재 상태:
  - `pytest -q` 전체 통과: **50 passed**
  - 고위험 경로(F-01~F-05, F-07) 대상 신규 테스트는 반영 완료
- 잔여 이슈:
  - 모든 UI 모드의 end-to-end 회귀를 포괄하지는 않음
  - 대용량/실제 운영 입력(대량 파일, 특수 PDF) 중심 시나리오는 추가 여지 존재
- 후속 권장:
  1. 고급 탭 주요 모드에 대한 파일 생성/결과물 검증형 스모크 확대
  2. 보안 입력(첨부명, 링크, 범위 파싱) 퍼지 케이스 추가
  3. 실제 사용자 플로우 기반 통합 테스트(작업 큐/취소/Undo 연동) 확장

---

## D0~D14 로드맵 반영 상태

- D0~D2 (F-01/F-02/F-03): 완료
- D3~D7 (F-04/F-05): 완료
- D8~D14 (F-06/F-07):
  - F-07 완료
  - F-06 부분 완화(잔여 리스크 유지)

## 적용 파일 및 검증 요약

- 코드 변경:
  - `src/core/worker.py`
  - `src/core/worker_ops/pdf_ops.py`
  - `src/ui/tabs_advanced/builders.py`
  - `src/ui/tabs_advanced/actions_misc.py`
  - `src/ui/tabs_advanced/actions_markup.py`
  - `src/ui/main_window_worker.py`
  - `src/core/i18n.py`
- 테스트 추가:
  - `tests/test_worker_batch_watermark.py`
  - `tests/test_worker_copy_page_range_strict.py`
  - `tests/test_worker_attachment_extract_security.py`
  - `tests/test_worker_resource_management_structure.py`
  - `tests/test_link_index_policy.py`
  - `tests/test_advanced_new_modes_ui_flow.py`
- 문서 동기화:
  - `pdf_master.spec`
  - `README.md`
  - `README_EN.md`
  - `CLAUDE.md`
  - `GEMINI.md`
  - `PDF_EDITOR_AUDIT.md`
- 테스트 결과: `pytest -q` → **50 passed**
