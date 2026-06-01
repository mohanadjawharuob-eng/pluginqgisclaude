"""widgets.py v3 — theme-aware reusable components.

All widget classes use setObjectName() + QSS rules rather than inline
setStyleSheet(CLR[...]) calls.  This means they respond correctly to
theme toggle (light ↔ dark) without any per-widget updateTheme() plumbing.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QToolButton, QScrollArea, QLineEdit
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer, QSize
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen, QBrush

from .styles import (CLR, LIGHT_CLR, btn_style, FONT_SANS,
                     CARD_QSS, TABLE_QSS,
                     BTN_PRIMARY, BTN_SECONDARY, BTN_GHOST, NAV_ITEM_QSS,
                     RADIUS, RADIUS_SM, FONT_SIZE_XS, FONT_SIZE_SM,
                     FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_MD)
from .icons import pixmap as icon_pixmap, has as icon_has


# ── Card  —  reusable content block ──────────────────────────────────────────
class Card(QFrame):
    """Standard content card with optional header."""
    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
        if title or subtitle:
            self._build_header(title, subtitle)
        self._body = QWidget()
        self._body.setStyleSheet("background:transparent;")
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(20, 16, 20, 20)
        self.body_layout.setSpacing(12)
        self._outer.addWidget(self._body, 1)

    def _build_header(self, title: str, subtitle: str):
        hdr = QFrame()
        hdr.setObjectName("cardHeader")
        h = QHBoxLayout(hdr)
        h.setContentsMargins(20, 14, 20, 14)
        h.setSpacing(8)
        vbox = QVBoxLayout(); vbox.setSpacing(2)
        t = QLabel(title); t.setObjectName("cardTitle")
        vbox.addWidget(t)
        if subtitle:
            s = QLabel(subtitle); s.setObjectName("cardSub")
            vbox.addWidget(s)
        h.addLayout(vbox); h.addStretch()
        self._header = hdr
        self._header_layout = h
        self._outer.addWidget(hdr)

    def header_layout(self):
        return getattr(self, "_header_layout", None)


# ── Stat card  —  big number + label + delta indicator ──────────────────────
class StatCard(QFrame):
    """Dashboard stat card — big number + label + optional delta."""
    def __init__(self, label: str, value: str = "0", icon: str = "",
                 delta: str = "", delta_positive: bool = True,
                 accent: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(110)
        accent = accent or CLR["accent"]
        outer = QHBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16); outer.setSpacing(14)
        if icon:
            ic = QLabel(icon)
            ic.setFixedSize(44, 44)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(
                f"background:{accent}28;color:{accent};"
                f"border-radius:{RADIUS_SM};font-size:20px;")
            outer.addWidget(ic)
        col = QVBoxLayout(); col.setSpacing(4)
        lbl = QLabel(label.upper()); lbl.setObjectName("statLabel")
        col.addWidget(lbl)
        self._val = QLabel(str(value)); self._val.setObjectName("statBig")
        col.addWidget(self._val)
        if delta:
            arrow = "↑" if delta_positive else "↓"
            d = QLabel(f"{arrow} {delta}")
            d.setObjectName("statDelta")
            col.addWidget(d)
        outer.addLayout(col); outer.addStretch()

    def set_value(self, v):
        self._val.setText(str(v))


# ── Pill / badge ─────────────────────────────────────────────────────────────
class Pill(QLabel):
    """Small coloured tag (e.g. period, origin)."""
    def __init__(self, text: str, color: str = None, parent=None):
        super().__init__(text, parent)
        color = color or CLR["accent_3"]
        self.setStyleSheet(
            f"background:{color}22;color:{color};border-radius:10px;"
            f"padding:3px 10px;font-size:{FONT_SIZE_XS};font-weight:600;")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)


# ── Status badge (site connection indicator) ─────────────────────────────────
class StatusBadge(QFrame):
    """Home-tab 'connected site' card — theme-aware via update_theme()."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("siteBadge")
        self._c = CLR
        self._connected = False
        self._site_name = ""
        self._n_layers = 0
        self._build()
        self._apply_styles()

    def _build(self):
        h = QHBoxLayout(self); h.setContentsMargins(12, 10, 12, 10); h.setSpacing(10)
        self._icon = QLabel("○")
        self._icon.setFixedSize(36, 36)
        self._icon.setAlignment(Qt.AlignCenter)
        h.addWidget(self._icon)
        col = QVBoxLayout(); col.setSpacing(0)
        self._line1 = QLabel("No site")
        self._line2 = QLabel("Open a GeoPackage")
        col.addWidget(self._line1); col.addWidget(self._line2)
        h.addLayout(col); h.addStretch()
        self._dot = QLabel(""); self._dot.setFixedSize(10, 10)
        h.addWidget(self._dot)

    def _apply_styles(self):
        c = self._c
        if self._connected:
            acc = c['accent']
            self._icon.setStyleSheet(
                f"background:{acc}28;border-radius:18px;color:{acc};"
                f"font-size:14px;font-weight:bold;")
            self._dot.setStyleSheet(f"background:{acc};border-radius:5px;")
            self.setStyleSheet(
                f"QFrame#siteBadge{{background:{c['bg_card']};"
                f"border:1px solid {acc};border-radius:{RADIUS};}}")
        else:
            self._icon.setStyleSheet(
                f"background:{c['bg_card_2']};border-radius:18px;"
                f"color:{c['text_dim']};font-size:18px;font-weight:bold;")
            self._dot.setStyleSheet(f"background:{c['text_muted']};border-radius:5px;")
            self.setStyleSheet(
                f"QFrame#siteBadge{{background:{c['bg_card']};"
                f"border:1px solid {c['border']};border-radius:{RADIUS};}}")
        self._line1.setStyleSheet(
            f"color:{c['text']};font-size:13px;font-weight:600;background:transparent;")
        self._line2.setStyleSheet(
            f"color:{c['text_dim']};font-size:11px;background:transparent;")

    def update_theme(self, c):
        self._c = c
        self._apply_styles()

    def set_connected(self, site: str, n_layers: int):
        self._connected = True; self._site_name = site; self._n_layers = n_layers
        self._icon.setText(site[:2].upper() if site else "?")
        self._line1.setText(site)
        self._line2.setText(f"{n_layers} layers connected")
        self._apply_styles()

    def set_disconnected(self):
        self._connected = False
        self._icon.setText("○")
        self._line1.setText("No site")
        self._line2.setText("Open a GeoPackage")
        self._apply_styles()


# ── Sidebar Nav Item ─────────────────────────────────────────────────────────
class NavItem(QPushButton):
    """Sidebar nav button — icon + label + subtitle stacked vertically."""
    def __init__(self, icon: str, label: str, sublabel: str = "", parent=None):
        super().__init__(parent)
        self._c = CLR
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._icon = icon
        self._label = label
        self._sublabel = sublabel
        self._build()

    def _build(self):
        self.setText("")
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        ic = QLabel()
        ic.setFixedSize(42, 46)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:transparent;")
        self._icon_lbl = ic
        self._paint_icon(self._c.get('sidebar_text_dim', self._c['text_dim']))
        h.addWidget(ic)

    def _paint_icon(self, color):
        """Render the icon as a recoloured SVG, or fall back to text/emoji."""
        if icon_has(self._icon):
            self._icon_lbl.setPixmap(icon_pixmap(self._icon, color, 20))
        else:
            self._icon_lbl.setText(self._icon)
            self._icon_lbl.setStyleSheet(
                f"font-size:16px;color:{color};background:transparent;")
        col = QVBoxLayout(); col.setContentsMargins(0, 0, 0, 0); col.setSpacing(0)
        self._lbl_text = QLabel(self._label)
        self._lbl_text.setStyleSheet(
            f"font-size:{FONT_SIZE_SM};font-weight:500;background:transparent;")
        col.addWidget(self._lbl_text)
        if self._sublabel:
            sub = QLabel(self._sublabel)
            sub.setStyleSheet("font-size:9px;background:transparent;")
            self._sub_lbl = sub
            col.addWidget(sub)
        else:
            self._sub_lbl = None
        h.addLayout(col, 1)
        h.addSpacing(8)

    def setChecked(self, b: bool):
        super().setChecked(b)
        c = self._c
        active_col   = c['accent']
        inactive_col = c.get('sidebar_text_dim', c['text_dim'])
        col = active_col if b else inactive_col
        self._lbl_text.setStyleSheet(
            f"color:{col};font-size:{FONT_SIZE_SM};"
            f"font-weight:{'600' if b else '500'};background:transparent;")
        self._paint_icon(active_col if b else inactive_col)
        if self._sub_lbl:
            dim = c.get('sidebar_text_dim', c['text_dim'])
            self._sub_lbl.setStyleSheet(f"font-size:9px;color:{dim};background:transparent;")

    def update_theme(self, c):
        self._c = c
        self.setChecked(self.isChecked())


# ── Toast / status message ───────────────────────────────────────────────────
class ToastLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(20)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setObjectName("statusMsg")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear)

    def show_msg(self, text: str, ms: int = 4000, error: bool = False):
        self.setObjectName("statusMsgErr" if error else "statusMsgOk")
        # Force QSS re-evaluation after objectName change
        self.style().unpolish(self); self.style().polish(self)
        self.setText(text)
        self._timer.start(ms)

    def show_error(self, text: str):
        self.show_msg(text, ms=6000, error=True)


# ── Data table ───────────────────────────────────────────────────────────────
class DataTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(36)
        self.setShowGrid(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def populate(self, headers, rows, fids=None):
        self.clear()
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setRowCount(len(rows))
        if fids is not None:
            self.setProperty("_fids", fids)
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(ri, ci, item)
        self.resizeColumnsToContents()


# ── Search bar ───────────────────────────────────────────────────────────────
class SearchBar(QFrame):
    """Legacy search bar — prefer SearchInput for new code."""
    def __init__(self, placeholder="Search…", parent=None):
        super().__init__(parent)
        self.setObjectName("searchBox")
        self.setFixedHeight(36)
        h = QHBoxLayout(self); h.setContentsMargins(12, 0, 12, 0); h.setSpacing(8)
        ic = QLabel("🔍"); h.addWidget(ic)
        self.edit = QLineEdit(); self.edit.setPlaceholderText(placeholder)
        h.addWidget(self.edit, 1)


# ── Top action bar — for page headers ────────────────────────────────────────
class TopBar(QFrame):
    """The global page header bar (title + theme toggle + actions)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(64)
        h = QHBoxLayout(self); h.setContentsMargins(24, 0, 24, 0); h.setSpacing(12)
        self._title_col = QVBoxLayout(); self._title_col.setSpacing(0)
        self.title = QLabel("Dashboard"); self.title.setObjectName("pageTitle")
        self.sub = QLabel("Overview"); self.sub.setObjectName("pageSub")
        self._title_col.addWidget(self.title)
        self._title_col.addWidget(self.sub)
        h.addLayout(self._title_col)
        h.addStretch()
        self._actions = h
        self._action_widgets = []

    def set_title(self, title: str, sub: str = ""):
        self.title.setText(title)
        self.sub.setText(sub)

    def add_action(self, widget):
        self._actions.addWidget(widget)
        self._action_widgets.append(widget)


# ── Action button row (legacy) ───────────────────────────────────────────────
class ActionBar(QWidget):
    def __init__(self, actions: list, parent=None):
        super().__init__(parent)
        hl = QHBoxLayout(self); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(6)
        self.buttons = {}
        for label, tip, cb, sk in actions:
            b = QPushButton(label)
            b.setToolTip(tip)
            b.setObjectName(f"btn_{sk}" if not sk.startswith("btn_") else sk)
            b.setCursor(Qt.PointingHandCursor)
            if cb: b.clicked.connect(cb)
            hl.addWidget(b); self.buttons[label] = b
        hl.addStretch()

    def set_enabled(self, label, enabled):
        if label in self.buttons:
            self.buttons[label].setEnabled(enabled)


# ── Section header ────────────────────────────────────────────────────────────
class SectionHeader(QFrame):
    """Small ALL-CAPS section label inside a content area."""
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(self); hl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text.upper())
        lbl.setObjectName("mutedXs")
        lbl.setStyleSheet(
            f"font-weight:600;letter-spacing:1.2px;background:transparent;"
            f"font-size:{FONT_SIZE_XS};")
        hl.addWidget(lbl); hl.addStretch()


# ── Collapsible panel ─────────────────────────────────────────────────────────
class CollapsiblePanel(QWidget):
    toggled = pyqtSignal(bool)
    def __init__(self, title: str, content: QWidget,
                 collapsed: bool = True, parent=None):
        super().__init__(parent)
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        self._btn = QPushButton(f"{'▶' if collapsed else '▼'}  {title}")
        self._btn.setCheckable(True); self._btn.setChecked(not collapsed)
        self._btn.setObjectName("collapseBtn")
        self._btn.clicked.connect(self._on_toggle)
        self._content = content
        self._content.setVisible(not collapsed)
        self._title = title
        vl.addWidget(self._btn); vl.addWidget(content)

    def _on_toggle(self, checked):
        self._content.setVisible(checked)
        self._btn.setText(f"{'▼' if checked else '▶'}  {self._title}")
        self.toggled.emit(checked)


def icon_btn(emoji, tooltip, size=28, bg=None, hover=None):
    """Small square icon-only tool button."""
    b = QToolButton()
    b.setText(emoji); b.setToolTip(tooltip)
    b.setFixedSize(size, size)
    b.setObjectName("iconBtn")
    b.setCursor(Qt.PointingHandCursor)
    return b


# ── Page content title widget ─────────────────────────────────────────────────
class ContentTitle(QWidget):
    """Page-level title + subtitle used at the top of each content tab.

    Uses objectName-based QSS rules so it themes correctly on toggle.
    """
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self.setStyleSheet("background:transparent;")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 12)
        v.setSpacing(3)
        t = QLabel(title)
        t.setObjectName("secTitle")
        v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("secSub")
            v.addWidget(s)


# ── Search input (icon + QLineEdit) ──────────────────────────────────────────
class SearchInput(QFrame):
    """Rounded search box with magnifying-glass icon.

    Exposes `.textChanged` signal and `.text()` / `.setText()` / `.clear()`.
    """
    def __init__(self, placeholder="Search…", parent=None):
        super().__init__(parent)
        self.setObjectName("searchBox")
        self.setFixedHeight(36)
        h = QHBoxLayout(self); h.setContentsMargins(12, 0, 12, 0); h.setSpacing(8)
        ic = QLabel("🔍"); h.addWidget(ic)
        self._edit = QLineEdit(); self._edit.setPlaceholderText(placeholder)
        h.addWidget(self._edit, 1)
        self.textChanged = self._edit.textChanged

    def text(self): return self._edit.text()
    def setText(self, t): self._edit.setText(t)
    def clear(self): self._edit.clear()


# ── Brand header (sidebar top) ───────────────────────────────────────────────
class BrandHeader(QWidget):
    """Sidebar brand row: logo tile + name + sub.

    Lives inside the always-dark sidebar, so it's fine to use CLR here.
    """
    def __init__(self, title="Arch Manager", sub="QGIS plugin v2", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{CLR['bg_root']};border-bottom:1px solid {CLR['border']};")
        h = QHBoxLayout(self); h.setContentsMargins(18, 18, 18, 18); h.setSpacing(10)
        logo = QLabel("⚱"); logo.setFixedSize(36, 36); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"background:{CLR['accent']}28;color:{CLR['accent']};"
            f"font-size:18px;font-weight:bold;border-radius:8px;")
        h.addWidget(logo)
        col = QVBoxLayout(); col.setSpacing(0)
        t = QLabel(title); t.setObjectName("brand")
        s = QLabel(sub); s.setObjectName("brand_sub")
        col.addWidget(t); col.addWidget(s)
        h.addLayout(col); h.addStretch()


SiteCard = StatusBadge  # legacy alias


# ── Detail panel ──────────────────────────────────────────────────────────────
class DetailPanel(QFrame):
    """Right-hand detail panel showing key/value pairs for a selected row.

    Methods
    -------
    show_record(title, pairs, pill_fields)  — replace all content at once
    clear()                                 — reset to placeholder state
    set_badge(text)                         — append a badge to the title
    add_field(label, value, pill)           — append one field row
    """
    def __init__(self, title="Details", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(260)
        self._base_title = title
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)

        # Header
        hdr = QFrame(); hdr.setObjectName("cardHeader")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(16, 12, 16, 12)
        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("cardTitle")
        hh.addWidget(self._title_lbl); hh.addStretch()
        v.addWidget(hdr)

        # Scroll body
        self._body_w = QWidget(); self._body_w.setStyleSheet("background:transparent;")
        self._body = QVBoxLayout(self._body_w)
        self._body.setContentsMargins(16, 12, 16, 16); self._body.setSpacing(10)
        v.addWidget(self._body_w, 1)

        self._is_empty = True
        self._show_placeholder()

    # ── public API ────────────────────────────────────────────────────────────

    def clear(self):
        self._wipe()
        self._is_empty = True
        self._show_placeholder()

    def set_badge(self, text: str):
        base = self._base_title
        self._title_lbl.setText(f"{base}  {text}" if text else base)

    def add_field(self, label: str, value, pill: bool = False):
        if self._is_empty:
            self._wipe()
            self._is_empty = False
        # Remove trailing stretch so we can append then re-add it
        self._pop_stretch()
        # Field container
        row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
        row_v = QVBoxLayout(row_w); row_v.setContentsMargins(0, 0, 0, 0); row_v.setSpacing(2)
        lbl = QLabel(label.upper()); lbl.setObjectName("detailKey")
        row_v.addWidget(lbl)
        valstr = str(value) if value not in (None, "", "NULL", "None") else "—"
        if pill and valstr != "—":
            p = Pill(valstr)
            wrap = QHBoxLayout(); wrap.setContentsMargins(0, 0, 0, 0)
            wrap.addWidget(p); wrap.addStretch()
            row_v.addLayout(wrap)
        else:
            v = QLabel(valstr); v.setObjectName("detailVal"); v.setWordWrap(True)
            row_v.addWidget(v)
        self._body.addWidget(row_w)
        self._body.addStretch()

    def show_record(self, title: str, pairs: list, pill_fields=None):
        """Replace all content at once (batch API)."""
        pill_fields = pill_fields or set()
        self._base_title = title
        self._title_lbl.setText(title)
        self._wipe()
        self._is_empty = False
        for label, value in pairs:
            self.add_field(label, value, pill=(label in pill_fields))
        if not pairs:
            self._is_empty = True
            self._show_placeholder()

    # ── internals ─────────────────────────────────────────────────────────────

    def _show_placeholder(self):
        lbl = QLabel("Select a row to see details")
        lbl.setObjectName("detailEmpty")
        lbl.setAlignment(Qt.AlignCenter); lbl.setWordWrap(True)
        self._body.addWidget(lbl)
        self._body.addStretch()

    def _wipe(self):
        while self._body.count():
            it = self._body.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _pop_stretch(self):
        if self._body.count() > 0:
            last = self._body.itemAt(self._body.count() - 1)
            if last and last.spacerItem():
                self._body.takeAt(self._body.count() - 1)
