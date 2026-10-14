# -*- mode: python ; coding: utf-8 -*-
# PDF Master - PyInstaller Spec File (version: see APP_VERSION from values.py below)
# One-file desktop build for the current split-package runtime layout.
# Python 3.15+ compatible, with explicit optional dependency boundaries.
#
# Verification baseline (docs/tests contract):
# - 2026-05-22: Worker/AI/UI split-package, preflight, cancel coverage, fake Gemini tests
# - 2026-07-14: PyMuPDF deep-util (cleanup_ops, deep compress, visual compare, SVG, etc.)
# - 2026-07-15: PROJECT_AUDIT follow-up — AI cancel_check + encrypted-PDF unlock path,
#   blank-page conservative keep, visual_error compare status, batch/page cancel, i18n
# - 2026-07-21: SOLID package split — worker_ops domain packages + settings/constants/undo
#   impl packages + ui/progress; public import facades retained for PyInstaller analysis
# - 2026-07-22: PROJECT_AUDIT follow-up — temp_cleanup orphan sweep, AI retry cancel,
#   thumbnail loader sender guard, cleanup confirm dialogs, list_annotations text contract
# - 2026-08-03: preview focus/fullscreen + textbox editor UX; SOLID split —
#   tabs_advanced/markup_actions/, annotation/highlight_markup+textbox, preview_widget mixins;
#   modes: insert_textboxes, replace_text_in_rect, extract_text_in_rect
# - 2026-08-05: SOLID Round 2 — worker_ops ai/batch/compose/form/security + _pdf_helpers_impl;
#   UI textbox_impl, tab_*_sections, thumbnail grid_* mixins, interaction_* , window_worker success/fail;
#   PreviewWidgetHost/ThumbnailGridHost; public facades retained for analysis
# - 2026-08-05: PROJECT_AUDIT residual + Quality Track B — AI stream/cancel, encrypted probe,
#   OCR hard-fail, kwargs scrub, AI text-cache shutdown, get_pdf_info i18n, FITZ startup guard,
#   undo large-source skip, AI ops split (temp_acl/prepare/handlers), thumbnail pixmap LRU,
#   ui.contracts monkeypatch SSOT; see PROJECT_AUDIT.md + PROJECT_AUDIT_QUALITY.md
# Validation: python -m pyright; python -m pytest -q (opt-in Gemini smoke skip);
#   python main.py --smoke; python -m PyInstaller pdf_master.spec --clean;
#   powershell -ExecutionPolicy Bypass -File scripts/package_smoke.ps1

import sys
import os
import importlib.util
import re
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

block_cipher = None
IS_WINDOWS = (os.name == "nt") or sys.platform.startswith("win")
ENABLE_STRIP = not IS_WINDOWS
_VERSION_SOURCE = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "src", "core", "_constants_impl", "values.py")
_VERSION_MATCH = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', open(_VERSION_SOURCE, encoding="utf-8").read(), re.MULTILINE)
if _VERSION_MATCH is None:
    raise RuntimeError("Could not read application VERSION")
APP_VERSION = _VERSION_MATCH.group(1)


def _module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


# Optional/dev-only module fragments that must never be forced into the bundle.
# google.genai local_tokenizer pulls transformers/torch and balloons EXE size.
_HEAVY_OR_DEV_MARKERS = (
    ".tests",
    ".test_",
    "._test_",
    ".testing",
    "local_tokenizer",
    "_local_tokenizer",
)


def _is_heavy_or_dev_module(module_name: str) -> bool:
    name = (module_name or "").strip()
    if not name:
        return True
    return any(marker in name for marker in _HEAVY_OR_DEV_MARKERS)


def _prune_hiddenimports(modules):
    """
    Remove non-runtime or unavailable modules from hiddenimports.
    - drop test / local-tokenizer modules (build size/noise reduction)
    - drop modules that are not importable in current environment
    - deduplicate while preserving order
    """
    out = []
    seen = set()
    for module_name in modules:
        if not module_name:
            continue
        if _is_heavy_or_dev_module(module_name):
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

# PySide6 필수
hiddenimports += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',  # v4.5: 인쇄 기능
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtSvg',  # QFluentWidgets icons and frameless title bar
    'PySide6.QtSvgWidgets',
]

# v4.5: Python 표준 라이브러리 (명시적 추가)
hiddenimports += [
    # platform 모듈의 Windows 버전 조회용. 빠지면 `cmd /c ver` 폴백이 돌아 콘솔 창이 번쩍인다.
    '_wmi',
    'threading',    # AI 싱글톤 스레드 안전성
    'tempfile',     # Undo 백업 디렉토리
    'shutil',       # 파일 복사/설정 백업
    'json',         # 설정 파일 처리
    'locale',       # i18n 언어 감지
    'datetime',     # Undo 타임스탬프
    'dataclasses',  # UndoManager ActionRecord
    'src.core.i18n',  # Explicitly include i18n for dynamic imports in widgets
    'src.core.optional_deps',  # Centralized optional fitz/keyring boundary
    'src.core.path_utils',  # Shared normalized path/resource helper used across settings/AI/UI
    'src.core._typing',  # Pyright/Pylance host contracts imported by worker mixins
    'src.core.settings',  # Settings facade (impl under _settings_impl)
    'src.core.constants',  # Constants facade (impl under _constants_impl)
    'src.core.undo_manager',  # Undo facade (impl under _undo_impl)
    'src.core.update_manifest',
    'src.core.update_installer',
    'src.ui.update_mixin',
    'src.ui._typing',  # Pyright/Pylance host contracts imported by UI mixins
    'src.ui.zoomable_preview',  # Runtime-critical preview widget path (main preview panel)
    'src.ui.thumbnail_grid',  # Runtime-loaded thumbnail grid path used by AI/page flows
    'src.ui.progress_overlay',  # Progress overlay facade (impl under ui.progress)
    'src.ui.tabs_ai.meta',  # AI result meta formatting/warning labels
    'src.ui.tabs_ai.actions',  # Canonical AI tab actions implementation
    'src.ui.tabs_ai.actions_meta',  # Compatibility shim for legacy hidden imports
    'src.ui.tabs_ai.storage',  # Versioned path+mtime chat history storage helpers
    # 2026-08-05 Quality Track B surfaces (also covered via collect_submodules below)
    'src.ui.contracts',  # Monkeypatch contract SSOT (import-light)
    'src.ui.thumbnail.pixmap_lru',  # Thumbnail pixmap LRU
    'src.core.worker_ops.ai.temp_acl',
    'src.core.worker_ops.ai.prepare',
    'src.core.worker_ops.ai.handlers',
]

# v4.5.3+: 폴더 기반 모듈 분할(hidden import 보강)
# v4.5.6 / 2026-07-21: SOLID 패키지 분할 — _*_impl 및 worker_ops 하위 도메인, ui.progress
# v4.5.6 / 2026-07-22: temp_cleanup (AI 평문 temp / atomic orphan 스윕)
hiddenimports += [
    'src.core.temp_cleanup',
    'src.core.path_utils',
    'src.core.pdf_validation',
]
for package_name in [
    'src.core.worker_ops',
    'src.core.worker_ops.annotation',
    'src.core.worker_ops.extract',
    'src.core.worker_ops.cleanup',
    'src.core.worker_ops.page',
    'src.core.worker_ops.transform',
    'src.core.worker_ops.compare',
    'src.core.worker_ops.ai',
    'src.core.worker_ops.batch',
    'src.core.worker_ops.compose',
    'src.core.worker_ops.form',
    'src.core.worker_ops.security',
    'src.core.worker_ops._pdf_helpers_impl',
    'src.core.worker_runtime',
    'src.core.ai',
    'src.core.i18n_catalogs',
    'src.core._settings_impl',
    'src.core._constants_impl',
    'src.core._undo_impl',
    'src.ui.common_widgets',
    'src.ui.tabs_basic',
    'src.ui.tabs_basic.security_impl',
    'src.ui.tabs_advanced',
    'src.ui.tabs_advanced.tab_builders',
    'src.ui.tabs_advanced.tab_builders.edit_sections',
    'src.ui.tabs_advanced.tab_builders.markup_sections',
    'src.ui.tabs_advanced.tab_builders.misc_sections',
    'src.ui.tabs_advanced.markup_actions',
    'src.ui.tabs_advanced.markup_actions.textbox_impl',
    'src.ui.tabs_ai',
    'src.ui.preview_widget',
    'src.ui.thumbnail',
    'src.ui.contracts',
    'src.ui.theme',
    'src.ui.progress',
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
    keyring_imports = ['keyring', 'keyring.backends']
    try:
        keyring_imports += collect_submodules('keyring')
    except Exception:
        pass
    hiddenimports += _prune_hiddenimports(keyring_imports)
    print("[OK] keyring detected")
else:
    print("[INFO] keyring not installed - API key will be stored in file")

# Fluent is a required desktop dependency. A build with the wrong Qt binding
# would silently ship the legacy tab UI, so reject it before collecting modules.
from src.ui.fluent_theme import is_fluent_available

if not is_fluent_available():
    raise RuntimeError("PySide6-Fluent-Widgets is required and must use the PySide6 binding")
hiddenimports += collect_submodules('qfluentwidgets')
hiddenimports += collect_submodules('qframelesswindow')
hiddenimports += ['darkdetect']
fluent_metadata = copy_metadata('PySide6-Fluent-Widgets')
print("[OK] PySide6 Fluent UI verified and included")

# Runtime helper imported indirectly through worker runtime save paths.
hiddenimports += ['src.core.worker_runtime.save_profiles']

# 데이터 파일 수집
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
APP_ICON_ICO = os.path.join(SPEC_DIR, "assets", "app_icon.ico")
APP_ICON_PNG = os.path.join(SPEC_DIR, "assets", "app_icon.png")

datas = []
datas += fluent_metadata
if os.path.isfile(APP_ICON_PNG):
    datas.append((APP_ICON_PNG, "assets"))
    print(f"[OK] App icon PNG bundled: {APP_ICON_PNG}")
else:
    print("[WARN] App icon PNG not found - runtime window icon will be skipped")

EXE_ICON = APP_ICON_ICO if os.path.isfile(APP_ICON_ICO) else None
if EXE_ICON:
    print(f"[OK] EXE icon: {EXE_ICON}")
else:
    print("[WARN] App icon ICO not found - EXE icon will be skipped")

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

# Final prune after all collect_submodules (keyring/google.genai/src packages).
hiddenimports = _prune_hiddenimports(hiddenimports)

# =====================================================================
# Native DLLs (런타임 필수)
# =====================================================================
# Python 3.15 free-threaded: abi3t stable ABI로 빌드된 확장(cryptography _rust.pyd)은
# python3t.dll(abi3t-compat/)에 링크된다. 통상 인터프리터는 시작 시 이 경로를 등록하지만
# onefile 번들에는 포함되지 않아 DLL load 실패가 난다. 명시적으로 포함한다.
spec_binaries = []
_ABI3T_DLL = os.path.join(sys.base_prefix, "abi3t-compat", "python3t.dll")
if os.path.isfile(_ABI3T_DLL):
    spec_binaries.append((_ABI3T_DLL, "."))
    print(f"[OK] python3t.dll bundled: {_ABI3T_DLL}")
else:
    print("[WARN] python3t.dll not found - abi3t extensions may fail to load")

# =====================================================================
# PDF to Word 기능 제거 (v4.2) - pdf2docx 의존성 삭제
# =====================================================================

print(f"[OK] Total hidden imports: {len(hiddenimports)}")

# =====================================================================
# Excludes (불필요한 모듈 - 경량화)
# =====================================================================
# NOTE: This machine may have torch/transformers/dask installed for other projects.
# They are NOT runtime deps of PDF Master; keep them out of Analysis even when present.
excludes = [
    # 과학/데이터/ML (대용량 — google.genai local_tokenizer optional chain)
    'matplotlib', 'scipy', 'pandas', 'sklearn', 'scikit-learn', 'numpy',
    'cv2', 'opencv', 'opencv-python',
    'tensorflow', 'tensorboard', 'torch', 'torchvision', 'torchaudio', 'keras',
    'jax', 'jaxlib', 'onnx', 'onnxruntime',
    'transformers', 'huggingface_hub', 'tokenizers', 'safetensors',
    'accelerate', 'datasets', 'peft', 'sentencepiece',
    'pyarrow', 'dask', 'distributed', 'fsspec', 'partd', 'toolz',
    'numba', 'llvmlite', 'sympy', 'networkx',
    'IPython', 'notebook', 'jupyter', 'jupyter_client', 'jupyter_core',

    # google-genai optional local tokenizer (forces transformers/torch)
    'google.genai.local_tokenizer',
    'google.genai._local_tokenizer_loader',
    'google.genai._test_api_client',

    # PDF to Word 관련 (사용 안함)
    'pdf2docx', 'docx', 'pdfplumber', 'pdfminer',

    # GUI 프레임워크
    'tkinter', 'tk', 'wx', 'kivy', 'PyQt6', 'PyQt5', 'PySide2',

    # PySide6 불필요 모듈
    'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtBluetooth', 'PySide6.QtNfc',
    'PySide6.QtPositioning', 'PySide6.QtLocation',
    'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtSerialBus',
    'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtDBus',
    'PySide6.QtNetworkAuth',
    'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtUiTools',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets',
    'PySide6.QtQml', 'PySide6.QtQmlCore', 'PySide6.QtQmlModels',
    'PySide6.QtRemoteObjects', 'PySide6.QtTextToSpeech',
    'PySide6.QtVirtualKeyboard',

    # 표준 라이브러리 / 개발용
    'unittest', 'test', 'tests', 'pytest', '_pytest', 'pluggy', 'iniconfig',
    'xmlrpc', 'pydoc', 'doctest',
    'lib2to3', 'idlelib', 'ensurepip',
    'venv', 'pdb', 'cProfile', 'profile',
    'keyring.testing',
]

# =====================================================================
# Analysis
# =====================================================================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=spec_binaries,
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
# 바이너리 / pure / data 필터링 (경량화 safety net)
# =====================================================================
# Even with excludes, Analysis can still pick up shared libs if a hook runs.
# Strip known non-runtime ML/data stacks that may be installed globally.
binary_excludes = [
    'qt6webengine', 'qt6multimedia', 'qt6quick', 'qt6qml',
    'qt63d', 'qt6charts', 'qt6datavisualization',
    'qt6bluetooth', 'qt6nfc', 'qt6sensors', 'qt6serial',
    'qt6positioning', 'qt6location', 'qt6remoteobjects',
    'qt6texttospeech', 'qt6virtualkeyboard', 'qt6webchannel',
    'qt6websockets',
    'opengl32sw.dll', 'd3dcompiler',
    # ML / data-science native libs
    'torch', 'torchvision', 'torchaudio', 'c10.', 'c10_', 'libtorch',
    'cudnn', 'cublas', 'cufft', 'curand', 'cusolver', 'cusparse', 'nvToolsExt',
    'transformers', 'pyarrow', 'arrow.', 'arrow_',
    'scipy', 'pandas', 'numpy', 'mkl_', 'libopenblas', 'openblas',
    'tensorflow', 'jaxlib', 'onnxruntime',
]

data_excludes = [
    'translations', 'qml', 'webengine',
    'torch', 'torchvision', 'transformers', 'huggingface',
    'pyarrow', 'dask', 'scipy', 'pandas', 'numpy', 'tokenizers',
    'sklearn', 'matplotlib',
]

pure_excludes_prefixes = (
    'torch', 'torchvision', 'torchaudio',
    'transformers', 'huggingface_hub', 'tokenizers', 'safetensors',
    'accelerate', 'datasets', 'peft',
    'pyarrow', 'dask', 'distributed', 'fsspec', 'partd', 'toolz',
    'numpy', 'scipy', 'pandas', 'sklearn', 'matplotlib',
    'tensorflow', 'tensorboard', 'keras', 'jax', 'jaxlib',
    'numba', 'llvmlite', 'sympy', 'networkx',
    'IPython', 'notebook', 'jupyter',
    'google.genai.local_tokenizer',
    'google.genai._local_tokenizer_loader',
    'google.genai._test_api_client',
    'keyring.testing',
    'pytest', '_pytest',
)


def _toc_name(entry) -> str:
    return str(entry[0] if isinstance(entry, (tuple, list)) else entry)


def _matches_any(name: str, needles) -> bool:
    lower = name.lower().replace("\\", "/")
    return any(n in lower for n in needles)


def _pure_is_excluded(name: str) -> bool:
    lower = name.lower()
    for prefix in pure_excludes_prefixes:
        p = prefix.lower()
        if lower == p or lower.startswith(p + "."):
            return True
    return False


_before_bin = len(a.binaries)
_before_data = len(a.datas)
_before_pure = len(a.pure)

a.binaries = [x for x in a.binaries if not _matches_any(_toc_name(x), binary_excludes)]
a.datas = [x for x in a.datas if not _matches_any(_toc_name(x), data_excludes)]
a.pure = [x for x in a.pure if not _pure_is_excluded(_toc_name(x))]

print(
    "[OK] Size filter removed: "
    f"binaries={_before_bin - len(a.binaries)}, "
    f"datas={_before_data - len(a.datas)}, "
    f"pure={_before_pure - len(a.pure)}"
)

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
    name=f'PDF_Master_v{APP_VERSION}',
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
    icon=EXE_ICON,
)

# =====================================================================
# 빌드: python -m PyInstaller pdf_master.spec --clean
# 예상 결과: dist/PDF_Master_v<APP_VERSION>.exe (~30-40MB)
#   - EXE 이름은 src/core/_constants_impl/values.py 의 VERSION 단일 소스에서
#     동적 생성되므로 (위 APP_VERSION), 버전은 values.py 만 갱신한다.
# =====================================================================
