# SOLID 코드 분할 Round 2 설계 (구현 완료)

**날짜:** 2026-08-05  
**범위:** 옵션 B — 고우선 대형 모듈 + Worker 잔여 도메인 패키지화  
**원칙:** move-only · public import/mode/kwargs 불변 · 심볼 누락 0

## 적용 결과

| Phase | 대상 | 결과 구조 |
|-------|------|-----------|
| P1 | UI textbox 액션 | `markup_actions/textbox.py` facade + `textbox_impl/{coords_style,placement,queue,actions,callbacks}.py` |
| P2a | Worker textbox | `annotation/textbox_helpers.py` + thin wrappers on mixin |
| P2b | Compare | `compare/helpers.py` (block/text geometry) + `ops.py` 진입점 |
| P3a | Thumbnail grid | `grid.py` shell + `grid_{layout,loading,selection,theme}.py` mixins |
| P3b | Text placement | `text_placement_geometry.py` + `text_placement.py` overlay |
| P4 | Tab builders | `edit_sections/*`, `markup_sections/*` + thin orchestrators |
| P5 | Worker 잔여 | `ai/`, `batch/`, `compose/`, `form/`, `security/` + `*_ops.py` facade; `_pdf_helpers_impl/` + facade |

## 의도적 비분할 / 부분 유지

- `main_window_worker.py` 메서드 surface — ToastWidget/WorkerThread **모듈 단위 monkeypatch** 계약 (본문은 `window_worker/success|fail` 로 이동)
- `tabs_ai/actions.py` — `AI_AVAILABLE`/`QDialog` monkeypatch 및 `__module__`/`atomic_text_write` source 계약으로 **단일 파일 유지**
- i18n base catalogs, theme QSS

## 후속 cleanup (같은 날짜)

- `interaction_overlays` → `interaction_{region,placement,queue}` + facade
- `PreviewWidgetHost` / `ThumbnailGridHost` + cooperative `__init__`
- `file_selection` → drop_zone/file_selector; `security_impl`; `misc_sections`

## 재현 스크립트

- `scripts/run_solid_split_2026_08_05.py` (P1)
- `scripts/_split_p2_textbox_helpers.py`, `_split_p2_compare_helpers.py`
- `scripts/_split_p3_text_placement.py`, `_split_p3_thumbnail_grid.py`
- `scripts/_split_p4_tab_builders.py`
- `scripts/_split_p5_worker_packages.py`

## 검증

- structure budget 확장: `tests/test_worker_structure_budget.py`
- `python -m pyright`
- `python -m pytest -q`

---

## Addendum: Round 2 잔여 정리 (옵션 C + pyright Host)

**날짜:** 2026-08-05 (후속)

| 항목 | 결과 |
|------|------|
| Preview/Thumbnail Host | `src/ui/_typing.py` — `PreviewWidgetHost`, `ThumbnailGridHost` + cooperative `__init__` |
| interaction_overlays | `interaction_region` / `interaction_placement` / `interaction_queue` + facade |
| main_window_worker | `window_worker/success.py`, `fail.py` 헬퍼; ToastWidget/WorkerThread 모듈 바인딩 유지 |
| file_selection | `drop_zone.py` + `file_selector.py` + facade |
| tabs_ai actions | **유지** (단일 파일) — `AI_AVAILABLE`/`QDialog` monkeypatch 및 `__module__`/`atomic_text_write` source 계약 |
| tabs_basic security | `security_impl/{setup,actions}.py` |
| tab_builders misc | `misc_sections/*` |
| text_placement | 인라인 편집기 Optional narrowing 수정 |

재현: `scripts/_add_mixin_hosts.py`, `_split_c2_interaction_overlays.py`, `_split_c4_remaining_ui.py`
