"""pdf_export.py v6 — clean values, friendly headers, image slots, photo plates,
professional cover, condensed tables. The report is the final deliverable, so this
module is written to produce a polished archaeological site report."""
import os

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QCheckBox, QPushButton, QLabel, QFileDialog, QLineEdit,
    QDialogButtonBox, QComboBox, QListWidget, QListWidgetItem,
    QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QAbstractItemView,
    QTextEdit
)
from qgis.PyQt.QtCore import Qt, QRectF, QDate, QMarginsF, QSize
from qgis.PyQt.QtGui import (
    QColor, QPen, QBrush, QPainter, QFont, QPixmap,
    QPagedPaintDevice, QFontMetrics
)

try:
    from qgis.PyQt.QtGui import QPdfWriter as _QPdfWriter
    HAS_PDF_WRITER = True
except ImportError:
    HAS_PDF_WRITER = False

try:
    from qgis.PyQt.QtPrintSupport import QPrinter
    HAS_PRINTER = True
except ImportError:
    HAS_PRINTER = False


def _mk_font(family, size, bold=False, italic=False):
    f = QFont(family, max(1, int(size)))
    if bold:   f.setBold(True)
    if italic: f.setItalic(True)
    return f


# ── Data cleaning ─────────────────────────────────────────────────────────────
def _clean_val(v):
    """Convert a raw QGIS attribute into a display string.
    NULL / None / empty become '' (the user never wants to see 'NULL')."""
    if v is None:
        return ""
    try:
        # QVariant NULL stringifies to 'NULL'
        from qgis.PyQt.QtCore import QVariant
        if isinstance(v, QVariant) and v.isNull():
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if s.lower() in ("null", "none", "nan", "<null>"):
        return ""
    # Pretty integers (3.0 -> 3) but keep real decimals
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s


# Map raw DB column names to human-readable headers
FRIENDLY_HEADERS = {
    "context_num": "Context", "context_r": "Context", "ctx_num": "Context",
    "context": "Context", "num": "No.", "number": "No.", "no": "No.",
    "type": "Type", "context_type": "Type", "kind": "Type",
    "period": "Period", "phase": "Phase", "horizon": "Horizon",
    "description": "Description", "desc": "Description",
    "above_ctx": "Above", "below_ctx": "Below", "equals_ctx": "Equals",
    "cuts_ctx": "Cuts", "cut_by_ctx": "Cut by",
    "notes": "Notes", "initials": "Recorder", "recorder": "Recorder",
    "date": "Date", "site": "Site", "area": "Area", "trench": "Trench",
    "form": "Form", "part": "Part", "fabric": "Fabric", "ware": "Ware",
    "count": "Count", "qty": "Count", "origin": "Origin",
    "decoration": "Decoration", "preservation": "Preservation",
    "material": "Material", "material_detail": "Material",
    "detailed_description": "Description", "condition": "Condition",
    "provenance": "Provenance", "parallels": "Parallels / comparanda",
    "dimensions": "Dimensions", "weight": "Weight",
    "artifact_id": "Artifact ID", "artifact_num": "Artifact",
    "skeleton_num": "Skeleton", "age_group": "Age", "age": "Age",
    "sex": "Sex", "position": "Position", "orientation": "Orientation",
    "element": "Element", "side": "Side", "bone": "Element",
    "image_path": "Photo", "photo": "Photo", "image": "Photo",
}

# Internal / geometry columns never shown in tables
HIDDEN_COLS = {"fid", "gid", "ogc_fid", "objectid", "geom", "geometry",
               "the_geom", "shape", "id_0"}

# Columns whose values are image paths -> rendered as a thumbnail slot
IMAGE_COLS = {"image_path", "photo", "image", "picture", "img"}


def _friendly(name):
    key = str(name).lower().strip()
    if key in FRIENDLY_HEADERS:
        return FRIENDLY_HEADERS[key]
    return name.replace("_", " ").strip().title()


SECTION_NAMES = {
    "cover":           "Cover Page",
    "harris":          "Harris Matrix",
    "context_sheets":  "Context Detail Sheets",
    "contexts":        "Contexts Inventory",
    "strat_matrix":    "Stratigraphic Matrix Table",
    "pottery":         "Pottery Inventory",
    "artifacts":       "Artifacts Inventory",
    "artifact_details":"Artifact Catalogue",
    "skeletons":       "Skeletal Remains",
    "bone_form":       "Bone Inventory Form",
    "rels":            "Stratigraphic Relationships",
    "plates":          "Photographic Plates",
}

COLOR_SCHEMES = {
    # Refined field-report palettes. Header = band/heading colour, accent = rules.
    "Field Report (default)": {"color_header":"#2b2b2b","color_accent":"#9a7b3f","color_text":"#1d1d1d","color_row_a":"#ffffff","color_row_b":"#f3efe7"},
    "Archaeology Gold":       {"color_header":"#2e2a26","color_accent":"#c89b3c","color_text":"#1e1a14","color_row_a":"#fdfaf4","color_row_b":"#f0ebe0"},
    "Parchment":              {"color_header":"#2a3d28","color_accent":"#4a7c59","color_text":"#1e1a14","color_row_a":"#fdfaf4","color_row_b":"#f0ebe0"},
    "Balamand Blue":          {"color_header":"#0d3a63","color_accent":"#1a4a8c","color_text":"#0a1a2e","color_row_a":"#ffffff","color_row_b":"#eef3f9"},
    "Clean White":            {"color_header":"#2a2a2a","color_accent":"#5a6a7a","color_text":"#111111","color_row_a":"#ffffff","color_row_b":"#f4f6f8"},
    "Terracotta":             {"color_header":"#4a2218","color_accent":"#b86040","color_text":"#1e1408","color_row_a":"#fdf8f4","color_row_b":"#f4e8e0"},
    "Minimal Grey":           {"color_header":"#3a3a3a","color_accent":"#7a7a7a","color_text":"#222222","color_row_a":"#fafafa","color_row_b":"#efefef"},
}

DEFAULT = {
    "margin_lr": 46, "margin_top": 50, "margin_bot": 46,
    "font_scale": 1.0, "row_height": 15, "col_trunc": 999, "wrap_text": True,
    "color_header": "#2b2b2b", "color_accent": "#9a7b3f",
    "color_text": "#1d1d1d", "color_row_a": "#ffffff", "color_row_b": "#f3efe7",
    "paper": "A4",
    "section_order": ["cover","harris","strat_matrix","contexts","pottery",
                      "artifacts","artifact_details","skeletons","bone_form",
                      "rels","plates"],
    "sections": {k: (k != "context_sheets") for k in
                 ["cover","harris","strat_matrix","contexts","pottery","artifacts",
                  "artifact_details","skeletons","bone_form","rels","plates",
                  "context_sheets"]},
    "harris_pages": 3,
}


# ── Designer Dialog ───────────────────────────────────────────────────────────
class ReportDesignerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Designer"); self.setMinimumSize(760, 620)
        self._build_ui()

    def _build_ui(self):
        vl = QVBoxLayout(self); tabs = QTabWidget()

        # Tab 1: Sections
        t1 = QWidget(); t1l = QHBoxLayout(t1); t1l.setSpacing(12)
        left_w = QWidget(); left_vl = QVBoxLayout(left_w); left_vl.setContentsMargins(0,0,0,0)
        sg = QGroupBox("Sections — tick to include, use ↑↓ to reorder")
        sv = QVBoxLayout(sg)
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.setDefaultDropAction(Qt.MoveAction)
        for k in DEFAULT["section_order"] + ["context_sheets"]:
            item = QListWidgetItem(SECTION_NAMES.get(k, k))
            item.setData(Qt.UserRole, k)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if DEFAULT["sections"].get(k, True) else Qt.Unchecked)
            self._list.addItem(item)
        sv.addWidget(self._list)
        sv.addWidget(QLabel("<small>Context Detail Sheets create one full page per context "
                            "(with photo slots) — leave off for large sites.</small>"))
        ud_row = QHBoxLayout(); ud_row.setSpacing(4)
        up_btn = QPushButton("▲ Move Up"); down_btn = QPushButton("▼ Move Down")
        def _move_up():
            r = self._list.currentRow()
            if r > 0:
                it = self._list.takeItem(r); self._list.insertItem(r-1, it)
                self._list.setCurrentRow(r-1); self._update_preview()
        def _move_down():
            r = self._list.currentRow()
            if r < self._list.count()-1:
                it = self._list.takeItem(r); self._list.insertItem(r+1, it)
                self._list.setCurrentRow(r+1); self._update_preview()
        up_btn.clicked.connect(_move_up); down_btn.clicked.connect(_move_down)
        ud_row.addWidget(up_btn); ud_row.addWidget(down_btn); ud_row.addStretch()
        sv.addLayout(ud_row)
        left_vl.addWidget(sg, 1)

        hg = QGroupBox("Report header")
        hf = QFormLayout(hg)
        self._title = QLineEdit("Archaeological Site Report")
        self._author = QLineEdit(); self._site = QLineEdit(); self._season = QLineEdit()
        self._season.setPlaceholderText("e.g. Season 2025")
        self._logo = QLineEdit(); self._logo.setReadOnly(True)
        self._logo.setPlaceholderText("(University of Balamand logo used by default)")
        lb = QPushButton("Browse…"); lb.clicked.connect(self._pick_logo)
        lr = QHBoxLayout(); lr.addWidget(self._logo, 1); lr.addWidget(lb)
        self._logo_size = QSpinBox(); self._logo_size.setRange(20, 120); self._logo_size.setValue(40)
        self._logo_pos = QComboBox(); self._logo_pos.addItems(["Right","Left","Centre"])
        self._cover_img = QLineEdit(); self._cover_img.setReadOnly(True)
        self._cover_img.setPlaceholderText("Optional site/hero photo for the cover…")
        cb = QPushButton("Browse…"); cb.clicked.connect(self._pick_cover)
        cr = QHBoxLayout(); cr.addWidget(self._cover_img, 1); cr.addWidget(cb)
        hf.addRow("Title:", self._title); hf.addRow("Author:", self._author)
        hf.addRow("Site:", self._site); hf.addRow("Season:", self._season)
        hf.addRow("Logo:", lr); hf.addRow("Logo height:", self._logo_size)
        hf.addRow("Logo position:", self._logo_pos)
        hf.addRow("Cover photo:", cr)
        self._cover_desc=QTextEdit(); self._cover_desc.setMaximumHeight(70)
        self._cover_desc.setPlaceholderText("Optional cover abstract / summary paragraph…")
        hf.addRow("Cover text:", self._cover_desc)
        left_vl.addWidget(hg)
        t1l.addWidget(left_w, 2)

        right_w = QWidget(); right_vl = QVBoxLayout(right_w); right_vl.setContentsMargins(0,0,0,0)
        prev_grp = QGroupBox("Page order preview")
        prev_vl = QVBoxLayout(prev_grp)
        self._preview_text = QTextEdit(); self._preview_text.setReadOnly(True)
        self._preview_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        prev_vl.addWidget(self._preview_text)
        right_vl.addWidget(prev_grp, 1)
        t1l.addWidget(right_w, 1)

        self._list.itemChanged.connect(self._update_preview)
        self._list.model().rowsMoved.connect(self._update_preview)
        self._update_preview()
        tabs.addTab(t1, "Sections & Header")

        # Tab 2: Page Layout
        t2 = QWidget(); t2l = QFormLayout(t2)
        self._ml = QSpinBox(); self._ml.setRange(10,100); self._ml.setValue(46)
        self._mt = QSpinBox(); self._mt.setRange(10,100); self._mt.setValue(50)
        self._mb = QSpinBox(); self._mb.setRange(10,100); self._mb.setValue(46)
        self._fs = QDoubleSpinBox(); self._fs.setRange(0.5,2.0); self._fs.setSingleStep(0.05); self._fs.setValue(1.0); self._fs.setDecimals(2)
        self._rh = QSpinBox(); self._rh.setRange(10,50); self._rh.setValue(15)
        self._paper = QComboBox(); self._paper.addItems(["A4","Letter","A3"])
        self._wrap = QCheckBox("Wrap cell text (rows auto-expand)"); self._wrap.setChecked(True)
        self._hide_empty = QCheckBox("Hide columns that are entirely empty"); self._hide_empty.setChecked(True)
        self._hpages = QSpinBox(); self._hpages.setRange(1,10); self._hpages.setValue(3)
        t2l.addRow("Paper:", self._paper)
        t2l.addRow("Left/right margin:", self._ml)
        t2l.addRow("Top margin:", self._mt)
        t2l.addRow("Bottom margin:", self._mb)
        t2l.addRow("Font scale:", self._fs)
        t2l.addRow("Min row height:", self._rh)
        t2l.addRow("", self._wrap)
        t2l.addRow("", self._hide_empty)
        t2l.addRow("Harris Matrix pages:", self._hpages)
        self._harris_hide_iso=QCheckBox("Hide isolated contexts (no relationships)")
        t2l.addRow("", self._harris_hide_iso)
        self._strat_only_linked=QCheckBox("Stratigraphic matrix: only contexts with relationships")
        self._strat_only_linked.setChecked(True)
        t2l.addRow("", self._strat_only_linked)
        tabs.addTab(t2, "Page Layout")

        # Tab 3: Table Columns
        t3 = QWidget(); t3l = QFormLayout(t3)
        t3l.addRow(QLabel("<b>Columns per table</b> (comma-separated, blank = auto)"))
        self._col_ctx = QLineEdit(); self._col_ctx.setPlaceholderText("context_num, type, period, description, above_ctx, below_ctx, notes")
        self._col_pot = QLineEdit(); self._col_pot.setPlaceholderText("context_num, form, fabric, decoration, count, origin, period")
        self._col_art = QLineEdit(); self._col_art.setPlaceholderText("context_num, type, material, description, period")
        self._col_ske = QLineEdit(); self._col_ske.setPlaceholderText("skeleton_num, context_num, age_group, sex, position, notes")
        t3l.addRow("Contexts:", self._col_ctx); t3l.addRow("Pottery:", self._col_pot)
        t3l.addRow("Artifacts:", self._col_art); t3l.addRow("Skeletons:", self._col_ske)
        self._thumbs = QCheckBox("Add a Photo column to pottery & artifacts (thumbnail or empty slot)")
        self._thumbs.setChecked(True)
        t3l.addRow("", self._thumbs)
        tabs.addTab(t3, "Table Columns")

        # Tab 4: Colours
        t4 = QWidget(); t4l = QFormLayout(t4)
        self._scheme = QComboBox(); self._scheme.addItems(list(COLOR_SCHEMES.keys()))
        self._scheme.setCurrentText("Field Report (default)")
        self._scheme.currentTextChanged.connect(self._apply_scheme)
        t4l.addRow("Quick scheme:", self._scheme)
        self._cfs = {}
        for k, lbl in [("color_header","Header / band"),("color_accent","Accent / rules"),
                        ("color_text","Body text"),("color_row_a","Table row A"),("color_row_b","Table row B")]:
            le = QLineEdit(DEFAULT[k]); self._cfs[k] = le; t4l.addRow(lbl+":", le)
        t4l.addRow(QLabel("<small>Use #rrggbb hex values</small>"))
        tabs.addTab(t4, "Colours")

        vl.addWidget(tabs)
        bb = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        vl.addWidget(bb)

    def _update_preview(self, *args):
        if not hasattr(self, '_preview_text'): return
        lines = []; page = 1
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it.checkState() != Qt.Checked: continue
            key = it.data(Qt.UserRole); name = SECTION_NAMES.get(key, key)
            if key == "cover":
                lines.append(f"Page {page}: Cover & Contents"); page += 1; continue
            lines.append(f"Page {page}: ── {name} ──")
            if key == "harris":
                lines.append(f"   {name} diagram (1–3 sheets)"); page += 3
            elif key in ("contexts","pottery","artifacts","skeletons","strat_matrix","bone_form"):
                lines.append(f"   {name} table (auto-paginated)"); page += 2
            elif key == "rels":
                lines.append(f"   Relationships list"); page += 1
            elif key == "artifact_details":
                lines.append(f"   Catalogue entries with photos"); page += 2
            elif key == "context_sheets":
                lines.append(f"   One detailed sheet per context"); page += 3
            elif key == "plates":
                lines.append(f"   Photo plates grid"); page += 2
            else:
                page += 1
        self._preview_text.setPlainText("\n".join(lines))

    def _pick_logo(self):
        p,_ = QFileDialog.getOpenFileName(self,"Logo","","Images (*.png *.jpg *.jpeg *.svg)")
        if p: self._logo.setText(p)

    def _pick_cover(self):
        p,_ = QFileDialog.getOpenFileName(self,"Cover photo","","Images (*.png *.jpg *.jpeg)")
        if p: self._cover_img.setText(p)

    def _apply_scheme(self, name):
        for k, le in self._cfs.items():
            if k in COLOR_SCHEMES.get(name,{}): le.setText(COLOR_SCHEMES[name][k])

    def get_options(self):
        order = []; sections = {}
        for i in range(self._list.count()):
            it = self._list.item(i); key = it.data(Qt.UserRole)
            order.append(key); sections[key] = it.checkState() == Qt.Checked
        def pcols(s): return [c.strip() for c in s.split(",") if c.strip()] if s.strip() else []
        return {
            "section_order": order, "sections": sections,
            "title": self._title.text(), "author": self._author.text(),
            "site": self._site.text(), "season": self._season.text(),
            "logo": self._logo.text(), "logo_size": self._logo_size.value(),
            "logo_pos": self._logo_pos.currentText(),
            "cover_img": self._cover_img.text(),
            "cover_desc": self._cover_desc.toPlainText(),
            "paper": self._paper.currentText(),
            "margin_lr": self._ml.value(), "margin_top": self._mt.value(),
            "margin_bot": self._mb.value(), "font_scale": self._fs.value(),
            "row_height": self._rh.value(), "wrap_text": self._wrap.isChecked(),
            "hide_empty": self._hide_empty.isChecked(),
            "harris_pages": self._hpages.value(),
            "harris_hide_isolated": self._harris_hide_iso.isChecked(),
            "strat_only_linked": self._strat_only_linked.isChecked(),
            "thumbs": self._thumbs.isChecked(),
            "cols_ctx": pcols(self._col_ctx.text()), "cols_pot": pcols(self._col_pot.text()),
            "cols_art": pcols(self._col_art.text()), "cols_ske": pcols(self._col_ske.text()),
            **{k: le.text() for k,le in self._cfs.items()},
        }


# ── Page helper ───────────────────────────────────────────────────────────────
class Page:
    W, H = 595, 842

    def __init__(self, painter, device, opts, logo_px):
        self.p = painter; self.device = device; self.opts = opts; self.logo = logo_px
        self._pagenum = 0
        self.fs  = float(opts.get("font_scale", 1.0))
        self.ML  = int(opts.get("margin_lr", 46))
        self.MT  = int(opts.get("margin_top", 50))
        self.MB  = int(opts.get("margin_bot", 46))
        self.WRAP = bool(opts.get("wrap_text", True))
        self.MIN_RH = int(opts.get("row_height", 15))
        def c(k,d): return QColor(opts.get(k,d))
        self.C_HEAD=c("color_header","#2b2b2b"); self.C_ACC=c("color_accent","#9a7b3f")
        self.C_TEXT=c("color_text","#1d1d1d");   self.C_ROWA=c("color_row_a","#ffffff")
        self.C_ROWB=c("color_row_b","#f3efe7")
        self.C_MUTE=QColor("#8a8a8a")
        self.C_LINE=QColor("#d8d2c4")
        self.BW = self.W - 2*self.ML
        self.BODY_BOT = self.H - self.MB
        self.y = self.MT

    def new_page(self, is_first=False):
        if self._pagenum > 0: self.device.newPage()
        self._pagenum += 1
        self.y = self.MT
        if not is_first:
            self._draw_header(); self._draw_footer()
            self.y = self.MT + 30

    # ── running header / footer ──
    def _draw_header(self):
        p=self.p; ML=self.ML; W=self.W; fs=self.fs
        logo_h = min(26, int(self.opts.get("logo_size", 40)))
        # left accent tick
        p.setBrush(QBrush(self.C_ACC)); p.setPen(Qt.NoPen)
        p.drawRect(ML, self.MT-26, 3, 20)
        # site / title text
        site = self.opts.get("site","").strip()
        title = self.opts.get("title","Archaeological Site Report")
        p.setFont(_mk_font("Helvetica", max(1,int(8*fs)), bold=True)); p.setPen(self.C_TEXT)
        p.drawText(ML+8, self.MT-18, (site or title).upper())
        p.setFont(_mk_font("Helvetica", max(1,int(6.5*fs)))); p.setPen(self.C_MUTE)
        p.drawText(ML+8, self.MT-9, title if site else self.opts.get("season",""))
        # logo right
        if self.logo and not self.logo.isNull():
            lw = int(self.logo.width()*logo_h/max(1, self.logo.height()))
            p.drawPixmap(W-ML-lw, self.MT-28, lw, logo_h, self.logo)
        # bottom rule
        p.setPen(QPen(self.C_ACC, 0.8)); p.drawLine(ML, self.MT-4, W-ML, self.MT-4)

    def _draw_footer(self):
        p=self.p; ML=self.ML; W=self.W; H=self.H; fs=self.fs
        p.setPen(QPen(self.C_LINE, 0.6)); p.drawLine(ML, H-self.MB+6, W-ML, H-self.MB+6)
        p.setFont(_mk_font("Helvetica", max(1,int(6.5*fs)))); fm=p.fontMetrics()
        author = self.opts.get("author","").strip()
        p.setPen(self.C_MUTE)
        if author: p.drawText(ML, H-self.MB+18, author)
        pstr = str(self._pagenum)
        pw = fm.horizontalAdvance(pstr) if hasattr(fm,'horizontalAdvance') else fm.width(pstr)
        p.drawText((W-pw)//2, H-self.MB+18, pstr)
        date = QDate.currentDate().toString("d MMM yyyy")
        dw = fm.horizontalAdvance(date) if hasattr(fm,'horizontalAdvance') else fm.width(date)
        p.drawText(W-ML-dw, H-self.MB+18, date)

    # ── primitives ──
    def heading1(self, text, subtitle=""):
        self.y += 4
        self.p.setFont(_mk_font("Helvetica", max(1,int(15*self.fs)), bold=True))
        self.p.setPen(self.C_TEXT); self.p.drawText(self.ML, self.y+6, text); self.y += 14
        self.p.setPen(QPen(self.C_ACC,1.6)); self.p.drawLine(self.ML, self.y, self.ML+self.BW, self.y)
        self.y += 4
        if subtitle:
            self.p.setFont(_mk_font("Helvetica", max(1,int(8*self.fs)), italic=True))
            self.p.setPen(self.C_MUTE); self.p.drawText(self.ML, self.y+9, subtitle); self.y += 12
        self.y += 6

    def body_text(self, text, gap=13):
        self.p.setFont(_mk_font("Helvetica", max(1,int(9*self.fs)))); self.p.setPen(self.C_TEXT)
        self.p.drawText(QRectF(self.ML, self.y, self.BW, 200), Qt.TextWordWrap, str(text))
        self.y += gap

    def ensure_space(self, needed):
        if self.y + needed > self.BODY_BOT - 6: self.new_page(); return True
        return False

    def section_title_page(self, title, subtitle=""):
        """Clean section divider (no full-bleed band — keeps it professional)."""
        self.new_page()
        p=self.p; ML=self.ML; W=self.W; BW=self.BW
        cy = self.H*0.40
        p.setPen(QPen(self.C_ACC, 2)); p.drawLine(ML, int(cy-26), ML+50, int(cy-26))
        p.setFont(_mk_font("Helvetica", max(1,int(26*self.fs)), bold=True))
        p.setPen(self.C_HEAD)
        p.drawText(QRectF(ML, cy-18, BW, 60), Qt.AlignLeft|Qt.AlignVCenter, title)
        if subtitle:
            p.setFont(_mk_font("Helvetica", max(1,int(10*self.fs))))
            p.setPen(self.C_MUTE)
            p.drawText(QRectF(ML, cy+30, BW, 24), Qt.AlignLeft, subtitle)
        if self.logo and not self.logo.isNull():
            lh=34; lw=int(self.logo.width()*lh/max(1,self.logo.height()))
            p.drawPixmap(W-ML-lw, int(cy-30), lw, lh, self.logo)

    def table(self, headers, rows, col_widths=None, image_col=None):
        """Render a table. image_col: index of a column whose cells are image
        paths -> drawn as a small thumbnail, or an empty bordered slot."""
        ML=self.ML; BW=self.BW; n=len(headers)
        if not col_widths or len(col_widths)!=n:
            cw_base=max(28, BW//max(1,n)); col_widths=[cw_base]*n
            spare=BW-sum(col_widths)
            if spare>0 and n>0: col_widths[-1]+=spare
        hh = max(18, int((self.MIN_RH+5)*self.fs))
        base_rh = max(14, int(self.MIN_RH*self.fs))
        font_size = max(1, int(7.2*self.fs))
        img_min_h = 34 if image_col is not None else 0

        def measure_row(row):
            mh = max(base_rh, img_min_h)
            if not self.WRAP: return mh
            for ci,(val, cw) in enumerate(zip(row, col_widths)):
                if ci == image_col: continue
                txt = _clean_val(val)
                fm = QFontMetrics(_mk_font("Helvetica", font_size))
                br = fm.boundingRect(0,0, cw-7, 9999, Qt.TextWordWrap, txt)
                mh = max(mh, br.height()+7)
            return mh

        def draw_header_row():
            self.ensure_space(hh+2)
            self.p.setBrush(QBrush(self.C_HEAD)); self.p.setPen(Qt.NoPen)
            self.p.drawRect(ML, self.y, BW, hh)
            self.p.setFont(_mk_font("Helvetica", font_size, bold=True))
            x = ML
            for h,cw in zip(headers, col_widths):
                self.p.setPen(QColor("#ffffff"))
                self.p.drawText(QRectF(x+4,self.y,cw-6,hh),
                                Qt.AlignVCenter|Qt.AlignLeft, _friendly(h))
                x += cw
            self.y += hh

        draw_header_row()
        for ri, row in enumerate(rows):
            rh = max(base_rh, measure_row(row))
            if self.ensure_space(rh + 2):
                draw_header_row()
            bg = self.C_ROWA if ri%2==0 else self.C_ROWB
            self.p.setBrush(QBrush(bg)); self.p.setPen(Qt.NoPen)
            self.p.drawRect(ML, self.y, BW, rh)
            # thin baseline separator
            self.p.setPen(QPen(self.C_LINE, 0.4))
            self.p.drawLine(ML, self.y+rh, ML+BW, self.y+rh)
            x = ML
            self.p.setFont(_mk_font("Helvetica", font_size))
            for ci,(val, cw) in enumerate(zip(row, col_widths)):
                if ci == image_col:
                    self._cell_image(val, x, self.y, cw, rh)
                else:
                    self.p.setPen(self.C_TEXT)
                    txt = _clean_val(val)
                    flags = (Qt.AlignTop|Qt.TextWordWrap) if self.WRAP else Qt.AlignVCenter
                    self.p.drawText(QRectF(x+4, self.y+3, cw-7, rh-4), flags, txt)
                x += cw
            self.y += rh
        self.y += 4

    def _cell_image(self, val, x, y, cw, rh):
        """Draw a thumbnail if the cell value is a valid image path, else an empty slot."""
        path = _clean_val(val)
        pad = 3; slot_w = cw-2*pad; slot_h = rh-2*pad
        if path and os.path.exists(path):
            px = QPixmap(path)
            if not px.isNull():
                px = px.scaled(int(slot_w), int(slot_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.p.drawPixmap(int(x+(cw-px.width())//2), int(y+(rh-px.height())//2),
                                  px.width(), px.height(), px)
                return
        # empty slot box
        self.p.setBrush(Qt.NoBrush); self.p.setPen(QPen(self.C_LINE, 0.6, Qt.DashLine))
        self.p.drawRect(int(x+pad), int(y+pad), int(slot_w), int(slot_h))

    def image_block(self, pixmap, caption="", max_h=500):
        if pixmap is None or pixmap.isNull(): return
        pw=pixmap.width(); ph=pixmap.height(); BW=self.BW; ML=self.ML
        scale=min(BW/max(1,pw), max_h/max(1,ph), 1.0)
        dw,dh=int(pw*scale),int(ph*scale)
        self.ensure_space(dh+20)
        self.p.drawPixmap(ML+(BW-dw)//2, self.y, dw, dh, pixmap)
        self.y+=dh+4
        if caption:
            self.p.setFont(_mk_font("Helvetica",max(1,int(7*self.fs)),italic=True))
            self.p.setPen(self.C_MUTE)
            self.p.drawText(QRectF(ML,self.y,BW,14), Qt.AlignHCenter, caption); self.y+=12

    # ── photographic plates grid ──
    def plates_grid(self, photos):
        """photos: list of {path, context, caption}. 2 columns of framed images."""
        ML=self.ML; BW=self.BW; fs=self.fs
        cols = 2; gap = 14
        cell_w = (BW - gap*(cols-1)) // cols
        img_h = int(cell_w * 0.72)
        cap_h = 26
        cell_h = img_h + cap_h
        col = 0; row_top = self.y
        plate_n = 1
        for ph in photos:
            if col == 0:
                if self.ensure_space(cell_h + 8):
                    row_top = self.y
                row_top = self.y
            x = ML + col*(cell_w+gap)
            # frame
            self.p.setBrush(QBrush(QColor("#f6f3ec"))); self.p.setPen(QPen(self.C_LINE, 0.8))
            self.p.drawRect(int(x), int(row_top), int(cell_w), int(img_h))
            path = ph.get('path','')
            drew = False
            if path and os.path.exists(path):
                px = QPixmap(path)
                if not px.isNull():
                    px = px.scaled(int(cell_w-6), int(img_h-6), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.p.drawPixmap(int(x+(cell_w-px.width())//2), int(row_top+(img_h-px.height())//2),
                                      px.width(), px.height(), px)
                    drew = True
            if not drew:
                self.p.setFont(_mk_font("Helvetica", max(1,int(7*fs)), italic=True))
                self.p.setPen(self.C_MUTE)
                self.p.drawText(QRectF(x, row_top+img_h/2-6, cell_w, 14), Qt.AlignCenter,
                                "[ photo unavailable ]")
            # caption
            self.p.setFont(_mk_font("Helvetica", max(1,int(7*fs)), bold=True)); self.p.setPen(self.C_TEXT)
            cap = f"Plate {plate_n}."
            ctx = ph.get('context','')
            if ctx: cap += f" Context {ctx}"
            self.p.drawText(int(x), int(row_top+img_h+11), cap)
            self.p.setFont(_mk_font("Helvetica", max(1,int(6.5*fs)))); self.p.setPen(self.C_MUTE)
            cptxt = ph.get('caption','')
            self.p.drawText(QRectF(x, row_top+img_h+13, cell_w, 12), Qt.TextSingleLine, cptxt[:46])
            plate_n += 1
            col += 1
            if col >= cols:
                col = 0; self.y = row_top + cell_h + 10
        if col != 0:
            self.y = row_top + cell_h + 10

    # ── single context recording sheet ──
    def draw_context_sheet(self, ctx_num, ctx_data, all_rels, photos=None):
        self.new_page()
        p=self.p; ML=self.ML; W=self.W; BW=self.BW; fs=self.fs
        photos = photos or []

        p.setFont(_mk_font("Helvetica", max(1,int(20*fs)), bold=True)); p.setPen(self.C_HEAD)
        p.drawText(ML, self.y+22, f"CONTEXT  {ctx_num}")
        self.y += 26
        p.setPen(QPen(self.C_ACC, 2.2)); p.drawLine(ML, self.y, ML+BW, self.y)
        self.y += 10

        left_w = int(BW * 0.56); right_w = BW - left_w - 10; rx = ML + left_w + 10
        top_y = self.y; ty = top_y
        row_h = max(15, int(14*fs))
        fields = [
            ("Context No.",    str(ctx_num)),
            ("Type",           _clean_val(ctx_data.get('type',''))),
            ("Period",         _clean_val(ctx_data.get('period',''))),
            ("Description",    _clean_val(ctx_data.get('description',''))),
            ("Interpretation", ""),
            ("Dimensions",     ""),
            ("Soil / Munsell", ""),
            ("Excavated by",   ""),
            ("Date",           ""),
        ]
        label_w = 92
        for idx,(label, val) in enumerate(fields):
            if label in ("Description","Interpretation") and len(val) > 36:
                fm_tmp = QFontMetrics(_mk_font("Helvetica", max(1,int(7.2*fs))))
                br_tmp = fm_tmp.boundingRect(0,0,left_w-label_w-6,9999,Qt.TextWordWrap,val)
                actual_h = max(row_h, br_tmp.height()+8)
            else:
                actual_h = row_h
            p.setBrush(QBrush(self.C_ROWA if idx%2==0 else self.C_ROWB)); p.setPen(Qt.NoPen)
            p.drawRect(ML, ty, left_w, actual_h)
            p.setPen(QPen(self.C_LINE,0.4)); p.drawLine(ML,ty+actual_h,ML+left_w,ty+actual_h)
            p.setFont(_mk_font("Helvetica", max(1,int(6.8*fs)), bold=True)); p.setPen(self.C_ACC)
            p.drawText(ML+4, ty+12, label)
            p.setFont(_mk_font("Helvetica", max(1,int(7.2*fs)))); p.setPen(self.C_TEXT)
            p.drawText(QRectF(ML+label_w, ty+3, left_w-label_w-5, actual_h-4),
                       Qt.AlignTop|Qt.TextWordWrap, val)
            ty += actual_h

        # right: stratigraphic position
        mini_y = top_y
        p.setFont(_mk_font("Helvetica", max(1,int(6.8*fs)), bold=True)); p.setPen(self.C_ACC)
        p.drawText(rx, mini_y+9, "STRATIGRAPHIC POSITION"); mini_y += 12
        p.setPen(QPen(self.C_ACC, 0.5)); p.drawLine(rx, mini_y, rx+right_w, mini_y); mini_y += 8
        ctx_rels = [r for r in all_rels if r['from_ctx']==ctx_num or r['to_ctx']==ctx_num]
        above = [r['from_ctx'] if r['to_ctx']==ctx_num else r['to_ctx']
                 for r in ctx_rels if (r['rel_type'] in ('above','cuts') and r['to_ctx']==ctx_num)
                 or (r['rel_type'] in ('below','is_cut_by') and r['from_ctx']==ctx_num)]
        below = [r['to_ctx'] if r['from_ctx']==ctx_num else r['from_ctx']
                 for r in ctx_rels if (r['rel_type'] in ('above','cuts') and r['from_ctx']==ctx_num)
                 or (r['rel_type'] in ('below','is_cut_by') and r['to_ctx']==ctx_num)]
        above = [c for c in dict.fromkeys(above) if c!=ctx_num][:3]
        below = [c for c in dict.fromkeys(below) if c!=ctx_num][:3]
        bcx = rx + right_w//2; bw=80; bh=17
        def _node(cy, label, active=False):
            bx = bcx - bw//2
            if active:
                p.setBrush(QBrush(self.C_ACC.lighter(160))); p.setPen(QPen(self.C_ACC,1.4))
            else:
                p.setBrush(QBrush(QColor('#eeeae2'))); p.setPen(QPen(QColor('#9a9486'),0.7))
            p.drawRect(bx, cy, bw, bh)
            p.setFont(_mk_font("Helvetica", max(1,int(6.4*fs)), bold=active)); p.setPen(self.C_TEXT)
            p.drawText(QRectF(bx, cy+2, bw, bh-2), Qt.AlignCenter, label)
        for cn in above:
            _node(mini_y, f"Context {cn}"); mini_y += bh
            p.setPen(QPen(QColor('#9a9486'),0.8)); p.drawLine(bcx, mini_y, bcx, mini_y+5); mini_y += 5
        _node(mini_y, f"Context {ctx_num}", active=True); mini_y += bh
        for cn in below:
            p.setPen(QPen(QColor('#9a9486'),0.8)); p.drawLine(bcx, mini_y, bcx, mini_y+5); mini_y += 5
            _node(mini_y, f"Context {cn}"); mini_y += bh
        if not above and not below:
            p.setFont(_mk_font("Helvetica", max(1,int(6.2*fs)), italic=True)); p.setPen(self.C_MUTE)
            p.drawText(rx+4, mini_y+10, "No stratigraphic links recorded"); mini_y += 14
        mini_y += 10
        # plan slot
        sketch_h = max(80, int(right_w*0.62))
        p.setBrush(QBrush(QColor('#f6f3ec'))); p.setPen(QPen(self.C_LINE,0.8,Qt.DashLine))
        p.drawRect(rx, mini_y, right_w, sketch_h)
        p.setFont(_mk_font("Helvetica", max(1,int(6.4*fs)), bold=True)); p.setPen(self.C_MUTE)
        p.drawText(QRectF(rx, mini_y+3, right_w, 12), Qt.AlignCenter, "PLAN / SECTION")
        p.setFont(_mk_font("Helvetica", max(1,int(5.6*fs)), italic=True))
        p.drawText(QRectF(rx, mini_y+sketch_h//2-4, right_w, 12), Qt.AlignCenter, "[ attach drawing ]")
        mini_y += sketch_h + 6

        self.y = max(ty, mini_y) + 10

        # associated finds
        self.ensure_space(26)
        p.setFont(_mk_font("Helvetica", max(1,int(6.8*fs)), bold=True)); p.setPen(self.C_ACC)
        p.drawText(ML, self.y+9, "ASSOCIATED FINDS"); self.y += 12
        p.setPen(QPen(self.C_ACC,0.4)); p.drawLine(ML,self.y,ML+BW,self.y); self.y += 5
        cats = ["Pottery","Artifacts","Bones","Coins","Glass","Other"]
        cat_w = BW//len(cats)
        p.setFont(_mk_font("Helvetica", max(1,int(6.4*fs))))
        for i,cat in enumerate(cats):
            cx = ML+i*cat_w
            p.setBrush(Qt.NoBrush); p.setPen(QPen(self.C_TEXT,0.7)); p.drawRect(cx+2,self.y+2,8,8)
            p.setPen(self.C_TEXT); p.drawText(cx+14, self.y+10, cat)
        self.y += 18

        # photo record — use tagged photos for this context, else empty slots
        self.ensure_space(80)
        p.setFont(_mk_font("Helvetica", max(1,int(6.8*fs)), bold=True)); p.setPen(self.C_ACC)
        p.drawText(ML, self.y+9, "PHOTO RECORD"); self.y += 12
        p.setPen(QPen(self.C_ACC,0.4)); p.drawLine(ML,self.y,ML+BW,self.y); self.y += 6
        ctx_photos = [ph for ph in photos if str(ph.get('context','')) == str(ctx_num)]
        ph_w = (BW-16)//3; ph_h = 62
        for i in range(3):
            px2 = ML + i*(ph_w+8)
            drew = False
            if i < len(ctx_photos):
                path = ctx_photos[i].get('path','')
                if path and os.path.exists(path):
                    pm = QPixmap(path)
                    if not pm.isNull():
                        pm = pm.scaled(ph_w, ph_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        p.drawPixmap(int(px2+(ph_w-pm.width())//2), int(self.y+(ph_h-pm.height())//2),
                                     pm.width(), pm.height(), pm)
                        drew = True
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(self.C_LINE,0.7, Qt.SolidLine if drew else Qt.DashLine))
            p.drawRect(px2, self.y, ph_w, ph_h)
            if not drew:
                p.setFont(_mk_font("Helvetica", max(1,int(5.6*fs)), italic=True)); p.setPen(self.C_MUTE)
                p.drawText(QRectF(px2, self.y+ph_h//2-5, ph_w, 12), Qt.AlignCenter, f"[ photo {i+1} ]")
        self.y += ph_h + 14


# ── Harris Matrix — classic B&W portrait renderer ───────────────────────────
def _draw_harris_pdf(pg, win, n_pages, hide_isolated=False):
    from .harris_view import compute_layout
    contexts = list(win.ctx_data.values())
    all_rels  = win.relationships + getattr(win,'layer_rels',[])
    if hide_isolated:
        connected = {r['from_ctx'] for r in all_rels}|{r['to_ctx'] for r in all_rels}
        contexts  = [c for c in contexts if c['num'] in connected]
    if not contexts:
        pg.new_page(); pg.heading1("Harris Matrix")
        pg.body_text("No contexts — build the matrix first."); return

    positions = compute_layout(contexts, all_rels)
    level_map = {}
    for ctx in contexts:
        n = ctx['num']
        if n not in positions: continue
        _x, y = positions[n]; lv = round(y/10)*10
        level_map.setdefault(lv,[]).append(ctx)
    sorted_levels = sorted(level_map.keys())

    ML = pg.ML; BW = pg.BW
    MAX_PER_ROW = max(4, min(12, n_pages*4))
    BOX_W = max(30, int((BW - 6*(MAX_PER_ROW-1)) // MAX_PER_ROW))
    H_GAP = max(6, (BW - BOX_W*MAX_PER_ROW)//(MAX_PER_ROW-1) if MAX_PER_ROW>1 else 6)
    BOX_H = 22; V_GAP = 26          # bigger vertical gap -> no overlap
    LINE_COL=QColor('#222222'); BOX_FILL=QColor('#ffffff'); BOX_BORDER=QColor('#222222'); TEXT_COL=QColor('#000000')
    fs = pg.fs

    boxes={}; page_idx=0; curr_y=pg.MT+34; BODY_BOT=pg.H-pg.MB-16
    def new_vpage():
        nonlocal page_idx, curr_y
        page_idx += 1; curr_y = pg.MT + 34
    for lv in sorted_levels:
        row_ctxs = sorted(level_map[lv], key=lambda c: c['num'])
        for rs in range(0, len(row_ctxs), MAX_PER_ROW):
            row = row_ctxs[rs:rs+MAX_PER_ROW]
            if curr_y + BOX_H + V_GAP > BODY_BOT: new_vpage()
            n_row=len(row); row_w=n_row*(BOX_W+H_GAP)-H_GAP; x0=ML+(BW-row_w)//2
            for i,ctx in enumerate(row):
                bx=x0+i*(BOX_W+H_GAP)
                boxes[ctx['num']]={'x':bx,'y':curr_y,'cx':int(bx+BOX_W/2),
                                   'cy':int(curr_y+BOX_H/2),'page':page_idx,'ctx':ctx}
            curr_y += BOX_H + V_GAP
        curr_y += 6
    total_pages = page_idx + 1

    for pi in range(total_pages):
        pg.new_page(is_first=(pi==0))
        p=pg.p
        if pi==0:
            p.setFont(_mk_font("Helvetica",max(1,int(15*fs)),bold=True)); p.setPen(pg.C_HEAD)
            p.drawText(ML, pg.y+4, "HARRIS MATRIX")
            pg.y+=14; p.setPen(QPen(pg.C_ACC,1.4)); p.drawLine(ML,pg.y,ML+BW,pg.y); pg.y+=8
        fnt_num=_mk_font("Courier New",max(1,int(max(6,BOX_H*0.4*fs))),bold=True)
        fnt_sub=_mk_font("Helvetica",max(1,int(max(4,BOX_H*0.26*fs))))
        # same-page lines
        p.setPen(QPen(LINE_COL,0.8))
        for rel in all_rels:
            f,t,rt=rel['from_ctx'],rel['to_ctx'],rel['rel_type']
            contemp=rt in ('contemporary','equals')
            if rt in ('below','is_cut_by'): f,t=t,f
            bf=boxes.get(f); bt=boxes.get(t)
            if not bf or not bt or bf['page']!=pi or bt['page']!=pi: continue
            py1=bf['y']; py2=bt['y']; p1cx=bf['cx']; p2cx=bt['cx']
            if contemp:
                p.setPen(QPen(LINE_COL,0.7,Qt.DashLine)); base=max(py1,py2)+BOX_H+6
                for off in (0,3):
                    p.drawLine(p1cx,int(py1+BOX_H),p1cx,int(base+off))
                    p.drawLine(p1cx,int(base+off),p2cx,int(base+off))
                    p.drawLine(p2cx,int(base+off),p2cx,int(bt['y']+BOX_H))
                p.setPen(QPen(LINE_COL,0.8))
            else:
                mid=int((py1+BOX_H+py2)//2)
                p.drawLine(p1cx,int(py1+BOX_H),p1cx,mid)
                p.drawLine(p1cx,mid,p2cx,mid); p.drawLine(p2cx,mid,p2cx,int(py2))
        # cross-page stubs
        for rel in all_rels:
            f,t,rt=rel['from_ctx'],rel['to_ctx'],rel['rel_type']
            if rt in ('below','is_cut_by'): f,t=t,f
            bf=boxes.get(f); bt=boxes.get(t)
            if not bf or not bt or bf['page']==bt['page']: continue
            for binfo,is_from in [(bf,True),(bt,False)]:
                if binfo['page']!=pi: continue
                other_p=(bt if is_from else bf)['page']
                bx2=binfo['cx']; by2=binfo['y']
                p.setPen(QPen(QColor('#777'),0.6,Qt.DotLine))
                if is_from:
                    p.drawLine(bx2,int(by2+BOX_H),bx2,int(by2+BOX_H+9))
                    p.setPen(QColor('#999')); p.drawText(bx2-7,int(by2+BOX_H+18),f"p{other_p+1}")
                else:
                    p.drawLine(bx2,int(by2-9),bx2,int(by2))
                    p.setPen(QColor('#999')); p.drawText(bx2-7,int(by2-11),f"p{other_p+1}")
        # boxes
        for num,binfo in boxes.items():
            if binfo['page']!=pi: continue
            bx=binfo['x']; by=binfo['y']
            p.setBrush(QBrush(BOX_FILL)); p.setPen(QPen(BOX_BORDER,0.9))
            p.drawRect(int(bx),int(by),BOX_W,BOX_H)
            p.setFont(fnt_num); p.setPen(TEXT_COL)
            p.drawText(QRectF(bx+1,by+1,BOX_W-2,BOX_H*0.6),Qt.AlignCenter,str(num))
            t2=_clean_val(binfo['ctx'].get('type',''))[:4]
            if t2:
                p.setFont(fnt_sub); p.setPen(QColor('#666'))
                p.drawText(QRectF(bx+1,by+BOX_H*0.55,BOX_W-2,BOX_H*0.42),Qt.AlignCenter,t2)
        if total_pages>1:
            p.setFont(_mk_font("Helvetica",max(1,int(6.5*fs)))); p.setPen(QColor('#999'))
            p.drawText(pg.W-pg.ML-66,pg.H-pg.MB-2,f"Sheet {pi+1} / {total_pages}")
    pg.y = pg.H - pg.MB


# ── column helpers ──────────────────────────────────────────────────────────
def _visible_cols(lyr, col_keys, hide_empty=True):
    """Return field names to display: requested or all, minus hidden/all-empty."""
    all_fn = [f.name() for f in lyr.fields()]
    if col_keys:
        cols = [f for f in col_keys if f in all_fn] or all_fn
    else:
        cols = [f for f in all_fn if f.lower() not in HIDDEN_COLS]
    if hide_empty and not col_keys:
        non_empty = set()
        checked = 0
        for feat in lyr.getFeatures():
            for f in cols:
                if f in non_empty: continue
                if _clean_val(feat.attribute(f)): non_empty.add(f)
            checked += 1
            if checked > 500: break          # sample cap for huge layers
        cols = [f for f in cols if f in non_empty] or cols
    return cols


def _col_widths_for(col_names, BW, image_idx=None):
    wide = {'description','notes','detailed_description','provenance','parallels',
            'material_detail','dimensions','condition','interpretation'}
    narrow = {'no.','context','count','period','date','sex','age','side','type'}
    weights=[]
    for i,c in enumerate(col_names):
        if i==image_idx: weights.append(1.1); continue
        cl=c.lower()
        if cl in wide: weights.append(2.4)
        elif _friendly(c).lower() in narrow or cl in narrow: weights.append(0.8)
        else: weights.append(1.2)
    total=sum(weights) or 1; unit=BW/total
    cw=[max(26,int(w*unit)) for w in weights]
    diff=BW-sum(cw)
    if diff and cw: cw[-1]+=diff
    return cw


def _load_default_logo():
    """Load logo.svg shipped with the plugin as a QPixmap (header/cover default)."""
    svg_path = os.path.join(os.path.dirname(__file__), 'logo.svg')
    if not os.path.exists(svg_path): return None
    try:
        from qgis.PyQt.QtSvg import QSvgRenderer
        from qgis.PyQt.QtCore import QSize as _QSz
        r = QSvgRenderer(svg_path)
        px = QPixmap(_QSz(220, 220)); px.fill(Qt.transparent)
        pr = QPainter(px); r.render(pr); pr.end()
        return px
    except Exception:
        return None


def export_pdf(output_path, opts, win):
    # Logo: user-picked, else bundled UOB logo
    logo_px = None
    if opts.get("logo"):
        lp = opts["logo"]
        if lp.lower().endswith(".svg"):
            try:
                from qgis.PyQt.QtSvg import QSvgRenderer
                from qgis.PyQt.QtCore import QSize as _QSz
                r=QSvgRenderer(lp); logo_px=QPixmap(_QSz(220,220)); logo_px.fill(Qt.transparent)
                pr=QPainter(logo_px); r.render(pr); pr.end()
            except Exception: logo_px=None
        else:
            logo_px = QPixmap(lp)
            if logo_px.isNull(): logo_px=None
    if logo_px is None:
        logo_px = _load_default_logo()

    if HAS_PDF_WRITER:
        device = _QPdfWriter(output_path); device.setResolution(72)
        pmap={"A4":QPagedPaintDevice.A4,"Letter":QPagedPaintDevice.Letter,"A3":QPagedPaintDevice.A3}
        device.setPageSize(pmap.get(opts.get("paper","A4"), QPagedPaintDevice.A4))
        try: device.setPageMargins(QMarginsF(0,0,0,0))
        except Exception: pass
    elif HAS_PRINTER:
        device=QPrinter(QPrinter.HighResolution); device.setOutputFormat(QPrinter.PdfFormat)
        device.setOutputFileName(output_path)
        pmap={"A4":QPrinter.A4,"Letter":QPrinter.Letter,"A3":QPrinter.A3}
        device.setPaperSize(pmap.get(opts.get("paper","A4"),QPrinter.A4))
        device.setPageMargins(0,0,0,0,QPrinter.Millimeter)
    else:
        from qgis.PyQt.QtWidgets import QMessageBox
        QMessageBox.critical(None,"","No PDF output device available."); return False

    painter=QPainter()
    if not painter.begin(device): return False
    if not HAS_PDF_WRITER and HAS_PRINTER:
        pr=device.pageRect(); painter.scale(pr.width()/595.0, pr.height()/842.0)

    pg=Page(painter, device, opts, logo_px)
    sections  =opts.get("sections",{})
    sec_order =opts.get("section_order", DEFAULT["section_order"])
    n_harris  =int(opts.get("harris_pages",3))
    hide_empty=bool(opts.get("hide_empty",True))
    add_thumbs=bool(opts.get("thumbs",True))

    # gather tagged photos from the gallery registry
    registry = getattr(win,'_photo_registry',{}) or {}
    all_photos = []
    for cat in ('photos','drawings','refs'):
        all_photos += registry.get(cat, [])
    img_photos = [ph for ph in all_photos
                  if ph.get('path') and os.path.exists(ph['path'])
                  and ph['path'].lower().endswith(('.png','.jpg','.jpeg','.bmp','.tiff'))]

    def _img_field(lyr):
        for f in lyr.fields():
            if f.name().lower() in IMAGE_COLS: return f.name()
        return None

    def _lyr_table(lyr, title, col_keys=None, allow_thumb=False):
        if not lyr:
            pg.section_title_page(title, "No layer connected")
            pg.new_page(); pg.heading1(title); pg.body_text("No layer connected for this section."); return
        cols = _visible_cols(lyr, col_keys or [], hide_empty=hide_empty)
        image_idx = None
        img_f = _img_field(lyr)          # real image field name, or None
        if allow_thumb and add_thumbs:
            # always show a Photo slot column at the end (thumbnail or empty slot)
            if img_f is None: img_f = "image_path"
            if img_f not in cols: cols = cols + [img_f]
            image_idx = cols.index(img_f)
        elif img_f and img_f in cols:
            image_idx = cols.index(img_f)
        n = lyr.featureCount()
        pg.section_title_page(title, f"{n} record{'s' if n!=1 else ''}")
        pg.new_page(); pg.heading1(title, f"{n} record{'s' if n!=1 else ''}")
        rows=[]
        for feat in lyr.getFeatures():
            row=[]
            for c in cols:
                if c == img_f and img_f is not None:
                    try: row.append(_clean_val(feat.attribute(c)))
                    except Exception: row.append("")
                else:
                    try: row.append(_clean_val(feat.attribute(c)))
                    except Exception: row.append("")
            rows.append(row)
        cw=_col_widths_for(cols, pg.BW, image_idx)
        pg.table(cols, rows, cw, image_col=image_idx)

    for sec in sec_order:
        if not sections.get(sec, True): continue

        if sec=="cover":
            _draw_cover(pg, painter, opts, logo_px, sec_order, sections)

        elif sec=="harris":
            n_ctx=len(win.ctx_data); n_rel=len(win.relationships)+len(getattr(win,'layer_rels',[]))
            pg.section_title_page("Harris Matrix",f"{n_ctx} contexts · {n_rel} relationships")
            _draw_harris_pdf(pg, win, n_harris, hide_isolated=opts.get("harris_hide_isolated",False))

        elif sec=="contexts":
            _lyr_table(win._lyr(win.ctx_layer_cb),"Contexts Inventory",opts.get("cols_ctx"))
        elif sec=="pottery":
            _lyr_table(win._lyr(win.pot_layer_cb),"Pottery Inventory",opts.get("cols_pot"),allow_thumb=True)
        elif sec=="artifacts":
            _lyr_table(win._lyr(win.art_layer_cb),"Artifacts Inventory",opts.get("cols_art"),allow_thumb=True)
        elif sec=="skeletons":
            _lyr_table(win._lyr(win.ske_layer_cb),"Skeletal Remains",opts.get("cols_ske"))

        elif sec=="artifact_details":
            _draw_artifact_catalogue(pg, win)

        elif sec=="bone_form":
            if hasattr(win,"_skel_view"):
                try:
                    pg.section_title_page("Bone Inventory","Recording form")
                    pg.new_page(); pg.heading1("Bone Inventory — Recording Form")
                    bpx=win._skel_view.render_to_pixmap(480,900)
                    pg.image_block(bpx, max_h=580)
                except Exception as e:
                    pg.new_page(); pg.body_text(f"Bone form unavailable: {e}")

        elif sec=="rels":
            from .dock import REL_LABELS
            all_r=win.relationships+getattr(win,"layer_rels",[])
            if all_r:
                pg.section_title_page("Stratigraphic Relationships",f"{len(all_r)} relationships")
                pg.new_page(); pg.heading1("Stratigraphic Relationships", f"{len(all_r)} recorded")
                rows=[[r["from_ctx"],REL_LABELS.get(r["rel_type"],r["rel_type"]),
                       r["to_ctx"],r.get("source","manual")] for r in all_r]
                bw=pg.BW
                pg.table(["Context A","Relationship","Context B","Source"],
                         rows,[int(bw*.13),int(bw*.52),int(bw*.13),int(bw*.22)])

        elif sec=="context_sheets":
            ctx_all = win.ctx_data if hasattr(win,'ctx_data') else {}
            all_r = win.relationships + getattr(win,'layer_rels',[])
            if ctx_all:
                pg.section_title_page("Context Detail Sheets", f"{len(ctx_all)} contexts")
                for cn, ci in sorted(ctx_all.items()):
                    pg.draw_context_sheet(cn, ci, all_r, photos=img_photos)

        elif sec=="strat_matrix":
            _draw_strat_matrix(pg, win, opts)

        elif sec=="plates":
            if img_photos:
                pg.section_title_page("Photographic Plates", f"{len(img_photos)} photographs")
                pg.new_page(); pg.heading1("Photographic Plates",
                                           "Site, find and context photography")
                pg.plates_grid(img_photos)
            # if no photos, silently skip — no empty section

    painter.end()
    return True


def _draw_cover(pg, p, opts, logo_px, sec_order, sections):
    pg.new_page(is_first=True)
    W=pg.W; H=pg.H; ML=pg.ML; BW=pg.BW; fs=pg.fs
    # background
    p.setBrush(QBrush(QColor('#ffffff'))); p.setPen(Qt.NoPen); p.drawRect(0,0,W,H)
    # left accent bar
    p.setBrush(QBrush(pg.C_ACC)); p.drawRect(0,0,6,H)

    y=64
    # institution line
    p.setFont(_mk_font("Helvetica", max(1,int(8*fs)), bold=True)); p.setPen(pg.C_MUTE)
    p.drawText(ML, y, "DEPARTMENT OF ARCHAEOLOGY & MUSEOLOGY · UNIVERSITY OF BALAMAND")
    y += 10
    p.setPen(QPen(pg.C_ACC,0.8)); p.drawLine(ML, y, W-ML, y); y += 44

    # title
    title = opts.get("title","Archaeological Site Report")
    p.setFont(_mk_font("Helvetica", max(1,int(30*fs)), bold=True)); p.setPen(pg.C_HEAD)
    p.drawText(QRectF(ML, y, BW, 90), Qt.TextWordWrap, title)
    y += 84
    # site + season subtitle
    sub_bits = [b for b in [opts.get("site","").strip(), opts.get("season","").strip()] if b]
    if sub_bits:
        p.setFont(_mk_font("Helvetica", max(1,int(13*fs)))); p.setPen(pg.C_ACC)
        p.drawText(ML, y, "  ·  ".join(sub_bits)); y += 22
    p.setFont(_mk_font("Helvetica", max(1,int(7.5*fs)))); p.setPen(pg.C_MUTE)
    p.drawText(ML, y, "OFFICIAL FIELD DOCUMENTATION"); y += 18
    p.setPen(QPen(pg.C_LINE,0.6)); p.drawLine(ML, y, W-ML, y); y += 18

    # abstract
    desc = opts.get("cover_desc","").strip()
    if desc:
        p.setFont(_mk_font("Helvetica", max(1,int(9*fs)))); p.setPen(pg.C_TEXT)
        p.drawText(QRectF(ML, y, BW*0.7, 70), Qt.TextWordWrap, desc); y += 70

    # hero image (cover photo or logo)
    cover_img = opts.get("cover_img","").strip()
    hero = None
    if cover_img and os.path.exists(cover_img):
        hero = QPixmap(cover_img)
        if hero.isNull(): hero=None
    box_top = y; box_h = min(250, H - y - 230)
    if box_h > 90:
        if hero is not None:
            hs = hero.scaled(int(BW), int(box_h), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            # center-crop
            p.save(); p.setClipRect(ML, box_top, BW, box_h)
            p.drawPixmap(int(ML+(BW-hs.width())//2), int(box_top+(box_h-hs.height())//2),
                         hs.width(), hs.height(), hs)
            p.restore()
            p.setBrush(Qt.NoBrush); p.setPen(QPen(pg.C_LINE,0.8)); p.drawRect(ML, box_top, BW, box_h)
        elif logo_px is not None and not logo_px.isNull():
            lh=min(box_h-20,170); lw=int(logo_px.width()*lh/max(1,logo_px.height()))
            p.drawPixmap(ML+(BW-lw)//2, box_top+(box_h-lh)//2, lw, lh, logo_px)
        else:
            p.setBrush(QBrush(QColor('#f3efe7'))); p.setPen(QPen(pg.C_LINE,0.8))
            p.drawRect(ML, box_top, BW, box_h)
        y = box_top + box_h + 24

    # table of contents
    p.setFont(_mk_font("Helvetica", max(1,int(11*fs)), bold=True)); p.setPen(pg.C_HEAD)
    p.drawText(ML, y+12, "Contents"); y += 18
    p.setPen(QPen(pg.C_ACC,0.8)); p.drawLine(ML, y, W-ML, y); y += 14
    fm=p.fontMetrics()
    pg_n=2
    p.setFont(_mk_font("Helvetica", max(1,int(9*fs))))
    for sec_k in sec_order:
        if sec_k=="cover" or not sections.get(sec_k, True): continue
        name=SECTION_NAMES.get(sec_k, sec_k)
        item_y=y+12
        tw=fm.horizontalAdvance(name) if hasattr(fm,'horizontalAdvance') else fm.width(name)
        pgs=str(pg_n)
        pw=fm.horizontalAdvance(pgs) if hasattr(fm,'horizontalAdvance') else fm.width(pgs)
        p.setPen(QColor('#c9c2b4'))
        dot=ML+tw+6
        while dot < W-ML-pw-6:
            p.drawText(int(dot), item_y, "."); dot+=5
        p.setPen(pg.C_TEXT); p.drawText(ML, item_y, name)
        p.setFont(_mk_font("Helvetica", max(1,int(9*fs)), bold=True))
        p.drawText(W-ML-pw, item_y, pgs)
        p.setFont(_mk_font("Helvetica", max(1,int(9*fs))))
        y+=16
        pg_n += (3 if sec_k=='harris' else 2)


def _draw_artifact_catalogue(pg, win):
    artdet_lyr = win._lyr(win.artdet_layer_cb) if hasattr(win,'artdet_layer_cb') else None
    art_lyr    = win._lyr(win.art_layer_cb)
    if not (artdet_lyr and artdet_lyr.featureCount()>0):
        return  # skip silently — no empty section
    pg.section_title_page("Artifact Catalogue", f"{artdet_lyr.featureCount()} detailed records")
    pg.new_page(); pg.heading1("Artifact Catalogue", "Detailed records with photography")

    art_info={}
    if art_lyr:
        afns=[f.name() for f in art_lyr.fields()]
        id_fn=next((f for f in ['id','fid','artifact_id'] if f in afns), afns[0] if afns else None)
        type_fn=next((f for f in ['type','material'] if f in afns), None)
        ctx_fn=next((f for f in ['context_num','ctx_num'] if f in afns), None)
        for feat in art_lyr.getFeatures():
            try:
                aid=_clean_val(feat.attribute(id_fn))
                art_info[aid]={'type':_clean_val(feat.attribute(type_fn)) if type_fn else '',
                               'context':_clean_val(feat.attribute(ctx_fn)) if ctx_fn else ''}
            except Exception: pass

    field_pairs=[('detailed_description','Description'),('condition','Condition'),
                 ('material_detail','Material'),('dimensions','Dimensions'),
                 ('provenance','Provenance'),('parallels','Parallels / comparanda'),
                 ('notes','Notes')]
    fnames=[f.name() for f in artdet_lyr.fields()]
    for feat in artdet_lyr.getFeatures():
        aid = _clean_val(feat.attribute('artifact_id')) if 'artifact_id' in fnames else ''
        base=art_info.get(aid,{})
        # collect non-empty fields
        vals=[]
        for fn,flabel in field_pairs:
            if fn not in fnames: continue
            v=_clean_val(feat.attribute(fn))
            if v: vals.append((flabel,v))
        img_path = _clean_val(feat.attribute('image_path')) if 'image_path' in fnames else ''
        has_img = bool(img_path) and os.path.exists(img_path)
        # skip totally-empty entries
        if not vals and not has_img and not aid: continue

        p=pg.p; ML=pg.ML; BW=pg.BW
        pg.ensure_space(70)
        card_y=pg.y
        # header bar
        p.setBrush(QBrush(pg.C_HEAD)); p.setPen(Qt.NoPen); p.drawRect(ML,card_y,BW,17)
        p.setFont(_mk_font("Helvetica",max(1,int(9*pg.fs)),bold=True)); p.setPen(QColor("#ffffff"))
        label = f"Artifact {aid}" if aid else "Artifact"
        if base.get('type'): label+=f"   —   {base['type']}"
        if base.get('context'): label+=f"   |   Context {base['context']}"
        p.drawText(ML+6, card_y+12, label)
        pg.y += 22

        img_w=0; img_h=0; img_x=0
        if has_img:
            px=QPixmap(img_path)
            if not px.isNull():
                img_w=int(BW*0.34); img_h=int(img_w*0.95)
                px=px.scaled(img_w,img_h,Qt.KeepAspectRatio,Qt.SmoothTransformation)
                img_x=ML+BW-px.width()
                pg.ensure_space(px.height()+8)
                p.drawPixmap(img_x, pg.y, px.width(), px.height(), px)
                p.setPen(QPen(pg.C_LINE,0.6)); p.drawRect(img_x, pg.y, px.width(), px.height())
                img_w=px.width(); img_h=px.height()
        else:
            # empty image slot
            img_w=int(BW*0.34); img_h=int(img_w*0.8); img_x=ML+BW-img_w
            p.setBrush(Qt.NoBrush); p.setPen(QPen(pg.C_LINE,0.7,Qt.DashLine))
            p.drawRect(img_x, pg.y, img_w, img_h)
            p.setFont(_mk_font("Helvetica",max(1,int(6*pg.fs)),italic=True)); p.setPen(pg.C_MUTE)
            p.drawText(QRectF(img_x,pg.y+img_h//2-5,img_w,12),Qt.AlignCenter,"[ attach photo ]")

        text_w = BW - img_w - 12
        txt_y=pg.y
        for flabel,val in vals:
            p.setFont(_mk_font("Helvetica",max(1,int(6.6*pg.fs)),bold=True)); p.setPen(pg.C_ACC)
            p.drawText(ML+2, txt_y+9, flabel+":")
            p.setFont(_mk_font("Helvetica",max(1,int(7.2*pg.fs)))); p.setPen(pg.C_TEXT)
            fm2=p.fontMetrics()
            br=fm2.boundingRect(0,0,int(text_w)-94,9999,Qt.TextWordWrap,val)
            p.drawText(QRectF(ML+92,txt_y,text_w-94,br.height()+4),Qt.TextWordWrap,val)
            txt_y+=max(13,br.height()+5)
            if txt_y > pg.H-pg.MB-24: break
        pg.y=max(txt_y, pg.y+img_h)+12
        p.setPen(QPen(pg.C_LINE,0.5)); p.drawLine(ML,pg.y-5,ML+BW,pg.y-5)


def _draw_strat_matrix(pg, win, opts):
    ctx_all = win.ctx_data if hasattr(win,'ctx_data') else {}
    all_r = win.relationships + getattr(win,'layer_rels',[])
    if not ctx_all: return
    only_linked = bool(opts.get("strat_only_linked", True))

    above_map={}; below_map={}
    for r in all_r:
        rt=r['rel_type']
        if rt in ('above','cuts'): above_map.setdefault(r['to_ctx'],[]).append(r['from_ctx'])
        elif rt in ('below','is_cut_by'): below_map.setdefault(r['from_ctx'],[]).append(r['to_ctx'])
    linked = set(above_map)|set(below_map)
    items = sorted(ctx_all.items())
    if only_linked:
        items = [(n,i) for n,i in items if n in linked]
    if not items:
        # nothing linked — fall back to all so the section isn't empty
        items = sorted(ctx_all.items())

    n=len(items)
    pg.section_title_page("Stratigraphic Matrix", f"{n} contexts with relationships")
    pg.new_page(); pg.heading1("Stratigraphic Matrix", "Context relationships table")

    type_colors={'fill':'#b8d4c8','cut':'#e8b99a','deposit':'#d4c89a','layer':'#c4b8d8',
                 'wall':'#d8c8a8','floor':'#e0d4b0','pit':'#d4a8a8','trench':'#f0d898',
                 'surface':'#a8d4c0','feature':'#c4a8d4','rubble':'#c8c8b8'}
    ML=pg.ML; BW=pg.BW; fs=pg.fs
    headers=["","Context","Type","Period","Above","Below"]
    col_ws=[18, int(BW*.14), int(BW*.16), int(BW*.16), int(BW*.18), 0]
    col_ws[-1]=BW-sum(col_ws)
    p=pg.p; hh=int((pg.MIN_RH+5)*fs)
    def hdr():
        pg.ensure_space(hh+2)
        p.setBrush(QBrush(pg.C_HEAD)); p.setPen(Qt.NoPen); p.drawRect(ML,pg.y,BW,hh)
        p.setFont(_mk_font("Helvetica",max(1,int(7*fs)),bold=True)); p.setPen(QColor("#ffffff"))
        x=ML
        for h,cw in zip(headers,col_ws):
            p.drawText(QRectF(x+4,pg.y,cw-6,hh),Qt.AlignVCenter|Qt.AlignLeft,h); x+=cw
        pg.y+=hh
    hdr()
    for ri,(cn,ci) in enumerate(items):
        rh=int(pg.MIN_RH*fs)+2
        if pg.ensure_space(rh+2): hdr()
        bg=pg.C_ROWA if ri%2==0 else pg.C_ROWB
        p.setBrush(QBrush(bg)); p.setPen(Qt.NoPen); p.drawRect(ML,pg.y,BW,rh)
        p.setPen(QPen(pg.C_LINE,0.4)); p.drawLine(ML,pg.y+rh,ML+BW,pg.y+rh)
        ctype=_clean_val(ci.get('type',''))
        sq=QColor(type_colors.get(ctype.lower(),'#cfcabb'))
        aboves=', '.join(str(x) for x in above_map.get(cn,[])[:3])
        belows=', '.join(str(x) for x in below_map.get(cn,[])[:3])
        vals=[None, f"Context {cn}", ctype, _clean_val(ci.get('period','')), aboves, belows]
        x=ML
        for vi,(val,cw) in enumerate(zip(vals,col_ws)):
            if vi==0:
                p.setBrush(QBrush(sq)); p.setPen(QPen(QColor('#9a9486'),0.4))
                p.drawRect(x+5, pg.y+rh//2-4, 8, 8)
            else:
                p.setFont(_mk_font("Helvetica",max(1,int(7*fs)))); p.setPen(pg.C_TEXT)
                p.drawText(QRectF(x+4,pg.y,cw-6,rh),Qt.AlignVCenter|Qt.AlignLeft,str(val)[:40])
            x+=cw
        pg.y+=rh
    pg.y+=4


# ── Per-context PDF export (single page, used by "Export context PDF") ────────
def _export_context_page(output_path, ctx_num, win):
    if HAS_PDF_WRITER:
        device=_QPdfWriter(output_path); device.setResolution(72)
        device.setPageSize(QPagedPaintDevice.A4)
        try: device.setPageMargins(QMarginsF(0,0,0,0))
        except Exception: pass
    elif HAS_PRINTER:
        device=QPrinter(QPrinter.HighResolution); device.setOutputFormat(QPrinter.PdfFormat)
        device.setOutputFileName(output_path); device.setPaperSize(QPrinter.A4)
        device.setPageMargins(0,0,0,0,QPrinter.Millimeter)
    else:
        return False
    painter=QPainter()
    if not painter.begin(device): return False
    if not HAS_PDF_WRITER and HAS_PRINTER:
        pr=device.pageRect(); painter.scale(pr.width()/595.0,pr.height()/842.0)

    opts={"font_scale":1.0,"margin_lr":46,"margin_top":50,"margin_bot":46,
          "row_height":15,"wrap_text":True,"site":getattr(win,'_current_site',''),
          "title":"Context Record","author":getattr(win,'_current_user',''),
          **DEFAULT}
    logo_px=_load_default_logo()
    pg=Page(painter, device, opts, logo_px)
    all_r=win.relationships+getattr(win,'layer_rels',[])
    registry=getattr(win,'_photo_registry',{}) or {}
    photos=[]
    for cat in ('photos','drawings','refs'): photos+=registry.get(cat,[])
    photos=[ph for ph in photos if ph.get('path') and os.path.exists(ph['path'])]
    ctx=win.ctx_data.get(ctx_num,{})
    pg.draw_context_sheet(ctx_num, ctx, all_r, photos=photos)
    painter.end()
    return True
