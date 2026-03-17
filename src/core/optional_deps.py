from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, cast

logger = logging.getLogger(__name__)


def _import_optional_module(module_name: str) -> Any | None:
    try:
        return import_module(module_name)
    except ImportError:
        return None


def _has_required_attrs(module: object, required_attrs: tuple[str, ...]) -> bool:
    return all(hasattr(module, attr) for attr in required_attrs)


class _MissingDependencyCallable:
    def __init__(self, module_name: str, attr_name: str) -> None:
        self._module_name = module_name
        self._attr_name = attr_name

    def __call__(self, *args: object, **kwargs: object) -> Any:
        raise ModuleNotFoundError(
            f"Optional dependency '{self._module_name}' is required for '{self._attr_name}'. "
            f"Install it to use this feature."
        )


def _make_missing_type(module_name: str, attr_name: str, base: type[object] = object) -> type[object]:
    class _MissingType(base):
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ModuleNotFoundError(
                f"Optional dependency '{module_name}' is required for '{attr_name}'. "
                f"Install it to use this feature."
            )

    _MissingType.__name__ = attr_name
    return _MissingType


class _MissingFitzProxy:
    PDF_PERM_ACCESSIBILITY = 0
    PDF_PERM_PRINT = 0
    PDF_PERM_COPY = 0
    PDF_ENCRYPT_AES_256 = 0
    LINK_URI = 0
    LINK_GOTO = 0

    Document = _make_missing_type("fitz", "Document")
    Matrix = _make_missing_type("fitz", "Matrix")
    Rect = _make_missing_type("fitz", "Rect")
    Point = _make_missing_type("fitz", "Point")
    Pixmap = _make_missing_type("fitz", "Pixmap")
    FileDataError = cast(type[Exception], _make_missing_type("fitz", "FileDataError", Exception))
    open = _MissingDependencyCallable("fitz", "open")

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"Optional dependency 'fitz' is not available; attribute '{name}' cannot be accessed."
        )


_fitz_module = _import_optional_module("fitz")
if _fitz_module is not None and not _has_required_attrs(
    _fitz_module,
    ("open", "Document", "Matrix", "Rect", "Point"),
):
    logger.warning("Ignoring non-PyMuPDF 'fitz' module because required PDF APIs are missing")
    _fitz_module = None

FITZ_AVAILABLE = _fitz_module is not None
fitz: Any = _fitz_module if _fitz_module is not None else _MissingFitzProxy()


_keyring_module = _import_optional_module("keyring")
if _keyring_module is not None and not _has_required_attrs(
    _keyring_module,
    ("get_password", "set_password", "delete_password"),
):
    logger.warning("Ignoring 'keyring' module because required credential APIs are missing")
    _keyring_module = None

KEYRING_AVAILABLE = _keyring_module is not None
keyring: Any | None = _keyring_module


__all__ = [
    "FITZ_AVAILABLE",
    "KEYRING_AVAILABLE",
    "fitz",
    "keyring",
]
