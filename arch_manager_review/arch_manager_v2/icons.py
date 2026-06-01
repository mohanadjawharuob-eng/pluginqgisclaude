"""icons.py — small, themeable SVG line-icon set.

Replaces the emoji used in the UI with crisp vector icons that render the same
on every OS and recolour with the active theme. Icons are stroke-based 24×24
paths (Feather, MIT-licensed); the stroke colour is injected at render time so
the same icon works for active (accent) and inactive (dim) states.

Usage:
    from .icons import icon, pixmap
    btn.setIcon(icon("layers", "#D4A94D"))
    label.setPixmap(pixmap("home", c["text_dim"], 18))
"""
from qgis.PyQt.QtCore import QByteArray, Qt
from qgis.PyQt.QtGui import QPixmap, QPainter, QIcon, QColor
from qgis.PyQt.QtSvg import QSvgRenderer

# ── 24×24 stroke icon bodies ({color} stroke injected at render) ─────────────
_PATHS = {
    "home":     '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
                '<polyline points="9 22 9 12 15 12 15 22"/>',
    # Stratigraphy — stacked layers
    "layers":   '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
                '<polyline points="2 17 12 22 22 17"/>'
                '<polyline points="2 12 12 17 22 12"/>',
    # Finds — amphora / vessel
    "finds":    '<path d="M9 3h6"/>'
                '<path d="M9.5 3c0 2 1 2.6 1 3.6C10.5 7.6 7 9.5 7 14a5 5 0 0 0 10 0'
                'c0-4.5-3.5-6.4-3.5-7.4 0-1 1-1.6 1-3.6"/>',
    # Recording — clipboard
    "clipboard":'<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
                '<rect x="8" y="2" width="8" height="4" rx="1"/>',
    # Field — map sheet
    "map":      '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>'
                '<line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>',
    # Analysis — bar chart
    "chart":    '<line x1="18" y1="20" x2="18" y2="10"/>'
                '<line x1="12" y1="20" x2="12" y2="4"/>'
                '<line x1="6" y1="20" x2="6" y2="14"/>',
    # Provenance — clock / history
    "history":  '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    # Settings — sliders
    "sliders":  '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
                '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
                '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
                '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
                '<line x1="17" y1="16" x2="23" y2="16"/>',
    # Guide — book
    "book":     '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
                '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "search":   '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "pin":      '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
                '<circle cx="12" cy="10" r="3"/>',
    "plus":     '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "link":     '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/>'
                '<path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
}

# Friendly aliases so callers can use domain words
_ALIAS = {
    "stratigraphy": "layers", "context": "layers", "matrix": "layers",
    "recording": "clipboard", "sheet": "clipboard", "skeleton": "clipboard",
    "field": "map", "grid": "map", "analysis": "chart", "stats": "chart",
    "provenance": "history", "settings": "sliders", "guide": "book",
    "relationships": "link",
}


def _svg(name: str, color: str) -> bytes:
    body = _PATHS.get(name) or _PATHS.get(_ALIAS.get(name, ""), _PATHS["home"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


def pixmap(name: str, color="#E8E4DC", size: int = 20) -> QPixmap:
    """Render an icon to a transparent QPixmap at the given stroke colour."""
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    try:
        renderer = QSvgRenderer(QByteArray(_svg(name, color)))
        p = QPainter(px)
        renderer.render(p)
        p.end()
    except Exception:
        pass
    return px


def icon(name: str, color="#E8E4DC", size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))


def has(name: str) -> bool:
    return name in _PATHS or name in _ALIAS
