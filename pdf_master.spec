# -*- mode: python ; coding: utf-8 -*-
# PDF Master v3.3 - PyInstaller Spec File (경량화 최적화)
# 
# 주요 변경:
# - UI/UX 리팩토링 (#4f8cff 파란색 테마)
# - 로깅 시스템 추가
# - 전역 예외 핸들러
# - 입력 유효성 검사 강화
#
# 빌드: pyinstaller pdf_master.spec
# 결과: dist/PDF_Master_v3.3.exe (~25-35MB)

import sys
import os

block_cipher = None

# PyMuPDF 모듈 수집
try:
    from PyInstaller.utils.hooks import collect_data_files, collect_submodules
    fitz_datas = collect_data_files('fitz', include_py_files=True)
    fitz_hiddenimports = collect_submodules('fitz')
    pymupdf_datas = collect_data_files('pymupdf', include_py_files=True)
    pymupdf_hiddenimports = collect_submodules('pymupdf')
except Exception:
    fitz_datas = []
    fitz_hiddenimports = []
    pymupdf_datas = []
    pymupdf_hiddenimports = []

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=[],
    datas=[('src', 'src')] + fitz_datas + pymupdf_datas,
    hiddenimports=[
        # PyQt6 Core (최소 필수)
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # PyMuPDF
        'fitz',
        'fitz.fitz',
        'fitz.utils',
        'pymupdf',
        'pymupdf.mupdf',
        *fitz_hiddenimports,
        *pymupdf_hiddenimports,
        # Local modules
        'src',
        'src.core',
        'src.core.settings',
        'src.core.worker',
        'src.ui',
        'src.ui.styles',
        'src.ui.widgets',
        'src.ui.main_window',
        # v3.3: logging support
        'logging',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ===== 불필요한 표준 라이브러리 =====
        'tkinter', '_tkinter', 'turtle', 'turtledemo',
        'unittest', 'test', 'tests', 'doctest',
        'pydoc', 'pydoc_data',
        'idlelib', 'lib2to3',
        'ensurepip', 'venv', 'zipapp',
        'ctypes.test', 'distutils',
        'xml.etree', 'xmlrpc',
        'email', 'http.server', 'ftplib', 'imaplib', 'smtplib',
        'multiprocessing.popen_spawn_win32',
        'asyncio', 'concurrent.futures',
        
        # ===== 대형 과학/ML 패키지 =====
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'cv2', 'opencv', 'PIL', 'Pillow', 'pytesseract',
        'tensorflow', 'torch', 'keras',
        'sklearn', 'scikit-learn',
        
        # ===== 개발 도구 =====
        'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx', 'docutils',
        'setuptools', 'pkg_resources', 'pip',
        
        # ===== PyQt6 불필요 모듈 (경량화 핵심) =====
        'PyQt6.QtNetwork', 'PyQt6.QtSql', 'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
        'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
        'PyQt6.QtPositioning', 'PyQt6.QtLocation',
        'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.Qt3DInput', 'PyQt6.Qt3DExtras',
        'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
        'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtQml',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
        'PyQt6.QtTest',
        'PyQt6.QtTextToSpeech',
        'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets',
        'PyQt6.QtXml',
        'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtUiTools',
        'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
        'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtDBus',
        'PyQt6.QtPrintSupport',  # 인쇄 기능 미사용 시 제외
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ===== 바이너리 필터링 (경량화) =====
BINARY_EXCLUDES = [
    # Qt WebEngine (매우 큰 용량)
    'qt6webengine', 'qtwebengine', 'webengine',
    # Qt Quick/QML
    'qt6quick', 'qtquick', 'qt6qml', 'qtqml',
    # Qt Multimedia
    'qt6multimedia', 'qtmultimedia',
    # Qt Network
    'qt6network', 'qtnetwork',
    # Qt SQL
    'qt6sql', 'qtsql',
    # Qt SVG
    'qt6svg', 'qtsvg',
    # Qt Charts
    'qt6charts', 'qtcharts',
    # Qt PDF
    'qt6pdf', 'qtpdf',
    # Qt 3D
    'qt63d', 'qt3d',
    # 기타 Qt 모듈
    'qt6bluetooth', 'qt6positioning', 'qt6serialport', 'qt6sensors', 'qt6test',
    'qt6designer', 'qt6help', 'qt6uitools',
    'qt6virtualkeyboard', 'qt6webchannel', 'qt6websockets',
    # OpenGL/DirectX (SW 렌더링 사용 시 불필요)
    'opengl32sw', 'd3dcompiler',
    # SSL (HTTPS 불필요 시)
    'libcrypto', 'libssl',
    # Windows API
    'api-ms-win',
    # ICU 데이터 (대용량)
    'icudt', 'icuin', 'icuuc',
]

a.binaries = [x for x in a.binaries if not any(
    excl in x[0].lower() for excl in BINARY_EXCLUDES
)]

# ===== 데이터 파일 필터링 =====
DATA_EXCLUDES = [
    'translations',  # 번역 파일 (한국어만 필요 시 개별 포함)
    'qml',
    'icons',
    'qtwebengine',
    'qtquick',
    'resources/qtwebengine',
]

a.datas = [x for x in a.datas if not any(
    excl in x[0].lower() for excl in DATA_EXCLUDES
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF_Master_v3.3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 심볼 제거 (경량화)
    upx=True,    # UPX 압축 활성화
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 경로 지정: 'icon.ico'
    version=None,
)

# ============================================
# 빌드 명령어
# ============================================
# pyinstaller pdf_master.spec
#
# 결과물: dist/PDF_Master_v3.3.exe
# 예상 크기: ~25-35MB
#
# ============================================
# v3.3 변경 사항
# ============================================
# - UI/UX: 글래스모피즘, 색상 통일 (#4f8cff)
# - 로깅: 파일 로그 (~/.pdf_master.log)
# - 안정성: 전역 예외 핸들러, 입력 검증
# - 기능: 스티키 노트, 프리핸드 드로잉
#
# ============================================
# 경량화 팁
# ============================================
# 1. UPX 설치: https://upx.github.io/
#    (PATH에 추가하면 자동 압축)
#
# 2. 더 작은 빌드:
#    --onedir 옵션 사용 시 더 작지만 폴더 배포
#
# 3. 특정 Qt 모듈만 포함:
#    BINARY_EXCLUDES 리스트 조정
