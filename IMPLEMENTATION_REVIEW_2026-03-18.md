# Implementation Review 2026-03-18

## Scope

- Reviewed implementation gaps against `README.md`, `README_EN.md`, `CLAUDE.md`, and the active codebase.
- Followed up by implementing the approved fixes in preview, worker ops, i18n, docs, and regression tests.
- Re-checked packaging (`pdf_master.spec`) and repository hygiene (`.gitignore`) after the code changes.

## Completed Items

| Item | Status | Notes |
|------|--------|-------|
| Main preview uses `ZoomablePreviewWidget` | Done | Wheel zoom, drag pan, page navigation, print, and controlled pixmap updates are now on the real preview path. |
| Preview rerender after resize/splitter move | Done | Controlled preview emits `renderRequested`; main window rerenders after viewport changes. |
| `resize_pages` fit-center behavior | Done | Original content is placed on a new target-size page while preserving aspect ratio. |
| Auto output filename collision handling | Done | `convert_to_img` and `extract_text` use `name`, `name__2`, `name__3`, ... stems. |
| Worker message i18n follow-up | Done | Updated touched AI/batch/annotation/extract flows to use catalog-backed messages. |
| `compare_pdfs` order/duplicate diff | Done | Sequence-based line diff now catches line-order changes and duplicate-count changes. |
| Optional visual diff PDF UI path | Done | Advanced tab compare flow forwards `generate_visual_diff`. |
| Docs sync | Done | `README.md`, `README_EN.md`, `CLAUDE.md`, and `GEMINI.md` now describe the current runtime behavior. |
| Regression tests | Done | Added focused tests for preview, compare diffing, output naming, resize behavior, and worker i18n smoke coverage. |

## Packaging Check

- `pdf_master.spec` was reviewed after the preview refactor.
- Added an explicit `src.ui.zoomable_preview` hidden import because the widget is now runtime-critical for the main right-side preview panel.
- No extra data-file packaging was required for the new behavior:
  - `src/core/i18n_catalogs/*` remains packaged as Python modules.
  - The compare visual diff flow writes runtime output files only and does not need bundled assets.

## Gitignore Check

- `.gitignore` was re-checked after validation runs.
- Existing rules already cover the generated artifacts seen during work:
  - `__pycache__/`
  - `.pytest_cache/`
  - `build/`
  - `dist/`
  - `.pdf_master_*.tmp.pdf`
- No additional ignore rule was required for the implemented changes.

## Validation

- `pyright`
  - Passed with `0 errors`
- `python -m pytest -q`
  - Passed in the current environment

## Follow-up Notes

- The repository still reports version `v4.5.4` in docs/spec naming. I did not bump the app version because this review/fix batch was implemented as an in-place maintenance update rather than a requested release version change.
- If a release cut is planned later, the next cleanup candidate is to normalize some remaining legacy doc sections that still describe features more generically than the current runtime behavior.
