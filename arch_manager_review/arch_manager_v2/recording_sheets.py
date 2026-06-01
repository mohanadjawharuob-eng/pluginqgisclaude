"""
recording_sheets.py — Customizable recording sheet framework.
Each context can have multiple recording sheets (skeleton, masonry, soil, etc.)
Forms are defined by JSON schemas the user can edit via the Form Builder.
"""
import os, json, datetime
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTextEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QScrollArea, QFrame, QGroupBox, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QInputDialog, QListWidget,
    QListWidgetItem, QAbstractItemView, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QFont, QColor

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsFields,
    QgsField, QgsFeature, QgsWkbTypes, QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext
)

from .styles import CLR, btn_style, FONT_SANS
from .widgets import SectionHeader

# ── Built-in sheet templates ──────────────────────────────────────────────────
BUILTIN_SHEETS = {
    "skeleton": {
        "label": "Skeleton",
        "icon": "💀",
        "table": "sheet_skeleton",
        "fields": [
            {"name": "skeleton_num", "label": "Skeleton #", "type": "int", "required": True},
            {"name": "context_num",  "label": "Context #",  "type": "int", "required": True},
            {"name": "grave",        "label": "Grave",      "type": "text"},
            {"name": "site",         "label": "Site",       "type": "text"},
            {"name": "age_group",    "label": "Age group",   "type": "choice",
             "options": ["Foetus","Newborn","Infant","Child","Juvenile","Adolescent",
                         "Young Adult","Middle Adult","Old Adult","Adult","Unknown"]},
            {"name": "sex",          "label": "Sex",         "type": "choice",
             "options": ["?","M","F","M?","F?","Indeterminate"]},
            {"name": "position",     "label": "Body position","type": "choice",
             "options": ["Supine","Prone","Left side","Right side","Flexed","Crouched","Disturbed","Unknown"]},
            {"name": "orientation",  "label": "Orientation", "type": "choice",
             "options": ["N-S","S-N","E-W","W-E","NE-SW","NW-SE","Unknown"]},
            {"name": "completeness", "label": "Completeness %", "type": "int"},
            {"name": "preservation", "label": "Preservation", "type": "choice",
             "options": ["Excellent","Good","Fair","Poor","Very poor"]},
            {"name": "associated_finds","label":"Associated finds","type":"longtext"},
            {"name": "samples_taken","label":"Samples taken","type":"longtext"},
            {"name": "field_notes",  "label": "Field notes", "type": "longtext"},
        ]
    },
    "masonry": {
        "label": "Masonry",
        "icon": "🧱",
        "table": "sheet_masonry",
        "fields": [
            {"name": "context_num", "label": "Context #",   "type": "int", "required": True},
            {"name": "wall_id",     "label": "Wall ID",     "type": "text"},
            {"name": "material",    "label": "Material",    "type": "choice",
             "options": ["Limestone","Sandstone","Basalt","Granite","Brick","Mudbrick","Mixed","Unknown"]},
            {"name": "bond",        "label": "Bond / coursing", "type": "choice",
             "options": ["Coursed","Uncoursed","Ashlar","Rubble","Mixed","Polygonal","Cyclopean","Unknown"]},
            {"name": "mortar",      "label": "Mortar",      "type": "choice",
             "options": ["Lime","Mud","Gypsum","Cement","None","Unknown"]},
            {"name": "length_m",    "label": "Length (m)",  "type": "float"},
            {"name": "width_m",     "label": "Width (m)",   "type": "float"},
            {"name": "height_m",    "label": "Preserved height (m)", "type": "float"},
            {"name": "courses",     "label": "Visible courses", "type": "int"},
            {"name": "stone_size_max", "label": "Max stone (cm)", "type": "float"},
            {"name": "stone_size_avg", "label": "Avg stone (cm)", "type": "float"},
            {"name": "alignment",   "label": "Alignment",   "type": "text"},
            {"name": "condition",   "label": "Condition",   "type": "choice",
             "options": ["Excellent","Good","Fair","Poor","Collapsed"]},
            {"name": "description", "label": "Description", "type": "longtext"},
            {"name": "notes",       "label": "Notes",       "type": "longtext"},
        ]
    },
    "soil": {
        "label": "Soil / Sediment",
        "icon": "🟫",
        "table": "sheet_soil",
        "fields": [
            {"name": "context_num", "label": "Context #",   "type": "int", "required": True},
            {"name": "texture",     "label": "Texture",     "type": "choice",
             "options": ["Sand","Silty sand","Sandy silt","Silt","Clay","Sandy clay","Silty clay",
                         "Gravel","Loam","Mixed","Unknown"]},
            {"name": "munsell_color","label":"Munsell color","type":"text"},
            {"name": "color_dry",   "label": "Color (dry)", "type": "text"},
            {"name": "color_wet",   "label": "Color (wet)", "type": "text"},
            {"name": "compactness", "label": "Compactness", "type": "choice",
             "options": ["Loose","Friable","Firm","Compact","Hard","Indurated"]},
            {"name": "moisture",    "label": "Moisture",    "type": "choice",
             "options": ["Dry","Slightly moist","Moist","Wet","Saturated"]},
            {"name": "inclusions",  "label": "Inclusions",  "type": "longtext"},
            {"name": "inclusion_pct","label":"Inclusion %", "type": "int"},
            {"name": "ph",          "label": "pH",          "type": "float"},
            {"name": "thickness_cm","label": "Thickness (cm)","type": "float"},
            {"name": "samples_taken","label":"Samples taken","type":"longtext"},
            {"name": "description", "label": "Description", "type": "longtext"},
            {"name": "notes",       "label": "Notes",       "type": "longtext"},
        ]
    },
    "ceramic_diagnostic": {
        "label": "Ceramic Diagnostic",
        "icon": "🏺",
        "table": "sheet_ceramic_diag",
        "fields": [
            {"name": "context_num", "label": "Context #",   "type": "int", "required": True},
            {"name": "sherd_id",    "label": "Sherd ID",    "type": "text"},
            {"name": "part",        "label": "Part",        "type": "choice",
             "options": ["Rim","Body","Base","Handle","Spout","Neck","Shoulder","Foot","Lid","Decorated body"]},
            {"name": "form",        "label": "Form",        "type": "choice",
             "options": ["Amphora","Cooking pot","Bowl","Jar","Jug","Plate","Lamp","Pithos","Storage jar","Unknown"]},
            {"name": "fabric",      "label": "Fabric",      "type": "text"},
            {"name": "ware",        "label": "Ware",        "type": "text"},
            {"name": "surface_treat","label":"Surface treatment","type":"choice",
             "options": ["None","Slipped","Burnished","Painted","Glazed","Combed","Incised","Stamped"]},
            {"name": "decoration",  "label": "Decoration",  "type": "longtext"},
            {"name": "rim_diam",    "label": "Rim diam (cm)","type": "float"},
            {"name": "base_diam",   "label": "Base diam (cm)","type":"float"},
            {"name": "thickness_mm","label": "Thickness (mm)","type":"float"},
            {"name": "period",      "label": "Period",      "type": "text"},
            {"name": "parallel",    "label": "Parallels",   "type": "longtext"},
            {"name": "notes",       "label": "Notes",       "type": "longtext"},
        ]
    },
}

# Field type → QVariant mapping for layer creation
TYPE_MAP = {
    "int":      QVariant.Int,
    "float":    QVariant.Double,
    "text":     QVariant.String,
    "longtext": QVariant.String,
    "choice":   QVariant.String,
    "bool":     QVariant.Bool,
    "date":     QVariant.String,
}


def _sheets_dir():
    """Where user-customized sheet schemas live."""
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "user_sheets")
    os.makedirs(p, exist_ok=True)
    return p


def load_sheet_schema(sheet_key: str) -> dict:
    """Load a sheet schema — user-customized version takes priority."""
    user_path = os.path.join(_sheets_dir(), f"{sheet_key}.json")
    if os.path.exists(user_path):
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return BUILTIN_SHEETS.get(sheet_key, {})


def save_sheet_schema(sheet_key: str, schema: dict):
    """Persist a user-modified schema."""
    user_path = os.path.join(_sheets_dir(), f"{sheet_key}.json")
    with open(user_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


def list_available_sheets() -> list:
    """Return list of sheet keys (builtin + custom)."""
    keys = set(BUILTIN_SHEETS.keys())
    for fn in os.listdir(_sheets_dir()):
        if fn.endswith(".json"):
            keys.add(fn[:-5])
    return sorted(keys)


# ─────────────────────────────────────────────────────────────────────────────
# FormBuilderDialog — let user customize a sheet schema
# ─────────────────────────────────────────────────────────────────────────────
class FormBuilderDialog(QDialog):
    """Dialog to add/remove/edit fields on a recording sheet."""

    def __init__(self, sheet_key: str, parent=None):
        super().__init__(parent)
        self.sheet_key = sheet_key
        self.schema = load_sheet_schema(sheet_key)
        if not self.schema:
            self.schema = {"label": sheet_key.title(),
                           "icon": "📋",
                           "table": f"sheet_{sheet_key}",
                           "fields": []}
        self.setWindowTitle(f"Form Builder — {self.schema['label']}")
        self.resize(720, 540)
        self._build_ui()
        self._refresh_field_list()

    def _build_ui(self):
        vl = QVBoxLayout(self)

        # Header
        hdr = QLabel(
            f"<b>Customize the '{self.schema['label']}' recording sheet</b><br>"
            f"<small>Add, remove, or edit fields. Changes apply to new records — existing data is preserved.</small>"
        )
        hdr.setStyleSheet(
            f"background:#1e1e1e;color:{CLR['accent_gold']};"
            f"padding:10px;border-radius:3px;")
        vl.addWidget(hdr)

        # Sheet metadata row
        meta = QHBoxLayout()
        meta.addWidget(QLabel("Label:"))
        self.label_edit = QLineEdit(self.schema.get("label", ""))
        meta.addWidget(self.label_edit)
        meta.addWidget(QLabel("Icon:"))
        self.icon_edit = QLineEdit(self.schema.get("icon", "📋"))
        self.icon_edit.setMaximumWidth(50)
        meta.addWidget(self.icon_edit)
        meta.addWidget(QLabel("Table:"))
        self.table_edit = QLineEdit(self.schema.get("table", ""))
        self.table_edit.setReadOnly(True)
        self.table_edit.setStyleSheet("color:#888;background:#eee;")
        meta.addWidget(self.table_edit)
        vl.addLayout(meta)

        # Fields table
        vl.addWidget(QLabel("<b>Fields:</b>"))
        self.field_tbl = QTableWidget()
        self.field_tbl.setColumnCount(5)
        self.field_tbl.setHorizontalHeaderLabels(
            ["Field name", "Display label", "Type", "Options (comma-sep)", "Required"])
        self.field_tbl.horizontalHeader().setStretchLastSection(True)
        self.field_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        vl.addWidget(self.field_tbl, 1)

        # Field actions
        actions = QHBoxLayout()
        add_btn = QPushButton("＋ Add field")
        add_btn.setStyleSheet(btn_style(CLR['accent_green'], '#5a9a5a'))
        add_btn.clicked.connect(self._add_field)
        actions.addWidget(add_btn)

        del_btn = QPushButton("🗑 Delete selected")
        del_btn.setStyleSheet(btn_style(CLR['accent_red'], '#a03030'))
        del_btn.clicked.connect(self._delete_field)
        actions.addWidget(del_btn)

        up_btn = QPushButton("▲ Move up")
        up_btn.setStyleSheet(btn_style('#3a3a3a', '#4a4a4a'))
        up_btn.clicked.connect(lambda: self._move(-1))
        actions.addWidget(up_btn)

        down_btn = QPushButton("▼ Move down")
        down_btn.setStyleSheet(btn_style('#3a3a3a', '#4a4a4a'))
        down_btn.clicked.connect(lambda: self._move(1))
        actions.addWidget(down_btn)

        reset_btn = QPushButton("↺ Reset to defaults")
        reset_btn.setStyleSheet(btn_style('#5a3a00', '#7a5800'))
        reset_btn.clicked.connect(self._reset)
        actions.addWidget(reset_btn)

        actions.addStretch()
        vl.addLayout(actions)

        # OK / Cancel
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        vl.addWidget(bb)

    def _refresh_field_list(self):
        fields = self.schema.get("fields", [])
        self.field_tbl.setRowCount(len(fields))
        for r, f in enumerate(fields):
            self.field_tbl.setItem(r, 0, QTableWidgetItem(f.get("name", "")))
            self.field_tbl.setItem(r, 1, QTableWidgetItem(f.get("label", "")))
            type_cb = QComboBox()
            type_cb.addItems(["text", "longtext", "int", "float", "choice", "bool", "date"])
            type_cb.setCurrentText(f.get("type", "text"))
            self.field_tbl.setCellWidget(r, 2, type_cb)
            opts = ", ".join(f.get("options", []))
            self.field_tbl.setItem(r, 3, QTableWidgetItem(opts))
            req_cb = QCheckBox()
            req_cb.setChecked(bool(f.get("required", False)))
            self.field_tbl.setCellWidget(r, 4, req_cb)

    def _add_field(self):
        name, ok = QInputDialog.getText(self, "New field",
            "Field name (snake_case, no spaces):")
        if not ok or not name.strip():
            return
        name = name.strip().replace(" ", "_").lower()
        # Sanitize
        name = "".join(c for c in name if c.isalnum() or c == "_")
        if not name:
            QMessageBox.warning(self, "", "Invalid field name."); return
        if any(f.get("name") == name for f in self.schema["fields"]):
            QMessageBox.warning(self, "", "A field with that name already exists.")
            return
        self.schema["fields"].append({
            "name": name,
            "label": name.replace("_", " ").title(),
            "type": "text",
            "required": False,
        })
        self._refresh_field_list()

    def _delete_field(self):
        rows = self.field_tbl.selectionModel().selectedRows()
        if not rows: return
        if QMessageBox.question(
                self, "Delete", "Delete selected field(s)?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        # Save current edits before delete
        self._collect()
        to_remove = sorted({r.row() for r in rows}, reverse=True)
        for r in to_remove:
            if 0 <= r < len(self.schema["fields"]):
                del self.schema["fields"][r]
        self._refresh_field_list()

    def _move(self, delta):
        rows = self.field_tbl.selectionModel().selectedRows()
        if not rows: return
        self._collect()
        r = rows[0].row()
        tgt = r + delta
        if 0 <= tgt < len(self.schema["fields"]):
            self.schema["fields"][r], self.schema["fields"][tgt] = (
                self.schema["fields"][tgt], self.schema["fields"][r])
            self._refresh_field_list()
            self.field_tbl.selectRow(tgt)

    def _reset(self):
        if self.sheet_key not in BUILTIN_SHEETS:
            QMessageBox.information(self, "", "No defaults for custom sheets.")
            return
        if QMessageBox.question(
                self, "Reset",
                "Reset to built-in defaults? Custom fields will be lost.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self.schema = dict(BUILTIN_SHEETS[self.sheet_key])
        self.schema["fields"] = [dict(f) for f in self.schema["fields"]]
        self._refresh_field_list()

    def _collect(self):
        """Read field edits from the table into self.schema."""
        fields = []
        for r in range(self.field_tbl.rowCount()):
            name_item = self.field_tbl.item(r, 0)
            label_item = self.field_tbl.item(r, 1)
            opts_item = self.field_tbl.item(r, 3)
            type_w = self.field_tbl.cellWidget(r, 2)
            req_w = self.field_tbl.cellWidget(r, 4)
            if not name_item or not name_item.text().strip():
                continue
            f = {
                "name": name_item.text().strip(),
                "label": (label_item.text() if label_item else "").strip()
                         or name_item.text().strip(),
                "type": type_w.currentText() if type_w else "text",
                "required": req_w.isChecked() if req_w else False,
            }
            if f["type"] == "choice" and opts_item:
                opts = [o.strip() for o in opts_item.text().split(",") if o.strip()]
                if opts: f["options"] = opts
            fields.append(f)
        self.schema["fields"] = fields
        self.schema["label"] = self.label_edit.text().strip() or self.schema.get("label","")
        self.schema["icon"]  = self.icon_edit.text().strip() or "📋"

    def _save(self):
        self._collect()
        save_sheet_schema(self.sheet_key, self.schema)
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# SheetForm — actual form widget for one record type
# ─────────────────────────────────────────────────────────────────────────────
class SheetForm(QWidget):
    """Renders a customizable form from a schema."""
    record_saved = pyqtSignal(str, dict)  # sheet_key, data

    def __init__(self, sheet_key: str, on_save, on_customize, parent=None):
        super().__init__(parent)
        self.sheet_key = sheet_key
        self.schema    = load_sheet_schema(sheet_key)
        self._widgets  = {}
        self._on_save  = on_save
        self._on_customize = on_customize
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # Header bar
        hdr = QFrame()
        hdr.setStyleSheet(
            f"background:#1e1e1e;border-radius:3px;padding:6px;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(8,4,8,4)
        title = QLabel(f"{self.schema.get('icon','📋')}  "
                       f"<b style='color:{CLR['accent_gold']};font-size:13px;'>"
                       f"{self.schema.get('label', self.sheet_key.title())}</b>")
        hl.addWidget(title); hl.addStretch()

        customize_btn = QPushButton("⚙ Customize fields")
        customize_btn.setStyleSheet(btn_style('#3a3000', '#5a4a00'))
        customize_btn.clicked.connect(self._customize_clicked)
        hl.addWidget(customize_btn)
        outer.addWidget(hdr)

        # Scroll area for form fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{CLR['bg_content']};}}")
        form_w = QWidget()
        form_w.setStyleSheet(f"background:{CLR['bg_white']};")
        self._form_layout = QFormLayout(form_w)
        self._form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._form_layout.setSpacing(8)
        self._form_layout.setContentsMargins(14, 12, 14, 12)
        self._populate_fields()
        scroll.setWidget(form_w)
        outer.addWidget(scroll, 1)

        # Save bar
        bar = QHBoxLayout()
        clear_btn = QPushButton("🗑 Clear form")
        clear_btn.setStyleSheet(btn_style('#3a3a3a', '#4a4a4a'))
        clear_btn.clicked.connect(self.clear)
        bar.addWidget(clear_btn)
        bar.addStretch()
        save_btn = QPushButton("💾 Save record")
        save_btn.setStyleSheet(btn_style(CLR['accent_green'], '#5a9a5a', tall=True))
        save_btn.clicked.connect(self._save_clicked)
        bar.addWidget(save_btn)
        outer.addLayout(bar)

    def _populate_fields(self):
        self._widgets = {}
        # Clear existing
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for f in self.schema.get("fields", []):
            label_text = f["label"]
            if f.get("required"):
                label_text += " *"
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size:10px;color:#222;")
            w = self._make_widget(f)
            self._form_layout.addRow(lbl, w)
            self._widgets[f["name"]] = (w, f["type"])

    def _make_widget(self, f):
        t = f.get("type", "text")
        if t == "int":
            w = QSpinBox(); w.setRange(-999999, 999999); w.setSpecialValueText(""); w.setValue(-999999)
            return w
        if t == "float":
            w = QDoubleSpinBox(); w.setRange(-99999, 99999); w.setDecimals(3); w.setSpecialValueText("")
            w.setValue(-99999); return w
        if t == "choice":
            w = QComboBox(); w.setEditable(True)
            w.addItem("")
            for opt in f.get("options", []):
                w.addItem(opt)
            return w
        if t == "longtext":
            w = QTextEdit(); w.setMinimumHeight(50); w.setMaximumHeight(80)
            return w
        if t == "bool":
            return QCheckBox()
        # default: text
        return QLineEdit()

    def _customize_clicked(self):
        dlg = FormBuilderDialog(self.sheet_key, self)
        if dlg.exec_() == QDialog.Accepted:
            # Reload schema and rebuild
            self.schema = load_sheet_schema(self.sheet_key)
            self._populate_fields()
            if self._on_customize:
                self._on_customize(self.sheet_key, self.schema)

    def get_values(self) -> dict:
        out = {}
        for name, (w, t) in self._widgets.items():
            if t == "int":
                v = w.value()
                out[name] = None if v == w.minimum() else int(v)
            elif t == "float":
                v = w.value()
                out[name] = None if v == w.minimum() else float(v)
            elif t == "choice":
                v = w.currentText().strip()
                out[name] = v if v else None
            elif t == "longtext":
                v = w.toPlainText().strip()
                out[name] = v if v else None
            elif t == "bool":
                out[name] = w.isChecked()
            else:
                v = w.text().strip()
                out[name] = v if v else None
        return out

    def set_values(self, data: dict):
        for name, (w, t) in self._widgets.items():
            v = data.get(name)
            if v is None: continue
            try:
                if t == "int":
                    w.setValue(int(v))
                elif t == "float":
                    w.setValue(float(v))
                elif t == "choice":
                    w.setCurrentText(str(v))
                elif t == "longtext":
                    w.setPlainText(str(v))
                elif t == "bool":
                    w.setChecked(bool(v))
                else:
                    w.setText(str(v))
            except Exception:
                pass

    def clear(self):
        for name, (w, t) in self._widgets.items():
            if t == "int" or t == "float":
                w.setValue(w.minimum())
            elif t == "choice":
                w.setCurrentIndex(0); w.setEditText("")
            elif t == "longtext":
                w.clear()
            elif t == "bool":
                w.setChecked(False)
            else:
                w.clear()

    def _save_clicked(self):
        data = self.get_values()
        # Required field check
        missing = []
        for f in self.schema.get("fields", []):
            if f.get("required"):
                v = data.get(f["name"])
                if v is None or v == "":
                    missing.append(f["label"])
        if missing:
            QMessageBox.warning(
                self, "Missing fields",
                f"Required field(s) not filled:\n  • " +
                "\n  • ".join(missing))
            return
        if self._on_save:
            self._on_save(self.sheet_key, self.schema, data)


# ─────────────────────────────────────────────────────────────────────────────
# Layer management for sheets
# ─────────────────────────────────────────────────────────────────────────────
def ensure_sheet_layer(gpkg_path: str, schema: dict,
                        site_prefix: str = "") -> QgsVectorLayer | None:
    """
    Make sure the GeoPackage has a table matching this schema.
    Returns the loaded QgsVectorLayer.
    """
    table = schema.get("table") or f"sheet_{schema.get('label','custom').lower()}"
    layer_name = f"{site_prefix}_{table}" if site_prefix else table

    # Check if it's already loaded
    for lyr in QgsProject.instance().mapLayers().values():
        try:
            uri = lyr.dataProvider().dataSourceUri()
            if gpkg_path in uri and f"layername={table}" in uri:
                return lyr
        except Exception:
            continue

    # Create the table
    fields = QgsFields()
    fields.append(QgsField("rec_id",       QVariant.Int))
    fields.append(QgsField("created_at",   QVariant.String))
    fields.append(QgsField("created_by",   QVariant.String))
    fields.append(QgsField("updated_at",   QVariant.String))
    for f in schema.get("fields", []):
        fields.append(QgsField(f["name"], TYPE_MAP.get(f["type"], QVariant.String)))

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.fileEncoding = "UTF-8"
    opts.layerName = table
    # If the .gpkg exists, append a layer; otherwise create
    if os.path.exists(gpkg_path):
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    QgsVectorFileWriter.create(
        gpkg_path, fields, QgsWkbTypes.NoGeometry,
        QgsCoordinateReferenceSystem("EPSG:4326"),
        QgsCoordinateTransformContext(), opts)

    # Load it
    uri = f"{gpkg_path}|layername={table}"
    lyr = QgsVectorLayer(uri, layer_name, "ogr")
    if lyr.isValid():
        QgsProject.instance().addMapLayer(lyr)
        return lyr
    return None


def save_sheet_record(lyr: QgsVectorLayer, data: dict, user: str = "?",
                      rec_id: int | None = None) -> bool:
    """Insert or update a sheet record."""
    if not lyr: return False
    fields = lyr.fields()
    field_names = {f.name() for f in fields}
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lyr.startEditing()
    if rec_id is None:
        # Find next rec_id
        max_id = 0
        for f in lyr.getFeatures():
            try:
                v = f.attribute("rec_id")
                if v is not None and int(v) > max_id:
                    max_id = int(v)
            except Exception:
                pass
        feat = QgsFeature(fields)
        feat.setAttribute("rec_id", max_id + 1)
        feat.setAttribute("created_at", now)
        feat.setAttribute("created_by", user)
    else:
        # Find existing
        feat = None
        for f in lyr.getFeatures():
            try:
                if int(f.attribute("rec_id")) == rec_id:
                    feat = f; break
            except Exception:
                continue
        if feat is None:
            lyr.rollBack(); return False
    feat.setAttribute("updated_at", now)

    for name, v in data.items():
        if name in field_names:
            feat.setAttribute(name, v)

    ok = (lyr.addFeature(feat) if rec_id is None
          else lyr.updateFeature(feat))
    if ok:
        lyr.commitChanges()
    else:
        lyr.rollBack()
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# RecordingSheetsTab — the main tab with sub-tabs
# ─────────────────────────────────────────────────────────────────────────────
class RecordingSheetsTab(QWidget):
    """
    Multi-tab container for all recording sheet types.
    Each sub-tab is a SheetForm (skeleton, masonry, soil, etc.)
    """
    def __init__(self, get_gpkg_path, get_site, get_user, on_msg, parent=None):
        super().__init__(parent)
        self.get_gpkg_path = get_gpkg_path  # callable() → str | None
        self.get_site      = get_site       # callable() → str
        self.get_user      = get_user       # callable() → str
        self.on_msg        = on_msg         # callable(str, error=bool)
        self._sheet_forms  = {}
        self._build_ui()

    def _build_ui(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Top action bar
        bar = QFrame()
        bar.setStyleSheet(f"background:#1e1e1e;border-bottom:1px solid {CLR['accent_gold']};")
        hl = QHBoxLayout(bar); hl.setContentsMargins(10, 6, 10, 6)
        title = QLabel(f"<b style='color:{CLR['accent_gold']};font-size:13px;'>"
                       f"📋  Recording Sheets</b>"
                       f"<span style='color:#888;font-size:10px;'>"
                       f"  —  Customizable forms per record type</span>")
        hl.addWidget(title); hl.addStretch()

        add_btn = QPushButton("＋ New sheet type…")
        add_btn.setStyleSheet(btn_style(CLR['accent_green'], '#5a9a5a'))
        add_btn.setToolTip("Create a new custom recording sheet type")
        add_btn.clicked.connect(self._add_sheet_type)
        hl.addWidget(add_btn)
        vl.addWidget(bar)

        # Sub-tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabBar::tab{padding:6px 14px;font-size:10px;}"
            "QTabBar::tab:selected{font-weight:bold;}")
        vl.addWidget(self._tabs, 1)

        # Add a tab for each available sheet
        for key in list_available_sheets():
            self._add_form_tab(key)

    def _add_form_tab(self, sheet_key: str):
        if sheet_key in self._sheet_forms:
            return
        schema = load_sheet_schema(sheet_key)
        if not schema:
            return
        form = SheetForm(sheet_key,
                         on_save=self._handle_save,
                         on_customize=self._handle_customize,
                         parent=self)
        self._sheet_forms[sheet_key] = form
        label = f"{schema.get('icon','📋')} {schema.get('label', sheet_key)}"
        self._tabs.addTab(form, label)

    def _add_sheet_type(self):
        name, ok = QInputDialog.getText(
            self, "New sheet type",
            "Identifier for this sheet (snake_case):\n"
            "Examples: pottery_diagnostic, sample, photo_log")
        if not ok or not name.strip(): return
        key = name.strip().replace(" ", "_").lower()
        key = "".join(c for c in key if c.isalnum() or c == "_")
        if not key:
            QMessageBox.warning(self, "", "Invalid name."); return
        if key in self._sheet_forms:
            QMessageBox.information(self, "", "A sheet with that name already exists.")
            self._tabs.setCurrentWidget(self._sheet_forms[key])
            return
        # Create a blank schema and open builder
        schema = {"label": key.replace("_", " ").title(),
                  "icon": "📋",
                  "table": f"sheet_{key}",
                  "fields": [
                      {"name": "context_num", "label": "Context #", "type": "int", "required": True},
                      {"name": "notes", "label": "Notes", "type": "longtext"},
                  ]}
        save_sheet_schema(key, schema)
        dlg = FormBuilderDialog(key, self)
        if dlg.exec_() == QDialog.Accepted:
            self._add_form_tab(key)
            self._tabs.setCurrentWidget(self._sheet_forms[key])

    def _handle_save(self, sheet_key, schema, data):
        gpkg = self.get_gpkg_path()
        if not gpkg:
            QMessageBox.warning(
                self, "No GeoPackage",
                "Connect a GeoPackage first (Site Quick Connect or Open GeoPackage).")
            return
        site = self.get_site() or ""
        lyr = ensure_sheet_layer(gpkg, schema, site_prefix=site)
        if not lyr:
            self.on_msg(f"Failed to create/open table for {sheet_key}", error=True)
            return
        ok = save_sheet_record(lyr, data, user=self.get_user())
        if ok:
            label = schema.get("label", sheet_key)
            self.on_msg(f"✓ {label} record saved")
            # Auto-clear after save
            self._sheet_forms[sheet_key].clear()
        else:
            self.on_msg(f"Save failed for {sheet_key}", error=True)

    def _handle_customize(self, sheet_key, schema):
        # Update tab label in case icon/label changed
        for i in range(self._tabs.count()):
            if self._tabs.widget(i) is self._sheet_forms.get(sheet_key):
                self._tabs.setTabText(
                    i, f"{schema.get('icon','📋')} {schema.get('label', sheet_key)}")
                break
        self.on_msg(f"Form '{schema.get('label')}' customized")
