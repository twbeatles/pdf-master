# -*- mode: python ; coding: utf-8 -*-
# PDF Master v4.5 - PyInstaller Spec File
# 경량화 최적화 빌드 설정 (onefile)
# Python 3.10+ 호환, v4.5 코드 변경 사항 반영 (Verified 2026-02-05)

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

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
    'src.core.i18n', # Explicitly include i18n for dynamic imports in widgets
]

# v4.5: keyring (보안 API 키 저장)
try:
    import keyring
    hiddenimports += ['keyring', 'keyring.backends']
    try:
        hiddenimports += collect_submodules('keyring')
    except Exception:
        pass
    print("✓ keyring detected")
except ImportError:
    print("○ keyring not installed - API key will be stored in file")

# 데이터 파일 수집
datas = []

# =====================================================================
# AI 기능 (조건부) - google-genai SDK
# =====================================================================
# 패키지명: google-genai (pip install google-genai)
# Import: from google import genai
# 참고: google-generativeai는 2025년 11월 deprecated됨

ai_hiddenimports = []

try:
    from google import genai
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
    
    hiddenimports += ai_hiddenimports
    print(f"✓ google-genai SDK detected ({len(ai_hiddenimports)} imports)")
    
except ImportError:
    # deprecated SDK 폴백 (2025.11 이전 호환)
    try:
        import google.generativeai
        ai_hiddenimports += [
            'google.generativeai',
            'google.ai.generativelanguage',
        ]
        try:
            ai_hiddenimports += collect_submodules('google.generativeai')
            ai_hiddenimports += collect_submodules('google.ai')
        except Exception:
            pass
        hiddenimports += ai_hiddenimports
        print(f"⚠ Using deprecated google-generativeai SDK ({len(ai_hiddenimports)} imports)")
    except ImportError:
        print("○ No Gemini SDK installed - AI features disabled")

# =====================================================================
# PDF to Word 기능 제거 (v4.2) - pdf2docx 의존성 삭제
# =====================================================================

print(f"✓ Total hidden imports: {len(hiddenimports)}")

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
    'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
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
    hiddenimports=list(set(hiddenimports)),
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
    'qt6pdf', 'qt63d', 'qt6charts', 'qt6datavisualization',
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
    name='PDF_Master_v4.5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
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
# 빌드: pyinstaller pdf_master.spec --clean
# 예상 결과: dist/PDF_Master_v4.5.exe (~30-40MB)
# =====================================================================
