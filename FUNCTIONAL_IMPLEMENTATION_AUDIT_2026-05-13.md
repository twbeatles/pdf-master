# PDF Master 기능 구현 및 구조 정합성 감사

작성일: 2026-05-13

## 감사 범위

`README.md`, `README_EN.md`, `CLAUDE.md`, `GEMINI.md`, `PROJECT_ANALYSIS_AND_FEATURE_ROADMAP.md`, `pdf_master.spec`, `.gitignore`를 현재 코드베이스와 대조했다. 기준 코드는 F-01~F-07 개선과 후속 코드 분할 리팩토링이 모두 반영된 상태다.

확인한 주요 구현 표면:

- Worker 실행 계약: `src/core/worker_runtime/*`, `src/core/worker_ops/*`
- PDF 검증 공용화: `src/core/pdf_validation.py`
- AI 서비스 분리: `src/core/ai_service.py`, `src/core/ai/*`
- UI facade 분리: `src/ui/widgets.py`, `thumbnail_grid.py`, `zoomable_preview.py`, `styles.py`, `tabs_advanced/builders.py`
- 패키징: `pdf_master.spec`, `scripts/package_smoke.ps1`, `main.py --smoke`
- 무시 규칙: `.gitignore`, `git check-ignore -v`

## 현재 결론

이전 감사 항목 F-01~F-07은 구현 완료 상태다. 추가로 긴 파일 분할 리팩토링도 동작 변경 없이 완료되었고, 기존 public import 경로와 Worker mode 이름은 유지된다.

주요 완료 항목:

- `OperationSpec.required_any_kwargs`로 파일 출력 mode의 `output_path`/`output_dir` one-of 계약을 preflight에서 fail-fast 처리한다.
- `ai_summarize`는 UI 메모리 결과를 허용해야 하므로 `output_path` optional 상태를 유지한다.
- Worker preflight와 UI file widget이 `src/core/pdf_validation.py`의 PDF size/header 검증을 공유한다.
- `progress_overlay.py`, common file widgets의 사용자 표시 문자열은 KO/EN i18n catalog와 runtime hardcoded-string smoke 대상에 포함된다.
- Gemini File API smoke는 `PDF_MASTER_GEMINI_FILE_API_SMOKE=1`과 `GEMINI_API_KEY`가 있을 때만 실제 API를 호출한다.
- `main.py --smoke`와 `scripts/package_smoke.ps1`로 앱 초기화 및 PyInstaller EXE smoke를 자동화했다.
- `_pdf_impl.py`, `ai_service.py`, `widgets.py`, `thumbnail_grid.py`, `zoomable_preview.py`, `styles.py`, `tabs_advanced/builders.py`, `i18n_catalogs/shared.py`는 compatibility facade로 축소했다.

## 구조 분할 현황

Worker handler는 책임 단위로 분리되어 있다.

- `page_ops.py`: split/reorder/page insert/replace/duplicate/reverse/page-number 계열
- `compare_ops.py`: PDF 비교
- `form_ops.py`: form field 조회/채우기
- `extract_ops.py`: text/image/link/info/bookmark/markdown/attachment 추출
- `annotation_ops.py`: highlight/redact/shape/link/textbox/sticky/ink annotation
- `compose_ops.py`: merge/images-to-PDF/copy-page 계열
- `transform_ops.py`: metadata/compress/crop/resize 계열

AI와 UI도 facade 뒤 하위 패키지로 분리되어 있다.

- `src/core/ai/*`: Gemini client/config/cache/schema/prompt/session/generation/service/errors
- `src/ui/common_widgets/*`: file selector, list, empty state, toast, validators
- `src/ui/thumbnail/*`: document, loader, tile, grid
- `src/ui/preview_widget/*`: preview widget, search helpers
- `src/ui/tabs_advanced/tab_builders/*`: edit/extract/markup/misc/advanced builders
- `src/ui/theme/*`: colors, dark QSS, light QSS
- `src/ui/window_worker/*`: helper/result/undo/same-path 로직

## Spec / 문서 / .gitignore 정합성

- `pdf_master.spec`는 새 하위 패키지 `src.core.ai`, `src.ui.common_widgets`, `src.ui.preview_widget`, `src.ui.thumbnail`, `src.ui.theme`, `src.ui.tabs_advanced.tab_builders`를 hidden import 수집 대상으로 포함한다.
- `README.md`, `README_EN.md`, `CLAUDE.md`, `GEMINI.md`, `PROJECT_ANALYSIS_AND_FEATURE_ROADMAP.md`는 현재 split-package 구조, smoke 명령, opt-in Gemini smoke 정책, facade 유지 정책을 반영한다.
- `.gitignore`는 `build/`, `dist/`, `.pytest_tmp/`, `.pytest_cache/`, `pdf_master.egg-info/`, `*.whl`, `*.tar.gz`, `.pdf_master_*.tmp*`를 제외한다.
- `git check-ignore -v`로 package smoke EXE, PyInstaller 산출물, pytest 임시 디렉터리, egg-info, atomic temp 파일이 실제 무시되는 것을 확인했다.

## 검증 결과

현재 로컬 기준 검증:

| 검증 | 결과 |
| --- | --- |
| `python -m pyright` | 통과: 0 errors, 0 warnings |
| `python -m pytest -q` | 통과: 165 collected, 164 passed, 1 skipped |
| `python -m build` | 통과: sdist/wheel 생성 |
| `powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1` | 통과: clean `PYTHONPATH` PyInstaller 빌드 + EXE `--smoke` |
| Gemini File API smoke | 환경 변수 미설정 시 skip되는 opt-in 테스트 |

PyInstaller 경고 중 `pycparser.lextab`/`pycparser.yacctab` hidden import not found, Python 3.14/Pydantic V1 경고는 현재 smoke 실행에는 영향을 주지 않는 비치명 경고로 확인했다.

## 남은 운영 메모

- 실제 Gemini File API 연동은 비용/키가 필요한 opt-in 검증이므로 keyed 환경에서 별도로 주기 실행한다.
- compatibility facade line budget 테스트는 유지해야 한다. 새 기능 추가 시 facade가 다시 비대해지면 domain module에 구현을 둔다.
- `.gitignore`는 현재 산출물을 충분히 덮고 있어 추가 규칙은 필요하지 않다. 새 빌드 도구나 릴리스 산출물이 추가될 때만 재검토한다.
