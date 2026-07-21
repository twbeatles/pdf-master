from __future__ import annotations

APP_NAME = "PDF Master"

VERSION = "4.5.6"

MAX_CHAT_HISTORY_ENTRIES = 40

MAX_CHAT_HISTORY_PDFS = 20

PAGE_SIZES = {
    'A4': (595, 842),
    'A3': (842, 1191),
    'A5': (420, 595),
    'Letter': (612, 792),
    'Legal': (612, 1008),
    'B4': (709, 1001),
    'B5': (499, 709),
}

DEFAULT_PAGE_SIZE = PAGE_SIZES['A4']

DEFAULT_DPI = 200

SUPPORTED_IMAGE_FORMATS = ('png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp')

THUMBNAIL_SIZE = 150

MAX_RENDER_DIMENSION = 8000

MAX_RENDER_ZOOM = 4.0

MIN_RENDER_ZOOM = 0.1

WATERMARK_DEFAULTS = {
    'opacity': 0.3,
    'color': (0.5, 0.5, 0.5),
    'fontsize': 40,
    'rotation': 45,
    'fontname': 'helv',
    'position': 'center',
    'layer': 'foreground',
}

WATERMARK_TILE_SPACING_X = 300

WATERMARK_TILE_SPACING_Y = 200

STAMP_DEFAULTS = {
    'text': '기밀',
    'position': 'top-right',
    'color': (1, 0, 0),  # 빨강
    'fontsize': 14,
}

SIGNATURE_DEFAULTS = {
    'width': 150,
    'height': 50,
    'position': 'bottom_right',
}

COMPRESSION_SETTINGS = {
    'low': {'garbage': 4, 'deflate': True, 'deflate_images': True, 'deflate_fonts': True, 'clean': True},
    'medium': {'garbage': 3, 'deflate': True, 'deflate_images': True},
    'high': {'garbage': 2, 'deflate': True},
}

PDF_DEFAULT_PERMISSIONS = ['accessibility', 'print', 'copy']

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

MIN_PDF_SIZE = 100

MAX_PAGE_RANGE_LENGTH = 1000

TOAST_DURATION_DEFAULT = 3000

TOAST_DURATION_ERROR = 5000

TOAST_DURATION_SUCCESS = 2500

THREAD_CLEANUP_TIMEOUT = 3000

THREAD_TERMINATE_TIMEOUT = 1000

AI_DEFAULT_TIMEOUT = 30

AI_MAX_TEXT_LENGTH = 30000

AI_MAX_RETRIES = 3

AI_BASE_DELAY = 1.0

AI_MAX_DELAY = 30.0

UNDO_BACKUP_MAX_SIZE_MB = 500

UNDO_BACKUP_MAX_FILES = 100

UNDO_BACKUP_MAX_AGE_HOURS = 24

RECENT_FILES_MAX = 20

