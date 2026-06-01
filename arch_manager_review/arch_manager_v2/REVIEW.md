# Archaeological Manager — Code Review & Changes

Reviewed: v1.0 (metadata) / internal v5–v6. QGIS ≥ 3.22.

## Overall verdict
A genuinely impressive, feature-rich plugin: Harris Matrix, context/pottery/
artifact registers, an interactive skeleton bone-inventory chart, customizable
recording sheets, CAD import, a polished PDF report exporter, dual light/dark
themes, and edit history. The *product* is strong. The *code* works but carries
real structural debt that will make it hard to maintain and extend safely.

## Fixes applied in this copy (safe, behavior-preserving)
1. **Grid-map PDF export was broken** (`dock.py::_export_grid_map`).
   `QPagedPaintDevice` and `QMarginsF` were used but never imported, so the PDF
   branch always failed with a confusing "PDF error" dialog. Added the imports.
2. **`harris_view.py::export_png` used `QImage` without importing it** → guaranteed
   `NameError` whenever called. Added the import. (Note: this module is currently
   dead code — see below — but the bug is now fixed should it be wired up.)
3. **Six file-handle leaks** — `json.load(open(...))` / `json.dump(..., open(...))`
   never closed the file. Converted to `with open(...)` blocks in `LoginDialog`,
   the pre-excavation checklist save/load, and the site-photo config.

All files still `py_compile` cleanly after the changes.

## High-priority issues to address next (NOT changed here — need a running QGIS to verify)

### 1. Massive duplication between `dock.py` and the "split" modules
`dock.py`'s header claims logic was split into `data_manager.py`, `harris_view.py`,
etc. In reality `dock.py` **re-imports and then re-defines** the same symbols, and
the copies have already drifted:
- `coerce()` — data_manager maps `"NULL"`/`"None"` → `None`; dock.py's local copy
  does not, so text fields can be saved with the literal string `"NULL"`.
- `SCHEMAS['bone_inventory']` — data_manager has a `notes` column; dock.py's copy
  dropped it. The table you get depends on which code path created it.
- `HarrisView` / `compute_layout` / `ContextNode` exist in both files with
  **different box dimensions** (80×28 vs 112×44).
- `harris_view.py` is never imported anywhere → **the whole module is dead code.**

➡ Pick one source of truth: delete the duplicates from `dock.py`, import from the
modules, and remove (or actually use) `harris_view.py`.

### 2. Monkey-patching the main class (39 methods)
`_patch_archwindow()`, `_build_archaeologist_tab_and_patch()`, and
`_build_grid_map_tab_and_patch()` graft ~39 methods onto `ArchWindow` *after* the
class is defined, including re-wrapping `_write_feat` and `_delete_rows` at import
time. This is the single biggest readability/maintenance hazard. Fold these methods
into the class body (or real mixin base classes).

### 3. Silent exception swallowing (~110 occurrences)
`except: pass` / `except Exception: pass` are everywhere. Bugs disappear instead of
surfacing. Narrow the exception types and at minimum log via `QgsMessageLog`.

### 4. Theme toggle doesn't reach two tabs
`bone_view.py` (SkeletonView) and `recording_sheets.py` use hardcoded hex colors
(`#1e1e1e`, `#f5f2eb`, `#888`, …) instead of the object-name + QSS approach used by
`widgets.py`. Toggle to Light mode and those panels stay dark. Route them through
`build_*_qss` like the rest.

### 5. User data is written inside the plugin folder
`.user_config.json`, `.site_photos.json`, and `user_sheets/` live in
`os.path.dirname(__file__)`. A plugin upgrade/reinstall wipes that folder and the
user's settings with it. Use `QgsSettings` or `QStandardPaths.AppDataLocation`.

## Lower-priority polish
- `metadata.txt` is missing `tracker`, `repository`, and `homepage` (required for
  publishing to the official QGIS plugin repo) and `email` is blank.
- `bare except:` on the relationships JSON parse in `ArchWindow.__init__`.
- `widgets.py` keeps a `SearchBar` explicitly marked "legacy — prefer SearchInput";
  pick one.
- Editing uses `startEditing()/commitChanges()` per write with no transaction
  grouping; bulk imports will be slow and aren't atomic.
- Consider a small test harness (mock `qgis.core`) so syntax/regression checks can
  run in CI without a full QGIS.
