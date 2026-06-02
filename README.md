# Archaeological Manager — QGIS plugin

Field recording & post-excavation management for archaeology: Harris Matrix,
context / pottery / artifact registers, an interactive skeleton bone-inventory
chart, customizable recording sheets, **Crates** (virtual storage boxes),
artifact photo auto-matching, CAD import and a PDF site-report exporter.
Works directly on your existing QGIS GeoPackage layers.

## Install
1. Download this repository (green **Code** button → **Download ZIP**) and extract it.
2. Copy the **`arch_manager_v2`** folder into your QGIS plugins directory:
   - **Windows:** `%APPDATA%\\QGIS\\QGIS3\\profiles\\default\\python\\plugins\\`
   - **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Restart QGIS → **Plugins → Manage and Install Plugins** → enable *Archaeological Manager*.

Tip: you can also zip just the `arch_manager_v2` folder and use
**Plugins → Install from ZIP**.

## Tests
A stub-QGIS harness runs with plain Python (no QGIS/PyQt/pytest needed):

```
python3 tests/run_tests.py
```
