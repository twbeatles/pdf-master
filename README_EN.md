# PDF Master v4.5.6

📑 **All-in-One PDF Editor** — PyQt6 Desktop Application

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

[🇰🇷 한국어 README](README.md) | [🇺🇸 English](#)

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Installation & Run](#-installation--run)
- [Usage](#-usage)
- [Shortcuts](#️-shortcuts)
- [Known Limitations](#️-known-limitations)
- [Build](#-build-pyinstaller)
- [Changelog](#-changelog)

---

## ✨ Key Features

### 📄 PDF Merge & Convert
| Feature | Description | Formats |
|---------|-------------|---------|
| **PDF Merge** | Merge multiple PDFs into one | Drag & Drop supported |
| **PDF → Image** | Convert pages to images | PNG, JPG, WEBP, BMP, TIFF |
| **Image → PDF** | Combine images into PDF | PNG, JPG, BMP, GIF, WEBP |
| **Extract Text** | Extract text from PDF | Save as TXT |

### ✂️ Page Editing
| Feature | Description |
|---------|-------------|
| **Extract Pages** | Pull out specific pages (e.g., `1-3, 5, 7-10`) |
| **Delete Pages** | Remove selected pages |
| **Rotate Pages** | 90°, 180°, 270° — full doc or selected pages only |
| **Reorder Pages** | Drag & drop to rearrange |
| **Page Numbers** | Custom position, format, and font (`Page 1 of N`, `1/N`, etc.) |
| **Insert Blank Page** | Add a blank page anywhere |
| **Duplicate Page** | Copy selected page |
| **Reverse Order** | Flip the entire page order |
| **Resize Pages** | Convert to A4, A3, Letter, Legal, etc. (aspect ratio preserved) |
| **Replace Page** | Swap a page with one from another PDF |
| **Remove Blank Pages** | Drop empty pages without text/images |
| **Remove Duplicate Pages** | Signature-based duplicate cleanup |
| **N-up Impose** | 2-up / 4-up print layouts |
| **Auto Bookmarks** | Build outline from heading-size heuristics |

### 🔒 Security & Protection
| Feature | Description |
|---------|-------------|
| **Encrypt PDF** | AES-256 password plus print/copy/modify permission flags |
| **Decrypt PDF** | Remove password |
| **Sanitize PDF** | Scrub metadata, attachments, annotations before sharing |
| **Text Watermark** | Custom opacity, rotation, and position |
| **Image Watermark** | 9 positions, custom scale and opacity |
| **Add Stamp** | Confidential, Approved, Draft, Copy, etc. |

### 🔧 Advanced Editing
| Feature | Description |
|---------|-------------|
| **Split PDF** | Split by page, range, or **bookmarks** |
| **Compress PDF** | `fast` / `compact` / `web` with image downsample + font subsetting |
| **Crop PDF** | Margin crop or **content-aware auto crop** |
| **Edit Metadata** | Modify title, author, subject, keywords |
| **Compare PDFs** | Text / **visual (pixel)** / both + optional visual diff PDF |
| **Set Bookmarks** | Define outline structure manually |
| **Flatten Form** | Bake filled form fields into permanent content |

### 📝 Annotation & Markup
| Feature | Description |
|---------|-------------|
| **Highlight Text** | Highlighter effect |
| **Sticky Note** | Add memo notes |
| **Add Annotation** | Text or freetext annotation |
| **Underline / Strikethrough** | Text markup |
| **Draw Shapes** | Add rectangles, circles, lines |
| **Add Hyperlinks** | URL or page navigation links |
| **Insert Textbox** | Type text directly on the PDF |
| **Redact Text** | Permanently remove sensitive text matches |
| **Redact Area** | Permanently remove by coordinates |
| **Add Background** | Change page background color |
| **Freehand Signature** | Draw and embed a handwritten signature |

### 📊 Data Extraction
| Feature | Description | Output |
|---------|-------------|--------|
| **Extract Links** | List all URLs in the document | TXT |
| **Extract Images** | Pull out embedded images | PNG / JPG |
| **Export SVG** | Vector page export | SVG |
| **Extract Tables** | Export table data | CSV |
| **Extract Bookmarks** | Export outline structure | TXT |
| **Markdown Convert** | `auto/native/text` mode | MD |
| **Attachment Manager** | Add / extract file attachments | Various |

### 🤖 AI Features (Google Gemini)
| Feature | Description |
|---------|-------------|
| **PDF Summary** | AI-generated summary in Korean or English |
| **PDF Chat** | Ask questions about the PDF content |
| **Keyword Extraction** | Automatically identify key terms |
| **Summary Style** | Concise / Detailed / Bullet points |

> AI features require a **Gemini API key** from [Google AI Studio](https://aistudio.google.com/) and the `google-genai` package. The AI service implementation lives under `src/core/ai/`.

### 🎨 UI/UX
- **Dark / Light Theme** — Glassmorphism design
- **Zoom / Pan Preview** — Mouse wheel zoom, drag move, print
- **Preview Search / Bookmarks** — Collapsible side panel (`Ctrl+F`)
- **Thumbnail Grid** — View all pages at a glance
- **Drag & Drop** — Add files, reorder pages
- **Undo / Redo** — Undo and redo major editing operations
- **Progress Overlay** — Full-screen cancellable progress dialog
- **External File Watching** — Detects changes via `QFileSystemWatcher`; preview auto-reloads when the PDF is replaced externally
- **Batch Processing** — Apply one operation to many files at once
- **Multilingual** — Korean / English (auto-detect + manual switch)

---

## 🚀 Installation & Run

### Use the Prebuilt Executable (Windows)

Run `dist/PDF_Master_v4.5.6.exe` directly — no installation required.

### Run from Source

**Requires:** Python 3.10 or higher

```bash
# 1. Install dependencies (pyproject.toml)
pip install -e .[dev]
# or compatibility shim: pip install -r requirements-dev.txt

# For AI features
pip install -e .[ai]

# 2. Launch
python main.py
```

---

## 📖 Usage

### 1. Merge PDFs
1. Select the **Merge** tab
2. Drag & drop files or click **Add Files**
3. Reorder the list as needed (drag to move)
4. Click **Merge** → choose a save location

### 2. PDF → Image
1. Select the **Convert** tab
2. Select a PDF file
3. Choose an output format (PNG, JPG, WEBP, etc.)
4. Set DPI (default: 150 / recommended for high quality: 200–300)
5. Click **Convert** → choose an output folder

### 3. Page Operations (Extract / Delete / Rotate)
1. Select the **Page** tab
2. Select a PDF file
3. Extract / Delete: enter a page range (e.g., `1-3, 5, 7-10`)
4. Rotate: pick an angle and choose the scope:
   - **All pages** — rotate the entire document
   - **Selected pages** — `Ctrl` / `Shift`-click thumbnails to choose specific pages
5. Click **Run** → choose a save location

### 4. Add Watermark
1. Select the **Security** tab
2. Select a PDF file
3. Enter watermark text
4. Adjust opacity, font size, rotation, and position (center or tile)
5. Click **Add Watermark**

### 5. Encrypt / Decrypt PDF
1. Select the **Security** tab
2. Select a PDF file
3. Enter a password (encrypt) or the current password (decrypt)
4. Click **Encrypt** or **Decrypt**

### 6. AI Summary & Chat (Gemini API)
1. Select the **AI** tab
2. Enter your Gemini API key and click **Save** (first time only)
3. Select a PDF file
4. Choose an action:
   - **Summary**: pick language (Korean/English) and style (Concise/Detailed/Bullets) → **Summarize**
   - **Chat**: type a question → **Ask**
   - **Keywords**: click **Extract Keywords**

> **Clear Chat** resets only the conversation history for the currently selected PDF.

### 7. Markdown Extraction
1. Go to **Advanced** tab → **Extract** section → **Markdown**
2. Choose extraction mode (`auto` / `native` / `text`)
3. Enable YAML front matter, page markers, or image/table placeholders as needed
4. Click **Extract Markdown**

### 8. Batch Processing
1. Select the **Batch** tab
2. Add multiple PDF files
3. Choose an operation (compress, watermark, encrypt, etc.)
4. Set shared options and click **Batch Run**

### Change Language
Menu bar → **Language** (🌐) → **Korean** or **English** → restart the app to apply

---

## ⌨️ Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file |
| `Ctrl+Q` | Quit |
| `Ctrl+T` | Toggle dark / light theme |
| `Ctrl+F` | Open preview search |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+1` | Merge tab |
| `Ctrl+2` | Convert tab |
| `Ctrl+3` | Page tab |
| `Ctrl+4` | Security tab |
| `Ctrl+5` | Reorder tab |
| `Ctrl+6` | Batch tab |
| `Ctrl+7` | Advanced tab |
| `Ctrl+8` | AI tab |

---

## ⚠️ Known Limitations

| Item | Limit |
|------|-------|
| AI summary text | 30,000 characters max |
| Image rendering | 8,000 px max |
| File size | 2 GB max |
| Encrypted PDFs | Some operations require decryption first |

---

## 📦 Build (PyInstaller)

To build the Windows executable from source:

```bash
# Install build tools
pip install -e .[build]

# Static analysis
python -m pyright

# Run tests
python -m pytest -q

# Package build
python -m build

# Executable build
python -m PyInstaller pdf_master.spec --clean

# App initialization smoke check
python main.py --smoke

# Package smoke (clean PYTHONPATH)
powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1
```

Output: `dist/PDF_Master_v4.5.6.exe` (~30–40 MB)

Type stubs live in the `typings/` directory and are referenced by `pyrightconfig.json`.

Validation baseline: `python -m pytest -q` → **230 collected / 229 passed / 1 opt-in Gemini smoke skipped**. See `PROJECT_AUDIT.md` for the functional audit and 2026-07-15/2026-07-22 follow-up fixes.

---

## 📝 Changelog

### v4.5.6
- **Deep compress**: image downsample, JPEG re-encode, and font subsetting for `compact`/`web`
- Split by bookmarks, remove blank/duplicate pages, auto bookmarks, N-up (2/4), sanitize
- Content-aware crop, area redaction, form flatten
- Encrypt permission checkboxes (print/copy/modify/annotate/form/assemble)
- PDF compare modes: `text` / `visual` / `both` (pixel diffs for scans)
- SVG page export; graceful fallback when linearization is unavailable
- New `cleanup_ops` worker domain and extended regression tests
- **2026-07-15 audit follow-up**: AI cooperative cancel + encrypted-PDF password unlock, conservative blank-page keep, visual compare `visual_error` status, area-redact confirmation, batch/extract cancel and i18n hardening
- **2026-07-21 SOLID code split**: Worker domain packages (`annotation`/`extract`/`cleanup`/`page`/`transform`/`compare`) plus settings/constants/undo impl packages and progress UI split; public imports and behavior contracts unchanged
- **2026-07-22 audit follow-up**: thumbnail loader sender guard, AI temp/atomic orphan sweep (`temp_cleanup`), interruptible AI retry sleep + no retry on cancel, confirm dialogs for blank/dedupe/sanitize, cancel rollback without mtime heuristic, `list_annotations` text contract, batch encrypt permission note, chat session single-flight

### v4.5.5
- Preview zoom, pan, and print stability (Qt print pipeline)
- Encrypted PDF thumbnails reuse the preview password session
- Expanded Undo/Redo coverage (signature, highlight, sticky note, page copy, etc.)
- PDF comparison — detect line-order and duplicate-count changes; bidirectional visual diff PDF
- AI summary results now show source info and whether text was truncated
- Output dialogs remember and reuse the last output folder
- Batch output filenames auto-avoid collisions (`__2`, `__3` suffixes)
- Preview auto-reloads when an external app replaces the open PDF
- `Resize Pages` preserves aspect ratio and centers the source content
- Markdown extraction modes (`auto / native / text`, front matter, page markers)
- **Clear Chat** now resets only the current PDF's history
- Batch fail-fast for unsupported operations and missing watermark/encrypt options (no silent copy)
- Worker pending FIFO queue (`_pending_workers`), shortcut/menu disabling while busy
- `remove_annotations` cancellation checks, blank `search_term` reject, i18n uncaught-exception dialog

### v4.5.4
- Dedicated thumbnail list inside the rotate section
- Partial rotation — rotate only `Ctrl` / `Shift`-selected pages
- Rotate thumbnail clicks sync the right-side preview instantly

### v4.5.3
- Added UI for `Replace Page`, `Set Bookmarks`, `Add Annotation`
- Fixed batch watermark failure; added per-file error summaries
- Hardened attachment extraction (filename sanitization, path traversal guard)

### v4.5.2
- Freehand signature UI
- Expanded PDF → Image output formats (WEBP, BMP, TIFF)
- Stricter annotation input validation

### v4.5
- Draw shapes (rectangle, circle, line)
- Add hyperlinks (URL / page navigation)
- Insert textbox
- Copy pages from another PDF
- AI PDF chat and keyword extraction

### v4.4
- Korean / English multilingual support (auto-detect system language)
- Manual language switching

### v4.3
- Undo / Redo
- Cancellable progress overlay

### v4.2
- Switched to Google Gemini API (google-genai)
- Lightweight build (~30–40 MB)

---

## 📄 License

MIT License — Copyright (c) 2026 PDF Master
