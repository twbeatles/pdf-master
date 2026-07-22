# PDF Master Project Analysis And Feature Roadmap

Date: 2026-07-22

This roadmap tracks the current implementation baseline after the Worker/AI/compare stabilization passes, the **v4.5.6 PyMuPDF deep-util** feature pack (dependency-free), the **2026-07-15 PROJECT_AUDIT follow-up** (AI cancel/encrypted unlock, blank-page safety, visual_error compare), the **2026-07-21 SOLID code split** (domain packages + thin facades), and the **2026-07-22 PROJECT_AUDIT follow-up** (temp orphan sweep, thumbnail sender guard, interruptible AI retry, cleanup confirm dialogs, cancel rollback hardening).

## Current Baseline

- Preview remains based on QtPdf (`QPdfDocument`, `QPdfView`, search/bookmark/navigation models).
- Worker execution is organized through `src.core.worker_runtime` and responsibility-based `src.core.worker_ops` domain packages (`annotation`/`extract`/`cleanup`/`page`/`transform`/`compare` + remaining ops modules) with stable `*_ops.py` facades.
- `OperationSpec` is the source of truth for required kwargs, output kind, result payload keys, preview refresh, and cancel cleanup policy.
- Compression profiles (`fast` / `compact` / `web`) now drive both save flags and optional **image downsample + font subsetting**.
- Page cleanup modes: `remove_blank_pages`, `dedupe_pages`, `split_by_bookmarks`, `auto_bookmarks`, `sanitize_pdf`, `impose_nup`.
- Crop supports `crop_mode=margins|content`; redaction supports search text and **area rects** (UI confirms destructive area redaction).
- Form fill can be baked with `flatten_form` (`Document.bake(widgets=True)`).
- Encrypt accepts granular `permissions` lists; UI exposes print/copy/modify/annotate/form/assemble. Batch encrypt reuses the same permission resolver when kwargs are supplied.
- `compare_pdfs` supports `compare_mode=text|visual|both` with optional visual diff PDF; visual failures surface as `visual_error` (not silent identical).
- `convert_to_svg` exports page vectors via `page.get_svg_image()`.
- Atomic PDF save falls back when `linear` is unsupported (PyMuPDF 1.28+).
- AI uses `google-genai` only; legacy `google-generativeai` paths are out of scope.
- AI ops honor cooperative cancel via `cancel_check`; encrypted PDFs may unlock using preview `passwords` into a temp cleartext path for File API/text extract.
- AI retry sleep is interruptible; cancelled errors are not retried. Chat session creation is single-flight per cache key.
- `src/core/temp_cleanup.py` removes orphan `pdf_master_ai_*` / `.pdf_master_*` files on startup, cancel, force-terminate, and shutdown.
- Thumbnail loader signals ignore stale senders after PDF switch.
- Blank/dedupe/sanitize actions require UI confirmation (same policy family as redaction).
- Cancel single-file rollback uses only `created_output_paths` (no mtime heuristic).
- Legacy public import paths remain stable after the 2026-05-13 refactor and the 2026-07-21 SOLID package split.
- Settings/constants/undo implementations live under `_settings_impl` / `_constants_impl` / `_undo_impl` with facade modules at the previous paths.
- Progress UI lives under `src/ui/progress/` with `progress_overlay.py` facade.

## Spec / Docs / Gitignore Audit

- `pdf_master.spec` package name tracks app version (`PDF_Master_v4.5.6`); hiddenimports include `src.core.temp_cleanup` and domain packages for freeze analysis.
- README, README_EN, CLAUDE, GEMINI, this roadmap, `PROJECT_AUDIT.md` (current functional findings + follow-up), the SOLID design doc under `docs/superpowers/specs/`, and the historical contract file `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-22.md` share the same validation/build command contract.
- `.gitignore` excludes build/dist, pytest temp, CodeGraph/agent tooling (`terminals/`, `.codegraph/`, `.grok/`, `mcps/`), session/agent scratch, atomic temps (`.pdf_master_*`), AI unlock temps (`pdf_master_ai_*`), and local settings backup accidents.

## Validation Contract

```bash
python -m pyright
python -m pytest -q
python -m build
python -m PyInstaller pdf_master.spec --clean
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
python main.py --smoke
```

Current local baseline (2026-07-22): `python -m pytest -q` → **230 collected / 229 passed / 1 opt-in Gemini smoke skipped**. Deep-util + audit-follow-up + SOLID-split + 2026-07-22 audit follow-up regression tests are included.

## Next Priorities

1. Run the real Gemini File API smoke periodically in a keyed environment with `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` and `GEMINI_API_KEY`.
2. Richer compare/report UI beyond the current completion summary dialog (structured payload already includes `visual_error_count`).
3. Define OCR design and optional dependency strategy (`pdf-master[ocr]`) before adding Tesseract or similar.
4. Preview interactive area selection for crop/redact (Worker rect path already exists; coordinate text entry + confirm is shipped for area redaction and cleanup modes).
5. SDK-level AI request abort (cooperative cancel covers stream/retry boundaries; in-flight HTTP may still finish).
6. Keep facade line-budget and public import tests in place so compatibility shims do not grow again.
7. Optional: Protocol-host typed mixins for preview/thumbnail if further UI splits are needed without pyright regressions.
8. Optional: batch encrypt permission UI parity with the Security tab (Worker kwargs already support permissions/owner/user).
