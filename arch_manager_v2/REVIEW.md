# Archaeological Manager — Review & Improvement Log

Reviewed and refactored from v1.0. QGIS ≥ 3.22. All work verified with a
stub-`qgis` test harness (`tests/run_tests.py`, **14/14 pass**) since a full
QGIS isn't available offline. **Runtime/visual behaviour should still be
confirmed in QGIS** — especially the tabs touched in Phases 2 and 4.

## Verdict
A genuinely impressive, feature-rich plugin (Harris Matrix, context/pottery/
artifact registers, interactive skeleton bone-inventory, customizable recording
sheets, CAD import, PDF report exporter, dual themes, edit history). The product
is strong; this pass paid down the structural debt that made it risky to change.

## What changed (in order)

**Pre-work — crash/leak fixes**
- Grid-map PDF export used `QPagedPaintDevice`/`QMarginsF` without importing them
  → added imports (PDF export was silently failing).
- `harris_view.py::export_png` used `QImage` unimported → fixed.
- 6 `json.load(open(...))`/`dump(open(...))` file-handle leaks → `with` blocks.

**Phase 0 — test safety net** (`tests/`)
- `_qgis_stub.py`: a minimal fake `qgis`/`PyQt` so modules import with no QGIS.
- `run_tests.py`: import-smoke for all 9 modules, unit tests (coerce,
  compute_layout, detect_sites/find_layer, read_xlsx), and a static
  undefined-name scan that catches the exact bug class above.

**Phase 1 — single source of truth**
- Removed dock.py's duplicated `coerce`, `SCHEMAS`, `HarrisView`, `ContextNode`,
  `compute_layout` and box constants — the copies had drifted into real bugs:
  - dock's `coerce` stored literal `"NULL"` in text fields → now uses the correct
    `data_manager.coerce` (merged in its `LongLong` handling).
  - dock's `SCHEMAS` was missing `bone_inventory.notes` → restored.
  - `harris_view.py` is now the canonical (and no longer dead) module.

**Phase 2 — no more monkey-patching**
- The three `_patch_*()` functions grafted 39 methods onto `ArchWindow` at import
  time. Replaced with real mixin classes:
  `ArchWindow(_HistoryAndTabsMixin, _ArchaeologistMixin, _GridMapMixin, QMainWindow)`.
  Method-wrap chains preserved via a base/override split (e.g. `_edit_row` →
  `_edit_row_ext_impl` → `_edit_row_base`).

**Phase 3 — robustness**
- 49 bare `except:` → `except Exception:` (bare also swallows Ctrl-C / SystemExit).
- Added `data_manager.qlog()` (QgsMessageLog) and wired it into the silent
  data paths (write/delete rollbacks, history-write failures).

**Phase 4 — theme completeness**
- Embedded recording-sheet widgets were hardcoded dark (form labels were
  `#222` on a dark card — nearly invisible). Converted to objectName-based
  styling so the themed QSS cascades and the light/dark toggle works.

**Phase 5 — persistence & metadata**
- User data (name/colour, site photos, custom sheet schemas) moved out of the
  plugin folder to `QStandardPaths.AppDataLocation` (legacy copies migrated
  once) so a plugin upgrade no longer wipes them.
- `metadata.txt`: version 1.1, `about`/`tags`/`icon`/`changelog` added.

dock.py: **4828 → 4588 lines**; 0 monkey-patch functions, 0 duplicated
symbols, 0 bare excepts.

## Known remaining items (deliberately not changed)
- `bone_view.py` skeleton chart keeps its paper background (B&W bone PNGs need a
  light canvas) — flag if you'd prefer it themed.
- `FormBuilderDialog` (modal) keeps its own dark styling; not in the main-window
  cascade, so it won't follow the toggle. Easy follow-up if wanted.
- `metadata.txt` `email`/`homepage`/`tracker`/`repository` left blank for you.
- Broader logging (the ~120 `except Exception: pass`) left as-is to avoid noise;
  convert selectively as needed.

## Running the tests
```
python3 tests/run_tests.py     # no QGIS/PyQt/pytest needed
```
