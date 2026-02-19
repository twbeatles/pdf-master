# PDF Master v4.5

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

### 📝 Annotation & Markup
| Feature | Description |
|---------|-------------|
| **Highlight Text** | Highlighter effect |
| **Sticky Note** | Add memo notes |
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
| **Extract Links** | List URLs inside document | List view |
| **Extract Images** | Extract embedded images | Save as PNG/JPG |
| **Extract Tables** | Extract table data | Save as CSV |
| **Extract Bookmarks** | Extract outline structure | List view |
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
4. Set DPI (Default: 200)
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
- Output: `dist/PDF_Master_v4.5.exe`
- Size: ~30-40MB (UPX Compressed)

---

## 📁 Project Structure

```
pdf-master-main/
├── main.py                    # Entry point
├── pdf_master.spec            # PyInstaller spec
├── README.md                  # Korean Documentation
├── README_EN.md               # English Documentation
├── CLAUDE.md                  # Claude AI Guide
├── GEMINI.md                  # Gemini AI Guide
└── src/
    ├── core/                  # Core Business Logic
    │   ├── ai_service.py      # Gemini AI Service
    │   ├── constants.py       # Global Constants
    │   ├── i18n.py            # Internationalization (v4.4)
    │   ├── settings.py        # Settings Management
    │   ├── undo_manager.py    # Undo/Redo Manager
    │   └── worker.py          # Worker Thread
    └── ui/                    # UI Components
        ├── main_window.py     # Main Window
        ├── progress_overlay.py # Progress Overlay
        ├── styles.py          # Theme/Styles
        ├── thumbnail_grid.py  # Thumbnail Grid
        ├── widgets.py         # Custom Widgets
        └── zoomable_preview.py # Zoomable Preview
```

Detailed UI module split used by current codebase:

```
src/ui/
├── main_window.py               # Main window assembly/lifecycle
├── main_window_config.py        # App constants/AI availability
├── main_window_core.py          # Menu/header/theme/shortcuts
├── main_window_preview.py       # Preview/recent files
├── main_window_worker.py        # Worker binding/overlay flow
├── main_window_undo.py          # Undo/Redo + backup cleanup
├── main_window_tabs_basic.py    # Basic tabs
├── main_window_tabs_advanced.py # Advanced sub-tabs/actions
├── main_window_tabs_ai.py       # AI tab/chat/keywords
├── progress_overlay.py
├── styles.py
├── thumbnail_grid.py
├── widgets.py
└── zoomable_preview.py
```

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

---

## 📝 Changelog

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

## 🧪 Test Status (v4.5.1)

- Added:
  - `tests/test_worker_param_compat.py`
  - `tests/test_worker_preflight.py`
  - `tests/test_i18n.py`
- Current baseline remains `pytest -q` pass for existing + new test suites.

---

## 📄 License

MIT License

Copyright (c) 2026 PDF Master
