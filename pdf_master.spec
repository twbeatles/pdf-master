# -*- mode: python ; coding: utf-8 -*-
# PDF Master v3.1 - PyInstaller Spec File
# 경량화 최적화 빌드 설정

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# PyMuPDF 서브모듈 수집
hiddenimports = collect_submodules('fitz')

# 제외할 불필요한 모듈 (경량화)
excludes = [
    'matplotlib', 'numpy', 'scipy', 'pandas',
    'PIL.ImageTk', 'tkinter', 'tk',
    'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
    'PyQt6.QtPositioning', 'PyQt6.QtLocation',
    'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
    'PyQt6.QtTest', 'PyQt6.QtSql',
    'PyQt6.QtNetwork', 'PyQt6.QtXml',
    'PyQt6.QtDesigner', 'PyQt6.QtHelp',
    'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
    'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
    'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender',
    'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtQml',
    'unittest', 'test', 'tests',
    'email', 'html', 'http', 'urllib',
    'xml', 'xmlrpc', 'pydoc',
    'doctest', 'argparse', 'difflib',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 불필요한 바이너리 제거 (경량화)
a.binaries = [x for x in a.binaries if not any(
    exclude in x[0].lower() for exclude in [
        'qt6webengine', 'qt6multimedia', 'qt6quick',
        'qt6qml', 'qt6pdf', 'qt63d', 'qt6charts',
        'qt6datavisualization', 'qt6bluetooth',
        'opengl32sw', 'd3dcompiler',
    ]
)]

# 불필요한 데이터 파일 제거
a.datas = [x for x in a.datas if not any(
    exclude in x[0].lower() for exclude in [
        'translations', 'qml', 'webengine',
    ]
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF_Master',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 심볼 제거 (경량화)
    upx=True,    # UPX 압축 (경량화)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if sys.platform == 'win32' else None,
    version_info=None,
)
