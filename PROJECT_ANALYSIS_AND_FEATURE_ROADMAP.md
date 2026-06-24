# PDF Master Project Analysis And Feature Roadmap

Date: 2026-05-22

This roadmap tracks the current implementation baseline after the Worker, AI, compare, packaging, documentation, split-package stabilization, and 2026-05-22 audit follow-up pass.

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
- `get_pdf_info`, `search_text`, `extract_tables`, and `list_annotations` check cooperative cancellation inside page loops before writing output files.
- Credential-free fake SDK tests cover Gemini File API upload caching, generate/stream paths, chat reuse, structured parsing, and upload-fallback behavior; live Gemini smoke remains opt-in only.
- Text, PDF, image, and attachment outputs use atomic save paths where applicable.
- Legacy public import paths remain stable after the 2026-05-13 refactor: `_pdf_impl.py`, `ai_service.py`, `widgets.py`, `thumbnail_grid.py`, `zoomable_preview.py`, `styles.py`, and `tabs_advanced/builders.py` are facades over smaller modules.

## Spec / Docs / Gitignore Audit

- `pdf_master.spec` is aligned with split-package runtime imports and collects `src.core.ai`, `src.core.worker_ops`, `src.core.i18n_catalogs`, `src.ui.common_widgets`, `src.ui.preview_widget`, `src.ui.thumbnail`, `src.ui.theme`, `src.ui.tabs_advanced.tab_builders`, and the existing tab/window packages.
- `.gitignore` excludes build/test/package artifacts and `.pdf_master_*.tmp*` atomic-save temporary files.
- README, README_EN, CLAUDE, GEMINI, this roadmap, and the latest repo-local functional audit document (`FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md`) share the same validation/build contract.
- `.gitignore` coverage was rechecked with `git check-ignore -v` for `build/`, `dist/`, `.pytest_tmp/`, `.pytest_cache/`, `pdf_master.egg-info/`, `pip-wheel-metadata/`, wheel/sdist artifacts, package-smoke EXE output, `__pycache__/`, and `.pdf_master_*.tmp*`; `git ls-files -o --exclude-standard` showed no unignored generated leftovers.

## Validation Contract

```bash
python -m pyright
python -m pytest -q
python -m build
python -m PyInstaller pdf_master.spec --clean
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
python main.py --smoke
```

Current local baseline after the 2026-06-24 project audit follow-up: `python -m pyright` passes with 0 errors, `python -m pytest -q` collects 192 tests with 191 passed and 1 opt-in Gemini smoke skipped, `python -m build` produces sdist/wheel, and `scripts/package_smoke.ps1` rebuilds the PyInstaller EXE and runs `--smoke`. See `PROJECT_AUDIT.md` for the 2026-06-24 functional audit and implemented fixes.

## Next Priorities

1. Run the real Gemini File API smoke periodically in a keyed environment with `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` and `GEMINI_API_KEY`; credential-free fake SDK tests now cover the local File API contract.
2. Add richer compare/report UI beyond the current completion summary dialog.
3. Define OCR design and optional dependency strategy before adding any OCR engine or package extra.
4. Keep facade line-budget and public import tests in place so the compatibility shims do not grow again.
