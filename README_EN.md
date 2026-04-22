# PDF Master v4.5.5

📑 **All-in-One PDF Editor** - PyQt6 based Desktop Application

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Current Behavior Notes

- The right preview panel now uses `src/ui/zoomable_preview.py` directly for wheel zoom, drag pan, page navigation, and preview print.
- Preview text search is now asynchronous on a preview-dedicated worker, with collapse/expand UI, current-hit highlighting, next/previous navigation, and `Ctrl+F` entry.
- Preview print now goes through the Qt print pipeline instead of OS-level `print` delegation, so printer/page-range choices are applied to the actual job.
- AI/rotate thumbnail entry points stay synchronized with the right preview document, and encrypted PDFs reuse the authenticated preview password session for thumbnail loading.
- Preview rendering is refreshed after splitter moves and panel resize events to avoid stale low-resolution previews.
- `Resize Pages` keeps the original page aspect ratio and places the source page fit-centered on the target paper size.
- Auto-generated outputs from `PDF -> Image` and `Extract Text` avoid filename collisions with `__2`, `__3`, and later suffixes.
- `Compare PDFs` now detects line-order changes and duplicate-count differences, and visual diff PDF generation is optional from the Advanced tab UI.
- Single-input/single-output PDF mutation modes can save back to the original path; if preview is holding the same file, it is closed before the worker starts and restored after success/fail/cancel, including preview search query/index restoration.
- Output save/folder dialogs reuse `last_output_dir` as their starting directory and update it after successful output selection.
- Undo/Redo now restores before/after snapshots instead of re-running the worker, and the expanded snapshot flow covers `resize_pages`, `insert_signature`, `highlight_text`, `add_sticky_note`, `add_ink_annotation`, and `copy_page_between_docs`.
- Updated worker result/status messages in the touched flows are synchronized through the KO/EN i18n catalogs.

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Installation & Run](#-installation--run)
- [Usage](#-usage)
- [Shortcuts](#-shortcuts)
- [Build](#-build-pyinstaller)
- [Development Validation](#-development-validation)
- [Project Structure](#-project-structure)
- [Changelog](#-changelog)

---

## ✨ Key Features

### 📄 PDF Merge & Convert
| Feature | Description | Supported Formats |
|---------|-------------|-------------------|
| **PDF Merge** | Merge multiple PDFs into one | Drag & Drop supported |
| **PDF → Image** | Convert pages to images with collision-safe auto filenames | PNG, JPG, WEBP, BMP, TIFF |
| **Image → PDF** | Combine images into PDF | PNG, JPG, BMP, GIF, WEBP |
| **Extract Text** | Extract text from PDF with collision-safe TXT output naming | Save as TXT |

### ✂️ Page Editing
| Feature | Description |
|---------|-------------|
| **Extract Pages** | Extract specific pages (e.g., 1-3, 5, 7-10) |
| **Delete Pages** | Remove selected pages |
| **Rotate Pages** | Rotate 90°, 180°, 270° or only the selected pages |
| **Reorder Pages** | Rearrange pages via drag & drop |
| **Page Numbers** | Custom position/format/font (Page 1 of N, 1/N, etc.) |
| **Insert Blank Page** | Add blank page at desired position |
| **Duplicate Page** | Copy selected page |
| **Reverse Order** | Reverse page order |
| **Resize Pages** | Fit-center into A4, A3, Letter, Legal, etc. while preserving aspect ratio |
| **Replace Page** | Replace target page with a page from another PDF (v4.5.3) |

### 🔒 Security & Protection
| Feature | Description |
|---------|-------------|
| **Encrypt PDF** | Set AES-256 password |
| **Decrypt PDF** | Remove password |
| **Watermark** | Text/Tile watermark (custom opacity, rotation, position) |
| **Image Watermark** | Position(9), Scale, Opacity controls (v4.5 enhanced) |
| **Add Stamp** | Confidential, Approved, Draft, etc. |

### 🔧 Advanced Editing
| Feature | Description |
|---------|-------------|
| **Split PDF** | Split by page or range |
| **Compress PDF** | High/Medium/Low compression levels |
| **Crop PDF** | Trim margins |
| **Edit Metadata** | Modify title, author, subject, keywords |
| **Compare PDFs** | Analyze text differences including line order/duplicate changes, with optional visual diff PDF |
| **Set Bookmarks** | Save outline via `level|title|page` lines (v4.5.3) |

### 📝 Annotation & Markup
| Feature | Description |
|---------|-------------|
| **Highlight Text** | Highlighter effect |
| **Sticky Note** | Add memo notes |
| **Basic Annotation** | Add text/freetext annotation (v4.5.3) |
| **Underline/Strike** | Text markup |
| **Draw Shapes** | Add rectangles, circles, lines (v4.5) |
| **Add Hyperlinks** | URL or page navigation links (v4.5) |
| **Insert Textbox** | Add text directly to PDF (v4.5) |
| **Copy Pages** | Copy pages from another PDF (v4.5) |
| **Redact Text** | Permanently remove sensitive info |
| **Add Background** | Change page background color |
| **Freehand Ink** | Insert handwritten signature/drawing |

### 📊 Data Extraction
| Feature | Description | Output |
|---------|-------------|--------|
| **Extract Links** | List URLs inside document | Save as TXT |
| **Extract Images** | Extract embedded images | Save as PNG/JPG |
| **Extract Tables** | Extract table data | Save as CSV |
| **Extract Bookmarks** | Extract outline structure | Save as TXT |
| **Markdown Convert** | PDF → Markdown | Save as MD |
| **Attachment Manager** | Add/Extract attachments | Various formats |

### 🤖 AI Features (Gemini API)
| Feature | Description |
|---------|-------------|
| **PDF Summary** | AI-based document summary (Korean/English) |
| **PDF Chat** | Ask questions about PDF content to AI (v4.5) |
| **Keyword Extraction** | AI-based keyword extraction (v4.5) |
| **Summary Style** | Concise/Detailed/Bullet points |
| **Page Limit** | Set max pages to summarize |

> **Note**: AI features require `google-genai` package and a Gemini API key.

### 🎨 UI/UX
- **Multilingual Support** - English & Korean (Auto-detect & Manual switch)
- **Dark/Light Theme** - Premium Glassmorphism Design
- **Progress Overlay** - Full-screen dialog with cancellation
- **Toast Notifications** - Non-intrusive notifications
- **Drag & Drop** - Add files, reorder pages
- **Zoom/Pan Preview** - Mouse wheel zoom, drag move, page navigation, print, and resize-aware rerender
- **Preview Search** - Collapsible search bar, async text search, current-hit highlight, `Enter`/`Shift+Enter` navigation, and `Ctrl+F` focus
- **Thumbnail Grid** - View all pages at a glance with preview document/page synchronization
- **Rotate-tab Page Sync** - Clicking a thumbnail jumps the right preview to the same page
- **Undo/Redo** - Undo/Redo across single-output PDF mutation workflows
- **Same-path Save Safety** - Overwriting the source PDF is allowed for single-input/single-output mutation flows
- **Remember Output Folder** - Output dialogs reopen from the last successful output directory
- **Preview Print** - Print the current PDF through Qt print pipeline (v4.5)

---

## 🚀 Installation & Run

### Requirements
- Python 3.10 or higher
- Windows / macOS / Linux

### Install Dependencies
```bash
# Core packages
pip install PyQt6 PyMuPDF

# Validation toolchain
pip install -r requirements-dev.txt

# For builds
pip install PyInstaller

# For AI features (optional)
pip install google-genai

# Or legacy SDK (deprecated)
pip install google-generativeai
```

### Run
```bash
python main.py
```

---

## 📖 Usage

### 1. Merge PDF
1. Select **Merge** tab
2. Drag & drop files or click **Add Files**
3. Reorder list (Drag to move)
4. Click **Merge PDF** → Select save location

### 2. PDF → Image
1. Select **Convert** tab
2. Select PDF file
3. Choose output format (PNG, JPG, WEBP, etc.)
4. Set DPI (Default: 150)
5. **Convert** → Select output folder

### 3. Page Operations (Extract/Delete/Rotate)
1. Select **Page** tab
2. Select PDF file
3. For extract/delete, enter a page range (e.g., `1-3, 5, 7-10`)
4. For rotate, choose an angle and then choose the target scope:
   - `All pages`: rotate the whole document
   - `Selected pages`: rotate only pages chosen in the rotate-section thumbnails with `Ctrl`/`Shift`
5. A normal thumbnail click moves the right preview to the same page immediately
6. **Execute** → Select save location

### 4. Add Watermark
1. Select **Edit/Sec** tab
2. Select PDF file
3. Enter watermark text
4. Set options (Opacity, Size, Angle, Position)
5. Click **Add Watermark**

### 5. Encrypt PDF
1. Select **Edit/Sec** tab
2. Select PDF file
3. Enter password
4. Click **Encrypt**

### 6. AI Summary (Gemini API)
1. Select **AI Summary** tab
2. Enter API Key and click **Save**
3. Select PDF file
4. Choose Language (Korean/English)
5. Choose Style (Concise/Detailed/Bullet)
6. Click **AI Summary**

### 7. Reorder Pages
1. Select **Reorder** tab
2. Select PDF file (Automatically loads pages)
3. Drag pages to reorder
4. Click **Save**

### 8. Batch Processing
1. Select **Batch** tab
2. Add multiple PDF files
3. Select operation (Compress, Watermark, Encrypt, etc.)
4. Set common options
5. Click **Batch Run**

---

## ⌨️ Shortcuts

| Shortcut | Function |
|----------|----------|
| `Ctrl+O` | Open File |
| `Ctrl+Q` | Exit App |
| `Ctrl+T` | Toggle Theme |
| `Ctrl+F` | Open/Focus Preview Search |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+1` | Merge Tab |
| `Ctrl+2` | Convert Tab |
| `Ctrl+3` | Page Tab |
| `Ctrl+4` | Edit/Sec Tab |
| `Ctrl+5` | Reorder Tab |
| `Ctrl+6` | Batch Tab |
| `Ctrl+7` | Advanced Tab |
| `Ctrl+8` | AI Tab |

---

## 📦 Build (PyInstaller)

### Run Build
```bash
python -m PyInstaller pdf_master.spec --clean
```

### Build Result
- Output: `dist/PDF_Master_v4.5.5.exe`
- Size: ~30-40MB (UPX Compressed)

---

## ✅ Development Validation

- Prepare validation environment: `pip install -r requirements-dev.txt`
- Static analysis: `python -m pyright` -> `0 errors`
- Regression tests: `python -m pytest -q`
- `pytest` temp files stay inside repo-local `.pytest_tmp`
- Encoding audit: tracked text files pass UTF-8 decode/BOM/U+FFFD checks

---

## 📁 Project Structure

```
pdf-master/
├── .editorconfig
├── main.py
├── pdf_master.spec
├── pyrightconfig.json
├── requirements-dev.txt
├── typings/
├── README.md
├── README_EN.md
├── CLAUDE.md
├── GEMINI.md
└── src/
    ├── core/
    │   ├── ai_service.py
    │   ├── _typing.py              # worker mixin host contracts
    │   ├── constants.py
    │   ├── i18n.py                 # TranslationManager facade
    │   ├── i18n_catalogs/          # translation catalog storage
    │   ├── optional_deps.py        # fitz/keyring optional dependency boundary
    │   ├── settings.py
    │   ├── undo_manager.py
    │   ├── worker.py               # QThread facade
    │   ├── worker_runtime/         # shared runtime/dispatch/preflight
    │   └── worker_ops/             # split worker implementations
    │       ├── pdf_ops.py          # compatibility shim
    │       └── ai_ops.py
    └── ui/
        ├── main_window.py
        ├── _typing.py                   # UI mixin host contracts
        ├── main_window_config.py
        ├── main_window_tabs_basic.py     # compatibility shim
        ├── main_window_tabs_advanced.py  # compatibility shim
        ├── main_window_tabs_ai.py        # compatibility shim
        ├── main_window_core.py           # compatibility shim
        ├── main_window_preview.py        # compatibility shim
        ├── main_window_worker.py         # compatibility shim
        ├── main_window_undo.py           # compatibility shim
        ├── tabs_basic/                   # split basic-tab modules
        ├── tabs_advanced/                # split advanced-tab modules
        ├── tabs_ai/                      # split AI-tab modules
        ├── window_core/                  # split core-window modules
        ├── window_preview/               # split preview modules
        ├── window_worker/                # split worker-UI modules
        ├── window_undo/                  # split undo modules
        ├── progress_overlay.py
        ├── styles.py
        ├── thumbnail_grid.py
        ├── widgets.py
        └── zoomable_preview.py
```

Note: `main_window_*.py` remains a compatibility shim layer, while `worker.py` is the public `QThread` facade. Runtime worker flow and implementations now live in the folder modules.
Note: `src/core/optional_deps.py` centralizes `fitz`/`keyring` optional imports so `Pylance`/`Pyright` stays clean even when those packages are absent.
Note: `typings/` provides the minimal external stubs used by `pyrightconfig.json` so repository-level `python -m pyright` stays reproducible.
Note: when `PyMuPDF` is missing, only PDF-engine-dependent tests are skipped; the remaining regression tests still run.

---

## 🔧 Config File

Location: `~/.pdf_master_settings.json`

```json
{
  "theme": "dark",
  "language": "auto",
  "recent_files": [],
  "last_output_dir": "",
  "preview_search_expanded": true,
  "window_geometry": "..."
}
```

API key storage policy:
- `keyring` available: keyring-first save/load
- `keyring` unavailable: settings-file fallback (`gemini_api_key`)
- Legacy plain key is migrated/cleaned when keyring path is active
- `load_settings()` normalizes `recent_files`, `chat_histories`, `splitter_sizes`, `theme`, `language`, `window_geometry`, `last_output_dir`, and `preview_search_expanded` during load.

---

## 📝 Changelog

### v4.5.5 (2026-04-22) - Preview Search Hardening
- Moved preview text search to a preview-dedicated async `QThread` worker with request-id stale-result protection.
- Added preview search result caching keyed by `(abs_path, mtime_ns, query)` and kept search highlights as display-only overlays on the preview pixmap.
- Added controlled-vs-standalone preview search policy, `Ctrl+F`, `Enter`/`Shift+Enter`/`Esc` keyboard UX, and same-path search context restoration.
- Added regression coverage for preview search worker flow, preview search keyboard UX, and same-path search-state restore.

### v4.5.5 (2026-04-10) - Stability Bundle
- Added safe same-path overwrite handling by closing preview-held documents before worker start and restoring preview after success/fail/cancel.
- Reworked Undo/Redo to restore explicit before/after snapshots rather than re-running worker logic.
- Expanded Undo coverage to include `resize_pages`, `insert_signature`, `highlight_text`, `add_sticky_note`, `add_ink_annotation`, and `copy_page_between_docs`.
- Wired all output save/folder dialogs to `last_output_dir`.
- Moved `thumbnail_grid.py` user-facing strings into i18n and widened the runtime UI hardcoded-string smoke scan.
- Added regression coverage for output dialog state, same-path preview restore, and undo snapshot cleanup.

### v4.5.5 (2026-04-02) - Preview/Thumbnail/Undo Hardening
- Synced AI/rotate thumbnail flows to the active preview document before page jumps.
- Reused preview password sessions for encrypted thumbnail loading instead of prompting from the grid itself.
- Replaced OS print delegation with Qt print rendering so selected printer/page ranges affect the real output.
- Added cancellation checkpoints to `split`, `get_form_fields`, `fill_form`, and `add_freehand_signature`.
- Made app shutdown wait cooperatively before any forced worker termination.
- Expanded Undo coverage to single-source/single-output PDF mutation modes.
- Synced README/README_EN/CLAUDE/GEMINI/spec/.gitignore and added 8 regression suites for the new contracts.

### v4.5.4 (2026-03-18 addendum) - Rotate UX Upgrade
- Added a dedicated thumbnail list inside the Page tab rotate section.
- Added explicit `All pages` / `Selected pages` rotate scope toggle.
- Added partial rotation for Ctrl/Shift-selected pages only.
- Synced rotate thumbnails with the right-side preview navigation without clearing the selected rotate targets.
- Added focused regression tests for rotate selection and thumbnail state behavior.

### v4.5.4 (2026-03-25 validation follow-up) - Worker, Docs, and Build Consistency
- Fixed `add_ink_annotation` / `add_freehand_signature` persistence failures.
- Centralized strict page validation for page-targeted worker modes; only signature flows keep `-1` last-page sentinel support.
- Cancelled directory-output jobs now roll back only files created by the current run.
- Improved `compare_pdfs` sample output with paired before/after diff lines.
- Added `requirements-dev.txt`, `typings/`, and repo-local `.pytest_tmp` validation guidance.

### v4.5.4 (2026-03-18 core refactor) - Core Module Split Consistency
- Reduced `src/core/worker.py` to the public facade and moved shared execution flow into `src/core/worker_runtime/*`.
- Reorganized `src/core/worker_ops` into responsibility-based mixins (`compose/transform/annotation/extract/security/batch`).
- Kept `src/core/worker_ops/pdf_ops.py` as a compatibility shim so old imports continue to work.
- Kept runtime i18n APIs in `src/core/i18n.py` and moved translation catalogs into `src/core/i18n_catalogs/*`.
- Added regression coverage for worker dispatch registry, i18n catalog facade, and resource-cleanup structure checks.
- Synced `pdf_master.spec`, `.gitignore`, and repository docs with the new core layout.

### v4.5.4 (2026-03-09) - Typing, Encoding, and Build Consistency
- Added `pyrightconfig.json` and reached `python -m pyright` -> `0 errors` across the repository.
- Added `src/core/_typing.py` and `src/ui/_typing.py` to make worker/UI mixin host contracts explicit.
- Hardened optional SDK loading in `ai_service`, worker layers, and Qt widgets to remove latent Pylance issues without changing user flows.
- Completed UTF-8 text scan and mojibake check (decode failures `0`, U+FFFD hits `0`).
- Synced `pdf_master.spec` with importlib-based optional Gemini SDK loading and the new `_typing` modules.
- Expanded `.gitignore` for Python validation, coverage, and packaging artifacts.

### v4.5.3 (2026-02-26) - PDF Editor Core Risk Fixes + Module Refactor
- Fixed `batch(operation=watermark)` runtime failure (`insert_text` -> `insert_textbox`) and added per-file failure summaries.
- Applied strict range policy to `copy_page_between_docs` (invalid/missing range now hard-fails).
- Hardened `extract_attachments` (filename sanitization, path traversal guard, duplicate suffixing).
- Unified `fitz.open()` cleanup (`try/finally`) for selected worker methods.
- Unified `add_link(goto)` policy to 0-based target at worker boundary.
- Exposed basic UI for `replace_page`, `set_bookmarks`, `add_annotation`.
- Refactored large UI/worker files into folder-based modules (`tabs_*`, `window_*`, `worker_ops`) with compatibility shims.
- Updated `pdf_master.spec` hiddenimports to include split packages.

### v4.5.2 (2026-02-25) - Implementation Risk Fix Pack
- Strengthened `add_text_markup` input validation (`markup_type` whitelist + crash guard)
- Switched form field / attachment listing to worker path (`get_form_fields`, `list_attachments`)
- Expanded PDF→Image format options to `png/jpg/webp/bmp/tiff` with legacy preset fallback
- Added Freehand Signature UI and connected worker mode (`add_freehand_signature`)
- Unified AI key storage through `settings.get_api_key/set_api_key`
- Unified page index policy (1-based UI, normalized before worker call)
- Replaced major UI hardcoded strings with i18n keys and synced translation maps
- Added regression tests for each risk area

### v4.5.1 (2026-02-19) - Stability/Compatibility
- Added worker input preflight validation (existence/size checks before execution)
- Added bidirectional kwargs normalization for advanced actions:
  `draw_shapes`, `add_link`, `insert_textbox`, `copy_page_between_docs`, `image_watermark`
- Fixed advanced action behavior mismatch between UI inputs and worker execution
- Fixed Undo registration typo for `duplicate_page`
- Improved folder opening compatibility on Linux/macOS via Qt `QDesktopServices`
- Replaced deprecated locale detection path in i18n (`getlocale + env fallback`)
- Added regression tests for worker compat/preflight/i18n

### v4.5 (2026-01-22)
- 📐 **Draw Shapes** - Add rectangles, circles, lines (position, size, color)
- 🔗 **Add Hyperlinks** - Insert URL links or page navigation links
- 📝 **Insert Textbox** - Add text directly to PDF (position, font, color)
- 📋 **Copy Pages** - Copy specific pages from another PDF
- 🖼️ **Image Watermark Enhanced** - 9 positions, scale (10-200%), opacity
- 🖨️ **Preview Print** - Print directly from preview panel
- 💬 **PDF Chat** - Ask questions about PDF content to AI
- 🏷️ **Keyword Extraction** - AI-based keyword extraction
- 🌐 **i18n Expansion** - 88 new translation keys

### v4.4 (2026-01-16)
- 🌐 **Internationalization (i18n)** - English & Korean support
- 🔄 **Language Setting** - Auto-detect & Manual switch available

### v4.3 (2026-01-16)
- 🔄 **Undo/Redo** - Support for page delete, rotate, compress, etc.
- 💾 **Auto Save Settings** - Window geometry, theme
- 🎨 **Progress Overlay** - Full-screen modal with cancel

---

## 🧪 Test and Consistency Status (v4.5.5)

- Static analysis: `python -m pyright` -> `0 errors`
- Regression tests: `python -m pytest -q` -> `131 passed, 1 warning`
- Text encoding audit: `tests/test_encoding_audit.py` guards UTF-8 decode/BOM/U+FFFD regressions

- Added:
  - `tests/test_ai_thumbnail_grid_flow.py`
  - `tests/test_thumbnail_grid_runtime.py`
  - `tests/test_preview_print.py`
  - `tests/test_worker_cancel_regression.py`
  - `tests/test_worker_undo_modes.py`
  - `tests/test_worker_regression_modes.py`
  - `tests/test_ai_worker_ui_flow.py`
  - `tests/test_close_shutdown_flow.py`
  - `tests/test_output_dialog_state.py`
  - `tests/test_same_path_preview_restore.py`
  - `tests/test_preview_search.py`
  - `tests/test_undo_backup_flow.py`
  - `tests/test_worker_batch_watermark.py`
  - `tests/test_worker_copy_page_range_strict.py`
  - `tests/test_worker_attachment_extract_security.py`
  - `tests/test_worker_resource_management_structure.py`
  - `tests/test_worker_dispatch_registry.py`
  - `tests/test_link_index_policy.py`
  - `tests/test_advanced_new_modes_ui_flow.py`
  - `tests/test_worker_param_compat.py`
  - `tests/test_worker_preflight.py`
  - `tests/test_i18n.py`
  - `tests/test_i18n_catalogs.py`
  - `tests/test_worker_markup_validation.py`
  - `tests/test_worker_form_attachment_modes.py`
  - `tests/test_convert_format_options.py`
  - `tests/test_freehand_signature_ui_flow.py`
  - `tests/test_ai_key_storage_path.py`
  - `tests/test_worker_ink_signature_runtime.py`
  - `tests/test_worker_page_validation.py`
  - `tests/test_worker_cancel_cleanup.py`
  - `tests/test_validation_docs_config.py`
  - `tests/test_page_index_policy.py`
  - `tests/test_i18n_ui_hardcoded_smoke.py`
  - `tests/test_worker_rotate_selection.py`
  - `tests/test_rotate_selection_ui_flow.py`
  - `tests/test_thumbnail_grid_selection.py`
  - `tests/test_zoomable_preview_widget.py`

---

## 📄 License

MIT License

Copyright (c) 2026 PDF Master
