# SOLID 전 계층 코드 분할 설계

**날짜:** 2026-07-21  
**범위:** Worker 도메인 · Core 인프라 · UI 잔여 대형 모듈  
**원칙:** Move-only 우선, public import 경로 유지, 동작·mode·kwargs 계약 불변, 심볼 누락 0

## 목표

단일 파일이 비대해진 영역을 기능 폴더로 분리하고 SOLID(특히 SRP/OCP)에 맞게 다듬는다.  
기존 facade/budget 테스트 패턴을 확장하며, `pytest`·`pyright` 통과를 게이트로 한다.

## 접근

**하이브리드 (패키지 기계 분할 + 순수 헬퍼 분리)**

1. 대형 믹스인/모듈 → 하위 패키지 + thin facade
2. 이미 순수에 가까운 헬퍼만 별도 모듈
3. i18n 카탈로그·QSS 문자열 대용량 파일은 데이터 성격상 제외

## 대상 구조 (요약)

### Worker

- `worker_ops/annotation/` ← `annotation_ops.py`
- `worker_ops/extract/` ← `extract_ops.py`
- `worker_ops/cleanup/` ← `cleanup_ops.py`
- `worker_ops/page/` ← `page_ops.py`
- `worker_ops/transform/` ← `transform_ops.py`
- `worker_ops/compare/` ← `compare_ops.py`
- 각 `*_ops.py`는 re-export facade (≤80줄)

### Core

- `settings/` ← `settings.py` (defaults / normalize / persistence / api_key)
- `constants/` ← 도메인 그룹 상수 + facade
- `undo/` ← ActionRecord / UndoManager (선택 분할)

### UI

- `preview_widget/` 내부 믹스인 분리 (document / navigation / zoom / search / theme)
- `thumbnail/` 내부 믹스인 분리 (loading / layout / selection)
- `progress/` ← `progress_overlay.py`
- `main_window_worker.py` 잔여 로직을 `window_worker/`로 흡수

## 호환성

- `from src.core.worker_ops.annotation_ops import WorkerAnnotationOpsMixin` 등 기존 경로 유지
- `from src.core.settings import load_settings` 유지
- `WorkerPdfOpsMixin` MRO 조합 유지, public mode 이름 불변

## 검증

1. 분할 전 AST 심볼 스냅샷
2. 분할 후 동일 메서드/함수 export
3. `python -m pytest -q`
4. `python -m pyright`
5. structure budget facade ≤80줄 확장

## PR Plan (구현 단계)

| PR | 내용 |
|----|------|
| P1 | annotation + extract 패키지 |
| P2 | cleanup + page + transform + compare |
| P3 | settings 패키지 |
| P4 | preview / thumbnail / progress |
| P5 | main_window_worker 흡수 + constants/undo |
| P6 | budget 테스트·문서·최종 검증 |

## Key Decisions

1. **Mixin composition 유지** — 전면 핸들러 레지스트리 재설계는 회귀 위험이 커서 채택하지 않음
2. **Facade 경로 고정** — 테스트·외부 import 파손 방지
3. **i18n base 카탈로그 비분할** — 데이터 딕셔너리, SRP 이득 적음

## Implementation Notes (2026-07-21 완료)

### 적용됨

| 영역 | 결과 |
|------|------|
| `worker_ops/annotation|extract|cleanup|page|transform` | 하위 패키지 + thin `*_ops.py` facade |
| `worker_ops/compare` | 패키지화 (`compare/ops.py` 단일 클래스 유지 — 교차 메서드 pyright 안정) |
| `settings` | `_settings_impl/` (config/normalize/defaults/persistence/api_key) + facade |
| `constants` | `_constants_impl/values.py` + facade |
| `undo_manager` | `_undo_impl/` (models + manager) + facade |
| `progress_overlay` | `ui/progress/` (overlay + spinner) + facade |
| structure budget | 신규 facade 경로 예산·심볼 보존 테스트 확장 |

### 의도적 비분할 / 유지

| 항목 | 사유 |
|------|------|
| `preview_widget/widget.py`, `thumbnail/grid.py` | PyQt 시그널·MRO·pyright 교차 속성 비용이 이득을 상회 |
| `main_window_worker.py` 오버라이드 | `ToastWidget`/`WorkerThread` 모듈 단위 monkeypatch 테스트 계약 |
| i18n `ko_base`/`en_base`, QSS dark/light | 데이터/스타일 문자열 |

### 검증

- `python -m pytest -q` — 통과
- `python -m pyright` — 0 errors
