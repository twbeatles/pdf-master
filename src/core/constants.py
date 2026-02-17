"""
PDF Master Constants v4.5
공통 상수 값들을 정의합니다.
"""

# ===================== 앱 정보 (v4.5) =====================

APP_NAME = "PDF Master"
VERSION = "4.5"

# ===================== 채팅 히스토리 설정 (v4.5) =====================

MAX_CHAT_HISTORY_ENTRIES = 40
MAX_CHAT_HISTORY_PDFS = 20

# ===================== 페이지 크기 (포인트) =====================

PAGE_SIZES = {
    'A4': (595, 842),
    'A3': (842, 1191),
    'A5': (420, 595),
    'Letter': (612, 792),
    'Legal': (612, 1008),
    'B4': (709, 1001),
    'B5': (499, 709),
}

# 기본 페이지 크기
DEFAULT_PAGE_SIZE = PAGE_SIZES['A4']

# ===================== 이미지 설정 =====================

# 기본 DPI
DEFAULT_DPI = 200

# 이미지 변환 포맷
SUPPORTED_IMAGE_FORMATS = ('png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp')

# 썸네일 크기 (픽셀)
THUMBNAIL_SIZE = 150

# 최대 렌더링 크기 (메모리 보호)
MAX_RENDER_DIMENSION = 8000
MAX_RENDER_ZOOM = 4.0
MIN_RENDER_ZOOM = 0.1

# ===================== 워터마크 기본값 =====================

WATERMARK_DEFAULTS = {
    'opacity': 0.3,
    'color': (0.5, 0.5, 0.5),
    'fontsize': 40,
    'rotation': 45,
    'fontname': 'helv',
    'position': 'center',
    'layer': 'foreground',
}

# 타일 워터마크 간격 (포인트)
WATERMARK_TILE_SPACING_X = 300
WATERMARK_TILE_SPACING_Y = 200

# ===================== 스탬프 기본값 =====================

STAMP_DEFAULTS = {
    'text': '기밀',
    'position': 'top-right',
    'color': (1, 0, 0),  # 빨강
    'fontsize': 14,
}

# ===================== 서명 설정 =====================

SIGNATURE_DEFAULTS = {
    'width': 150,
    'height': 50,
    'position': 'bottom_right',
}

# ===================== PDF 압축 설정 =====================

COMPRESSION_SETTINGS = {
    'low': {'garbage': 4, 'deflate': True, 'deflate_images': True, 'deflate_fonts': True, 'clean': True},
    'medium': {'garbage': 3, 'deflate': True, 'deflate_images': True},
    'high': {'garbage': 2, 'deflate': True},
}

# ===================== 암호화 설정 =====================

# PyMuPDF 암호화 권한
PDF_DEFAULT_PERMISSIONS = ['accessibility', 'print', 'copy']

# ===================== 입력 검증 =====================

# 최대 파일 크기 (바이트) - 2GB
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

# 최소 유효 PDF 크기 (바이트)
MIN_PDF_SIZE = 100

# 페이지 범위 최대 문자열 길이
MAX_PAGE_RANGE_LENGTH = 1000

# ===================== UI 상수 =====================

# 토스트 알림 기본 시간 (밀리초)
TOAST_DURATION_DEFAULT = 3000
TOAST_DURATION_ERROR = 5000
TOAST_DURATION_SUCCESS = 2500

# 스레드 타임아웃 (밀리초)
THREAD_CLEANUP_TIMEOUT = 3000
THREAD_TERMINATE_TIMEOUT = 1000

# ===================== AI 서비스 =====================

# API 타임아웃 (초)
AI_DEFAULT_TIMEOUT = 30

# 최대 텍스트 길이 (API 입력 제한)
AI_MAX_TEXT_LENGTH = 30000

# 재시도 설정
AI_MAX_RETRIES = 3
AI_BASE_DELAY = 1.0
AI_MAX_DELAY = 30.0

# ===================== Undo 백업 설정 (v4.5) =====================

# 최대 백업 폴더 크기 (MB)
UNDO_BACKUP_MAX_SIZE_MB = 500

# 최대 백업 파일 수
UNDO_BACKUP_MAX_FILES = 100

# 백업 파일 보존 시간 (시간)
UNDO_BACKUP_MAX_AGE_HOURS = 24

# ===================== UI 설정 (v4.5) =====================

# 최근 파일 최대 개수
RECENT_FILES_MAX = 20
