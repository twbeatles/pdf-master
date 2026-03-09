# PDF Master v4.5.4

📑 **All-in-One PDF Editor** - PyQt6 based Desktop Application

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

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
| **PDF → Image** | Convert pages to images | PNG, JPG, WEBP, BMP, TIFF |
| **Image → PDF** | Combine images into PDF | PNG, JPG, BMP, GIF, WEBP |
| **Extract Text** | Extract text from PDF | Save as TXT |

### ✂️ Page Editing
| Feature | Description |
|---------|-------------|
| **Extract Pages** | Extract specific pages (e.g., 1-3, 5, 7-10) |
| **Delete Pages** | Remove selected pages |
| **Rotate Pages** | Rotate 90°, 180°, 270° |
| **Reorder Pages** | Rearrange pages via drag & drop |
| **Page Numbers** | Custom position/format/font (Page 1 of N, 1/N, etc.) |
| **Insert Blank Page** | Add blank page at desired position |
| **Duplicate Page** | Copy selected page |
| **Reverse Order** | Reverse page order |
| **Resize Pages** | Resize to A4, A3, Letter, Legal, etc. |
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
| **Compare PDFs** | Analyze text differences between two PDFs |
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
- **Zoom/Pan Preview** - Mouse wheel zoom, drag move
- **Thumbnail Grid** - View all pages at a glance
- **Undo/Redo** - Undo/Redo for page delete, rotate, compress, etc.
- **Preview Print** - Print directly from preview panel (v4.5)

---

## 🚀 Installation & Run

### Requirements
- Python 3.10 or higher
- Windows / macOS / Linux

### Install Dependencies
```bash
# Core packages
pip install PyQt6 PyMuPDF

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
3. Enter page range (e.g., `1-3, 5, 7-10`)
4. Select operation (Extract/Delete/Rotate)
5. **Execute** → Select save location

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
pyinstaller pdf_master.spec --clean
```

### Build Result
- Output: `dist/PDF_Master_v4.5.4.exe`
- Size: ~30-40MB (UPX Compressed)

---

## ✅ Development Validation

- Static analysis: `pyright .` -> `0 errors`
- Regression tests: `pytest -q` -> `50 passed`
- Encoding audit: UTF-8 decode failures `0`, U+FFFD (`�`) hits `0`

---

## 📁 Project Structure

```
pdf-master/
├── main.py
├── pdf_master.spec
├── pyrightconfig.json
├── README.md
├── README_EN.md
├── CLAUDE.md
├── GEMINI.md
└── src/
    ├── core/
    │   ├── ai_service.py
    │   ├── _typing.py              # worker mixin host contracts
    │   ├── constants.py
    │   ├── i18n.py
    │   ├── settings.py
    │   ├── undo_manager.py
    │   ├── worker.py                # compatibility shim + shared logic
    │   └── worker_ops/              # split worker implementations
    │       ├── pdf_ops.py
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

Note: `main_window_*.py` and `worker.py` are retained as compatibility shims; runtime implementations live in folder modules.

---

## 🔧 Config File

Location: `~/.pdf_master_settings.json`

```json
{
  "theme": "dark",
  "language": "auto",
  "recent_files": [],
  "last_output_dir": "",
  "window_geometry": "..."
}
```

API key storage policy:
- `keyring` available: keyring-first save/load
- `keyring` unavailable: settings-file fallback (`gemini_api_key`)
- Legacy plain key is migrated/cleaned when keyring path is active

---

## 📝 Changelog

### v4.5.4 (2026-03-09) - Typing, Encoding, and Build Consistency
- Added `pyrightconfig.json` and reached `pyright .` -> `0 errors` across the repository.
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

## 🧪 Test and Consistency Status (v4.5.4)

- Static analysis: `pyright .` -> `0 errors`
- Regression tests: `pytest -q` -> `50 passed`
- Text encoding audit: UTF-8 decode failures `0`, U+FFFD hits `0`

- Added:
  - `tests/test_worker_batch_watermark.py`
  - `tests/test_worker_copy_page_range_strict.py`
  - `tests/test_worker_attachment_extract_security.py`
  - `tests/test_worker_resource_management_structure.py`
  - `tests/test_link_index_policy.py`
  - `tests/test_advanced_new_modes_ui_flow.py`
  - `tests/test_worker_param_compat.py`
  - `tests/test_worker_preflight.py`
  - `tests/test_i18n.py`
  - `tests/test_worker_markup_validation.py`
  - `tests/test_worker_form_attachment_modes.py`
  - `tests/test_convert_format_options.py`
  - `tests/test_freehand_signature_ui_flow.py`
  - `tests/test_ai_key_storage_path.py`
  - `tests/test_page_index_policy.py`
  - `tests/test_i18n_ui_hardcoded_smoke.py`

---

## 📄 License

MIT License

Copyright (c) 2026 PDF Master
