# PDF Master Project Analysis And Feature Roadmap

Date: 2026-07-14

This roadmap tracks the current implementation baseline after the Worker/AI/compare stabilization passes and the **v4.5.6 PyMuPDF deep-util** feature pack (dependency-free).

## Current Baseline

- Preview remains based on QtPdf (`QPdfDocument`, `QPdfView`, search/bookmark/navigation models).
- Worker execution is organized through `src.core.worker_runtime` and responsibility-based `src.core.worker_ops` domain mixins, including **`cleanup_ops`**.
- `OperationSpec` is the source of truth for required kwargs, output kind, result payload keys, preview refresh, and cancel cleanup policy.
- Compression profiles (`fast` / `compact` / `web`) now drive both save flags and optional **image downsample + font subsetting**.
- Page cleanup modes: `remove_blank_pages`, `dedupe_pages`, `split_by_bookmarks`, `auto_bookmarks`, `sanitize_pdf`, `impose_nup`.
- Crop supports `crop_mode=margins|content`; redaction supports search text and **area rects**.
- Form fill can be baked with `flatten_form` (`Document.bake(widgets=True)`).
- Encrypt accepts granular `permissions` lists; UI exposes print/copy/modify/annotate/form/assemble.
- `compare_pdfs` supports `compare_mode=text|visual|both` with optional visual diff PDF.
- `convert_to_svg` exports page vectors via `page.get_svg_image()`.
- Atomic PDF save falls back when `linear` is unsupported (PyMuPDF 1.28+).
- AI uses `google-genai` only; legacy `google-generativeai` paths are out of scope.
- Legacy public import paths remain stable after the 2026-05-13 refactor.

## Spec / Docs / Gitignore Audit

- `pdf_master.spec` package name tracks app version (`PDF_Master_v4.5.6`).
- README, README_EN, CLAUDE, GEMINI, this roadmap, and the repo-local functional audit document (`FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md`) share the same validation/build contract.

## Validation Contract

```bash
python -m pyright
python -m pytest -q
python -m build
python -m PyInstaller pdf_master.spec --clean
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
python main.py --smoke
```

Current local baseline after the 2026-07-14 PyMuPDF deep-util pass: `python -m pyright` passes on changed worker modules, and `python -m pytest -q` passes with the new deep-compress / extras regression suites included (1 opt-in Gemini smoke remains skippable).

## Next Priorities

1. Run the real Gemini File API smoke periodically in a keyed environment with `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` and `GEMINI_API_KEY`.
2. Richer compare/report UI beyond the current completion summary dialog (structured payload already exists).
3. Define OCR design and optional dependency strategy (`pdf-master[ocr]`) before adding Tesseract or similar.
4. Preview interactive area selection for crop/redact (Worker rect path already exists).
5. Keep facade line-budget and public import tests in place so compatibility shims do not grow again.
