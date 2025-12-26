# -*- mode: python ; coding: utf-8 -*-
# PDF Master v2.2 - PyInstaller Spec File

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# PyMuPDF 관련 데이터 및 모듈 수집
fitz_datas = collect_data_files('fitz')
fitz_hiddenimports = collect_submodules('fitz')

a = Analysis(
    ['pdf-master-v2.py'],
    pathex=[],
    binaries=[],
    datas=fitz_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'fitz',
        'fitz.fitz',
        *fitz_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF_Master_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘이 있다면 'icon.ico' 경로 지정
    version=None,
)

# 참고: 빌드 명령어
# pyinstaller pdf_master.spec
#
# 결과: dist/PDF_Master_v2.exe
