# -*- mode: python ; coding: utf-8 -*-
# PDF Master v3.1 - PyInstaller Spec File (Optimized Onefile)
# 버튼 UI 색상 변경: #4f8cff (밝은 파란색)

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
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 대형 패키지 제외 (경량화)
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'cv2', 'opencv', 'PIL', 'Pillow', 'pytesseract',
        'tkinter', '_tkinter', 'turtle',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx', 'docutils',
        'tensorflow', 'torch', 'keras',
        'sklearn', 'scikit-learn',
        'setuptools', 'pkg_resources',
        'xml.etree', 'xmlrpc',
        'unittest', 'test', 'tests',
        'email', 'http.server',
        'multiprocessing.popen_spawn_win32',
        'asyncio', 'concurrent',
        'ctypes.test', 'distutils',
        'ensurepip', 'idlelib', 'lib2to3',
        'pydoc', 'pydoc_data', 'turtledemo',
        'venv', 'zipapp',
        # PyQt6 불필요 모듈
        'PyQt6.QtNetwork', 'PyQt6.QtSql', 'PyQt6.QtSvg',
        'PyQt6.QtMultimedia', 'PyQt6.QtWebEngine',
        'PyQt6.QtBluetooth', 'PyQt6.QtPositioning',
        'PyQt6.Qt3D', 'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
        'PyQt6.QtQuick', 'PyQt6.QtQml', 'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtTest',
        'PyQt6.QtTextToSpeech', 'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets',
        'PyQt6.QtXml',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 불필요한 바이너리 필터링 (경량화)
a.binaries = [x for x in a.binaries if not any(
    excl in x[0].lower() for excl in [
        'qt6webengine', 'qt6quick', 'qt6qml', 'qt6multimedia',
        'qt6network', 'qt6sql', 'qt6svg', 'qt6charts',
        'qt6pdf', 'qt63d', 'qt6bluetooth', 'qt6positioning',
        'qt6serialport', 'qt6sensors', 'qt6test',
        'opengl32sw', 'd3dcompiler',
        'qt6designer', 'qt6help', 'qt6uitools',
        'qt6virtualkeyboard', 'qt6webchannel', 'qt6websockets',
        'libcrypto', 'libssl',
        'api-ms-win',
    ]
)]

# 불필요한 데이터 파일 필터링
a.datas = [x for x in a.datas if not any(
    excl in x[0].lower() for excl in [
        'translations', 'qml', 'icons',
        'qtwebengine', 'qtquick',
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
    name='PDF_Master_v3.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version=None,
)

# ============== 빌드 명령어 ==============
# pyinstaller pdf_master.spec
#
# 결과물: dist/PDF_Master_v3.1.exe
# 예상 크기: 약 20-30MB
#
# ============== v3.1 변경 사항 ==============
# - 버튼 UI 색상 변경: #e94560 → #4f8cff (밝은 파란색)
# - Dark/Light 테마 모두 파란색 버튼 적용
# - 가독성 및 시인성 향상
