# PDF Master Project Analysis And Feature Roadmap

Date: 2026-05-13

This roadmap tracks the current implementation baseline after the Worker, AI, compare, packaging, documentation, and split-package stabilization pass.

## Current Baseline

- Preview remains based on QtPdf (`QPdfDocument`, `QPdfView`, search/bookmark/navigation models).
- Worker execution is organized through `src.core.worker_runtime` and responsibility-based `src.core.worker_ops` domain mixins.
- `OperationSpec` is the source of truth for required kwargs, output kind, result payload keys, preview refresh, and cancel cleanup policy.
- `OperationSpec.required_any_kwargs` makes file output contracts explicit before handlers run.
- `src.core.pdf_validation` is the shared PDF size/header validator for Worker preflight and UI file widgets.
- AI uses `google-genai` only; legacy `google-generativeai` paths are out of scope.
- `src.core.ai_service` is a compatibility facade; the real Gemini client/cache/schema/session/prompt/service implementation lives under `src.core.ai`.
- UI chat histories are stored with `v2:{mtime_ns}:{normalized_path}` keys so replacing a PDF at the same path creates a separate conversation context.
- `split_by_pages` matches the current UI contract: `output_dir`, `split_mode`, and optional `ranges`; unsupported `pages_per_file` behavior is not part of this pass.
- Encrypted PDF workers can use explicit `password` or `passwords={normalized_path: password}` mapping, including preview-authenticated password reuse.
- `compare_pdfs` keeps existing TXT/PDF output behavior and now also returns structured payloads for UI summary dialogs.
- Text, PDF, image, and attachment outputs use atomic save paths where applicable.
- Legacy public import paths remain stable after the 2026-05-13 refactor: `_pdf_impl.py`, `ai_service.py`, `widgets.py`, `thumbnail_grid.py`, `zoomable_preview.py`, `styles.py`, and `tabs_advanced/builders.py` are facades over smaller modules.

## Spec / Docs / Gitignore Audit

- `pdf_master.spec` is aligned with split-package runtime imports and collects `src.core.ai`, `src.core.worker_ops`, `src.core.i18n_catalogs`, `src.ui.common_widgets`, `src.ui.preview_widget`, `src.ui.thumbnail`, `src.ui.theme`, `src.ui.tabs_advanced.tab_builders`, and the existing tab/window packages.
- `.gitignore` excludes build/test/package artifacts and `.pdf_master_*.tmp*` atomic-save temporary files.
- README, README_EN, CLAUDE, GEMINI, this roadmap, and the repo-local functional audit document share the same validation/build contract.
- `.gitignore` coverage was rechecked with `git check-ignore -v` for `build/`, `dist/`, `.pytest_tmp/`, `.pytest_cache/`, `pdf_master.egg-info/`, package-smoke EXE output, and `.pdf_master_*.tmp*`.

## Validation Contract

```bash
python -m pyright
python -m pytest -q
python -m build
python -m PyInstaller pdf_master.spec --clean
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
python main.py --smoke
```

Current local baseline: `python -m pyright` passes with 0 errors, `python -m pytest -q` collects 165 tests with 164 passed and 1 opt-in Gemini smoke skipped, `python -m build` produces sdist/wheel, and `scripts/package_smoke.ps1` rebuilds the PyInstaller EXE and runs `--smoke`.

## Next Priorities

1. Run the real Gemini File API smoke periodically in a keyed environment with `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` and `GEMINI_API_KEY`.
2. Add richer compare/report UI beyond the current completion summary dialog.
3. Define OCR design and optional dependency strategy.
4. Keep facade line-budget and public import tests in place so the compatibility shims do not grow again.
