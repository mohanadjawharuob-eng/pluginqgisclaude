"""Lightweight stand-in for the parts of ``qgis`` / ``PyQt`` the plugin imports.

This lets the pure-Python logic and every plugin module *import* (and be
smoke-tested) in a plain Python environment that has neither QGIS nor PyQt
installed. It is deliberately NOT a working Qt: instantiating "widgets" or
calling Qt methods returns inert stub objects.

Its job is twofold:
  1. Catch import-time errors — missing imports, NameError, symbol drift.
     (This alone would have caught the ``QImage`` / ``QPagedPaintDevice`` bugs.)
  2. Let us unit-test the algorithmic functions that only need QVariant-style
     enums and plain Python: ``read_xlsx``, ``compute_layout``, ``coerce``,
     ``detect_sites``, ``find_layer``.

Anything that needs a real running Qt/QGIS must be verified in QGIS itself.
"""
import sys
import types

# Interned enum-like sentinels (so ``QVariant.Int is QVariant.Int``) ───────────
_ENUM_CACHE = {}


class _Enum:
    """Stand-in for a Qt / QVariant enum value (e.g. ``QVariant.Int``)."""
    __slots__ = ("_name",)

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return f"<stub {self._name}>"

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return isinstance(other, _Enum) and other._name == self._name

    def __ne__(self, other):
        return not self.__eq__(other)

    # Qt flag arithmetic (Qt.AlignLeft | Qt.AlignVCenter) and int coercion
    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self

    def __and__(self, other):
        return self

    def __int__(self):
        return 0

    def __index__(self):
        return 0

    def __bool__(self):
        return True


def _enum(name):
    if name not in _ENUM_CACHE:
        _ENUM_CACHE[name] = _Enum(name)
    return _ENUM_CACHE[name]


class _StubMeta(type):
    """Metaclass so class-attribute access (``QVariant.Int``, ``Qt.AlignCenter``)
    yields interned sentinels, while the class stays subclassable/instantiable."""

    def __getattr__(cls, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _enum(f"{cls.__name__}.{name}")


class Stub(metaclass=_StubMeta):
    """Base for every stubbed Qt/QGIS class. Subclassable and callable."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _Method(name)

    def __call__(self, *a, **k):
        return Stub()

    def __or__(self, other):
        return self

    def __int__(self):
        return 0

    def __index__(self):
        return 0

    def __iter__(self):
        return iter(())


class _Method:
    """Instance attribute / bound-method stand-in: callable and chainable."""

    def __init__(self, name):
        self._name = name

    def __call__(self, *a, **k):
        return Stub()

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _Method(name)


def _make_module(fullname, is_pkg=False):
    mod = types.ModuleType(fullname)
    if is_pkg:
        mod.__path__ = []          # mark as package, but with no search path
    _classes = {}

    def __getattr__(name, _c=_classes, _fn=fullname):
        # PEP 562 module-level __getattr__: fabricate a stub class on demand.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name not in _c:
            _c[name] = _StubMeta(name, (Stub,), {"__module__": _fn})
        return _c[name]

    mod.__getattr__ = __getattr__
    sys.modules[fullname] = mod
    return mod


def install():
    """Install the fake ``qgis`` package tree into ``sys.modules`` (idempotent)."""
    if getattr(sys.modules.get("qgis"), "_IS_STUB", False):
        return
    qgis = _make_module("qgis", is_pkg=True)
    qgis._IS_STUB = True
    pyqt = _make_module("qgis.PyQt", is_pkg=True)
    qgis.PyQt = pyqt
    qgis.core = _make_module("qgis.core")
    for sub in ("QtCore", "QtGui", "QtWidgets", "QtSvg"):
        setattr(pyqt, sub, _make_module(f"qgis.PyQt.{sub}"))
    # Intentionally NOT created: QtWebEngineWidgets, QtWebChannel,
    # QtPrintSupport — so the plugin's ``try/except ImportError`` fallbacks
    # (HAS_WEBENGINE / HAS_PRINTER) take the "absent" branch, like a minimal
    # QGIS build.


install()
