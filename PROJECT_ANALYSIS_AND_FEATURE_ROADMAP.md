# PDF Master Project Analysis And Feature Roadmap

Date: 2026-04-27

This roadmap tracks the current implementation baseline after the Worker, AI, compare, packaging, and documentation stabilization pass.

## Current Baseline

- Preview remains based on QtPdf (`QPdfDocument`, `QPdfView`, search/bookmark/navigation models).
- Worker execution is organized through `src.core.worker_runtime` and responsibility-based `src.core.worker_ops` mixins.
- `OperationSpec` is the source of truth for required kwargs, output kind, result payload keys, preview refresh, and cancel cleanup policy.
- AI uses `google-genai` only; legacy `google-generativeai` paths are out of scope.
- UI chat histories are stored with `v2:{mtime_ns}:{normalized_path}` keys so replacing a PDF at the same path creates a separate conversation context.
- `split_by_pages` matches the current UI contract: `output_dir`, `split_mode`, and optional `ranges`; unsupported `pages_per_file` behavior is not part of this pass.
- Encrypted PDF workers can use explicit `password` or `passwords={normalized_path: password}` mapping, including preview-authenticated password reuse.
- `compare_pdfs` keeps existing TXT/PDF output behavior and now also returns structured payloads for UI summary dialogs.
- Text, PDF, image, and attachment outputs use atomic save paths where applicable.

## Spec / Docs / Gitignore Audit

- `pdf_master.spec` is aligned with split-package runtime imports and keeps `src.ui.tabs_ai.actions_meta` as a compatibility shim hidden import.
- `.gitignore` excludes build/test/package artifacts and `.pdf_master_*.tmp*` atomic-save temporary files.
- README, README_EN, CLAUDE, GEMINI, implementation review, and feature review documents share the same validation/build contract.

## Validation Contract

```bash
python -m pyright
python -m pytest -q
python -m build
python -m PyInstaller pdf_master.spec --clean
```

## Next Priorities

1. Real Gemini File API smoke testing behind opt-in environment variables.
2. Further decomposition of `src/core/worker_ops/_pdf_impl.py`.
3. Advanced tab builder decomposition.
4. Richer compare/report UI beyond the current completion summary dialog.
5. OCR design and optional dependency strategy.
