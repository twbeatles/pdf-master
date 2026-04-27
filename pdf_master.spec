# -*- mode: python ; coding: utf-8 -*-
# PDF Master v4.5.5 - PyInstaller Spec File
# One-file desktop build for the current split-package runtime layout.
# Python 3.10+ compatible, with explicit optional dependency boundaries.
# Verified 2026-04-27 after AI action consolidation, path+mtime chat history,
# encrypted-PDF password mapping, compare result payloads, atomic text/binary
# save rollout, worker i18n cleanup, and docs/build validation sync.

import sys
import os
import importlib.util
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
IS_WINDOWS = (os.name == "nt") or sys.platform.startswith("win")
ENABLE_STRIP = not IS_WINDOWS


def _module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _prune_hiddenimports(modules):
    """
    Remove non-runtime or unavailable modules from hiddenimports.
    - drop test modules (build size/noise reduction)
    - drop modules that are not importable in current environment
    - deduplicate while preserving order
    """
    out = []
    seen = set()
    for module_name in modules:
        if not module_name:
            continue
        if ".tests" in module_name or ".test_" in module_name:
            continue
        if module_name in seen:
            continue
        if not _module_exists(module_name):
            continue
        seen.add(module_name)
        out.append(module_name)
    return out

# =====================================================================
# Hidden Imports (필수 모듈)
# =====================================================================
hiddenimports = []

# fitz (PyMuPDF)
try:
    hiddenimports += collect_submodules('fitz')
except Exception:
    hiddenimports += ['fitz']

# PyQt6 필수
hiddenimports += [
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',  # v4.5: 인쇄 기능
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
]

# v4.5: Python 표준 라이브러리 (명시적 추가)
hiddenimports += [
    'threading',    # AI 싱글톤 스레드 안전성
    'tempfile',     # Undo 백업 디렉토리
    'shutil',       # 파일 복사/설정 백업
    'json',         # 설정 파일 처리
    'locale',       # i18n 언어 감지
    'datetime',     # Undo 타임스탬프
    'dataclasses',  # UndoManager ActionRecord
    'src.core.i18n',  # Explicitly include i18n for dynamic imports in widgets
    'src.core.optional_deps',  # Centralized optional fitz/keyring boundary
    'src.core.path_utils',  # Shared normalized path helper used across settings/AI/UI
    'src.core._typing',  # Pyright/Pylance host contracts imported by worker mixins
    'src.ui._typing',  # Pyright/Pylance host contracts imported by UI mixins
    'src.ui.zoomable_preview',  # Runtime-critical preview widget path (main preview panel)
    'src.ui.thumbnail_grid',  # Runtime-loaded thumbnail grid path used by AI/page flows
    'src.ui.tabs_ai.meta',  # AI result meta formatting/warning labels
    'src.ui.tabs_ai.actions',  # Canonical AI tab actions implementation
    'src.ui.tabs_ai.actions_meta',  # Compatibility shim for legacy hidden imports
    'src.ui.tabs_ai.storage',  # Versioned path+mtime chat history storage helpers
]

# v4.5.3+: 폴더 기반 모듈 분할(hidden import 보강)
for package_name in [
    'src.core.worker_ops',
    'src.core.worker_runtime',
    'src.core.i18n_catalogs',
    'src.ui.tabs_basic',
    'src.ui.tabs_advanced',
    'src.ui.tabs_ai',
    'src.ui.window_core',
    'src.ui.window_preview',
    'src.ui.window_worker',
    'src.ui.window_undo',
]:
    try:
        hiddenimports += collect_submodules(package_name)
    except Exception:
        # 패키지 수집 실패 시 최소 루트 모듈만 포함
        hiddenimports += [package_name]

# v4.5: keyring (보안 API 키 저장)
if _module_exists('keyring'):
    hiddenimports += ['keyring', 'keyring.backends']
    try:
        hiddenimports += collect_submodules('keyring')
    except Exception:
        pass
    print("[OK] keyring detected")
else:
    print("[INFO] keyring not installed - API key will be stored in file")

# Runtime helper imported indirectly through worker runtime save paths.
hiddenimports += ['src.core.worker_runtime.save_profiles']

# 데이터 파일 수집
datas = []

# =====================================================================
# AI 기능 (조건부) - google-genai SDK only
# =====================================================================
# 패키지명: google-genai (pip install google-genai)
# Import: from google import genai

ai_hiddenimports = []

if _module_exists('google.genai'):
    # google-genai 핵심 모듈
    ai_hiddenimports += [
        'google.genai',
        'google.genai.types',
        'google.genai.client',
        'google.genai.models',
        'google.genai.errors',
    ]
    
    # google-genai 의존성
    ai_hiddenimports += [
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.auth.credentials',
        'google.api_core',
        'google.api_core.exceptions',
        'google.api_core.retry',
        'google.protobuf',
        'httpx',
        'httpcore',
        'anyio',
        'sniffio',
        'h11',
        'certifi',
    ]
    
    # submodules 자동 수집
    try:
        ai_hiddenimports += collect_submodules('google.genai')
    except Exception:
        pass

    # v4.5.3: 테스트/미설치 모듈 정리
    ai_hiddenimports = _prune_hiddenimports(ai_hiddenimports)
    
    hiddenimports += ai_hiddenimports
    print(f"[OK] google-genai SDK detected ({len(ai_hiddenimports)} imports)")
else:
    print("[INFO] google-genai SDK not installed - AI features disabled")

# =====================================================================
# PDF to Word 기능 제거 (v4.2) - pdf2docx 의존성 삭제
# =====================================================================

print(f"[OK] Total hidden imports: {len(hiddenimports)}")

# =====================================================================
# Excludes (불필요한 모듈 - 경량화)
# =====================================================================
excludes = [
    # 과학/데이터 (대용량)
    'matplotlib', 'scipy', 'pandas', 'sklearn', 'numpy',
    'cv2', 'tensorflow', 'torch', 'keras',
    'IPython', 'notebook', 'jupyter',
    
    # PDF to Word 관련 (사용 안함)
    'pdf2docx', 'docx', 'pdfplumber', 'pdfminer',
    
    # GUI 프레임워크
    'tkinter', 'tk', 'wx', 'kivy', 'PySide6',
    
    # PyQt6 불필요 모듈
    'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets',
    'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
    'PyQt6.QtPositioning', 'PyQt6.QtLocation',
    'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtSerialBus',
    'PyQt6.QtTest', 'PyQt6.QtSql', 'PyQt6.QtDBus',
    'PyQt6.QtNetworkAuth',
    'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
    'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtUiTools',
    'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
    'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.Qt3DInput',
    'PyQt6.Qt3DLogic', 'PyQt6.Qt3DAnimation', 'PyQt6.Qt3DExtras',
    'PyQt6.QtQuick', 'PyQt6.QtQuick3D', 'PyQt6.QtQuickWidgets', 
    'PyQt6.QtQml', 'PyQt6.QtQmlCore', 'PyQt6.QtQmlModels',
    'PyQt6.QtRemoteObjects', 'PyQt6.QtTextToSpeech',
    'PyQt6.QtVirtualKeyboard',
    
    # 표준 라이브러리 (개발용)
    'unittest', 'test', 'tests', 'pytest',
    'xmlrpc', 'pydoc', 'doctest', 
    'lib2to3', 'idlelib', 'ensurepip',
    'venv', 'pdb', 'cProfile', 'profile',
]

# =====================================================================
# Analysis
# =====================================================================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    # Reproducible builds: deterministic ordering
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# =====================================================================
# 바이너리 필터링 (경량화)
# =====================================================================
binary_excludes = [
    'qt6webengine', 'qt6multimedia', 'qt6quick', 'qt6qml',
    'qt63d', 'qt6charts', 'qt6datavisualization',
    'qt6bluetooth', 'qt6nfc', 'qt6sensors', 'qt6serial',
    'qt6positioning', 'qt6location', 'qt6remoteobjects',
    'qt6texttospeech', 'qt6virtualkeyboard', 'qt6webchannel',
    'qt6websockets',
    'opengl32sw.dll', 'd3dcompiler',
]

a.binaries = [x for x in a.binaries if not any(
    exclude in x[0].lower() for exclude in binary_excludes
)]

# =====================================================================
# 데이터 파일 필터링
# =====================================================================
data_excludes = ['translations', 'qml', 'webengine']
a.datas = [x for x in a.datas if not any(
    exclude in x[0].lower() for exclude in data_excludes
)]

# =====================================================================
# PYZ & EXE
# =====================================================================
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF_Master_v4.5.5',
    debug=False,
    bootloader_ignore_signals=False,
    # Windows에서 strip 실행 파일이 없는 환경이 많아 자동 비활성화
    strip=ENABLE_STRIP,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll', 'api-ms-*.dll', 'ucrtbase.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# =====================================================================
# 빌드: python -m PyInstaller pdf_master.spec --clean
# 예상 결과: dist/PDF_Master_v4.5.5.exe (~30-40MB)
# =====================================================================
