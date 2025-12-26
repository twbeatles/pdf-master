# -*- mode: python ; coding: utf-8 -*-
# PDF Master v2.4 - PyInstaller Spec File (Optimized Onefile)

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# PyMuPDF 모듈 수집
fitz_datas = collect_data_files('fitz')
fitz_hiddenimports = collect_submodules('fitz')

a = Analysis(
    ['pdf-master-v2.py'],
    pathex=[],
    binaries=[],
    datas=fitz_datas,
    hiddenimports=[
        # PyQt6 최소 필수 모듈만
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # PyMuPDF
        'fitz',
        *fitz_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 대형 패키지 제외 (용량 대폭 절약)
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'Pillow', 'cv2', 'opencv',
        'tkinter', '_tkinter', 'turtle',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx', 'docutils',
        'tensorflow', 'torch', 'keras',
        'sklearn', 'scikit-learn',
        'setuptools', 'pkg_resources',
        'xml.etree', 'xmlrpc',
        'unittest', 'test', 'tests',
        'email', 'html', 'http.server',
        'multiprocessing.popen_spawn_win32',
        # PyQt6 불필요 모듈
        'PyQt6.QtNetwork', 'PyQt6.QtSql', 'PyQt6.QtSvg',
        'PyQt6.QtMultimedia', 'PyQt6.QtWebEngine',
        'PyQt6.QtBluetooth', 'PyQt6.QtPositioning',
        'PyQt6.Qt3D', 'PyQt6.QtCharts', 'PyQt6.QtDataVisualization',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 불필요한 바이너리 필터링
a.binaries = [x for x in a.binaries if not any(
    excl in x[0].lower() for excl in [
        'qt6webengine', 'qt6quick', 'qt6qml', 'qt6multimedia',
        'qt6network', 'qt6sql', 'qt6svg', 'qt6charts',
        'qt6pdf', 'qt63d', 'qt6bluetooth', 'qt6positioning',
        'qt6serialport', 'qt6sensors', 'qt6test',
        'opengl32sw', 'd3dcompiler',
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
    name='PDF_Master_v2.4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX 압축 활성화
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘: 'icon.ico'
    version=None,
)

# ============== 빌드 명령어 ==============
# pyinstaller pdf_master.spec
#
# 결과물: dist/PDF_Master_v2.4.exe
# 예상 크기: 약 25-35MB (최적화 후)
#
# 추가 용량 절감 옵션:
# - UPX 설치: https://upx.github.io/
# - pyinstaller --upx-dir=C:\upx pdf_master.spec
