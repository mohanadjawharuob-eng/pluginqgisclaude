#!/usr/bin/env python3
"""Zero-dependency test runner for the Archaeological Manager plugin.

No pytest / PyQt / QGIS required — it installs a stub ``qgis`` (see
``_qgis_stub.py``) and then:
  * smoke-imports every plugin module (catches import/NameError/drift bugs),
  * unit-tests the pure-Python logic (coerce, compute_layout, detect_sites,
    find_layer, read_xlsx).

Run:  python3 tests/run_tests.py
Exit code is non-zero if anything fails (suitable for CI / a SessionStart hook).
"""
import os
import sys
import io
import zipfile
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.dirname(HERE)          # .../arch_manager_review
sys.path.insert(0, HERE)                    # find _qgis_stub
sys.path.insert(0, PKG_PARENT)              # find the arch_manager_v2 package

import _qgis_stub  # noqa: F401  (installs the fake qgis on import)

_RESULTS = []


def check(name, fn):
    try:
        fn()
        _RESULTS.append((name, True, ""))
        print(f"  PASS  {name}")
    except Exception as exc:  # noqa: BLE001 - test harness reports everything
        _RESULTS.append((name, False, traceback.format_exc()))
        print(f"  FAIL  {name}: {exc}")


# ── Smoke: every module must import cleanly ──────────────────────────────────
MODULES = [
    "styles", "data_manager", "widgets", "harris_view", "bone_view",
    "recording_sheets", "pdf_export", "dock", "plugin",
]


def _import(modname):
    return lambda: __import__(f"arch_manager_v2.{modname}", fromlist=["*"])


print("Import smoke tests:")
for _m in MODULES:
    check(f"import arch_manager_v2.{_m}", _import(_m))


# ── Unit tests: pure-Python logic ────────────────────────────────────────────
print("\nUnit tests:")


def test_coerce():
    from arch_manager_v2.data_manager import coerce
    from qgis.PyQt.QtCore import QVariant
    assert coerce("5", QVariant.Int) == 5
    assert coerce("5.9", QVariant.Int) == 5            # int(float(...))
    assert coerce("7", QVariant.LongLong) == 7         # GPKG integer columns
    assert coerce("3.5", QVariant.Double) == 3.5
    assert coerce("hello", QVariant.String) == "hello"
    # The bug the dock.py copy had: "NULL"/"None"/"" must become None, not text
    assert coerce("NULL", QVariant.String) is None
    assert coerce("None", QVariant.String) is None
    assert coerce("", QVariant.Int) is None
    assert coerce(None, QVariant.String) is None
    assert coerce("abc", QVariant.Int) is None
check("data_manager.coerce", test_coerce)


def test_compute_layout():
    from arch_manager_v2.harris_view import compute_layout
    contexts = [{"num": 1}, {"num": 2}, {"num": 3}]
    rels = [
        {"from_ctx": 1, "to_ctx": 2, "rel_type": "above"},
        {"from_ctx": 2, "to_ctx": 3, "rel_type": "above"},
    ]
    pos = compute_layout(contexts, rels)
    assert set(pos) == {1, 2, 3}, pos
    # 1 is "above" (later) → drawn higher → smaller y; 1 < 2 < 3 down the page
    assert pos[1][1] < pos[2][1] < pos[3][1], pos
check("harris_view.compute_layout", test_compute_layout)


def test_detect_sites_and_find_layer():
    from arch_manager_v2.data_manager import detect_sites, find_layer

    class _Provider:
        def __init__(self, uri):
            self._uri = uri
        def dataSourceUri(self):
            return self._uri

    class _Layer:
        def __init__(self, name, uri):
            self._name = name
            self._uri = uri
        def name(self):
            return self._name
        def id(self):
            return "id_" + self._name
        def dataProvider(self):
            return _Provider(self._uri)

    layers = [
        _Layer("Anfeh_contexts", "/data/Anfeh.gpkg|layername=contexts"),
        _Layer("Anfeh_pottery", "/data/Anfeh.gpkg|layername=pottery"),
    ]
    sites = detect_sites(layers)
    assert "Anfeh" in sites, sites
    assert find_layer(layers, "Anfeh", "contexts") == "id_Anfeh_contexts"
    assert find_layer(layers, "Anfeh", "skeletons") is None
check("data_manager.detect_sites / find_layer", test_detect_sites_and_find_layer)


_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _make_xlsx(path):
    shared = (f'<?xml version="1.0"?><sst xmlns="{_MAIN}">'
              '<si><t>context_num</t></si><si><t>name</t></si>'
              '<si><t>hello</t></si></sst>')
    workbook = (f'<?xml version="1.0"?><workbook xmlns="{_MAIN}" xmlns:r="{_R}">'
                '<sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets>'
                '</workbook>')
    rels = (f'<?xml version="1.0"?><Relationships xmlns="{_PKG}">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
            '</Relationships>')
    sheet1 = (f'<?xml version="1.0"?><worksheet xmlns="{_MAIN}"><sheetData>'
              '<row r="1"><c r="A1" t="s"><v>0</v></c>'
              '<c r="B1" t="s"><v>1</v></c></row>'
              '<row r="2"><c r="A2" t="s"><v>2</v></c>'
              '<c r="B2"><v>42</v></c></row>'
              '</sheetData></worksheet>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet1)


def test_read_xlsx():
    from arch_manager_v2.dock import read_xlsx
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "sample.xlsx")
        _make_xlsx(p)
        sheets = read_xlsx(p)
    assert "Data" in sheets, list(sheets)
    header, rows = sheets["Data"]
    assert header == ["context_num", "name"], header
    assert rows == [["hello", "42"]], rows
check("dock.read_xlsx", test_read_xlsx)


def test_no_undefined_names():
    """Static scan: every Name loaded must be bound somewhere or a builtin.

    Catches the bug class that bit this plugin twice (QImage / QPagedPaintDevice
    used without import) and any stray closure reference from refactors.
    """
    import ast
    import builtins
    known_builtins = set(dir(builtins)) | {
        "__file__", "__name__", "__doc__", "__class__", "__qualname__"}
    pkg = os.path.join(PKG_PARENT, "arch_manager_v2")
    problems = {}
    for fn in sorted(f for f in os.listdir(pkg) if f.endswith(".py")):
        tree = ast.parse(open(os.path.join(pkg, fn), encoding="utf-8").read())
        bound = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                bound.add(n.id)
            elif isinstance(n, ast.arg):
                bound.add(n.arg)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(n.name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.ImportFrom):
                for a in n.names:
                    bound.add(a.asname or a.name)
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                bound.update(n.names)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                bound.add(n.name)
        known = bound | known_builtins
        bad = {n.id: n.lineno for n in ast.walk(tree)
               if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
               and n.id not in known}
        if bad:
            problems[fn] = bad
    assert not problems, f"undefined name references: {problems}"
check("static: no undefined names", test_no_undefined_names)


# ── Summary ──────────────────────────────────────────────────────────────────
_passed = sum(1 for _, ok, _ in _RESULTS if ok)
_failed = [(n, tb) for n, ok, tb in _RESULTS if not ok]
print(f"\n{_passed}/{len(_RESULTS)} passed")
if _failed:
    print("\n── Failures ──")
    for name, tb in _failed:
        print(f"\n### {name}\n{tb}")
    sys.exit(1)
print("All green ✓")
