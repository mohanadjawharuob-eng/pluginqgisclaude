"""
Archaeological Manager dock.py v5
Refactored: logic split into data_manager.py, styles.py, widgets.py, harris_view.py
"""
import json, csv, zipfile, os, re
import shutil, datetime
import xml.etree.ElementTree as ET
from functools import partial

from qgis.PyQt.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QComboBox, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QFileDialog, QHeaderView, QDialog, QDialogButtonBox, QLineEdit,
    QGraphicsView, QGraphicsScene, QGraphicsObject, QGraphicsRectItem, QGraphicsTextItem, QMessageBox,
    QAbstractItemView, QScrollArea, QStatusBar, QSplitter, QFrame,
    QCheckBox, QStackedWidget, QToolButton, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QInputDialog, QColorDialog, QProgressBar
)
from qgis.PyQt.QtCore import Qt, QRectF, QVariant, pyqtSignal
from qgis.PyQt.QtGui import (
    QColor, QPen, QBrush, QPainterPath, QFont, QPainter, QImage, QPixmap, QFontMetrics, QIcon
)

try:
    from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
    from qgis.PyQt.QtWebChannel import QWebChannel
    from qgis.PyQt.QtCore import QObject, pyqtSlot, QUrl
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

class QtBridge(QObject if HAS_WEBENGINE else object):
    def __init__(self, callback):
        if HAS_WEBENGINE: super().__init__()
        self._cb = callback
    if HAS_WEBENGINE:
        @pyqtSlot(str)
        def receive_bone_data(self, json_str):
            self._cb(json_str)

from qgis.core import (
    QgsProject, QgsMapLayer, QgsFeature, QgsField, QgsFields,
    QgsVectorLayer, QgsVectorFileWriter, QgsWkbTypes,
    QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
)

# ── Plugin modules ────────────────────────────────────────────────────────────
from .styles import (CLR, LIGHT_CLR, btn_style, CONTENT_QSS, SIDEBAR_QSS,
                      STATUS_BAR_QSS, NAV_BTN_QSS, ROOT_QSS,
                      BTN_PRIMARY, BTN_SECONDARY, BTN_PURPLE, BTN_DANGER, BTN_GHOST,
                      CARD_QSS, TABLE_QSS, RADIUS, RADIUS_SM,
                      FONT_SIZE_XS, FONT_SIZE_SM, FONT_SIZE_LG, FONT_SIZE_XL,
                      build_all_qss)
from .widgets import (StatusBadge, SiteCard, StatCard, ToastLabel, ActionBar,
                      DataTable, CollapsiblePanel, SectionHeader, DetailPanel,
                      SearchInput, ContentTitle, BrandHeader, icon_btn,
                      NavItem, Card, TopBar)
from .styles import (APP_QSS, TAB_QSS, CARD_QSS, INPUT_QSS,
                     stat_card_qss)
from .data_manager import (SCHEMAS, TABLE_NAMES, coerce, vlayers as dm_vlayers,
                            lyr_from_cb, schema_for, write_feature, delete_features,
                            create_project as dm_create_project, open_gpkg as dm_open_gpkg,
                            detect_sites, find_layer, safe_int, user_data_path,
                            user_data_dir, fmt_cell)
from .recording_sheets import RecordingSheetsTab
from .harris_view import HarrisView

# ── Vocabularies ──────────────────────────────────────────────────────────────
CTX_TYPES = ['Fill','Cut','Deposit','Layer','Wall','Floor','Pit',
             'Trench','Surface','Feature','Rubble','Other']
POT_FORMS = ['Amphora','Bowl','Cooking Pot','Dish','Jar','Jug','Lamp',
             'Pan','Plate','Pitcher','Flask','Basin','Lid','Other']
PERIODS   = ['Prehistoric','Early Bronze Age','Middle Bronze Age','Late Bronze Age',
             'Iron Age','Persian','Hellenistic','Roman','Byzantine','Early Islamic',
             'Crusader','Medieval','Mamluk','Ottoman','Modern','Unknown']
ORIGINS   = ['Local','Regional','Cyprus','Asia Minor','Sinope','Cilicia',
             'Beirut','Egypt','North Africa','Greece','Italy','Spain','Unknown']
PARTS     = ['Rim','Base','Handle','Body','Decoration','Complete']
REL_TYPES = ['above','below','cuts','is_cut_by','contemporary','equals']
REL_LABELS= {'above':'is above (later than)','below':'is below (earlier than)',
             'cuts':'cuts','is_cut_by':'is cut by',
             'contemporary':'is contemporary with','equals':'equals / same unit'}
CTX_COLORS= {t.lower():c for t,c in zip(CTX_TYPES,
    ['#b8d4c8','#e8b99a','#d4c89a','#c4b8d8','#d8c8a8','#e0d4b0',
     '#d4a8a8','#f0d898','#a8d4c0','#c4a8d4','#c8c8b8','#d8d8d0'])}
VOCAB_MAP = {'type':CTX_TYPES,'context_type':CTX_TYPES,'form':POT_FORMS,
             'part':PARTS,'period':PERIODS,'date_period':PERIODS,'origin':ORIGINS}

BONE_STATUS = ['—','Complete','Fragmentary','Precise ID/side unknown',
               'Highly Crushed/distorted','Sampled (14C/DNA/isotopes)','Estimated','Absent']

AGE_GROUPS = ['Adult','Child-Adolescent','Young Child','Perinatal-Infant',
              'Unknown']
SEX_OPTIONS = ['Unknown','Male','Probable Male','Female','Probable Female',
               'Indeterminate']

# region, bone, sides, segments
BONE_ELEMENTS = [
    ('Cranium','Frontal',     ['—'],   ['']),
    ('Cranium','Parietal',    ['R','L'],['']),
    ('Cranium','Temporal',    ['R','L'],['']),
    ('Cranium','Occipital',   ['—'],   ['']),
    ('Cranium','Sphenoid',    ['—'],   ['']),
    ('Cranium','Ethmoid',     ['—'],   ['']),
    ('Face',   'Maxilla',     ['R','L'],['']),
    ('Face',   'Zygomatic',   ['R','L'],['']),
    ('Face',   'Nasal',       ['R','L'],['']),
    ('Face',   'Lacrimal',    ['R','L'],['']),
    ('Face',   'Palatine',    ['R','L'],['']),
    ('Face',   'Vomer',       ['—'],   ['']),
    ('Face',   'Inf. N. Concha',['R','L'],['']),
    ('Face',   'Mandible',    ['—'],   ['']),
    ('Face',   'Hyoid',       ['—'],   ['']),
    ('Cervical','C1',['—'],['']),('Cervical','C2',['—'],['']),
    ('Cervical','C3',['—'],['']),('Cervical','C4',['—'],['']),
    ('Cervical','C5',['—'],['']),('Cervical','C6',['—'],['']),
    ('Cervical','C7',['—'],['']),
    ('Thoracic','T1',['—'],['']),('Thoracic','T2',['—'],['']),
    ('Thoracic','T3',['—'],['']),('Thoracic','T4',['—'],['']),
    ('Thoracic','T5',['—'],['']),('Thoracic','T6',['—'],['']),
    ('Thoracic','T7',['—'],['']),('Thoracic','T8',['—'],['']),
    ('Thoracic','T9',['—'],['']),('Thoracic','T10',['—'],['']),
    ('Thoracic','T11',['—'],['']),('Thoracic','T12',['—'],['']),
    ('Lumbar', 'L1',['—'],['']),('Lumbar','L2',['—'],['']),
    ('Lumbar', 'L3',['—'],['']),('Lumbar','L4',['—'],['']),
    ('Lumbar', 'L5',['—'],['']),
    ('Sacrum', 'S1',['—'],['']),('Sacrum','S2',['—'],['']),
    ('Sacrum', 'S3',['—'],['']),('Sacrum','S4',['—'],['']),('Sacrum','S5',['—'],['']),
    ('Coccyx', 'Coccyx',['—'],['']),
    ('Ribs','Rib 1', ['R','L'],['']),('Ribs','Rib 2', ['R','L'],['']),
    ('Ribs','Rib 3', ['R','L'],['']),('Ribs','Rib 4', ['R','L'],['']),
    ('Ribs','Rib 5', ['R','L'],['']),('Ribs','Rib 6', ['R','L'],['']),
    ('Ribs','Rib 7', ['R','L'],['']),('Ribs','Rib 8', ['R','L'],['']),
    ('Ribs','Rib 9', ['R','L'],['']),('Ribs','Rib 10',['R','L'],['']),
    ('Ribs','Rib 11',['R','L'],['']),('Ribs','Rib 12',['R','L'],['']),
    ('Sternum','Manubrium',['—'],['']),
    ('Sternum','Sternal body',['—'],['']),
    ('Sternum','Xiphoid',['—'],['']),
    ('Upper Limb','Clavicle', ['R','L'],['']),
    ('Upper Limb','Scapula',  ['R','L'],['']),
    ('Upper Limb','Humerus',  ['R','L'],['Px','In','Di']),
    ('Upper Limb','Radius',   ['R','L'],['Px','In','Di']),
    ('Upper Limb','Ulna',     ['R','L'],['Px','In','Di']),
    ('Upper Limb','Carpals',  ['R','L'],['']),
    ('Upper Limb','Metacarpals',['R','L'],['']),
    ('Upper Limb','Ph. Hand', ['R','L'],['Px','In','Di']),
    ('Lower Limb','Os Coxae', ['R','L'],['']),
    ('Lower Limb','Femur',    ['R','L'],['Px','In','Di']),
    ('Lower Limb','Patella',  ['R','L'],['']),
    ('Lower Limb','Tibia',    ['R','L'],['Px','In','Di']),
    ('Lower Limb','Fibula',   ['R','L'],['Px','In','Di']),
    ('Lower Limb','Tarsals',  ['R','L'],['']),
    ('Lower Limb','Metatarsals',['R','L'],['']),
    ('Lower Limb','Ph. Foot', ['R','L'],['Px','In','Di']),
    ('Teeth (deciduous)','dI1',['R','L'],['']),('Teeth (deciduous)','dI2',['R','L'],['']),
    ('Teeth (deciduous)','dC', ['R','L'],['']),('Teeth (deciduous)','dM1',['R','L'],['']),
    ('Teeth (deciduous)','dM2',['R','L'],['']),
    ('Teeth (permanent)','I1', ['R','L'],['']),('Teeth (permanent)','I2',['R','L'],['']),
    ('Teeth (permanent)','C',  ['R','L'],['']),('Teeth (permanent)','P3',['R','L'],['']),
    ('Teeth (permanent)','P4', ['R','L'],['']),('Teeth (permanent)','M1',['R','L'],['']),
    ('Teeth (permanent)','M2', ['R','L'],['']),('Teeth (permanent)','M3',['R','L'],['']),
]


# ── Excel reader ──────────────────────────────────────────────────────────────
def read_xlsx(path):
    sheets={}
    ns ='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rns='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.parse(z.open('xl/sharedStrings.xml')).getroot()
            for si in root.findall(f'{{{ns}}}si'):
                t=si.find(f'{{{ns}}}t')
                strings.append(t.text or '' if t is not None
                               else ''.join(x.text or '' for x in si.iter(f'{{{ns}}}t')))
        wb  =ET.parse(z.open('xl/workbook.xml')).getroot()
        rels=ET.parse(z.open('xl/_rels/workbook.xml.rels')).getroot()
        rmap={r.get('Id'):r.get('Target') for r in rels}
        for sh in wb.findall(f'.//{{{ns}}}sheet'):
            name=sh.get('name','Sheet'); rid=sh.get(f'{{{rns}}}id')
            sp='xl/'+rmap.get(rid,'')
            if sp not in z.namelist(): continue
            sr=ET.parse(z.open(sp)).getroot(); rows=[]
            for row_el in sr.findall(f'.//{{{ns}}}row'):
                cells,prev=[],0
                for c in row_el.findall(f'{{{ns}}}c'):
                    ref=c.get('r',''); ci=0
                    for ch in ref:
                        if ch.isalpha(): ci=ci*26+(ord(ch.upper())-64)
                    ci-=1
                    while prev<ci: cells.append(''); prev+=1
                    t=c.get('t',''); ve=c.find(f'{{{ns}}}v'); val=''
                    if ve is not None and ve.text:
                        val=(strings[int(ve.text)] if t=='s' and int(ve.text)<len(strings) else ve.text)
                    cells.append(val); prev+=1
                rows.append(cells)
            if not rows: continue
            mc=max((len(r) for r in rows),default=0)
            rows=[r+['']*(mc-len(r)) for r in rows]
            sheets[name]=(rows[0],rows[1:])
    return sheets

# ── Dialogs ───────────────────────────────────────────────────────────────────
class RecordDialog(QDialog):
    def __init__(self,fields_list,defaults=None,title="Record",parent=None,extra_options=None):
        super().__init__(parent); self.setWindowTitle(title); self.setMinimumWidth(420)
        self._w={}; fl=QFormLayout(self); defaults=defaults or {}; extra_options=extra_options or {}
        for name,qtype in fields_list:
            val=str(defaults.get(name,'') or '')
            norm=name.lower().replace(' ','_')
            if norm in extra_options:
                w=QComboBox(); w.setEditable(True); w.addItems(['']+list(extra_options[norm]))
                idx=w.findText(val,Qt.MatchFixedString)
                if idx>=0: w.setCurrentIndex(idx)
                else: w.setEditText(val)
            elif norm in VOCAB_MAP:
                w=QComboBox(); w.setEditable(True); w.addItems(['']+VOCAB_MAP[norm])
                idx=w.findText(val,Qt.MatchFixedString)
                if idx>=0: w.setCurrentIndex(idx)
                else: w.setEditText(val)
            else: w=QLineEdit(val)
            fl.addRow(name.replace('_',' ').title()+':',w); self._w[name]=w
        bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); fl.addRow(bb)
    def values(self):
        return {k:(w.currentText() if isinstance(w,QComboBox) else w.text()) for k,w in self._w.items()}

class AddFieldDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("Add Column"); self.setMinimumWidth(300)
        fl=QFormLayout(self)
        self.name_input=QLineEdit(); self.name_input.setPlaceholderText("e.g. material, count")
        self.type_cb=QComboBox(); self.type_cb.addItems(["Text","Integer","Decimal"])
        fl.addRow("Column name:",self.name_input); fl.addRow("Type:",self.type_cb)
        bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); fl.addRow(bb)
    def get_field(self):
        name=self.name_input.text().strip().replace(' ','_')
        qtype={'Text':QVariant.String,'Integer':QVariant.Int,'Decimal':QVariant.Double}[self.type_cb.currentText()]
        return name,qtype

class ImportDialog(QDialog):
    def __init__(self,sheets,target_layers,parent=None):
        super().__init__(parent); self.setWindowTitle("Import Data"); self.setMinimumSize(620,420)
        self.sheets=sheets; self._combos=[]
        vl=QVBoxLayout(self)
        r1=QHBoxLayout(); r1.addWidget(QLabel("Sheet:")); self.sheet_cb=QComboBox()
        self.sheet_cb.addItems(list(sheets)); r1.addWidget(self.sheet_cb,1); vl.addLayout(r1)
        r2=QHBoxLayout(); r2.addWidget(QLabel("Import into:")); self.layer_cb=QComboBox()
        for n,lid in target_layers: self.layer_cb.addItem(n,lid)
        r2.addWidget(self.layer_cb,1); vl.addLayout(r2)
        self.preview_lbl=QLabel(); self.preview_lbl.setObjectName("muted"); vl.addWidget(self.preview_lbl)
        vl.addWidget(QLabel("<b>Map columns → fields</b> (sample value shown for reference):"))
        self.tbl=QTableWidget(0,3)
        self.tbl.setHorizontalHeaderLabels(["Source column","Sample value","Map to field →"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers); vl.addWidget(self.tbl)
        bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); vl.addWidget(bb)
        self.sheet_cb.currentTextChanged.connect(self._refresh)
        self.layer_cb.currentIndexChanged.connect(self._on_layer); self._refresh()
    def _refresh(self):
        sheet=self.sheet_cb.currentText(); headers,rows=self.sheets.get(sheet,([],[]))
        sample=rows[0] if rows else []
        self.preview_lbl.setText(f"{len(rows)} data rows · {len(headers)} columns")
        self.tbl.setRowCount(len(headers)); self._combos=[]
        for i,h in enumerate(headers):
            self.tbl.setItem(i,0,QTableWidgetItem(h))
            sv=sample[i] if i<len(sample) else ''
            self.tbl.setItem(i,1,QTableWidgetItem(str(sv)[:40]))
            cb=QComboBox(); self._combos.append(cb); self.tbl.setCellWidget(i,2,cb)
        self._on_layer()
    def _on_layer(self):
        lid=self.layer_cb.currentData(); lyr=QgsProject.instance().mapLayer(lid) if lid else None
        fnames=[f.name() for f in lyr.fields()] if lyr else []
        sheet=self.sheet_cb.currentText(); headers,_=self.sheets.get(sheet,([],[]))
        for i,(h,cb) in enumerate(zip(headers,self._combos)):
            cb.clear(); cb.addItem("— skip —",None)
            for fn in fnames: cb.addItem(fn,fn)
            h_norm=h.lower().strip().replace(' ','_').replace('-','_').replace('/','_').replace('.','')
            for fi,fn in enumerate(fnames):
                fn_norm=fn.lower().replace(' ','_')
                if h_norm==fn_norm or h.lower()==fn.lower(): cb.setCurrentIndex(fi+1); break
            else:
                for fi,fn in enumerate(fnames):
                    fn_norm=fn.lower().replace(' ','_')
                    if h_norm in fn_norm or fn_norm in h_norm: cb.setCurrentIndex(fi+1); break
    def get_mapping(self):
        sheet=self.sheet_cb.currentText(); headers,rows=self.sheets.get(sheet,([],[]))
        mapping={i:cb.currentData() for i,cb in enumerate(self._combos) if cb.currentData() is not None}
        return headers,rows,mapping
    def get_layer_id(self): return self.layer_cb.currentData()

# ── Login Dialog ──────────────────────────────────────────────────────────────
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome — Arch Manager")
        self.setMinimumWidth(360)
        # Coherent light dialog (the app opens in light mode); an explicit
        # QDialog background is required because the base QSS sets QWidget
        # backgrounds transparent — without it the labels were white-on-white.
        self.setStyleSheet(build_all_qss(LIGHT_CLR) +
                           f"QDialog{{background:{LIGHT_CLR['bg_root']};}}")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(24, 24, 24, 24); vl.setSpacing(16)

        title = QLabel("Who are you?"); title.setObjectName("h2")
        vl.addWidget(title)
        sub = QLabel("Your name will appear in the edit history for every change you make.")
        sub.setObjectName("muted"); sub.setWordWrap(True); vl.addWidget(sub)

        fl = QFormLayout(); fl.setSpacing(10)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("e.g. Maria Hassan")
        fl.addRow("Your name:", self.name_edit)

        # Colour picker row
        color_row = QHBoxLayout(); color_row.setSpacing(8)
        self._color = "#22c55e"
        self.color_btn = QPushButton("  Pick colour  ")
        self.color_btn.setStyleSheet(
            f"background:{self._color};color:#053019;border:none;border-radius:5px;"
            f"padding:7px 14px;font-weight:600;")
        self.color_btn.setCursor(Qt.PointingHandCursor)
        def pick_color():
            col = QColorDialog.getColor(QColor(self._color), self, "Choose your colour")
            if col.isValid():
                self._color = col.name()
                txt_col = '#ffffff' if col.lightness() < 128 else '#000000'
                self.color_btn.setStyleSheet(
                    f"background:{self._color};color:{txt_col};border:none;border-radius:5px;"
                    f"padding:7px 14px;font-weight:600;")
        self.color_btn.clicked.connect(pick_color)
        color_row.addWidget(self.color_btn); color_row.addStretch()
        fl.addRow("Your colour:", color_row)
        vl.addLayout(fl)

        # Remember checkbox
        self.remember_cb = QCheckBox("Remember me (save to settings)")
        self.remember_cb.setChecked(True); vl.addWidget(self.remember_cb)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Start session")
        bb.button(QDialogButtonBox.Ok).setObjectName("btn_primary")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        vl.addWidget(bb)

        # Load saved user
        try:
            import json as _json
            cfg = user_data_path('.user_config.json')
            if os.path.exists(cfg):
                with open(cfg) as _f:
                    data = _json.load(_f)
                self.name_edit.setText(data.get('name', ''))
                if data.get('color'):
                    self._color = data['color']
                    self.color_btn.setStyleSheet(
                        f"background:{self._color};color:#053019;border:none;border-radius:5px;"
                        f"padding:7px 14px;font-weight:600;")
        except Exception:
            pass

    def get_user(self):
        return self.name_edit.text().strip() or "Archaeologist"

    def get_color(self):
        return self._color

    def save_if_checked(self):
        if self.remember_cb.isChecked():
            try:
                import json as _json
                cfg = user_data_path('.user_config.json')
                with open(cfg, 'w') as _f:
                    _json.dump({'name': self.get_user(), 'color': self.get_color()}, _f)
            except Exception:
                pass


# ── Main window ───────────────────────────────────────────────────────────────
class _HistoryAndTabsMixin:
    """Edit-history logging plus Drawings/Media/Stats/Timeline/History tabs."""

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _log_history(self, action, table_name, record_id, details=""):
        """Write one row to edit_history — also keeps in-memory fallback."""
        import datetime as _dt
        ts=_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user=getattr(self,'_current_user','?')
        if not hasattr(self,'_mem_history'): self._mem_history=[]
        self._mem_history.append([ts,user,action,f"{table_name} #{record_id}: {str(details)[:60]}"])
        if len(self._mem_history)>500: self._mem_history=self._mem_history[-500:]
        hlyr = self._lyr(self.hist_layer_cb) if hasattr(self,'hist_layer_cb') else None
        if not hlyr: return
        from qgis.core import QgsFeature
        fields = hlyr.fields()
        feat = QgsFeature(fields)
        feat.setAttribute('timestamp', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        feat.setAttribute('user_name', getattr(self,'_current_user','?'))
        feat.setAttribute('action', action)
        feat.setAttribute('table_name', table_name)
        feat.setAttribute('record_id', str(record_id))
        feat.setAttribute('details', str(details)[:500])
        hlyr.startEditing(); hlyr.addFeature(feat); hlyr.commitChanges()

    # Patch _write_feat to log history
    def _write_feat(self, lyr, vals, fid=None):
        self._write_feat_base(lyr, vals, fid=fid)
        try:
            action = 'edit' if fid is not None else 'add'
            self._log_history(action, lyr.name(), fid or 'new', str(vals)[:200])
        except Exception: pass

    # Patch _delete_rows to log history
    def _delete_rows(self, tbl, lyr, pfx):
        rows=tbl.selectionModel().selectedRows()
        fids=tbl.property("_fids") or []
        to_del=[fids[r.row()] for r in rows if r.row()<len(fids)]
        self._delete_rows_base(tbl, lyr, pfx)
        try:
            for fid in to_del:
                self._log_history('delete', lyr.name(), fid, '')
        except Exception: pass

    # ── Drawings tab ─────────────────────────────────────────────────────────
    def _build_drawings_tab(self):
        from qgis.PyQt.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QFileDialog
        w=QWidget(); vl=QVBoxLayout(w)
        # Filter
        fr=QHBoxLayout(); fr.addWidget(QLabel("Context #:"))
        self.draw_filter=QComboBox(); self.draw_filter.setEditable(True); self.draw_filter.addItem("All")
        show=QPushButton("Show"); show.setObjectName("btn_secondary"); show.clicked.connect(self._reload_drawings)
        add=QPushButton("+ Attach drawing"); add.setObjectName("btn_primary"); add.clicked.connect(self._add_drawing)
        cad_btn=QPushButton("📐 Import CAD/DXF…"); cad_btn.setObjectName("btn_secondary"); cad_btn.clicked.connect(self._import_cad_drawing)
        edit=QPushButton("✏ Edit"); edit.setObjectName("btn_secondary"); edit.clicked.connect(self._edit_drawing)
        open_btn=QPushButton("📂 Open file"); open_btn.setObjectName("btn_secondary"); open_btn.clicked.connect(self._open_drawing_file)
        del_btn=QPushButton("🗑 Delete"); del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(lambda:self._delete_rows(self.draw_tbl,self._lyr(self.draw_layer_cb),'draw'))
        addcol=QPushButton("＋ Col"); addcol.setObjectName("btn_ghost"); addcol.clicked.connect(lambda:self._add_field(self._lyr(self.draw_layer_cb)))
        for b in [self.draw_filter,show,add,cad_btn,edit,open_btn,del_btn,addcol]: fr.addWidget(b)
        vl.addLayout(fr)
        self.draw_tbl=self._mktbl(); vl.addWidget(self.draw_tbl,1)
        return w

    def _reload_drawings(self, *a):
        lyr=self._lyr(self.draw_layer_cb)
        if not lyr: self.draw_tbl.setRowCount(0); return
        flt=self.draw_filter.currentText()
        fnames=[f.name() for f in lyr.fields()]
        self.draw_tbl.setColumnCount(len(fnames)); self.draw_tbl.setHorizontalHeaderLabels(fnames)
        feats=[]
        for feat in lyr.getFeatures():
            try:
                if flt!="All":
                    v=feat.attribute('context_num')
                    if str(v)!=flt: continue
            except Exception: pass
            feats.append(feat)
        self.draw_tbl.setRowCount(len(feats)); self.draw_tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn)
                self.draw_tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    def _add_drawing(self):
        lyr=self._lyr(self.draw_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Set drawings layer first."); return
        path,_=QFileDialog.getOpenFileName(self,"Attach drawing","","All files (*.*)")
        if not path: return
        defaults={'file_path':path,'context_num':self.draw_filter.currentText() if self.draw_filter.currentText()!="All" else ''}
        dlg=RecordDialog(self._schema_for(lyr),defaults=defaults,title="Attach Drawing",parent=self)
        if dlg.exec_()!=QDialog.Accepted: return
        self._write_feat(lyr,dlg.values()); self._reload_drawings()

    def _edit_drawing(self):
        self._edit_row('draw')

    # patch _edit_row to handle 'draw'
    def _edit_row_ext_impl(self, pfx):
        if pfx=='draw':
            tbl=self.draw_tbl; lyr=self._lyr(self.draw_layer_cb)
            if not lyr: return
            rows=tbl.selectionModel().selectedRows()
            if not rows: QMessageBox.information(self,"","Select a row first."); return
            ri=rows[0].row(); fids=tbl.property("_fids") or []
            if ri>=len(fids): return
            fid=fids[ri]; feat=lyr.getFeature(fid)
            defs={f.name():feat.attribute(f.name()) for f in lyr.fields()}
            dlg=RecordDialog(self._schema_for(lyr),defaults=defs,title="Edit Drawing",parent=self)
            if dlg.exec_()!=QDialog.Accepted: return
            self._write_feat(lyr,dlg.values(),fid=fid); self._reload_drawings()
        else: self._edit_row_base(pfx)

    def _open_drawing_file(self):
        rows=self.draw_tbl.selectionModel().selectedRows()
        if not rows: return
        ri=rows[0].row(); lyr=self._lyr(self.draw_layer_cb)
        if not lyr: return
        fids=self.draw_tbl.property("_fids") or []
        if ri>=len(fids): return
        feat=lyr.getFeature(fids[ri])
        try: path=str(feat.attribute('file_path') or '')
        except Exception: path=''
        if path and os.path.exists(path):
            import subprocess
            subprocess.Popen(['explorer' if os.name=='nt' else 'xdg-open', path])
        else:
            QMessageBox.warning(self,"","File not found: "+path)

    # ── CAD import ───────────────────────────────────────────────────────────
    def _import_cad_drawing(self):
        import datetime as _dt
        from qgis.PyQt.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, "Import CAD / DXF Drawing", "",
            "CAD Files (*.dxf *.dwg *.dgn *.plt);;All files (*.*)")
        if not path: return
        lyr = self._lyr(self.draw_layer_cb)
        if not lyr:
            QMessageBox.warning(self, "No drawings layer",
                "Connect a site first so the drawings layer is available.")
            return
        ctx_text, ok = QInputDialog.getText(
            self, "Context number",
            "Context number this drawing belongs to\n(leave blank if not applicable):")
        ctx_num = ctx_text.strip() if ok else ''
        scale_text, ok2 = QInputDialog.getText(
            self, "Scale",
            "Drawing scale (e.g. 1:20 — leave blank if unknown):")
        scale = scale_text.strip() if ok2 else ''
        today = _dt.date.today().isoformat()
        vals = {
            'drawing_type': 'CAD',
            'file_path': path,
            'context_num': ctx_num,
            'scale': scale,
            'notes': '',
            'date_recorded': today,
        }
        try:
            self._write_feat(lyr, vals)
            self._reload_drawings()
            try: self._log_history('import_cad', os.path.basename(path), 0, f"context {ctx_num or 'N/A'}")
            except Exception: pass
            if path.lower().endswith('.dxf'):
                from qgis.core import QgsVectorLayer, QgsProject
                vlyr = QgsVectorLayer(path, os.path.splitext(os.path.basename(path))[0], 'ogr')
                if vlyr.isValid():
                    QgsProject.instance().addMapLayer(vlyr)
                    self._msg(f"CAD drawing imported and loaded: {os.path.basename(path)}")
                else:
                    self._msg(f"CAD drawing recorded: {os.path.basename(path)}")
            else:
                self._msg(f"CAD drawing recorded: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Import error", str(e))

    # ── Gallery persistence ──────────────────────────────────────────────────
    def _get_media_json_path(self):
        for cb_name in ['ctx_layer_cb', 'hist_layer_cb', 'pot_layer_cb']:
            cb = getattr(self, cb_name, None)
            if cb is None: continue
            lyr = self._lyr(cb)
            if not lyr: continue
            src = lyr.dataProvider().dataSourceUri()
            gpkg = src.split('|')[0]
            if gpkg.endswith('.gpkg') and os.path.exists(gpkg):
                return gpkg + '.media.json'
        return None

    def _save_gallery_registry(self):
        path = self._get_media_json_path()
        if not path: return
        try:
            import json
            if not hasattr(self, '_photo_registry'):
                self._photo_registry = {}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._photo_registry, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_gallery_registry(self):
        path = self._get_media_json_path()
        if not path or not os.path.exists(path): return
        try:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                reg = json.load(f)
        except Exception:
            return
        if not isinstance(reg, dict): return
        self._photo_registry = reg
        from qgis.PyQt.QtWidgets import QListWidgetItem, QLabel
        from qgis.PyQt.QtGui import QPixmap, QIcon
        from qgis.PyQt.QtCore import Qt as _Qt
        galleries = getattr(self, '_gallery_widgets', {})
        for category, items in reg.items():
            gallery = galleries.get(category)
            if gallery is None: continue
            gallery.clear()
            files = []
            for entry in items:
                fpath = entry.get('path', '')
                caption = entry.get('caption', os.path.basename(fpath) if fpath else '')
                context = entry.get('context', '')
                files.append(fpath)
                item = QListWidgetItem()
                display = f"{caption}\n📍 Context {context}" if context else caption
                item.setText(display)
                item.setToolTip(fpath + (f"\n📍 Context {context}" if context else ''))
                px = QPixmap(fpath)
                if not px.isNull():
                    item.setIcon(QIcon(px.scaled(120, 90, _Qt.KeepAspectRatio, _Qt.SmoothTransformation)))
                else:
                    icon_lbl = "📄" if fpath.lower().endswith(('.pdf', '.docx', '.xlsx')) else "📐"
                    item.setText(f"{icon_lbl}\n{display}")
                gallery.addItem(item)
            gallery.setProperty("_files", files)
            parent = gallery.parent()
            if parent:
                for lbl in parent.findChildren(QLabel, "statusMsg"):
                    lbl.setText(f"{len(files)} file(s) attached" if files else
                                "No files added — click ＋ Add file to attach photos")
                    break

    # ── Statistics tab ────────────────────────────────────────────────────────
    def _build_stats_tab(self):
        from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                          QPushButton, QScrollArea, QLabel, QFrame)
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        vl.addWidget(ContentTitle("Statistics",
                                  "Record counts and distributions across context types, periods and find categories"))

        ab = QWidget(); ab.setObjectName("actionBar")
        hdr = QHBoxLayout(ab); hdr.setContentsMargins(24, 6, 24, 6); hdr.setSpacing(8)
        refresh = QPushButton("↻ Refresh statistics"); refresh.setObjectName("btn_secondary")
        refresh.clicked.connect(self._refresh_stats)
        hdr.addWidget(refresh); hdr.addStretch()
        vl.addWidget(ab)

        self._stats_scroll = QScrollArea()
        self._stats_scroll.setWidgetResizable(True)
        self._stats_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._stats_inner = QWidget(); self._stats_inner.setStyleSheet("background:transparent;")
        self._stats_vl = QVBoxLayout(self._stats_inner)
        self._stats_vl.setContentsMargins(32, 20, 32, 32); self._stats_vl.setSpacing(4)
        ph = QLabel("Click  ↻ Refresh statistics  to generate the charts")
        ph.setObjectName("emptyState"); ph.setAlignment(Qt.AlignCenter)
        self._stats_vl.addWidget(ph); self._stats_vl.addStretch()
        self._stats_scroll.setWidget(self._stats_inner)
        vl.addWidget(self._stats_scroll, 1)
        return w

    def _refresh_stats(self):
        from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
        # Clear
        while self._stats_vl.count():
            it = self._stats_vl.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        _tc = getattr(self, '_current_theme', LIGHT_CLR)
        palette = ['#5a8abf','#c8a860','#7ab87a','#e07820','#a050a0','#60b0b0',
                   '#3db5c8','#d4845a','#88b04b','#b07cc6']

        datasets = [
            ("Context Types",      self._count_by_field(self.ctx_layer_cb, 'type')),
            ("Pottery Forms",      self._count_by_field(self.pot_layer_cb, 'form')),
            ("Artifact Types",     self._count_by_field(self.art_layer_cb, 'type')),
            ("Periods — Contexts", self._count_by_field(self.ctx_layer_cb, 'period')),
        ]

        has_data = False
        for ds_idx, (title, counts) in enumerate(datasets):
            if not counts:
                continue
            has_data = True

            # Section header with record count
            sec_w = QWidget(); sec_w.setStyleSheet("background:transparent;")
            sec_h = QHBoxLayout(sec_w); sec_h.setContentsMargins(0, 16 if ds_idx else 0, 0, 6)
            sec_lbl = QLabel(title); sec_lbl.setObjectName("h4")
            total_lbl = QLabel(f"{sum(counts.values())} records")
            total_lbl.setObjectName("mutedXs")
            sec_h.addWidget(sec_lbl); sec_h.addStretch(); sec_h.addWidget(total_lbl)
            self._stats_vl.addWidget(sec_w)

            mx = max(counts.values())
            total = sum(counts.values())
            sorted_items = sorted(counts.items(), key=lambda x: -x[1])[:15]

            for ci, (label, count) in enumerate(sorted_items):
                color = palette[ci % len(palette)]

                row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
                row_h = QHBoxLayout(row_w)
                row_h.setContentsMargins(0, 2, 0, 2); row_h.setSpacing(10)

                # Category label (right-aligned, fixed width)
                name_lbl = QLabel(str(label)[:26])
                name_lbl.setFixedWidth(190)
                name_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                name_lbl.setObjectName("bodyText")
                row_h.addWidget(name_lbl)

                # Bar — fills proportional width using layout stretch
                track = QWidget(); track.setStyleSheet("background:transparent;")
                track_h = QHBoxLayout(track)
                track_h.setContentsMargins(0, 0, 0, 0); track_h.setSpacing(0)
                bar = QFrame(); bar.setFixedHeight(22)
                bar.setStyleSheet(
                    f"background:{color};border-radius:4px;")
                pct_int = max(2, int(count * 1000 / mx))
                rest = max(0, 1000 - pct_int)
                track_h.addWidget(bar, pct_int)
                if rest:
                    sp = QWidget(); sp.setStyleSheet("background:transparent;")
                    track_h.addWidget(sp, rest)
                row_h.addWidget(track, 1)

                # Count + percentage
                cnt_lbl = QLabel(f"{count}  ({100*count//total}%)")
                cnt_lbl.setObjectName("mutedXs")
                cnt_lbl.setFixedWidth(80)
                row_h.addWidget(cnt_lbl)

                self._stats_vl.addWidget(row_w)

            # Thin separator
            sep = QFrame(); sep.setObjectName("hsep")
            sep_wrap = QWidget(); sep_wrap.setStyleSheet("background:transparent;")
            sep_vl = QVBoxLayout(sep_wrap); sep_vl.setContentsMargins(0, 8, 0, 0)
            sep_vl.addWidget(sep)
            self._stats_vl.addWidget(sep_wrap)

        if not has_data:
            empty = QLabel("No data — connect layers and load a project first")
            empty.setObjectName("emptyState"); empty.setAlignment(Qt.AlignCenter)
            self._stats_vl.addWidget(empty)

        self._stats_vl.addStretch()

    def _count_by_field(self, layer_cb, field_name):
        lyr=self._lyr(layer_cb)
        if not lyr: return {}
        fnames=[f.name() for f in lyr.fields()]
        if field_name not in fnames: return {}
        counts={}
        for feat in lyr.getFeatures():
            v=str(feat.attribute(field_name) or 'Unknown').strip()
            if v.lower() in ('null','none',''): v='Unknown'
            counts[v]=counts.get(v,0)+1
        return counts

    # ── Timeline tab ─────────────────────────────────────────────────────────
    def _build_timeline_tab(self):
        from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                          QPushButton, QScrollArea, QLabel, QFrame)
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        vl.addWidget(ContentTitle("Timeline",
                                  "Stratigraphic period sequence — contexts, pottery and artifacts by era"))

        ab = QWidget(); ab.setObjectName("actionBar")
        hdr = QHBoxLayout(ab); hdr.setContentsMargins(24, 6, 24, 6); hdr.setSpacing(8)
        refresh = QPushButton("↻ Build timeline"); refresh.setObjectName("btn_secondary")
        refresh.clicked.connect(self._refresh_timeline)
        hdr.addWidget(refresh); hdr.addStretch()
        vl.addWidget(ab)

        self._tl_scroll = QScrollArea()
        self._tl_scroll.setWidgetResizable(True)
        self._tl_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._tl_inner = QWidget(); self._tl_inner.setStyleSheet("background:transparent;")
        self._tl_vl = QVBoxLayout(self._tl_inner)
        self._tl_vl.setContentsMargins(32, 20, 32, 32); self._tl_vl.setSpacing(4)
        ph = QLabel("Click  ↻ Build timeline  to generate the period chart")
        ph.setObjectName("emptyState"); ph.setAlignment(Qt.AlignCenter)
        self._tl_vl.addWidget(ph); self._tl_vl.addStretch()
        self._tl_scroll.setWidget(self._tl_inner)
        vl.addWidget(self._tl_scroll, 1)
        return w

    PERIOD_ORDER=[
        'Prehistoric','Early Bronze Age','Middle Bronze Age','Late Bronze Age',
        'Iron Age','Persian','Hellenistic','Roman','Byzantine','Early Islamic',
        'Crusader','Medieval','Mamluk','Ottoman','Modern','Unknown'
    ]
    PERIOD_COLORS=[
        '#8B7355','#CD853F','#DAA520','#B8860B','#808000','#6B8E23','#2E8B57',
        '#20B2AA','#4169E1','#6A5ACD','#9932CC','#C71585','#DC143C','#FF8C00',
        '#888','#999'
    ]

    def _refresh_timeline(self):
        from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
        # Clear
        while self._tl_vl.count():
            it = self._tl_vl.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        _tc = getattr(self, '_current_theme', LIGHT_CLR)

        # Collect period counts from all layers
        period_counts = {}
        for lcb, nf in [(self.ctx_layer_cb, 'period'),
                        (self.pot_layer_cb,  'period'),
                        (self.art_layer_cb,  'period')]:
            lyr = self._lyr(lcb)
            if not lyr: continue
            fnames = [f.name() for f in lyr.fields()]
            if nf not in fnames:
                nf = next((f for f in fnames if 'period' in f.lower() or 'date' in f.lower()), None)
                if not nf: continue
            for feat in lyr.getFeatures():
                v = str(feat.attribute(nf) or '').strip()
                if v.lower() in ('null', 'none', ''): continue
                period_counts[v] = period_counts.get(v, 0) + 1

        if not period_counts:
            empty = QLabel("No period data found — map the period fields in Layer Configuration")
            empty.setObjectName("emptyState"); empty.setAlignment(Qt.AlignCenter)
            self._tl_vl.addWidget(empty); self._tl_vl.addStretch()
            return

        def sort_key(p):
            try: return PERIOD_ORDER.index(p)
            except Exception: return len(PERIOD_ORDER) + (ord(p[0]) if p else 999)

        sorted_periods = sorted(period_counts.keys(), key=sort_key)
        total = sum(period_counts.values())
        mx = max(period_counts.values())

        # Summary row
        summ_w = QWidget(); summ_w.setStyleSheet("background:transparent;")
        summ_h = QHBoxLayout(summ_w); summ_h.setContentsMargins(0, 0, 0, 12)
        summ_lbl = QLabel(f"  {total} total records  ·  {len(sorted_periods)} periods")
        summ_lbl.setObjectName("muted")
        summ_h.addWidget(summ_lbl); summ_h.addStretch()
        self._tl_vl.addWidget(summ_w)

        for pi, period in enumerate(sorted_periods):
            count = period_counts[period]
            color = PERIOD_COLORS[pi % len(PERIOD_COLORS)]

            row_w = QWidget(); row_w.setStyleSheet("background:transparent;")
            row_h = QHBoxLayout(row_w)
            row_h.setContentsMargins(0, 2, 0, 2); row_h.setSpacing(0)

            # Left colour strip (period identity)
            strip = QFrame(); strip.setFixedWidth(5); strip.setFixedHeight(30)
            strip.setStyleSheet(f"background:{color};border-radius:2px;")
            row_h.addWidget(strip)
            row_h.addSpacing(10)

            # Period label
            per_lbl = QLabel(period)
            per_lbl.setFixedWidth(210)
            per_lbl.setObjectName("bodyText")
            per_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row_h.addWidget(per_lbl)

            # Proportional bar track
            track = QWidget(); track.setStyleSheet("background:transparent;")
            track_h = QHBoxLayout(track)
            track_h.setContentsMargins(0, 4, 0, 4); track_h.setSpacing(0)
            bar = QFrame()
            bar.setStyleSheet(
                f"background:{color};border-radius:4px;opacity:0.85;")
            pct_int = max(2, int(count * 1000 / mx))
            rest = max(0, 1000 - pct_int)
            track_h.addWidget(bar, pct_int)
            if rest:
                sp = QWidget(); sp.setStyleSheet("background:transparent;")
                track_h.addWidget(sp, rest)
            row_h.addWidget(track, 1)
            row_h.addSpacing(10)

            # Count + %
            cnt_lbl = QLabel(f"{count}  ({100*count//total}%)")
            cnt_lbl.setObjectName("mutedXs")
            cnt_lbl.setFixedWidth(90)
            cnt_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row_h.addWidget(cnt_lbl)

            self._tl_vl.addWidget(row_w)

        self._tl_vl.addStretch()

    # ── History tab ───────────────────────────────────────────────────────────
    def _build_history_tab(self):
        from qgis.PyQt.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QLabel
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        vl.addWidget(ContentTitle("Edit History",
                                  "Audit trail of all data changes in this project"))

        # Action bar
        ab = QWidget(); ab.setObjectName("actionBar")
        hdr = QHBoxLayout(ab); hdr.setContentsMargins(24, 6, 24, 6); hdr.setSpacing(8)

        # User pill
        user_lbl = QLabel("User:"); user_lbl.setObjectName("mutedXs")
        self._hist_dot = QLabel("●"); self._hist_dot.setObjectName("accentLabel")
        self.user_input = QLineEdit(self._current_user)
        self.user_input.setMaximumWidth(160); self.user_input.setObjectName("histUserInput")
        self.user_input.textChanged.connect(lambda t: setattr(self, '_current_user', t))

        refresh = QPushButton("↻ Refresh"); refresh.setObjectName("btn_secondary")
        refresh.clicked.connect(self._load_history)
        clear = QPushButton("🗑 Clear history"); clear.setObjectName("btn_danger")
        clear.clicked.connect(self._clear_history)

        hdr.addWidget(self._hist_dot); hdr.addWidget(user_lbl)
        hdr.addWidget(self.user_input); hdr.addWidget(refresh)
        hdr.addWidget(clear); hdr.addStretch()
        vl.addWidget(ab)

        tbl_w = QWidget(); tbl_w.setStyleSheet("background:transparent;")
        tbl_vl = QVBoxLayout(tbl_w); tbl_vl.setContentsMargins(16, 8, 16, 16)
        self.hist_tbl = self._mktbl()
        tbl_vl.addWidget(self.hist_tbl)
        vl.addWidget(tbl_w, 1)
        return w

    def _load_history(self):
        lyr=self._lyr(self.hist_layer_cb)
        if not lyr:
            # Show in-memory log if no layer connected
            mem=getattr(self,'_mem_history',[])
            self.hist_tbl.setColumnCount(4)
            self.hist_tbl.setHorizontalHeaderLabels(["Timestamp","User","Action","Details"])
            self.hist_tbl.setRowCount(max(1,len(mem)))
            if not mem:
                self.hist_tbl.setItem(0,0,QTableWidgetItem("No edit_history layer connected"))
                self.hist_tbl.setItem(0,1,QTableWidgetItem("Create a project or connect the edit_history layer"))
                self.hist_tbl.setSpan(0,0,1,1)
                for c in range(1,4): self.hist_tbl.setItem(0,c,QTableWidgetItem(""))
            else:
                for ri,row in enumerate(reversed(mem)):
                    for ci,v in enumerate(row): self.hist_tbl.setItem(ri,ci,QTableWidgetItem(str(v)))
            return
        fnames=[f.name() for f in lyr.fields()]
        feats=list(lyr.getFeatures())
        feats.sort(key=lambda f: str(f.attribute('timestamp') or ''),reverse=True)
        self.hist_tbl.setColumnCount(len(fnames)); self.hist_tbl.setHorizontalHeaderLabels(fnames)
        if not feats:
            self.hist_tbl.setRowCount(1)
            self.hist_tbl.setItem(0,0,QTableWidgetItem("No history recorded yet — actions will appear here as you add/edit data"))
            for c in range(1,len(fnames)): self.hist_tbl.setItem(0,c,QTableWidgetItem(""))
            return
        self.hist_tbl.setRowCount(len(feats)); self.hist_tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn)
                self.hist_tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    def _clear_history(self):
        lyr=self._lyr(self.hist_layer_cb)
        if not lyr: return
        reply=QMessageBox.question(self,"Clear history","Delete all history records?",
            QMessageBox.Yes|QMessageBox.No)
        if reply!=QMessageBox.Yes: return
        lyr.startEditing()
        lyr.deleteFeatures([f.id() for f in lyr.getFeatures()])
        lyr.commitChanges(); self._load_history()

    # ── Backup ───────────────────────────────────────────────────────────────
    def _backup_project(self):
        gpkg=None
        lyr=self._lyr(self.ctx_layer_cb)
        if lyr:
            uri=lyr.dataProvider().dataSourceUri()
            if '|' in uri: gpkg=uri.split('|')[0]
        if not gpkg or not os.path.exists(gpkg):
            gpkg,_=QFileDialog.getOpenFileName(self,"Select GeoPackage to back up","","GeoPackage (*.gpkg)")
            if not gpkg: return
        ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup=gpkg.replace('.gpkg',f'_backup_{ts}.gpkg')
        shutil.copy2(gpkg,backup)
        # Also back up the media sidecar if it exists
        media_src = gpkg + '.media.json'
        if os.path.exists(media_src):
            shutil.copy2(media_src, backup + '.media.json')
        self._msg(f"Backup saved: {os.path.basename(backup)}")
        QMessageBox.information(self,"Backup complete",f"Saved to:\n{backup}")

    # ── Per-context PDF ────────────────────────────────────────────────────────
    def _export_context_pdf(self):
        num_str=self.ctxdet_cb.currentText().strip() if hasattr(self,'ctxdet_cb') else ''
        if not num_str: QMessageBox.warning(self,"","Open Context View tab and select a context first."); return
        try: num=int(num_str)
        except Exception: QMessageBox.warning(self,"","Context number must be integer."); return
        path,_=QFileDialog.getSaveFileName(self,f"Export Context {num} PDF",
            f"context_{num}.pdf","PDF (*.pdf)")
        if not path: return
        from .pdf_export import _export_context_page
        ok=_export_context_page(path,num,self)
        if ok: self._msg(f"Context {num} exported to PDF")
        else: QMessageBox.warning(self,"","Export failed")

    # ── Load all extension ─────────────────────────────────────────────────────
    def _load_all(self):
        self._load_all_base()
        if hasattr(self,'draw_filter'):
            self.draw_filter.clear(); self.draw_filter.addItem("All")
            for n in sorted(self.ctx_data.keys()): self.draw_filter.addItem(str(n))
        if hasattr(self,'hist_tbl'): self._load_history()
        if hasattr(self,'_crate_tiles_layout'): self._reload_crates()



# ── Archaeologist Filter tab (appended) ──────────────────────────────────────
class _ArchaeologistMixin:
    """Archaeologist filter tab."""

    def _build_archaeologist_tab(self):
        from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        vl.addWidget(ContentTitle("By Archaeologist",
                                  "Filter all data by recorder — see every record made by one person"))

        body = QWidget(); body.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(body); bv.setContentsMargins(32, 12, 32, 16); bv.setSpacing(12)

        # Info
        info_frame = QFrame(); info_frame.setObjectName("infoCard")
        il = QHBoxLayout(info_frame); il.setContentsMargins(14, 10, 14, 10)
        info = QLabel("Select which field holds the archaeologist's initials, then pick a name. "
                      "All tables below update to show only their records.")
        info.setWordWrap(True)
        il.addWidget(info)
        bv.addWidget(info_frame)

        # Field pickers per layer
        cfg_grp = QGroupBox("Which field identifies the recorder?")
        cf = QFormLayout(cfg_grp); cf.setSpacing(6); cf.setContentsMargins(16, 10, 16, 10)
        self.arch_ctx_field   = QComboBox(); self.arch_ctx_field.setEditable(True)
        self.arch_pot_field   = QComboBox(); self.arch_pot_field.setEditable(True)
        self.arch_art_field   = QComboBox(); self.arch_art_field.setEditable(True)
        self.arch_ske_field   = QComboBox(); self.arch_ske_field.setEditable(True)
        for cb in [self.arch_ctx_field, self.arch_pot_field, self.arch_art_field, self.arch_ske_field]:
            cb.addItem("— none —")
        cf.addRow(QLabel("Context field:"),  self.arch_ctx_field)
        cf.addRow(QLabel("Pottery field:"),  self.arch_pot_field)
        cf.addRow(QLabel("Artifact field:"), self.arch_art_field)
        cf.addRow(QLabel("Skeleton field:"), self.arch_ske_field)
        bv.addWidget(cfg_grp)

        # Person selector + action buttons
        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        sel_lbl = QLabel("Archaeologist:"); sel_lbl.setObjectName("mutedXs")
        self.arch_person_cb = QComboBox(); self.arch_person_cb.setEditable(True)
        self.arch_person_cb.setMinimumWidth(180)
        scan_btn = QPushButton("↻ Scan names"); scan_btn.setObjectName("btn_ghost")
        scan_btn.clicked.connect(self._scan_archaeologists)
        filter_btn = QPushButton("🔍 Filter tables"); filter_btn.setObjectName("btn_primary")
        filter_btn.clicked.connect(self._apply_archaeologist_filter)
        clear_btn = QPushButton("✕ Clear"); clear_btn.setObjectName("btn_danger")
        clear_btn.clicked.connect(self._clear_archaeologist_filter)
        for w_ in (sel_lbl, self.arch_person_cb, scan_btn, filter_btn, clear_btn):
            sel_row.addWidget(w_)
        sel_row.addStretch()
        bv.addLayout(sel_row)

        self.arch_status = QLabel(""); self.arch_status.setObjectName("statusMsg")
        bv.addWidget(self.arch_status)
        vl.addWidget(body)

        # Results sub-tabs
        self.arch_tabs = QTabWidget(); self.arch_tabs.setObjectName("subTabs")
        self.arch_ctx_tbl = self._mktbl(); self.arch_tabs.addTab(self.arch_ctx_tbl,  "📋 Contexts")
        self.arch_pot_tbl = self._mktbl(); self.arch_tabs.addTab(self.arch_pot_tbl,  "🏺 Pottery")
        self.arch_art_tbl = self._mktbl(); self.arch_tabs.addTab(self.arch_art_tbl,  "⚱ Artifacts")
        self.arch_ske_tbl = self._mktbl(); self.arch_tabs.addTab(self.arch_ske_tbl,  "💀 Skeletons")
        vl.addWidget(self.arch_tabs, 1)
        return w


    def _populate_arch_fields(self):
        """Fill the field combos with fields from each layer."""
        for lyr_cb, field_cb, candidates in [
            (self.ctx_layer_cb, self.arch_ctx_field,
             ['initials','recorded_by','user','archaeologist','fieldworker','recorder','by','user_name']),
            (self.pot_layer_cb, self.arch_pot_field,
             ['initials','recorded_by','user','archaeologist','fieldworker','recorder','by','user_name']),
            (self.art_layer_cb, self.arch_art_field,
             ['initials','recorded_by','user','archaeologist','fieldworker','recorder','by','user_name']),
            (self.ske_layer_cb, self.arch_ske_field,
             ['initials','recorded_by','user','archaeologist','fieldworker','recorder','by','user_name']),
        ]:
            lyr = self._lyr(lyr_cb)
            if not lyr: continue
            fnames = [f.name() for f in lyr.fields()]
            field_cb.clear(); field_cb.addItem("— none —"); field_cb.addItems(fnames)
            for c in candidates:
                for fn in fnames:
                    if c.lower() in fn.lower():
                        idx = field_cb.findText(fn)
                        if idx >= 0: field_cb.setCurrentIndex(idx); break

    def _scan_archaeologists(self):
        """Collect all unique values from the recorder fields."""
        self._populate_arch_fields()
        people = set()
        for lyr_cb, field_cb in [
            (self.ctx_layer_cb, self.arch_ctx_field),
            (self.pot_layer_cb, self.arch_pot_field),
            (self.art_layer_cb, self.arch_art_field),
            (self.ske_layer_cb, self.arch_ske_field),
        ]:
            lyr = self._lyr(lyr_cb)
            fn  = field_cb.currentText()
            if not lyr or fn == "— none —": continue
            for feat in lyr.getFeatures():
                v = str(feat.attribute(fn) or "").strip()
                if v and v.lower() not in ("null","none",""): people.add(v)
        self.arch_person_cb.clear()
        for p in sorted(people): self.arch_person_cb.addItem(p)
        self.arch_status.setText(f"Found {len(people)} archaeologist(s): {', '.join(sorted(people))}")

    def _apply_archaeologist_filter(self):
        person = self.arch_person_cb.currentText().strip()
        if not person: QMessageBox.warning(self,"","Select or type an archaeologist name/initials."); return

        total = 0
        for lyr_cb, field_cb, tbl, tbl_name in [
            (self.ctx_layer_cb, self.arch_ctx_field, self.arch_ctx_tbl,  "contexts"),
            (self.pot_layer_cb, self.arch_pot_field, self.arch_pot_tbl,  "pottery"),
            (self.art_layer_cb, self.arch_art_field, self.arch_art_tbl,  "artifacts"),
            (self.ske_layer_cb, self.arch_ske_field, self.arch_ske_tbl,  "skeletons"),
        ]:
            tbl.clearContents(); tbl.setRowCount(0)
            lyr = self._lyr(lyr_cb); fn = field_cb.currentText()
            if not lyr or fn == "— none —":
                tbl.setColumnCount(1)
                tbl.setHorizontalHeaderLabels([f"No layer/field set for {tbl_name}"])
                continue
            fnames = [f.name() for f in lyr.fields()]
            tbl.setColumnCount(len(fnames)); tbl.setHorizontalHeaderLabels(fnames)
            feats = [f for f in lyr.getFeatures()
                     if str(f.attribute(fn) or "").strip().lower() == person.lower()]
            tbl.setRowCount(len(feats)); tbl.setProperty("_fids",[f.id() for f in feats])
            for ri, feat in enumerate(feats):
                for ci, fname in enumerate(fnames):
                    v = feat.attribute(fname)
                    tbl.setItem(ri, ci, QTableWidgetItem(fmt_cell(v)))
            total += len(feats)

        self.arch_status.setText(f"Showing {total} records for '{person}'")
        self._msg(f"Filter: {total} records for {person}")

    def _clear_archaeologist_filter(self):
        for tbl in [self.arch_ctx_tbl, self.arch_pot_tbl,
                    self.arch_art_tbl, self.arch_ske_tbl]:
            tbl.clearContents(); tbl.setRowCount(0)
        self.arch_status.setText("Filter cleared")



# ── Grid Map Tab ──────────────────────────────────────────────────────────────
class _GridMapMixin:
    """Excavation grid layer + grid map tab."""

    def _create_grid_layer(self):
        """Create excavation_grids polygon layer in existing GeoPackage."""
        path,_=QFileDialog.getOpenFileName(self,"Select GeoPackage","","GeoPackage (*.gpkg)")
        if not path: return
        schema=SCHEMAS.get('excavation_grids',[])
        fields=QgsFields()
        for fname,ftype in schema: fields.append(QgsField(fname,ftype))
        opts=QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName='GPKG'; opts.fileEncoding='UTF-8'
        opts.layerName='excavation_grids'
        opts.actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.create(path,fields,QgsWkbTypes.Polygon,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsCoordinateTransformContext(),opts)
        uri=f"{path}|layername=excavation_grids"
        site=getattr(self,'_current_site','SITE')
        lyr=QgsVectorLayer(uri,f"{site}_excavation_grids",'ogr')
        if lyr.isValid():
            # Apply a nice default style
            from qgis.core import QgsSimpleFillSymbolLayer, QgsSingleSymbolRenderer, QgsSymbol
            sym=QgsSymbol.defaultSymbol(QgsWkbTypes.PolygonGeometry)
            sym.setOpacity(0.6)
            fl=sym.symbolLayer(0)
            fl.setColor(QColor(180,210,240,140))
            fl.setStrokeColor(QColor(30,80,160))
            fl.setStrokeWidth(0.8)
            lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            # Label by grid_name
            from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat
            lbl=QgsPalLayerSettings()
            lbl.fieldName='grid_name'; lbl.enabled=True
            fmt=QgsTextFormat(); fmt.setSize(9)
            lbl.setFormat(fmt)
            lyr.setLabeling(QgsVectorLayerSimpleLabeling(lbl))
            lyr.setLabelsEnabled(True)
            QgsProject.instance().addMapLayer(lyr)
            self._refresh_combos()
            for i in range(self.grid_layer_cb.count()):
                if 'excavation_grids' in self.grid_layer_cb.itemText(i).lower():
                    self.grid_layer_cb.setCurrentIndex(i); break
            self._msg("excavation_grids layer created and styled")
            QMessageBox.information(self,"Done",
                "Excavation grids layer created.\n\n"
                "Use 'Start drawing' to digitize grids on the map,\n"
                "or toggle layer editing in QGIS and use the polygon digitizing tool.")
        else:
            QMessageBox.warning(self,"","Failed to create layer.")

    def _build_grid_map_tab(self):
        from qgis.PyQt.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QGroupBox, QFormLayout, QLineEdit, QDoubleSpinBox, QSplitter
        )
        w=QWidget(); vl=QVBoxLayout(w); vl.setContentsMargins(6,6,6,6); vl.setSpacing(6)

        # Header
        hdr=QLabel("⬡  Excavation Grid Map")
        hdr.setObjectName("h3")
        vl.addWidget(hdr)

        # Top controls
        top=QHBoxLayout()
        draw_btn=QPushButton("✏  Start drawing grid on map")
        draw_btn.setObjectName("btn_primary")
        draw_btn.clicked.connect(self._start_grid_drawing)
        stop_btn=QPushButton("⏹ Stop drawing")
        stop_btn.setObjectName("btn_danger")
        stop_btn.clicked.connect(self._stop_grid_drawing)
        zoom_btn=QPushButton("🔍 Zoom to grids")
        zoom_btn.setObjectName("btn_ghost")
        zoom_btn.clicked.connect(self._zoom_to_grids)
        export_btn=QPushButton("📄 Export grid map")
        export_btn.setObjectName("btn_purple")
        export_btn.clicked.connect(self._export_grid_map)
        for b in [draw_btn,stop_btn,zoom_btn,export_btn]: top.addWidget(b)
        vl.addLayout(top)

        # Split: form left, grid table right
        split=QSplitter(Qt.Horizontal)

        # Left: metadata form for new/selected grid
        form_w=QWidget(); form_v=QVBoxLayout(form_w)
        form_v.addWidget(QLabel("<b>Grid metadata</b><br><small>Fill in then click Add Grid</small>"))
        ff=QFormLayout(); ff.setSpacing(4)
        self.grid_name_input  =QLineEdit(); self.grid_name_input.setPlaceholderText("e.g. Square A1")
        self.grid_site_input  =QLineEdit(); self.grid_site_input.setText(getattr(self,'_current_site',''))
        self.grid_season_input=QLineEdit(); self.grid_season_input.setPlaceholderText("e.g. 2025")
        self.grid_elev_input  =QDoubleSpinBox(); self.grid_elev_input.setRange(-200,4000); self.grid_elev_input.setDecimals(1)
        self.grid_notes_input =QLineEdit()
        ff.addRow("Grid name:", self.grid_name_input)
        ff.addRow("Site:",      self.grid_site_input)
        ff.addRow("Season:",    self.grid_season_input)
        ff.addRow("Elevation:", self.grid_elev_input)
        ff.addRow("Notes:",     self.grid_notes_input)
        form_v.addLayout(ff)
        add_btn=QPushButton("＋ Add grid (draws next polygon)")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add_grid_record)
        form_v.addWidget(add_btn)
        edit_sel=QPushButton("✏ Edit selected grid")
        edit_sel.setObjectName("btn_secondary")
        edit_sel.clicked.connect(lambda:self._edit_row('grid'))
        del_sel=QPushButton("🗑 Delete selected"); del_sel.setObjectName("btn_danger")
        del_sel.clicked.connect(lambda:self._delete_rows(self.grid_tbl,self._lyr(self.grid_layer_cb),'grid'))
        row2=QHBoxLayout(); row2.addWidget(edit_sel); row2.addWidget(del_sel)
        form_v.addLayout(row2); form_v.addStretch()
        split.addWidget(form_w)

        # Right: grid table
        tbl_w=QWidget(); tbl_v=QVBoxLayout(tbl_w)
        tbl_v.addWidget(QLabel("<b>Recorded grids</b>"))
        self.grid_tbl=self._mktbl()
        self.grid_tbl.itemSelectionChanged.connect(self._on_grid_select)
        tbl_v.addWidget(self.grid_tbl,1)
        reload_btn=QPushButton("↻ Reload"); reload_btn.clicked.connect(self._reload_grids)
        tbl_v.addWidget(reload_btn)
        split.addWidget(tbl_w)
        split.setSizes([260,600])
        vl.addWidget(split,1)

        # Status label
        self.grid_status=QLabel("")
        self.grid_status.setObjectName("statusMsg")
        vl.addWidget(self.grid_status)
        self._grid_draw_tool=None
        return w

    def _start_grid_drawing(self):
        """Activate polygon drawing tool on the grid layer."""
        lyr=self._lyr(self.grid_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Create or connect the excavation_grids layer first."); return
        # Set as active layer and start editing
        self.iface.setActiveLayer(lyr)
        if not lyr.isEditable(): lyr.startEditing()
        # Activate add feature tool
        self.iface.actionAddFeature().trigger()
        self.grid_status.setText("Drawing mode active — click on the map to draw polygon vertices. Right-click to finish.")
        self._msg("Grid drawing active — draw on the QGIS map canvas")

    def _stop_grid_drawing(self):
        """Stop drawing and commit."""
        lyr=self._lyr(self.grid_layer_cb)
        if lyr and lyr.isEditable():
            lyr.commitChanges()
            self.iface.actionPan().trigger()
            self._reload_grids()
            self.grid_status.setText("Drawing stopped. Grids saved.")

    def _add_grid_record(self):
        """Add metadata record — call before or after drawing the polygon."""
        lyr=self._lyr(self.grid_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Set grid layer first."); return
        from qgis.core import QgsFeature
        vals={
            'grid_name':  self.grid_name_input.text().strip(),
            'site':       self.grid_site_input.text().strip() or getattr(self,'_current_site',''),
            'season':     self.grid_season_input.text().strip(),
            'elevation_m':self.grid_elev_input.value(),
            'notes':      self.grid_notes_input.text().strip(),
        }
        if not vals['grid_name']: QMessageBox.warning(self,"","Enter a grid name."); return
        self._write_feat(lyr,vals)
        self.grid_status.setText(f"Grid '{vals['grid_name']}' recorded. Draw its polygon on the map.")
        self._reload_grids()
        # Clear form
        self.grid_name_input.clear(); self.grid_notes_input.clear()

    def _reload_grids(self):
        lyr=self._lyr(self.grid_layer_cb)
        if not lyr: self.grid_tbl.setRowCount(0); return
        fnames=[f.name() for f in lyr.fields()]
        feats=list(lyr.getFeatures())
        self.grid_tbl.setColumnCount(len(fnames)); self.grid_tbl.setHorizontalHeaderLabels(fnames)
        self.grid_tbl.setRowCount(len(feats)); self.grid_tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn)
                self.grid_tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    def _on_grid_select(self):
        """Select grid on map when clicked in table."""
        rows=self.grid_tbl.selectionModel().selectedRows()
        if not rows: return
        ri=rows[0].row(); fids=self.grid_tbl.property("_fids") or []
        if ri>=len(fids): return
        lyr=self._lyr(self.grid_layer_cb)
        if not lyr: return
        lyr.removeSelection(); lyr.select(fids[ri])
        self.iface.mapCanvas().panToSelected(lyr)
        self._flash_feature(lyr, fids[ri])
        # Fill form with selected grid's data
        feat=lyr.getFeature(fids[ri])
        try:
            self.grid_name_input.setText(str(feat.attribute('grid_name') or ''))
            self.grid_site_input.setText(str(feat.attribute('site') or ''))
            self.grid_season_input.setText(str(feat.attribute('season') or ''))
            try: self.grid_elev_input.setValue(float(feat.attribute('elevation_m') or 0))
            except Exception: pass
            self.grid_notes_input.setText(str(feat.attribute('notes') or ''))
        except Exception: pass

    def _zoom_to_grids(self):
        lyr=self._lyr(self.grid_layer_cb)
        if lyr:
            self.iface.mapCanvas().setExtent(lyr.extent().buffered(lyr.extent().width()*0.1))
            self.iface.mapCanvas().refresh()

    # Patch _edit_row to handle 'grid'
    def _edit_row(self, pfx):
        if pfx=='grid':
            lyr=self._lyr(self.grid_layer_cb)
            tbl=self.grid_tbl
            if not lyr: return
            rows=tbl.selectionModel().selectedRows()
            if not rows: QMessageBox.information(self,"","Select a grid row first."); return
            ri=rows[0].row(); fids=tbl.property("_fids") or []
            if ri>=len(fids): return
            fid=fids[ri]; feat=lyr.getFeature(fid)
            defs={f.name():feat.attribute(f.name()) for f in lyr.fields()}
            dlg=RecordDialog(self._schema_for(lyr),defaults=defs,title="Edit Grid",parent=self)
            if dlg.exec_()!=QDialog.Accepted: return
            self._write_feat(lyr,dlg.values(),fid=fid); self._reload_grids()
        else: self._edit_row_ext_impl(pfx)

    def _export_grid_map(self):
        """Export the grid map as a professional PNG with site info overlay."""
        lyr=self._lyr(self.grid_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Set grid layer first."); return
        path,_=QFileDialog.getSaveFileName(self,"Export Grid Map","grid_map.png","PNG (*.png);;PDF (*.pdf)")
        if not path: return

        # Zoom to grid extent first
        self._zoom_to_grids()
        self.iface.mapCanvas().refresh()

        # Capture map canvas
        from qgis.PyQt.QtCore import QSize
        canvas=self.iface.mapCanvas()
        canvas_px=canvas.grab()   # QWidget.grab() -> QPixmap (render() needs a QPainter)

        # Compose final image with overlay
        margin=40; W=canvas_px.width()+2*margin; H=canvas_px.height()+2*margin+80
        final=QPixmap(W,H); final.fill(QColor('#f8f5ee'))
        p=QPainter(final); p.setRenderHint(QPainter.Antialiasing)

        # White map area
        p.drawPixmap(margin,margin+80,canvas_px)
        p.setPen(QPen(QColor('#2a2a2a'),1.2))
        p.drawRect(margin-1,margin+79,canvas_px.width()+2,canvas_px.height()+2)

        # Header band
        p.setBrush(QBrush(QColor('#1a1a1a'))); p.setPen(QPen(Qt.NoPen))
        p.drawRect(0,0,W,76)

        # Title
        site=getattr(self,'_current_site','')
        grid_count=lyr.featureCount()
        p.setPen(QColor('#c8a860'))
        p.setFont(QFont('Arial',18,QFont.Bold))
        p.drawText(margin,48,f"Excavation Grid Map  —  {site}")
        p.setFont(QFont('Arial',10)); p.setPen(QColor('#aaa'))
        from qgis.PyQt.QtCore import QDate
        p.drawText(margin,68,f"{grid_count} grids  |  Generated: {QDate.currentDate().toString('d MMMM yyyy')}")

        # North arrow (simple)
        na_x=W-margin-36; na_y=margin+90
        p.setBrush(QBrush(QColor('#333'))); p.setPen(QPen(Qt.NoPen))
        from qgis.PyQt.QtGui import QPolygon
        from qgis.PyQt.QtCore import QPoint
        p.drawPolygon(QPolygon([QPoint(na_x,na_y),QPoint(na_x-8,na_y+20),QPoint(na_x,na_y+14),QPoint(na_x+8,na_y+20)]))
        p.setFont(QFont('Arial',8,QFont.Bold)); p.setPen(QColor('#333'))
        p.drawText(na_x-4,na_y-4,'N')

        # Grid legend (grid names list)
        leg_y=margin+canvas_px.height()+90
        if leg_y+40 < H:
            p.setFont(QFont('Arial',8,QFont.Bold)); p.setPen(QColor('#333'))
            p.drawText(margin,leg_y,"Grids recorded:")
            p.setFont(QFont('Arial',8)); lx=margin+110
            for feat in lyr.getFeatures():
                try:
                    nm=str(feat.attribute('grid_name') or '')
                    if nm:
                        p.drawText(lx,leg_y,nm+' |'); lx+=p.fontMetrics().horizontalAdvance(nm+' | ')+2
                        if lx>W-margin: break
                except Exception: pass

        # Scale bar (approximate)
        p.setPen(QPen(QColor('#333'),2))
        p.drawLine(margin,H-16,margin+80,H-16)
        p.setFont(QFont('Arial',7)); p.drawText(margin,H-6,"approx. scale")

        p.end()

        if path.endswith('.pdf'):
            # Save as PDF via QPdfWriter
            try:
                from qgis.PyQt.QtGui import QPdfWriter, QPagedPaintDevice
                from qgis.PyQt.QtCore import QMarginsF
                dev=QPdfWriter(path); dev.setResolution(150)
                dev.setPageSize(QPagedPaintDevice.A3)
                pp=QPainter(dev); dev.setPageMargins(QMarginsF(0,0,0,0))
                dev.setPageSize(QPagedPaintDevice.A3)
                pp.drawPixmap(0,0,final.scaled(dev.width(),dev.height(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
                pp.end()
            except Exception as e:
                QMessageBox.warning(self,"PDF error",str(e)); return
        else:
            final.save(path,'PNG')
        self._msg(f"Grid map exported: {os.path.basename(path)}")
        QMessageBox.information(self,"Done",f"Grid map saved to:\n{path}")


class ArchWindow(_HistoryAndTabsMixin, _ArchaeologistMixin, _GridMapMixin, QMainWindow):
    def __init__(self,iface):
        super().__init__(); self.iface=iface
        self.setWindowTitle("Archaeological Manager — Anfeh Project")
        self.resize(1280,800); self.setMinimumSize(960,640)
        self.relationships=[]; self.layer_rels=[]; self.ctx_data={}
        # Photo registry: {'photos':[{path,context,caption}], 'drawings':[...], 'refs':[...]}
        self._photo_registry={'photos':[],'drawings':[],'refs':[]}
        self._connected_layer=None; self._block=False
        self._bone_widgets={}
        self._bone_view=None; self._qt_bridge=None; self._bone_js_data=None
        self._current_user='Archaeologist'
        self.hist_layer_cb=QComboBox()
        self.ctx_rel_layer_cb=QComboBox()
        self.draw_layer_cb=QComboBox()  # replaced in _build_ui
        self.grid_layer_cb=QComboBox()
        self._cfg_scroll=None  # set in _build_ui
        self._current_site=''   # set on connect
        raw,_=QgsProject.instance().readEntry("ArchManager","rels","[]")
        try: self.relationships=json.loads(raw)
        except Exception: pass
        # Status bar FIRST so _msg() works during UI build
        self.sb=QStatusBar(); self.setStatusBar(self.sb)
        self.sb.setObjectName("statusBar")
        self._toast=ToastLabel(self.sb); self.sb.addPermanentWidget(self._toast)
        self._build_ui(); self._refresh_combos()
        QgsProject.instance().layersAdded.connect(self._refresh_combos)
        QgsProject.instance().layersRemoved.connect(self._refresh_combos)

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _build_ui(self):
        """Image 4 style: sidebar + top header + content cards."""
        # ── Login ────────────────────────────────────────────────────────────
        self._current_user = "Archaeologist"
        self._user_color = CLR['accent']
        dlg = LoginDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self._current_user = dlg.get_user()
            self._user_color = dlg.get_color()
            dlg.save_if_checked()

        # Apply global stylesheet
        self.setStyleSheet(ROOT_QSS)
        if hasattr(self, 'statusBar'):
            try: self.statusBar().setObjectName("statusBar")
            except Exception: pass

        # Root container
        central = QWidget(); central.setObjectName("root")
        # central background handled by QSS
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ═══════════════════════════════════════════════════════════════════
        # LEFT SIDEBAR
        # ═══════════════════════════════════════════════════════════════════
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0); sb.setSpacing(0)

        # ── Brand header — UOB identity ──────────────────────────────────────
        brand = QWidget()
        brand.setObjectName("brandHeader")
        brand.setFixedHeight(88)
        bh = QHBoxLayout(brand)
        bh.setContentsMargins(12, 10, 12, 10)
        bh.setSpacing(10)

        # Custom drawn logo widget — loads logo.svg if available
        class _LogoWidget(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setFixedSize(52, 52)
                _svg_path = os.path.join(os.path.dirname(__file__), 'logo.svg')
                try:
                    from qgis.PyQt.QtSvg import QSvgRenderer
                    self._renderer = QSvgRenderer(_svg_path) if os.path.exists(_svg_path) else None
                except Exception:
                    self._renderer = None
            def paintEvent(self, e):
                from qgis.PyQt.QtGui import QPainter
                p = QPainter(self)
                p.setRenderHint(QPainter.Antialiasing)
                if self._renderer:
                    self._renderer.render(p)
                else:
                    # fallback: draw UOB initials
                    from qgis.PyQt.QtGui import QColor, QFont, QBrush, QPen
                    from qgis.PyQt.QtCore import QRectF, Qt
                    p.setBrush(QBrush(QColor("#1a4a8c")))
                    p.setPen(QPen(Qt.NoPen))
                    p.drawEllipse(1, 1, 50, 50)
                    p.setPen(QPen(QColor("#ffffff"), 1))
                    f = QFont("Arial", 14, QFont.Bold)
                    p.setFont(f)
                    p.drawText(QRectF(0, 0, 52, 52), Qt.AlignCenter, "UOB")
                p.end()

        logo_w = _LogoWidget(brand)
        bh.addWidget(logo_w)

        txt_col = QVBoxLayout(); txt_col.setSpacing(1)
        t1 = QLabel("Arch Manager"); t1.setObjectName("brand")
        t2 = QLabel("Dept. Archaeology & Museology")
        t2.setObjectName("brand_sub")
        t3 = QLabel("University of Balamand")
        t3.setObjectName("brand_sub")
        t3.setStyleSheet("font-weight:600;font-size:10px;")
        txt_col.addWidget(t1); txt_col.addWidget(t2); txt_col.addWidget(t3)
        bh.addLayout(txt_col)
        bh.addStretch()
        sb.addWidget(brand)

        self._nav_items = []
        self._current_theme = LIGHT_CLR  # starts in light mode
        self._nav_stack = QStackedWidget()

        nav_specs = [
            ("home",      "Home",         "Dashboard & site setup"),
            ("layers",    "Stratigraphy", "Contexts · Matrix · Map"),
            ("finds",     "Finds",        "Pottery · Artifacts"),
            ("clipboard", "Recording",    "Sheets · Skeletons · Bone"),
            ("map",       "Field",        "Grids · Drawings · Photos"),
            ("chart",     "Analysis",     "Counts · timeline"),
            ("history",   "Provenance",   "Edit log · by recorder"),
        ]

        # Group labels inserted before items at these indexes
        _nav_groups = {
            1: "RECORD",
            5: "REVIEW",
        }

        nav_scroll = QScrollArea(); nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        nav_inner = QWidget(); nav_inner.setStyleSheet("background:transparent;")
        nav_v = QVBoxLayout(nav_inner); nav_v.setContentsMargins(0, 4, 0, 8); nav_v.setSpacing(0)

        for i, (icon, lbl, sub) in enumerate(nav_specs):
            if i in _nav_groups:
                # thin separator line
                sep = QFrame(); sep.setObjectName("navSep"); sep.setFixedHeight(1)
                nav_v.addWidget(sep)
                # section label
                grp_lbl = QLabel(_nav_groups[i])
                grp_lbl.setObjectName("sectionLabel")
                nav_v.addWidget(grp_lbl)
            item = NavItem(icon, lbl, sub)
            item.clicked.connect(lambda _, idx=i: self._switch_nav(idx))
            self._nav_items.append(item)
            nav_v.addWidget(item)

        nav_v.addStretch()
        nav_scroll.setWidget(nav_inner)
        sb.addWidget(nav_scroll, 1)

        # Layer configuration (collapsible at bottom)
        cfg_toggle = QPushButton("⚙   Layer Configuration   ▼")
        cfg_toggle.setCheckable(True); cfg_toggle.setChecked(False)
        cfg_toggle.setCursor(Qt.PointingHandCursor)
        cfg_toggle.setObjectName("btn_ghost")
        self._cfg_toggle = cfg_toggle
        sb.addWidget(cfg_toggle)

        # Scrollable config form (hidden by default)
        cfg_scroll = QScrollArea(); cfg_scroll.setWidgetResizable(True)
        cfg_scroll.setMaximumHeight(360)
        cfg_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        cfg_scroll.setVisible(False)
        self._cfg_scroll = cfg_scroll
        cfg_w = QWidget(); cfg_w.setStyleSheet("background:transparent;")
        cf = QFormLayout(cfg_w)
        cf.setContentsMargins(14, 12, 14, 12); cf.setSpacing(6)
        cf.setLabelAlignment(Qt.AlignLeft)
        self._build_layer_config_form(cf)
        cfg_scroll.setWidget(cfg_w)
        sb.addWidget(cfg_scroll)
        cfg_toggle.clicked.connect(lambda checked:
            (cfg_scroll.setVisible(checked),
             cfg_toggle.setText(f"⚙   Layer Configuration   {'▲' if checked else '▼'}")))

        # Footer actions
        foot = QWidget(); foot.setObjectName("statusBar")
        fh = QVBoxLayout(foot); fh.setContentsMargins(14, 12, 14, 12); fh.setSpacing(6)
        load_btn = QPushButton("▶  Load / Refresh data")
        load_btn.setObjectName("btn_primary"); load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.clicked.connect(self._load_all)
        fh.addWidget(load_btn)
        f_row = QHBoxLayout(); f_row.setSpacing(6)
        pdf_btn = QPushButton("📄  PDF"); pdf_btn.setObjectName("btn_purple")
        pdf_btn.setCursor(Qt.PointingHandCursor); pdf_btn.clicked.connect(self._export_pdf)
        bak_btn = QPushButton("💾  Backup"); bak_btn.setObjectName("btn_secondary")
        bak_btn.setCursor(Qt.PointingHandCursor)
        if hasattr(self, '_backup_project'): bak_btn.clicked.connect(self._backup_project)
        f_row.addWidget(pdf_btn); f_row.addWidget(bak_btn)
        fh.addLayout(f_row)
        guide_btn = QPushButton("📖  Guide & Help")
        guide_btn.setObjectName("btn_ghost"); guide_btn.setCursor(Qt.PointingHandCursor)
        guide_btn.clicked.connect(self._show_guide)
        fh.addWidget(guide_btn)
        sb.addWidget(foot)

        root.addWidget(sidebar)

        # ═══════════════════════════════════════════════════════════════════
        # MAIN CONTENT AREA (top bar + stack)
        # ═══════════════════════════════════════════════════════════════════
        content = QWidget(); content.setObjectName("content")
        self._content_w = content
        cv = QVBoxLayout(content); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)

        # Top bar
        self._topbar = TopBar()
        self._topbar.set_title("Home", "Project dashboard & overview")
        # Theme toggle button — default: light mode
        self._dark_mode = False
        _theme_btn = QPushButton("🌙 Dark")
        _theme_btn.setObjectName("btn_ghost")
        _theme_btn.setCursor(Qt.PointingHandCursor)
        _theme_btn.setFixedWidth(80)
        _theme_btn.clicked.connect(lambda: self._toggle_theme(_theme_btn))
        self._topbar.add_action(_theme_btn)
        cv.addWidget(self._topbar)

        # Stack of pages
        cv.addWidget(self._nav_stack, 1)
        root.addWidget(content, 1)

        # ── Compatibility shim so old _build_*_tab() methods still work ──
        outer_self = self
        class _NavTabsShim:
            def addTab(_, widget, label):
                outer_self._nav_stack.addWidget(widget)
            def setCurrentIndex(_, i):
                outer_self._switch_nav(i)
            def count(_): return outer_self._nav_stack.count()
            def currentIndex(_): return outer_self._nav_stack.currentIndex()
        self.tabs = _NavTabsShim()

        # Compose the 7 sections — each becomes one page in _nav_stack, plus a
        # Guide page reached from the sidebar footer. Builders return widgets.
        self._gallery_widgets = {}
        home       = self._build_home_tab()
        strat      = self._section([
            ("Contexts",        self._build_ctx_tab()),
            ("Relationships",   self._build_rel_tab()),
            ("Harris Matrix",   self._build_matrix_tab()),
            ("Context View",    self._build_context_detail_tab()),
        ])
        finds      = self._section([
            ("Pottery",         self._build_linked_tab("Pottery", "pot", add_to_nav=False)),
            ("Artifacts",       self._build_linked_tab("Artifacts", "art", add_to_nav=False)),
            ("Artifact Detail", self._build_artdet_tab()),
            ("Crates",          self._build_crates_tab()),
        ])
        recording  = self._build_recording_tab()
        field      = self._section([
            ("Grid Map",        self._build_grid_map_tab()),
            ("Drawings",        self._build_drawings_tab()),
            ("Media",           self._build_media_tab()),
        ])
        analysis   = self._section([
            ("Statistics",      self._build_stats_tab()),
            ("Timeline",        self._build_timeline_tab()),
        ])
        provenance = self._section([
            ("Edit History",    self._build_history_tab()),
            ("By Archaeologist", self._build_archaeologist_tab()),
        ])
        self._guide_page = self._section([
            ("Workflow",        self._build_workflow_tab()),
            ("Pre-Excavation",  self._build_preexcav_tab()),
            ("Manual",          self._build_manual_tab()),
        ])
        for _w in (home, strat, finds, recording, field, analysis,
                   provenance, self._guide_page):
            self._nav_stack.addWidget(_w)

        # Activate Home tab
        if self._nav_items:
            self._nav_items[0].setChecked(True)
        self._nav_stack.setCurrentIndex(0)
        # Apply light theme at startup
        self.setStyleSheet(build_all_qss(LIGHT_CLR))
        for item in self._nav_items:
            item.update_theme(LIGHT_CLR)
        self.setWindowTitle("Arch Manager — Dept. of Archaeology & Museology, UOB")

    def _switch_nav(self, idx):
        """Activate nav item at idx and switch stack page."""
        if idx < 0 or idx >= self._nav_stack.count(): return
        self._nav_stack.setCurrentIndex(idx)
        for i, item in enumerate(self._nav_items):
            item.setChecked(i == idx)
        # Update top bar title
        if hasattr(self, '_topbar') and idx < len(self._nav_items):
            label = self._nav_items[idx]._label
            sub = self._nav_items[idx]._sublabel
            self._topbar.set_title(label, sub)

    def _toggle_theme(self, btn):
        """Toggle between dark and light themes at runtime."""
        self._dark_mode = not self._dark_mode
        c = CLR if self._dark_mode else LIGHT_CLR
        self._current_theme = c
        btn.setText("☀ Light" if self._dark_mode else "🌙 Dark")
        qss = build_all_qss(c)
        self.setStyleSheet(qss)
        # Update NavItem and site badge (they have inline styles)
        for item in self._nav_items:
            item.update_theme(c)
        if hasattr(self, '_site_badge'):
            self._site_badge.update_theme(c)
        if hasattr(self, 'hv'):
            self.hv.update_theme(
                bg_hex=c.get('bg_card','#232A30'),
                line_hex=c.get('text','#E8E4DC'),
                text_hex=c.get('text_dim','#A7A29A')
            )
        # Force repaint
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        # Rebuild theme-coloured dynamic Home content (next steps / activity)
        try: self._refresh_home_stats()
        except Exception: pass

    def _section(self, pairs):
        """Wrap (label, widget) pairs in a themed sub-tab bar; return the page.

        Used to compose several former top-level tabs into one nav section.
        """
        page = QWidget(); page.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(page); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        sub = QTabWidget(); sub.setObjectName("subTabs")
        for label, w in pairs:
            if w is not None:
                sub.addTab(w, label)
        vl.addWidget(sub)
        return page

    def _show_guide(self):
        """Switch to the Guide page (Workflow / Pre-excavation / Manual)."""
        if not hasattr(self, "_guide_page"):
            return
        idx = self._nav_stack.indexOf(self._guide_page)
        if idx < 0:
            return
        self._nav_stack.setCurrentIndex(idx)
        for item in self._nav_items:
            item.setChecked(False)
        if hasattr(self, "_topbar"):
            self._topbar.set_title("Guide & Help",
                                   "Workflow · Pre-excavation · Manual")

    def _build_grid_drawing_tab(self):
        """Composite tab: Harris Matrix + Drawings + Grid Map as sub-tabs."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        sub = QTabWidget(); sub.setObjectName("subTabs")
        matrix_w = self._build_matrix_tab()
        sub.addTab(matrix_w, "📐 Harris Matrix")
        draw_w = self._build_drawings_tab()
        sub.addTab(draw_w, "✏ Drawings")
        grid_w = self._build_grid_map_tab()
        sub.addTab(grid_w, "⬡ Grid Map")
        vl.addWidget(sub)
        self.tabs.addTab(page, "Grid & Drawing")

    def _build_artifacts_tab(self):
        """Composite tab: Artifacts list + Artifact Detail as sub-tabs."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        sub = QTabWidget(); sub.setObjectName("subTabs")
        art_w = self._build_linked_tab("Artifacts", "art", add_to_nav=False)
        sub.addTab(art_w, "⚱ Artifacts")
        det_w = self._build_artdet_tab()
        sub.addTab(det_w, "🔍 Artifact Detail")
        vl.addWidget(sub)
        self.tabs.addTab(page, "Artifacts")

    def _build_recording_tab(self):
        """Composite tab: Recording Sheets + Skeletons + Bone Form as sub-tabs."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        sub = QTabWidget(); sub.setObjectName("subTabs")
        self._recording_subtabs = sub
        sheets_w = self._build_recording_sheets_tab()
        sub.addTab(sheets_w, "📋 Recording Sheets")
        ske_w = self._build_skeleton_tab()
        sub.addTab(ske_w, "💀 Skeletons")
        bone_w = self._build_bone_form_tab()
        sub.addTab(bone_w, "🦴 Bone Form")
        vl.addWidget(sub)
        return page

    def _build_home_tab(self):
        """Dashboard home — connection, stat cards, next steps, map, photo."""
        _c = getattr(self, '_current_theme', CLR)
        page = QWidget(); page.setStyleSheet("background:transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0); page_layout.setSpacing(0)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll_content = QWidget(); scroll_content.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(scroll_content)
        outer.setContentsMargins(24, 22, 24, 24); outer.setSpacing(18)

        # ── Site Connection ──
        site_card = Card("Site Connection", "Open project and connect layers")
        sc_row1 = QHBoxLayout(); sc_row1.setSpacing(8)
        self.site_select_cb = QComboBox(); self.site_select_cb.setMinimumWidth(160)
        sc_row1.addWidget(self.site_select_cb, 1)
        home_open_btn = QPushButton("Open"); home_open_btn.setObjectName("btn_secondary")
        home_open_btn.clicked.connect(self._open_gpkg_file)
        home_scan_btn = QPushButton("Scan"); home_scan_btn.setObjectName("btn_secondary")
        home_scan_btn.setToolTip("Scan layers"); home_scan_btn.clicked.connect(self._scan_sites)
        home_conn_btn = QPushButton("Connect"); home_conn_btn.setObjectName("btn_primary")
        home_conn_btn.clicked.connect(self._connect_site)
        imp_xl_btn = QPushButton("Import Excel"); imp_xl_btn.setObjectName("btn_secondary"); imp_xl_btn.clicked.connect(self._imp_xl)
        imp_csv_btn = QPushButton("Import CSV"); imp_csv_btn.setObjectName("btn_secondary"); imp_csv_btn.clicked.connect(self._imp_csv)
        for b in [home_open_btn, home_scan_btn, home_conn_btn, imp_xl_btn, imp_csv_btn]:
            b.setCursor(Qt.PointingHandCursor); sc_row1.addWidget(b)
        site_card.body_layout.addLayout(sc_row1)
        self._site_badge = StatusBadge()
        site_card.body_layout.addWidget(self._site_badge)
        outer.addWidget(site_card)

        # ── Stat cards ──
        stats_row = QHBoxLayout(); stats_row.setSpacing(16)
        self._sc_contexts  = StatCard("Contexts",  "0", "layers")
        self._sc_finds     = StatCard("Finds",     "0", "finds",     accent=_c.get('accent_3'))
        self._sc_skeletons = StatCard("Skeletons", "0", "clipboard", accent=_c.get('accent_2'))
        self._sc_drawings  = StatCard("Drawings",  "0", "map",       accent=_c.get('status_ok'))
        for sc in [self._sc_contexts, self._sc_finds, self._sc_skeletons, self._sc_drawings]:
            stats_row.addWidget(sc, 1)
        outer.addLayout(stats_row)

        # ── Next steps + Recent activity ──
        row2 = QHBoxLayout(); row2.setSpacing(16)
        steps_card = Card("Your next steps", "Guided workflow")
        self._home_steps = QVBoxLayout(); self._home_steps.setSpacing(2)
        steps_card.body_layout.addLayout(self._home_steps); steps_card.body_layout.addStretch()
        row2.addWidget(steps_card, 3)
        ra_card = Card("Recent Activity", "Latest edits")
        self._home_activity = QVBoxLayout(); self._home_activity.setSpacing(6)
        ra_card.body_layout.addLayout(self._home_activity); ra_card.body_layout.addStretch()
        row2.addWidget(ra_card, 2)
        outer.addLayout(row2)

        # ── Site map ──
        map_card = Card("Site Location", "Connected layers on the map")
        map_v = QVBoxLayout(); map_v.setSpacing(8)
        try:
            from qgis.gui import QgsMapCanvas
            from qgis.core import QgsProject
            self._home_canvas = QgsMapCanvas()
            self._home_canvas.setMinimumHeight(260)
            self._home_canvas.setCanvasColor(Qt.white)
            try: self._home_canvas.setDestinationCrs(QgsProject.instance().crs())
            except Exception: pass
            map_v.addWidget(self._home_canvas, 1)
            map_btns = QHBoxLayout(); map_btns.setSpacing(8)
            zoom_btn = QPushButton("Zoom to site"); zoom_btn.setObjectName("btn_secondary"); zoom_btn.clicked.connect(self._home_zoom_to_site)
            refr_btn = QPushButton("Refresh"); refr_btn.setObjectName("btn_secondary"); refr_btn.clicked.connect(self._home_refresh_map)
            base_btn = QPushButton("Add basemap"); base_btn.setObjectName("btn_secondary"); base_btn.clicked.connect(self._add_basemap)
            for b in (zoom_btn, refr_btn, base_btn): b.setCursor(Qt.PointingHandCursor); map_btns.addWidget(b)
            map_btns.addStretch(); map_v.addLayout(map_btns)
        except Exception:
            self._home_canvas = None
            ph = QLabel("Map canvas unavailable"); ph.setAlignment(Qt.AlignCenter)
            ph.setMinimumHeight(260); ph.setObjectName("mapPlaceholder"); map_v.addWidget(ph)
        map_card.body_layout.addLayout(map_v)
        outer.addWidget(map_card)

        # ── Completion + Site photo ──
        row3 = QHBoxLayout(); row3.setSpacing(16)
        prog_card = Card("Project Completion", "Data entry progress")
        prog_v = QVBoxLayout(); prog_v.setSpacing(12)
        self._prog_pct_lbl = QLabel("0%"); self._prog_pct_lbl.setObjectName("statBig"); self._prog_pct_lbl.setAlignment(Qt.AlignCenter)
        prog_v.addWidget(self._prog_pct_lbl)
        self._prog_bar = QProgressBar(); self._prog_bar.setRange(0,100); self._prog_bar.setValue(0)
        self._prog_bar.setTextVisible(False); self._prog_bar.setFixedHeight(10); prog_v.addWidget(self._prog_bar)
        self._prog_detail = QLabel("No site connected"); self._prog_detail.setObjectName("cardSub"); self._prog_detail.setAlignment(Qt.AlignCenter)
        prog_v.addWidget(self._prog_detail)
        prog_card.body_layout.addLayout(prog_v)
        row3.addWidget(prog_card, 2)

        photo_card = Card("Site Photo", "Current excavation site")
        photo_v = QVBoxLayout(); photo_v.setSpacing(8)
        self._site_photo_lbl = QLabel(); self._site_photo_lbl.setMinimumHeight(160)
        self._site_photo_lbl.setAlignment(Qt.AlignCenter); self._site_photo_lbl.setObjectName("photoPlaceholder")
        self._site_photo_lbl.setText("No site photo")
        photo_v.addWidget(self._site_photo_lbl, 1)
        self._photo_upload_btn = QPushButton("Upload photo"); self._photo_upload_btn.setObjectName("btn_secondary")
        self._photo_upload_btn.setCursor(Qt.PointingHandCursor); self._photo_upload_btn.clicked.connect(self._upload_site_photo)
        self._photo_remove_btn = QPushButton("Remove photo"); self._photo_remove_btn.setObjectName("btn_ghost")
        self._photo_remove_btn.setCursor(Qt.PointingHandCursor); self._photo_remove_btn.clicked.connect(self._remove_site_photo)
        self._photo_remove_btn.setVisible(False)
        photo_v.addWidget(self._photo_upload_btn); photo_v.addWidget(self._photo_remove_btn)
        photo_card.body_layout.addLayout(photo_v)
        row3.addWidget(photo_card, 3)
        outer.addLayout(row3)

        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area, 1)
        return page

    # ── Crates (virtual storage boxes) ─────────────────────────────────────
    def _build_crates_tab(self):
        """Crates: box tiles on top, the selected crate's finds listed below."""
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(16, 16, 16, 16); vl.setSpacing(12)
        bar = QHBoxLayout(); bar.setSpacing(8)
        t = QLabel("Crates"); t.setObjectName("h3"); bar.addWidget(t); bar.addStretch()
        new_btn = QPushButton("+ New crate"); new_btn.setObjectName("btn_primary"); new_btn.clicked.connect(self._add_crate)
        edit_btn = QPushButton("Edit"); edit_btn.setObjectName("btn_secondary"); edit_btn.clicked.connect(self._edit_crate)
        del_btn = QPushButton("Delete"); del_btn.setObjectName("btn_danger"); del_btn.clicked.connect(self._delete_crate)
        mk_btn = QPushButton("Create crates layer"); mk_btn.setObjectName("btn_ghost"); mk_btn.clicked.connect(self._create_crates_layer)
        rf_btn = QPushButton("Refresh"); rf_btn.setObjectName("btn_secondary"); rf_btn.clicked.connect(self._reload_crates)
        for b in (new_btn, edit_btn, del_btn, mk_btn, rf_btn): b.setCursor(Qt.PointingHandCursor); bar.addWidget(b)
        vl.addLayout(bar)
        # Tiles row (horizontal scroll)
        self._crate_tiles_scroll = QScrollArea(); self._crate_tiles_scroll.setWidgetResizable(True)
        self._crate_tiles_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._crate_tiles_scroll.setFixedHeight(150)
        host = QWidget(); host.setStyleSheet("background:transparent;")
        self._crate_tiles_layout = QHBoxLayout(host)
        self._crate_tiles_layout.setContentsMargins(2, 2, 2, 2); self._crate_tiles_layout.setSpacing(12)
        self._crate_tiles_layout.setAlignment(Qt.AlignLeft)
        self._crate_tiles_scroll.setWidget(host)
        vl.addWidget(self._crate_tiles_scroll)
        # Contents
        self._crate_contents_lbl = QLabel("Select a crate to see its contents")
        self._crate_contents_lbl.setObjectName("h4")
        vl.addWidget(self._crate_contents_lbl)
        cbar = QHBoxLayout(); cbar.addStretch()
        ap = QPushButton("Add pottery"); ap.setObjectName("btn_secondary"); ap.clicked.connect(lambda: self._assign_finds_to_crate("pot"))
        aa = QPushButton("Add artifact"); aa.setObjectName("btn_secondary"); aa.clicked.connect(lambda: self._assign_finds_to_crate("art"))
        rm = QPushButton("Remove from crate"); rm.setObjectName("btn_ghost"); rm.clicked.connect(self._remove_find_from_crate)
        for b in (ap, aa, rm): b.setCursor(Qt.PointingHandCursor); cbar.addWidget(b)
        vl.addLayout(cbar)
        self._crate_contents_tbl = self._mktbl()
        vl.addWidget(self._crate_contents_tbl, 1)
        self._current_crate = None
        self._reload_crates()
        return w

    def _crate_counts(self):
        """Return {crate_label: number_of_finds} across pottery + artifacts."""
        counts = {}
        for cb in (getattr(self, "pot_layer_cb", None), getattr(self, "art_layer_cb", None)):
            lyr = self._lyr(cb) if cb is not None else None
            if not lyr or lyr.fields().indexOf("crate") < 0: continue
            for f in lyr.getFeatures():
                lab = fmt_cell(f.attribute("crate"))
                if lab: counts[lab] = counts.get(lab, 0) + 1
        return counts

    def _crate_labels(self):
        """Sorted list of existing crate labels (for find-form dropdowns)."""
        lyr = self._lyr(getattr(self, "crate_layer_cb", None))
        labels = []
        if lyr and lyr.fields().indexOf("crate_label") >= 0:
            for f in lyr.getFeatures():
                lab = fmt_cell(f.attribute("crate_label"))
                if lab: labels.append(lab)
        return sorted(set(labels))

    def _reload_crates(self):
        if not hasattr(self, "_crate_tiles_layout"): return
        while self._crate_tiles_layout.count():
            it = self._crate_tiles_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        lyr = self._lyr(getattr(self, "crate_layer_cb", None))
        if not lyr:
            ph = QLabel("No crates layer — click 'Create crates layer' or set it in Layer Configuration.")
            ph.setObjectName("muted"); ph.setWordWrap(True)
            self._crate_tiles_layout.addWidget(ph); return
        if lyr.fields().indexOf("crate_label") < 0:
            ph = QLabel("The selected layer isn't a crates layer (it has no 'crate_label' "
                        "field). Click 'Create crates layer', or pick the right layer in "
                        "Layer Configuration → Crates.")
            ph.setObjectName("muted"); ph.setWordWrap(True)
            self._crate_tiles_layout.addWidget(ph); return
        counts = self._crate_counts()
        has_loc = lyr.fields().indexOf("location") >= 0
        n = 0
        for feat in lyr.getFeatures():
            label = fmt_cell(feat.attribute("crate_label")) or f"Crate {feat.id()}"
            loc = fmt_cell(feat.attribute("location")) if has_loc else ""
            tile = QPushButton(f"\U0001F4E6  {label}\n{loc or '—'}\n{counts.get(label, 0)} finds")
            tile.setCheckable(True); tile.setCursor(Qt.PointingHandCursor)
            tile.setObjectName("crateTile"); tile.setFixedSize(150, 96)
            tile.clicked.connect(lambda _=False, lb=label, fid=feat.id(): self._on_crate_selected(lb, fid))
            self._crate_tiles_layout.addWidget(tile); n += 1
        if n == 0:
            ph = QLabel("No crates yet — click '+ New crate'."); ph.setObjectName("muted")
            self._crate_tiles_layout.addWidget(ph)
        self._crate_tiles_layout.addStretch()

    def _on_crate_selected(self, label, fid):
        self._current_crate = (label, fid)
        self._crate_contents_lbl.setText(f"Contents of crate '{label}'")
        self._load_crate_contents(label)

    def _load_crate_contents(self, label):
        rows = []; fids = []
        for kind, cb in (("Pottery", getattr(self, "pot_layer_cb", None)),
                         ("Artifact", getattr(self, "art_layer_cb", None))):
            lyr = self._lyr(cb) if cb is not None else None
            if not lyr or lyr.fields().indexOf("crate") < 0: continue
            for f in lyr.getFeatures():
                if fmt_cell(f.attribute("crate")) != label: continue
                ctx = fmt_cell(f.attribute("context_num"))
                desc = fmt_cell(f.attribute("form")) or fmt_cell(f.attribute("type")) or ""
                rows.append([kind, ctx, desc]); fids.append((lyr, f.id()))
        self._crate_contents_tbl.setColumnCount(3)
        self._crate_contents_tbl.setHorizontalHeaderLabels(["Kind", "Context", "Description"])
        self._crate_contents_tbl.setRowCount(len(rows))
        self._crate_contents_tbl.setProperty("_crate_fids", fids)
        for ri, row in enumerate(rows):
            for ci, v in enumerate(row):
                self._crate_contents_tbl.setItem(ri, ci, QTableWidgetItem(fmt_cell(v)))

    def _add_crate(self):
        lyr = self._lyr(getattr(self, "crate_layer_cb", None))
        if not lyr:
            QMessageBox.warning(self, "", "No crates layer. Click 'Create crates layer' first."); return
        defaults = {"site": getattr(self, "_current_site", "")}
        dlg = RecordDialog(self._schema_for(lyr), defaults=defaults, title="New Crate", parent=self)
        if dlg.exec_() != QDialog.Accepted: return
        self._write_feat(lyr, dlg.values()); self._reload_crates()

    def _edit_crate(self):
        if not getattr(self, "_current_crate", None):
            QMessageBox.information(self, "", "Click a crate tile first."); return
        lyr = self._lyr(getattr(self, "crate_layer_cb", None))
        if not lyr: return
        fid = self._current_crate[1]; feat = lyr.getFeature(fid)
        defs = {f.name(): feat.attribute(f.name()) for f in lyr.fields()}
        dlg = RecordDialog(self._schema_for(lyr), defaults=defs, title="Edit Crate", parent=self)
        if dlg.exec_() != QDialog.Accepted: return
        self._write_feat(lyr, dlg.values(), fid=fid); self._reload_crates()

    def _delete_crate(self):
        if not getattr(self, "_current_crate", None):
            QMessageBox.information(self, "", "Click a crate tile first."); return
        if QMessageBox.question(self, "Delete crate",
                "Delete this crate? Finds stay but lose their crate assignment.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        lyr = self._lyr(getattr(self, "crate_layer_cb", None))
        if lyr:
            try:
                lyr.startEditing(); lyr.deleteFeature(self._current_crate[1]); lyr.commitChanges()
            except Exception: pass
        self._current_crate = None; self._reload_crates()
        self._crate_contents_tbl.setRowCount(0)

    def _assign_finds_to_crate(self, pfx):
        if not getattr(self, "_current_crate", None):
            QMessageBox.information(self, "", "Click a crate tile first."); return
        cb = getattr(self, f"{pfx}_layer_cb", None)
        lyr = self._lyr(cb) if cb is not None else None
        if not lyr:
            QMessageBox.warning(self, "", f"No {pfx} layer set."); return
        if lyr.fields().indexOf("crate") < 0:
            QMessageBox.warning(self, "", "This layer has no 'crate' column. Use '+ Col' to add it, "
                                "or recreate the layer."); return
        label = self._current_crate[0]
        dlg = QDialog(self); dlg.setWindowTitle(f"Add {pfx} to crate '{label}'"); dlg.resize(460, 420)
        dv = QVBoxLayout(dlg)
        dv.addWidget(QLabel("Select finds to place in this crate (unassigned shown first):"))
        lst = QListWidget(); lst.setSelectionMode(QAbstractItemView.MultiSelection)
        items = []
        for f in lyr.getFeatures():
            cur = fmt_cell(f.attribute("crate"))
            ctx = fmt_cell(f.attribute("context_num"))
            desc = fmt_cell(f.attribute("form")) or fmt_cell(f.attribute("type")) or ""
            tag = f"  [in {cur}]" if cur and cur != label else (" [here]" if cur == label else "")
            it = QListWidgetItem(f"Ctx {ctx} — {desc}{tag}")
            it.setData(Qt.UserRole, f.id()); lst.addItem(it); items.append(it)
        dv.addWidget(lst, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); dv.addWidget(bb)
        if dlg.exec_() != QDialog.Accepted: return
        idx = lyr.fields().indexOf("crate"); chosen = lst.selectedItems()
        if not chosen: return
        lyr.startEditing()
        for it in chosen:
            lyr.changeAttributeValue(it.data(Qt.UserRole), idx, label)
        lyr.commitChanges()
        self._load_crate_contents(label); self._reload_crates()
        self._msg(f"Assigned {len(chosen)} find(s) to crate '{label}'")

    def _remove_find_from_crate(self):
        rows = self._crate_contents_tbl.selectionModel().selectedRows() if self._crate_contents_tbl.selectionModel() else []
        fids = self._crate_contents_tbl.property("_crate_fids") or []
        if not rows: QMessageBox.information(self, "", "Select a row first."); return
        for r in rows:
            if r.row() < len(fids):
                lyr, fid = fids[r.row()]
                idx = lyr.fields().indexOf("crate")
                if idx >= 0:
                    lyr.startEditing(); lyr.changeAttributeValue(fid, idx, None); lyr.commitChanges()
        if getattr(self, "_current_crate", None):
            self._load_crate_contents(self._current_crate[0]); self._reload_crates()

    def _build_media_tab(self):
        """Photo/Media gallery with categories."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        outer.addWidget(ContentTitle("Media Gallery",
                                     "Photos, field drawings and reference documents linked to your excavation"))

        if not hasattr(self, '_gallery_widgets'):
            self._gallery_widgets = {}

        # Sub-tabs: Photos, Drawings, Documents
        sub = QTabWidget(); sub.setObjectName("subTabs")
        sub.addTab(self._build_photo_gallery_subtab("photos"),   "📷 Photos")
        sub.addTab(self._build_photo_gallery_subtab("drawings"), "✏ Field Drawings")
        sub.addTab(self._build_photo_gallery_subtab("refs"),     "📄 Documents")
        outer.addWidget(sub, 1)
        return page

    def _build_photo_gallery_subtab(self, category):
        """Build a photo/file gallery widget for the given category."""
        from qgis.PyQt.QtCore import QSize as _QSize
        w = QWidget()
        vl = QVBoxLayout(w); vl.setContentsMargins(16, 16, 16, 16); vl.setSpacing(12)

        # Toolbar
        bar = QHBoxLayout(); bar.setSpacing(8)
        add_btn = QPushButton("＋ Add file"); add_btn.setObjectName("btn_primary")
        add_btn.setCursor(Qt.PointingHandCursor)
        open_btn = QPushButton("📂 Open"); open_btn.setObjectName("btn_secondary")
        open_btn.setCursor(Qt.PointingHandCursor)
        del_btn = QPushButton("🗑 Remove"); del_btn.setObjectName("btn_danger")
        del_btn.setCursor(Qt.PointingHandCursor)
        ctx_filter = QComboBox(); ctx_filter.setEditable(True)
        ctx_filter.addItem("All contexts"); ctx_filter.setMinimumWidth(140)
        caption_lbl = QLabel(f"Category: {category.title()}")
        caption_lbl.setObjectName("muted")
        bar.addWidget(caption_lbl); bar.addStretch()
        bar.addWidget(ctx_filter); bar.addWidget(add_btn); bar.addWidget(open_btn); bar.addWidget(del_btn)
        vl.addLayout(bar)

        # Gallery grid using QListWidget in icon mode
        gallery = QListWidget()
        gallery.setObjectName("gallery")
        gallery.setContextMenuPolicy(Qt.CustomContextMenu)
        gallery.setViewMode(QListWidget.IconMode)
        gallery.setIconSize(_QSize(120, 90))
        gallery.setResizeMode(QListWidget.Adjust)
        gallery.setSpacing(8)
        gallery.setProperty("_files", [])
        gallery.setProperty("_category", category)
        if not hasattr(self, '_gallery_widgets'):
            self._gallery_widgets = {}
        self._gallery_widgets[category] = gallery
        vl.addWidget(gallery, 1)

        # Status bar
        status_lbl = QLabel("No files added — click ＋ Add file to attach photos")
        status_lbl.setObjectName("statusMsg")
        vl.addWidget(status_lbl)

        def _sync_registry():
            """Mirror this gallery's files+tags into self._photo_registry[category]."""
            files = gallery.property("_files") or []
            reg = []
            for i in range(gallery.count()):
                it = gallery.item(i)
                path = files[i] if i < len(files) else ""
                txt = it.text()
                ctx = ""
                if "\n📍 Context " in txt:
                    ctx = txt.split("\n📍 Context ")[-1].split("\n")[0].strip()
                reg.append({'path': path,
                            'context': ctx,
                            'caption': os.path.basename(path) if path else txt})
            self._photo_registry[category] = reg

        def add_file():
            paths, _ = QFileDialog.getOpenFileNames(
                w, "Select files", "",
                "Images & Documents (*.png *.jpg *.jpeg *.bmp *.tiff *.pdf *.svg *.dwg *.dxf *.docx *.xlsx)")
            if not paths: return
            files = gallery.property("_files") or []
            for path in paths:
                files.append(path)
                item = QListWidgetItem()
                item.setText(os.path.basename(path))
                item.setToolTip(path)
                # Try to load image thumbnail
                px = QPixmap(path)
                if not px.isNull():
                    item.setIcon(QIcon(px.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    # Non-image file — show a generic doc icon
                    icon_lbl = "📄" if path.endswith(('.pdf', '.docx', '.xlsx')) else "📐"
                    item.setText(f"{icon_lbl}\n{os.path.basename(path)}")
                gallery.addItem(item)
            gallery.setProperty("_files", files)
            status_lbl.setText(f"{len(files)} file(s) attached")
            _sync_registry()
            try: self._save_gallery_registry()
            except Exception: pass
            try: self._log_history('media_add', category, os.path.basename(paths[-1]), f"{len(paths)} file(s)")
            except Exception: pass

        def open_file():
            items = gallery.selectedItems()
            if not items: return
            files = gallery.property("_files") or []
            idx = gallery.row(items[0])
            if idx < len(files):
                path = files[idx]
                if os.path.exists(path):
                    import subprocess
                    subprocess.Popen(['xdg-open', path])
                else:
                    QMessageBox.warning(w, "File not found", path)

        def del_file():
            items = gallery.selectedItems()
            if not items: return
            files = gallery.property("_files") or []
            idx = gallery.row(items[0])
            removed = files[idx] if idx < len(files) else ''
            gallery.takeItem(idx)
            if idx < len(files): files.pop(idx)
            gallery.setProperty("_files", files)
            status_lbl.setText(f"{len(files)} file(s) attached")
            _sync_registry()
            try: self._save_gallery_registry()
            except Exception: pass
            try: self._log_history('media_remove', category, os.path.basename(removed), '')
            except Exception: pass

        def context_menu(pos):
            items = gallery.selectedItems()
            if not items: return
            from qgis.PyQt.QtWidgets import QMenu, QInputDialog, QAction
            menu = QMenu(gallery)

            tag_action = QAction("🏷 Tag with context number…", gallery)
            def do_tag():
                text, ok = QInputDialog.getText(gallery, "Tag Photo",
                    "Context number (e.g. 103):")
                if ok and text.strip():
                    item = gallery.selectedItems()[0]
                    existing = item.toolTip()
                    # Append context tag
                    tag = f"Context {text.strip()}"
                    new_tip = f"{existing}\n📍 {tag}" if existing else f"📍 {tag}"
                    item.setToolTip(new_tip)
                    # Show tag in text
                    base_name = item.text().split('\n📍')[0]
                    item.setText(f"{base_name}\n📍 {tag}")
                    _sync_registry()
                    try: self._save_gallery_registry()
                    except Exception: pass
            tag_action.triggered.connect(do_tag)
            menu.addAction(tag_action)

            untag_action = QAction("✕ Remove tag", gallery)
            def do_untag():
                item = gallery.selectedItems()[0]
                name = item.text().split('\n📍')[0]
                item.setText(name)
                item.setToolTip(name)
                _sync_registry()
                try: self._save_gallery_registry()
                except Exception: pass
            untag_action.triggered.connect(do_untag)
            menu.addAction(untag_action)

            menu.addSeparator()

            open_action = QAction("📂 Open file", gallery)
            open_action.triggered.connect(open_file)
            menu.addAction(open_action)

            del_action = QAction("🗑 Remove from gallery", gallery)
            del_action.triggered.connect(del_file)
            menu.addAction(del_action)

            menu.exec_(gallery.viewport().mapToGlobal(pos))

        gallery.customContextMenuRequested.connect(context_menu)

        add_btn.clicked.connect(add_file)
        open_btn.clicked.connect(open_file)
        del_btn.clicked.connect(del_file)
        return w

    def _build_preexcav_tab(self):
        """Editable pre-excavation checklist, saved to JSON per project."""
        DEFAULT_ITEMS = [
            ("Safety & Permits", [
                "Site permits and authorizations confirmed",
                "Emergency contacts list distributed",
                "First-aid kit checked and stocked",
                "Safety briefing conducted with all team members",
                "Personal protective equipment distributed (boots, gloves, hats)",
            ]),
            ("Equipment", [
                "Total station / theodolite calibrated and charged",
                "GPS units charged and tested",
                "Drone batteries charged",
                "Camera equipment and memory cards ready",
                "Measuring tapes, ranging rods, string lines",
                "Drawing boards, film, scales and pencils",
                "Trowels, brushes, picks, buckets",
                "Wheelbarrows and shovels",
                "Shoring/propping materials if needed",
            ]),
            ("Documentation", [
                "Context record sheets printed or loaded on tablets",
                "Find bags and labels prepared",
                "Sample bags and labels prepared",
                "Database/GeoPackage backed up",
                "Daily log book ready",
            ]),
            ("Site Setup", [
                "Datum point established and recorded",
                "Site grid pegged out",
                "Topographic survey completed",
                "Spoil heap area designated",
                "Finds processing area set up",
                "Photography backdrop and scale bars available",
            ]),
        ]

        page = QWidget()
        page.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 20, 24, 20); outer.setSpacing(16)

        # Header
        title = ContentTitle("Pre-Excavation Checklist",
                             "Complete these tasks before starting excavation")
        outer.addWidget(title)

        hdr = QHBoxLayout()
        save_btn = QPushButton("💾 Save checklist"); save_btn.setObjectName("btn_primary")
        save_btn.setCursor(Qt.PointingHandCursor)
        load_btn = QPushButton("📂 Load"); load_btn.setObjectName("btn_secondary")
        load_btn.setCursor(Qt.PointingHandCursor)
        reset_btn = QPushButton("↺ Reset all"); reset_btn.setObjectName("btn_ghost")
        reset_btn.setCursor(Qt.PointingHandCursor)
        hdr.addStretch()
        for b in [reset_btn, load_btn, save_btn]: hdr.addWidget(b)
        outer.addLayout(hdr)

        # Progress bar row
        prog_row = QHBoxLayout()
        prog_lbl = QLabel("Progress: 0 / 0 items")
        prog_lbl.setObjectName("muted")
        self._preexcav_prog = prog_lbl
        prog_row.addWidget(prog_lbl); prog_row.addStretch()
        outer.addLayout(prog_row)

        # Scroll area for checklist
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{background:transparent;border:none;}}")
        list_w = QWidget(); list_w.setStyleSheet(f"background:transparent;")
        list_vl = QVBoxLayout(list_w); list_vl.setSpacing(12); list_vl.setContentsMargins(0, 0, 0, 0)

        self._preexcav_checks = []  # list of QCheckBox widgets

        def _update_progress():
            total = len(self._preexcav_checks)
            checked = sum(1 for cb in self._preexcav_checks if cb.isChecked())
            pct = '100%' if total == 0 else f'{checked * 100 // total}%'
            self._preexcav_prog.setText(f"Progress: {checked} / {total} items complete  ({pct})")

        def _build_list(items_spec):
            while list_vl.count():
                it = list_vl.takeAt(0)
                if it.widget(): it.widget().deleteLater()
            self._preexcav_checks.clear()

            for section, items in items_spec:
                sec_frame = QFrame(); sec_frame.setObjectName("card")
                sec_vl = QVBoxLayout(sec_frame); sec_vl.setContentsMargins(16, 12, 16, 12); sec_vl.setSpacing(8)

                sec_hdr = QHBoxLayout()
                sec_title = QLabel(section)
                sec_title.setObjectName("h4")
                add_item_btn = QPushButton("＋")
                add_item_btn.setObjectName("btn_ghost"); add_item_btn.setFixedSize(28, 28)
                add_item_btn.setCursor(Qt.PointingHandCursor)
                add_item_btn.setToolTip("Add item to this section")
                sec_hdr.addWidget(sec_title); sec_hdr.addStretch(); sec_hdr.addWidget(add_item_btn)
                sec_vl.addLayout(sec_hdr)

                for item_text in items:
                    cb_row = QHBoxLayout(); cb_row.setSpacing(8)
                    cb = QCheckBox(item_text)
                    cb.stateChanged.connect(_update_progress)
                    self._preexcav_checks.append(cb)
                    del_cb_btn = QPushButton("✕")
                    del_cb_btn.setObjectName("btn_ghost"); del_cb_btn.setFixedSize(22, 22)
                    del_cb_btn.setCursor(Qt.PointingHandCursor)

                    def make_del(cb_ref, btn_ref):
                        def do_del():
                            cb_ref.deleteLater(); btn_ref.deleteLater()
                            if cb_ref in self._preexcav_checks:
                                self._preexcav_checks.remove(cb_ref)
                            _update_progress()
                        return do_del
                    del_cb_btn.clicked.connect(make_del(cb, del_cb_btn))
                    cb_row.addWidget(cb, 1); cb_row.addWidget(del_cb_btn)
                    sec_vl.addLayout(cb_row)

                def make_add(sv=sec_vl, sc=section):
                    def do_add():
                        text, ok = QInputDialog.getText(
                            page, "Add item", f"New checklist item for '{sc}':")
                        if not ok or not text.strip(): return
                        new_cb = QCheckBox(text.strip())
                        new_cb.stateChanged.connect(_update_progress)
                        self._preexcav_checks.append(new_cb)
                        cb_row2 = QHBoxLayout(); cb_row2.setSpacing(8)
                        del2 = QPushButton("✕"); del2.setObjectName("btn_ghost"); del2.setFixedSize(22, 22)
                        def rm(cb_r=new_cb, btn_r=del2):
                            cb_r.deleteLater(); btn_r.deleteLater()
                            if cb_r in self._preexcav_checks: self._preexcav_checks.remove(cb_r)
                            _update_progress()
                        del2.clicked.connect(rm); del2.setCursor(Qt.PointingHandCursor)
                        cb_row2.addWidget(new_cb, 1); cb_row2.addWidget(del2)
                        sv.addLayout(cb_row2); _update_progress()
                    return do_add
                add_item_btn.clicked.connect(make_add())
                list_vl.addWidget(sec_frame)

            list_vl.addStretch()
            _update_progress()

        def _save_checklist():
            try:
                import json as _json
                data = {
                    'items': [{'text': cb.text(), 'checked': cb.isChecked()}
                              for cb in self._preexcav_checks]
                }
                path, _ = QFileDialog.getSaveFileName(
                    page, "Save checklist", "preexcav_checklist.json", "JSON (*.json)")
                if path:
                    with open(path, 'w') as _f:
                        _json.dump(data, _f, indent=2)
                    self._msg("Checklist saved.")
            except Exception as e:
                QMessageBox.warning(page, "Save failed", str(e))

        def _load_checklist():
            try:
                import json as _json
                path, _ = QFileDialog.getOpenFileName(page, "Load checklist", "", "JSON (*.json)")
                if not path: return
                with open(path) as _f:
                    data = _json.load(_f)
                items_spec = [("Loaded Checklist", [it['text'] for it in data.get('items', [])])]
                _build_list(items_spec)
                checks = data.get('items', [])
                for i, cb in enumerate(self._preexcav_checks):
                    if i < len(checks): cb.setChecked(checks[i].get('checked', False))
                self._msg("Checklist loaded.")
            except Exception as e:
                QMessageBox.warning(page, "Load failed", str(e))

        def _reset_all():
            for cb in self._preexcav_checks: cb.setChecked(False)
            _update_progress()

        save_btn.clicked.connect(_save_checklist)
        load_btn.clicked.connect(_load_checklist)
        reset_btn.clicked.connect(_reset_all)

        _build_list(DEFAULT_ITEMS)
        scroll.setWidget(list_w)
        outer.addWidget(scroll, 1)

        return page

    def _build_workflow_tab(self):
        """Visual step-by-step excavation workflow guide."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(32, 28, 32, 28); outer.setSpacing(24)

        hdr = QLabel("Excavation Workflow")
        hdr.setObjectName("h1")
        sub = QLabel("Follow these phases for each excavation campaign. Click any step to jump to the relevant plugin section.")
        sub.setObjectName("secSub")
        sub.setWordWrap(True)
        outer.addWidget(hdr); outer.addWidget(sub)

        # Phase accent colors — fixed HEX so they work in both light and dark themes
        _PHASE_COLORS = ["#E08020", "#3D9ABF", "#C89B3C", "#8D6ABD", "#C45B52"]

        phases = [
            ("1", "Pre-Excavation", _PHASE_COLORS[0],
             "⛏ Pre-Excavation",
             [("Permits & Safety", "Confirm site permits, distribute emergency contacts, safety briefing", "⛏"),
              ("Equipment Check", "Charge GPS/drone batteries, check total station, prepare drawing supplies", "🔧"),
              ("Documentation Setup", "Print context sheets, prepare find bags, back up database", "📋"),
              ("Site Grid", "Establish datum point, peg out grid, complete topographic survey", "🗺"),
             ]),
            ("2", "Site Setup & Opening", _PHASE_COLORS[1],
             "Grid & Drawing",
             [("Grid Layout", "Define excavation units in the Grid Map tab", "📐"),
              ("Baseline Survey", "Record coordinates of all grid pegs using total station", "📏"),
              ("Photography", "Take pre-excavation overview photos, link them in the Media tab", "📷"),
              ("Layer Config", "Connect GeoPackage layers in the Home dashboard", "🏠"),
             ]),
            ("3", "Excavation & Recording", _PHASE_COLORS[2],
             "Contexts",
             [("Open Context", "Create a new context record for each distinct stratigraphic unit", "📋"),
              ("Describe & Draw", "Fill type, period, description; attach field drawings", "✏"),
              ("Find Processing", "Log pottery (Pottery tab), artifacts (Artifacts tab)", "🏺"),
              ("Photography", "Photograph each context in plan and section; attach to Media", "📷"),
             ]),
            ("4", "Stratigraphic Analysis", _PHASE_COLORS[3],
             "Grid & Drawing",
             [("Build Harris Matrix", "Add relationships (above/below/cuts) and build the matrix", "📐"),
              ("Check Relationships", "Review the Relationships tab for consistency", "🔗"),
              ("Period Assignment", "Assign periods to contexts based on finds", "📅"),
              ("Context View", "Use Context View tab to review all data linked to each context", "🗺"),
             ]),
            ("5", "Post-Excavation", _PHASE_COLORS[4],
             "Statistics",
             [("Statistics Review", "Check totals and distributions in the Statistics tab", "📊"),
              ("Timeline", "Review and adjust the period sequence in Timeline tab", "📅"),
              ("Specialist Analysis", "Refer bone inventories (Recording Sheet → Bone Form)", "💀"),
              ("Export Report", "Generate PDF using the PDF button — select sections and layout", "📄"),
             ]),
        ]

        nav_targets = {
            "⛏ Pre-Excavation": "Pre-Excavation",
            "Grid & Drawing": "Grid & Drawing",
            "Contexts": "Contexts",
            "Statistics": "Statistics",
        }

        for phase_num, phase_name, color, nav_target, steps in phases:
            card = QFrame(); card.setObjectName("card")
            card.setStyleSheet(f"QFrame#card{{border-left:4px solid {color};}}")
            cv = QVBoxLayout(card); cv.setContentsMargins(20, 16, 20, 16); cv.setSpacing(12)

            # Phase header
            ph_row = QHBoxLayout()
            badge = QLabel(f"  {phase_num}  ")
            badge.setStyleSheet(f"background:{color};color:#ffffff;font-weight:700;font-size:13px;"
                                f"border-radius:14px;padding:4px 10px;")
            badge.setAlignment(Qt.AlignCenter)
            ph_title = QLabel(f"  {phase_name}")
            ph_title.setObjectName("h3")
            ph_row.addWidget(badge); ph_row.addWidget(ph_title); ph_row.addStretch()

            if nav_target:
                go_btn = QPushButton(f"→ Open {nav_target}")
                go_btn.setObjectName("btn_primary")
                go_btn.setCursor(Qt.PointingHandCursor)
                target = nav_targets.get(nav_target, nav_target)
                go_btn.clicked.connect(lambda _, t=target: self._switch_nav_to(t))
                ph_row.addWidget(go_btn)
            cv.addLayout(ph_row)

            # Steps grid
            grid = QHBoxLayout(); grid.setSpacing(10)
            for step_name, step_desc, step_icon in steps:
                step_w = QFrame()
                step_w.setStyleSheet("background:transparent;")
                sv = QVBoxLayout(step_w); sv.setContentsMargins(12, 10, 12, 10); sv.setSpacing(4)
                ic = QLabel(step_icon); ic.setStyleSheet(f"font-size:18px;background:transparent;")
                nm = QLabel(step_name); nm.setObjectName("bodyText")
                nm.setWordWrap(True)
                ds = QLabel(step_desc); ds.setObjectName("mutedXs")
                ds.setWordWrap(True)
                sv.addWidget(ic); sv.addWidget(nm); sv.addWidget(ds); sv.addStretch()
                grid.addWidget(step_w, 1)
            cv.addLayout(grid)
            outer.addWidget(card)

        outer.addStretch()
        scroll.setWidget(inner)
        page_vl = QVBoxLayout(page); page_vl.setContentsMargins(0,0,0,0)
        page_vl.addWidget(scroll)
        return page

    def _build_manual_tab(self):
        """In-plugin documentation and help."""
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(32, 28, 32, 28); outer.setSpacing(20)

        title = QLabel("Plugin Manual")
        title.setObjectName("h1")
        outer.addWidget(title)

        sections = [
            ("🏠 Getting Started", [
                ("Create a New Project",
                 "Click 🆕 New Project on the Home dashboard. You will be prompted to choose a save location. "
                 "The plugin creates a GeoPackage (.gpkg) file containing all data tables: contexts, pottery, "
                 "artifacts, skeletons, drawings, relationships, and edit history."),
                ("Open an Existing Project",
                 "Click 📂 Open on the Home dashboard and navigate to your .gpkg file. "
                 "Then click ↻ Scan to detect available layers, select your site from the dropdown, "
                 "and click Connect."),
                ("Load / Refresh Data",
                 "After connecting, click ▶ Load / Refresh data in the sidebar footer. "
                 "This populates all tables with the current data from the GeoPackage."),
            ]),
            ("📋 Recording Contexts", [
                ("Adding a Context",
                 "Go to Contexts → click ＋ Add. Fill in context number, type (Fill, Cut, Deposit…), "
                 "period, and description. The context is saved immediately to the GeoPackage."),
                ("Editing a Context",
                 "Select a row in the table and click ✏ Edit. Modify any field and click OK."),
                ("Stratigraphic Relationships",
                 "Go to Grid & Drawing → Harris Matrix. Use the 'Add relationship' form at the top to link "
                 "two contexts (e.g. Context 5 is above Context 3). Then click ▶ Build Matrix to render the diagram."),
            ]),
            ("🏺 Finds Recording", [
                ("Pottery",
                 "Go to Pottery tab. Click ＋ Add and fill in context number, form (Amphora, Bowl…), "
                 "part (Rim, Base…), count, origin, and period. Each record is linked to a context by context_num."),
                ("Artifacts",
                 "Go to Artifacts tab. The sub-tab ⚱ Artifacts holds the basic record; "
                 "🔍 Artifact Detail holds detailed catalogue entries including photos."),
                ("Skeletons & Bone Inventory",
                 "Go to Recording Sheet → 💀 Skeletons to record skeletal remains. "
                 "Use 🦴 Bone Form for the full bone inventory (bone-by-bone status for each skeleton)."),
            ]),
            ("📐 Harris Matrix", [
                ("Building the Matrix",
                 "First add contexts (Contexts tab) and relationships (Harris Matrix → Add relationship). "
                 "Click ▶ Build Matrix. The diagram shows contexts as boxes arranged from latest (top) to earliest (bottom). "
                 "Click a box to highlight it across all tabs."),
                ("Exporting the Matrix",
                 "Use Export SVG (vector, scalable) or Export PNG (raster at 2× resolution). "
                 "SVG is recommended for publication."),
                ("Unconnected Contexts",
                 "Contexts with no relationships appear in a separate row at the bottom of the diagram. "
                 "They are still included in the PDF Harris Matrix section."),
            ]),
            ("📄 PDF Export", [
                ("Opening the Report Designer",
                 "Click the 📄 PDF button in the sidebar footer. The Report Designer opens with three tabs: "
                 "Sections & Header (choose what to include and reorder), Page Layout, and Colours."),
                ("Reordering Sections",
                 "In the Sections panel, select a section in the list and use ▲ Move Up / ▼ Move Down. "
                 "The right panel shows a live preview of the page order."),
                ("Colour Schemes",
                 "Go to the Colours tab and choose a Quick Scheme (Manuscript, HFF green, Balamand blue…) "
                 "or enter custom #rrggbb hex values for each colour."),
                ("Context Detail Sheets",
                 "Each context can also be exported as a single-page summary via Context View → PDF Context. "
                 "This produces Frame H style sheets (header, info box, relationships, linked finds)."),
            ]),
            ("👤 Users & History", [
                ("Login",
                 "When the plugin starts, a login dialog asks for your name and favourite colour. "
                 "Your name appears in every history entry and in the History tab user badge."),
                ("Edit History",
                 "Every add, edit, and delete action is logged automatically. "
                 "Go to History tab to see who changed what and when. "
                 "Filter by user or date using the table's built-in column sorting."),
                ("Changing Your Name",
                 "Go to History tab and edit the 'Current user' field at the top."),
            ]),
            ("📷 Media Gallery", [
                ("Adding Files",
                 "Go to Media tab → Photos (or Field Drawings, or Documents). "
                 "Click ＋ Add file and select images or documents. "
                 "Image files show a thumbnail automatically."),
                ("Opening Files",
                 "Select a file in the gallery and click 📂 Open to open it with the system default application."),
            ]),
            ("⛏ Pre-Excavation Checklist", [
                ("Using the Checklist",
                 "Go to Pre-Excavation tab. Tick items as you complete them. "
                 "The progress counter updates automatically."),
                ("Saving & Loading",
                 "Click 💾 Save checklist to export the current list (with checked states) as a JSON file. "
                 "Click 📂 Load to restore a previously saved checklist."),
                ("Adding Items",
                 "Each section has a ＋ button to add a custom item. "
                 "Remove any item with its ✕ button."),
            ]),
        ]

        for sec_title, items in sections:
            sec_frame = QFrame(); sec_frame.setObjectName("card")
            sv = QVBoxLayout(sec_frame); sv.setContentsMargins(20, 16, 20, 16); sv.setSpacing(10)

            sec_lbl = QLabel(sec_title)
            sec_lbl.setObjectName("h4")
            sv.addWidget(sec_lbl)

            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            sep.setObjectName("hsep"); sep.setFixedHeight(1)
            sv.addWidget(sep)

            for q_title, q_text in items:
                q_lbl = QLabel(q_title)
                q_lbl.setObjectName("accentLabel")
                a_lbl = QLabel(q_text)
                a_lbl.setObjectName("muted")
                a_lbl.setWordWrap(True)
                sv.addWidget(q_lbl); sv.addWidget(a_lbl)

            outer.addWidget(sec_frame)

        outer.addStretch()
        scroll.setWidget(inner)
        page_vl = QVBoxLayout(page); page_vl.setContentsMargins(0,0,0,0)
        page_vl.addWidget(scroll)
        return page

    def _switch_nav_to(self, label_text):
        # Map old per-view names onto the new consolidated sections so existing
        # quick-action / workflow buttons keep working after the nav redesign.
        _alias = {
            "Contexts": "Stratigraphy", "Relationships": "Stratigraphy",
            "Context View": "Stratigraphy", "Harris Matrix": "Stratigraphy",
            "Grid & Drawing": "Field", "Pottery": "Finds", "Artifacts": "Finds",
            "Recording Sheet": "Recording", "Skeletons": "Recording",
            "Statistics": "Analysis", "Timeline": "Analysis",
            "History": "Provenance", "By Archaeologist": "Provenance",
            "Media": "Field",
        }
        label_text = _alias.get(label_text, label_text)
        for i, item in enumerate(self._nav_items):
            if item._label == label_text:
                self._switch_nav(i); return

    def _refresh_home_stats(self):
        # Update completion progress
        try: self._update_completion()
        except Exception: pass
        # Recent activity from history
        try:
            self._refresh_home_activity()
            self._refresh_home_overview()
            self._refresh_next_steps()
        except Exception: pass

    def _upload_site_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Site Photo", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path: return
        self._site_photo_path = path
        self._display_site_photo(path)
        # Save path in a per-site config
        import json
        cfg_path = user_data_path('.site_photos.json')
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path) as _f: cfg = json.load(_f)
            else:
                cfg = {}
        except Exception: cfg = {}
        cfg[getattr(self, '_current_site', 'default')] = path
        with open(cfg_path, 'w') as f: json.dump(cfg, f)

    def _display_site_photo(self, path):
        if not hasattr(self, '_site_photo_lbl'): return
        try:
            px = QPixmap(path)
            if not px.isNull():
                w = self._site_photo_lbl.width() or 320
                h = self._site_photo_lbl.height() or 160
                self._site_photo_lbl.setPixmap(
                    px.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._site_photo_lbl.setText("")
                self._site_photo_lbl.setStyleSheet("border:none;background:transparent;")
                self._site_photo_path = path
                if hasattr(self, '_photo_upload_btn'): self._photo_upload_btn.setVisible(False)
                if hasattr(self, '_photo_remove_btn'): self._photo_remove_btn.setVisible(True)
        except Exception: pass

    def _update_completion(self):
        """Recalculate overall data completion percentage."""
        if not hasattr(self, '_prog_bar'): return
        score = 0
        # Site connected?
        if getattr(self, '_current_site', ''):
            score += 20
        # Contexts?
        try:
            cb = getattr(self, 'ctx_layer_cb', None)
            if cb and cb.currentData():
                from qgis.core import QgsProject
                lyr = QgsProject.instance().mapLayer(cb.currentData())
                if lyr and lyr.featureCount() > 0: score += 20
        except Exception: pass
        # Pottery?
        try:
            cb = getattr(self, 'pot_layer_cb', None)
            if cb and cb.currentData():
                from qgis.core import QgsProject
                lyr = QgsProject.instance().mapLayer(cb.currentData())
                if lyr and lyr.featureCount() > 0: score += 20
        except Exception: pass
        # Artifacts?
        try:
            cb = getattr(self, 'art_layer_cb', None)
            if cb and cb.currentData():
                from qgis.core import QgsProject
                lyr = QgsProject.instance().mapLayer(cb.currentData())
                if lyr and lyr.featureCount() > 0: score += 20
        except Exception: pass
        # Relations defined?
        try:
            cb = getattr(self, 'ctx_rel_layer_cb', None)
            if cb and cb.currentData():
                from qgis.core import QgsProject
                lyr = QgsProject.instance().mapLayer(cb.currentData())
                if lyr and lyr.featureCount() > 0: score += 20
        except Exception: pass
        self._prog_bar.setValue(score)
        self._prog_pct_lbl.setText(f"{score}%")
        if score == 0:
            detail = "No site connected"
        elif score < 40:
            detail = "Getting started — connect site & add contexts"
        elif score < 80:
            detail = "In progress — keep recording finds"
        else:
            detail = "Well documented — all major categories filled"
        self._prog_detail.setText(detail)

    def _home_refresh_map(self):
        """Load connected vector layers into the dashboard map canvas."""
        if not getattr(self, '_home_canvas', None): return
        try:
            from qgis.core import QgsProject
            layers = [l for l in QgsProject.instance().mapLayers().values()]
            # show layers belonging to current site if known, else all
            site = getattr(self, '_current_site', '')
            vis = [l for l in layers if (not site or site.lower() in l.name().lower())]
            if not vis: vis = layers
            self._home_canvas.setLayers(vis)
            self._home_canvas.refresh()
            self._home_zoom_to_site()
        except Exception:
            pass

    def _home_zoom_to_site(self):
        if not getattr(self, '_home_canvas', None): return
        try:
            self._home_canvas.zoomToFullExtent()
        except Exception:
            pass

    def _load_site_photo(self):
        if not hasattr(self, '_site_photo_lbl'): return
        import json
        cfg_path = user_data_path('.site_photos.json')
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path) as _f: cfg = json.load(_f)
            else:
                cfg = {}
            path = cfg.get(getattr(self,'_current_site','default'),'')
            if path and os.path.exists(path):
                self._display_site_photo(path)
        except Exception: pass

    def _refresh_home_activity(self):
        if not hasattr(self, '_home_activity'): return
        while self._home_activity.count():
            it = self._home_activity.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        rows = []
        hist = self._lyr(self.hist_layer_cb) if hasattr(self, 'hist_layer_cb') else None
        if hist:
            feats = sorted(hist.getFeatures(),
                           key=lambda f: str(f.attribute('timestamp') or ''),
                           reverse=True)[:8]
            for f in feats:
                rows.append((str(f.attribute('action') or ''),
                             str(f.attribute('table_name') or ''),
                             str(f.attribute('timestamp') or '')))
        if not rows and hasattr(self, '_mem_history'):
            for r in list(reversed(self._mem_history))[:8]:
                rows.append((r[2], r[3][:30], r[0]))
        if not rows:
            lbl = QLabel("No activity yet — edits will appear here")
            _tc = getattr(self, '_current_theme', CLR)
            lbl.setStyleSheet(f"color:{_tc['text_muted']};font-size:{FONT_SIZE_SM};"
                              f"padding:16px 0;background:transparent;")
            lbl.setAlignment(Qt.AlignCenter)
            self._home_activity.addWidget(lbl)
            return
        icon_map = {'add':'➕','edit':'✏️','delete':'🗑️'}
        for action, table, ts in rows:
            _tc = getattr(self, '_current_theme', CLR)
            row = QFrame()
            row.setStyleSheet(f"background:{_tc['bg_card_2']};border-radius:{RADIUS_SM};")
            h = QHBoxLayout(row); h.setContentsMargins(10, 7, 10, 7); h.setSpacing(8)
            ic = QLabel(icon_map.get(action.lower(), '•'))
            ic.setStyleSheet("background:transparent;font-size:13px;")
            h.addWidget(ic)
            txt = QLabel(f"<b>{action.title()}</b> in {table}")
            txt.setStyleSheet(f"color:{_tc['text']};font-size:{FONT_SIZE_SM};background:transparent;")
            h.addWidget(txt); h.addStretch()
            t = QLabel(ts[-8:] if len(ts) > 8 else ts)
            t.setStyleSheet(f"color:{_tc['text_muted']};font-size:10px;background:transparent;")
            h.addWidget(t)
            self._home_activity.addWidget(row)

    def _refresh_home_overview(self):
        # Update the dashboard stat cards from the connected layers.
        def _count(cb):
            lyr = self._lyr(cb) if cb is not None else None
            try: return lyr.featureCount() if lyr else 0
            except Exception: return 0
        if hasattr(self, '_sc_contexts'):
            self._sc_contexts.set_value(_count(getattr(self, 'ctx_layer_cb', None)))
            self._sc_finds.set_value(_count(getattr(self, 'pot_layer_cb', None)) +
                                     _count(getattr(self, 'art_layer_cb', None)))
            self._sc_skeletons.set_value(_count(getattr(self, 'ske_layer_cb', None)))
            self._sc_drawings.set_value(_count(getattr(self, 'draw_layer_cb', None)))

    def _refresh_next_steps(self):
        if not hasattr(self, '_home_steps'): return
        while self._home_steps.count():
            it = self._home_steps.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        def _count(cb):
            lyr = self._lyr(cb) if cb is not None else None
            try: return lyr.featureCount() if lyr else 0
            except Exception: return 0
        connected = bool(getattr(self, '_current_site', ''))
        n_ctx = _count(getattr(self, 'ctx_layer_cb', None))
        n_rel = len(getattr(self, 'relationships', []) or []) + len(getattr(self, 'layer_rels', []) or [])
        steps = [
            (connected, "Connect a site", "Open a GeoPackage and connect its layers"),
            (n_ctx > 0, "Record contexts" + (" (%d)" % n_ctx if n_ctx else ""),
             "Add stratigraphic units under Stratigraphy"),
            (n_rel > 0, "Build the Harris Matrix",
             "Link contexts under Relationships, then Build Matrix"),
            (False, "Export the site report", "Generate a PDF once recording is complete"),
        ]
        _c = getattr(self, '_current_theme', CLR)
        for done, title, desc in steps:
            self._home_steps.addWidget(self._step_row(done, title, desc, _c))

    def _step_row(self, done, title, desc, c):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        h = QHBoxLayout(w); h.setContentsMargins(0, 6, 0, 6); h.setSpacing(10)
        dot = QLabel("\u2713" if done else "\u2022"); dot.setFixedSize(22, 22)
        dot.setAlignment(Qt.AlignCenter)
        col = c['status_ok'] if done else c['accent']
        dot.setStyleSheet(f"background:{col};color:#ffffff;border-radius:11px;"
                          f"font-weight:700;font-size:11px;")
        h.addWidget(dot)
        tcol = QVBoxLayout(); tcol.setSpacing(1)
        t = QLabel(title); t.setStyleSheet(f"color:{c['text']};font-size:12px;font-weight:600;background:transparent;")
        d = QLabel(desc); d.setStyleSheet(f"color:{c['text_dim']};font-size:10px;background:transparent;")
        tcol.addWidget(t); tcol.addWidget(d); h.addLayout(tcol, 1)
        return w

    def _add_basemap(self):
        """Add an OpenStreetMap XYZ basemap to the project (needs internet)."""
        try:
            from qgis.core import QgsProject, QgsRasterLayer
            for lyr in QgsProject.instance().mapLayers().values():
                if lyr.name() == "OpenStreetMap":
                    self._home_refresh_map(); self._msg("Basemap already added."); return
            url = ("type=xyz&url=https://tile.openstreetmap.org/"
                   "%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0")
            lyr = QgsRasterLayer(url, "OpenStreetMap", "wms")
            if not lyr.isValid():
                self._msg("Could not load basemap (needs internet).", error=True); return
            QgsProject.instance().addMapLayer(lyr)
            try:
                root = QgsProject.instance().layerTreeRoot()
                node = root.findLayer(lyr.id())
                if node is not None:
                    clone = node.clone(); root.insertChildNode(-1, clone)
                    root.removeChildNode(node)
            except Exception: pass
            self._home_refresh_map()
            self._msg("OpenStreetMap basemap added.")
        except Exception as e:
            self._msg(f"Basemap error: {e}", error=True)

    def _remove_site_photo(self):
        self._site_photo_path = None
        if hasattr(self, '_site_photo_lbl'):
            self._site_photo_lbl.setPixmap(QPixmap())
            self._site_photo_lbl.setText("No site photo")
        if hasattr(self, '_photo_upload_btn'): self._photo_upload_btn.setVisible(True)
        if hasattr(self, '_photo_remove_btn'): self._photo_remove_btn.setVisible(False)
        try:
            import json
            cfg_path = user_data_path('.site_photos.json')
            cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path) as _f: cfg = json.load(_f)
            cfg.pop(getattr(self, '_current_site', 'default'), None)
            with open(cfg_path, 'w') as _f: json.dump(cfg, _f)
        except Exception: pass

    def _build_layer_config_form(self, lf):
        def _rl(text):
            l = QLabel(text)
            return l
        def _sl(text):
            l = QLabel(text.upper()); l.setObjectName("mutedXs")
            return l
        lf.addRow(_sl("Contexts"))
        self.ctx_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.ctx_layer_cb)
        for attr, lbl in [('ctx_num_field','Num'),('ctx_type_field','Type'),
                          ('ctx_per_field','Period'),('ctx_desc_field','Desc'),
                          ('ctx_above_field','Above'),('ctx_below_field','Below'),
                          ('ctx_eq_field','Equals')]:
            cb = QComboBox(); setattr(self, attr, cb)
            lf.addRow(_rl(lbl+":"), cb)
        lf.addRow(_sl("Pottery"))
        self.pot_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.pot_layer_cb)
        self.pot_num_field = QComboBox()
        lf.addRow(_rl("Num:"), self.pot_num_field)
        lf.addRow(_sl("Artifacts"))
        self.art_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.art_layer_cb)
        self.art_num_field = QComboBox()
        lf.addRow(_rl("Num:"), self.art_num_field)
        lf.addRow(_sl("Crates"))
        self.crate_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.crate_layer_cb)
        lf.addRow(_sl("Skeletons"))
        self.ske_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.ske_layer_cb)
        self.ske_num_field = QComboBox()
        lf.addRow(_rl("Num:"), self.ske_num_field)
        lf.addRow(_sl("Bone Inventory"))
        self.bone_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.bone_layer_cb)
        lf.addRow(_sl("Artifact Details"))
        self.artdet_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.artdet_layer_cb)
        lf.addRow(_sl("Drawings"))
        self.draw_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.draw_layer_cb)
        lf.addRow(_sl("History"))
        self.hist_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.hist_layer_cb)
        lf.addRow(_sl("Relationships"))
        self.ctx_rel_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.ctx_rel_layer_cb)
        lf.addRow(_sl("Grid Map"))
        self.grid_layer_cb = QComboBox()
        lf.addRow(_rl("Layer:"), self.grid_layer_cb)
        if hasattr(self, '_on_ctx_layer'):
            self.ctx_layer_cb.currentIndexChanged.connect(self._on_ctx_layer)

    def _build_recording_sheets_tab(self):
        try:
            self._rec_sheets = RecordingSheetsTab(
                get_gpkg_path=self._current_gpkg_path,
                get_site=lambda: getattr(self, '_current_site', ''),
                get_user=lambda: getattr(self, '_current_user', 'Archaeologist'),
                on_msg=self._msg, parent=self)
            return self._rec_sheets
        except Exception as e:
            page = QWidget(); page.setStyleSheet("background:transparent;")
            vl = QVBoxLayout(page); vl.setContentsMargins(40,40,40,40)
            vl.addWidget(Card("Recording Sheets", f"Init error: {e}"))
            vl.addStretch()
            return page

    def _current_gpkg_path(self):
        for cb_name in ['ctx_layer_cb','pot_layer_cb','art_layer_cb','ske_layer_cb','bone_layer_cb']:
            cb = getattr(self, cb_name, None)
            if not cb: continue
            lyr = self._lyr(cb)
            if lyr:
                try:
                    uri = lyr.dataProvider().dataSourceUri()
                    if '.gpkg' in uri.lower(): return uri.split('|')[0]
                except Exception: continue
        return None

    def _build_matrix_tab(self):
        w=QWidget(); vl=QVBoxLayout(w); vl.setSpacing(12); vl.setContentsMargins(16, 16, 16, 16)
        rg=QGroupBox("Add relationship")
        self.rel_from=QComboBox(); self.rel_type_cb=QComboBox()
        self.rel_type_cb.addItems(REL_TYPES); self.rel_to=QComboBox()
        ar=QPushButton("Add"); ar.setObjectName("btn_primary"); ar.clicked.connect(self._add_rel)
        rel_row = QHBoxLayout(); rel_row.setSpacing(8)
        ctx_a_lbl = QLabel("A:"); ctx_a_lbl.setFixedWidth(18)
        rel_row.addWidget(ctx_a_lbl); rel_row.addWidget(self.rel_from, 1)
        rel_type_lbl = QLabel("rel:"); rel_type_lbl.setFixedWidth(24)
        rel_row.addWidget(rel_type_lbl); rel_row.addWidget(self.rel_type_cb, 1)
        ctx_b_lbl = QLabel("B:"); ctx_b_lbl.setFixedWidth(18)
        rel_row.addWidget(ctx_b_lbl); rel_row.addWidget(self.rel_to, 1)
        rel_row.addWidget(ar)
        rg_layout = QVBoxLayout(rg); rg_layout.addLayout(rel_row)
        vl.addWidget(rg)
        br=QHBoxLayout()
        bb=QPushButton("▶  Build Matrix"); bb.setObjectName("btn_secondary"); bb.clicked.connect(self._build_matrix)
        fit=QPushButton("Fit view"); fit.setObjectName("btn_ghost"); fit.clicked.connect(lambda:self.hv.fit())
        svg=QPushButton("Export SVG"); svg.setObjectName("btn_ghost"); svg.clicked.connect(self._exp_svg)
        png=QPushButton("Export PNG"); png.setObjectName("btn_ghost"); png.clicked.connect(self._exp_png)
        self._matrix_auto_arrange = QCheckBox("Auto-arrange by period")
        self._matrix_auto_arrange.stateChanged.connect(lambda: self._build_matrix())
        for b in [bb,fit,svg,png]: br.addWidget(b)
        br.addWidget(self._matrix_auto_arrange); br.addStretch()
        vl.addLayout(br); self.hv=HarrisView()
        self.hv.update_theme(
            bg_hex=getattr(self,'_current_theme',LIGHT_CLR).get('bg_card','#F8F5EE'),
            line_hex=getattr(self,'_current_theme',LIGHT_CLR).get('text','#2E2A26'),
            text_hex=getattr(self,'_current_theme',LIGHT_CLR).get('text_dim','#6F655B')
        )
        vl.addWidget(self.hv)
        return w

    def _build_ctx_tab(self):
        page = QWidget(); page.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(page); outer.setContentsMargins(0,0,0,0); outer.setSpacing(12)
        # Header row
        title = ContentTitle("Contexts", "Stratigraphic units and their attributes")
        outer.addWidget(title)
        # Filter + action bar
        bar = QHBoxLayout(); bar.setSpacing(8)
        self._ctx_search = SearchInput("Filter contexts by number, type, period...")
        self._ctx_search.textChanged.connect(self._filter_ctx_table)
        bar.addWidget(self._ctx_search, 1)
        for label, cb_name, variant in [
            ("＋  Add",        "_add_ctx",                          "btn_primary"),
            ("✏  Edit",        lambda: self._edit_row('ctx'),       "btn_secondary"),
            ("🔍  Zoom",       "_zoom_ctx",                         "btn_ghost"),
            ("＋  Column",     lambda: self._add_field(self._lyr(self.ctx_layer_cb)),  "btn_ghost"),
            ("🗑",            lambda: self._delete_rows(self.ctx_tbl, self._lyr(self.ctx_layer_cb), 'ctx'), "btn_danger"),
        ]:
            b = QPushButton(label); b.setObjectName(variant)
            b.setCursor(Qt.PointingHandCursor)
            if isinstance(cb_name, str):
                cb = getattr(self, cb_name, None)
                if cb: b.clicked.connect(cb)
            else:
                b.clicked.connect(cb_name)
            bar.addWidget(b)
        outer.addLayout(bar)
        # Split: table left + detail panel right
        split = QHBoxLayout(); split.setSpacing(14)
        # Table
        self.ctx_tbl = self._mktbl()
        self.ctx_tbl.itemSelectionChanged.connect(self._on_ctx_tbl_sel)
        self.ctx_tbl.itemSelectionChanged.connect(self._refresh_ctx_detail)
        split.addWidget(self.ctx_tbl, 3)
        # Detail panel
        side = QWidget(); side.setStyleSheet("background:transparent;")
        sv = QVBoxLayout(side); sv.setContentsMargins(0,0,0,0); sv.setSpacing(12)
        self._ctx_detail = DetailPanel("Context Details")
        sv.addWidget(self._ctx_detail)
        self._ctx_relations = DetailPanel("Relations")
        sv.addWidget(self._ctx_relations)
        sv.addStretch()
        side.setMinimumWidth(280); side.setMaximumWidth(340)
        split.addWidget(side, 1)
        outer.addLayout(split, 1)
        return page

    def _filter_ctx_table(self, text):
        """Filter visible rows in the contexts table."""
        text = (text or "").lower().strip()
        if not hasattr(self, "ctx_tbl"): return
        for r in range(self.ctx_tbl.rowCount()):
            show = True
            if text:
                show = False
                for c in range(self.ctx_tbl.columnCount()):
                    item = self.ctx_tbl.item(r, c)
                    if item and text in str(item.text()).lower():
                        show = True; break
            self.ctx_tbl.setRowHidden(r, not show)

    def _refresh_ctx_detail(self):
        """Show selected context info in the side detail panel."""
        if not hasattr(self, "_ctx_detail"): return
        rows = self.ctx_tbl.selectionModel().selectedRows() if self.ctx_tbl.selectionModel() else []
        if not rows:
            self._ctx_detail.clear(); self._ctx_relations.clear()
            self._ctx_detail.set_badge(""); self._ctx_relations.set_badge("")
            return
        ri = rows[0].row()
        fids = self.ctx_tbl.property("_fids") or []
        if ri >= len(fids): return
        lyr = self._lyr(self.ctx_layer_cb)
        if not lyr: return
        try:
            feat = lyr.getFeature(fids[ri])
            # Build detail panel
            self._ctx_detail.clear()
            ctx_num = self._safe_int(feat, self.ctx_num_field.currentText()) if self.ctx_num_field.currentText() != "— none —" else "?"
            self._ctx_detail.set_badge(f"ID {ctx_num}" if ctx_num else "")
            for label, fname_cb in [
                ("Context #", self.ctx_num_field),
                ("Type",      self.ctx_type_field),
                ("Period",    self.ctx_per_field),
                ("Description", self.ctx_desc_field),
            ]:
                fn = fname_cb.currentText()
                if fn and fn != "— none —":
                    v = feat.attribute(fn)
                    is_pill = label in ("Type", "Period")
                    self._ctx_detail.add_field(label, v, pill=is_pill)
            # Relations panel
            self._ctx_relations.clear()
            for label, fname_cb in [
                ("Above",  self.ctx_above_field),
                ("Below",  self.ctx_below_field),
                ("Equals", self.ctx_eq_field),
            ]:
                fn = fname_cb.currentText()
                if fn and fn != "— none —":
                    v = feat.attribute(fn)
                    self._ctx_relations.add_field(label, v)
        except Exception:
            pass

    def _build_linked_tab(self, label, pfx, add_to_nav=True):
        _META = {
            'pot': ('Pottery',   'Ceramic finds linked to excavation contexts'),
            'art': ('Artifacts', 'Non-ceramic finds linked to contexts'),
        }
        title_text, sub_text = _META.get(pfx, (label, ''))

        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # Page header
        vl.addWidget(ContentTitle(title_text, sub_text))

        # Search + context-filter bar
        bar_w = QWidget(); bar_w.setStyleSheet("background:transparent;")
        bar = QHBoxLayout(bar_w); bar.setContentsMargins(24, 6, 24, 6); bar.setSpacing(8)
        search = SearchInput(f"Search {title_text.lower()}…")
        bar.addWidget(search, 1)
        flbl = QLabel("Context #:"); flbl.setObjectName("mutedXs")
        fcb = QComboBox(); fcb.setEditable(True); fcb.addItem("All")
        fcb.setMinimumWidth(80)
        setattr(self, f"{pfx}_fcb", fcb)
        show_btn = QPushButton("Show"); show_btn.setObjectName("btn_secondary")
        show_btn.clicked.connect(partial(self._reload_linked, pfx))
        bar.addWidget(flbl); bar.addWidget(fcb); bar.addWidget(show_btn)
        vl.addWidget(bar_w)

        # Action strip
        ab = QWidget(); ab.setObjectName("actionBar")
        abl = QHBoxLayout(ab); abl.setContentsMargins(24, 6, 24, 6); abl.setSpacing(8)
        add_btn  = QPushButton("＋ Add");    add_btn.setObjectName("btn_primary")
        edit_btn = QPushButton("✏ Edit");   edit_btn.setObjectName("btn_secondary")
        col_btn  = QPushButton("＋ Column"); col_btn.setObjectName("btn_ghost")
        del_btn  = QPushButton("🗑 Delete"); del_btn.setObjectName("btn_danger")
        del_btn.setToolTip("Delete selected rows")
        add_btn.clicked.connect(partial(self._add_linked, pfx))
        edit_btn.clicked.connect(partial(self._edit_row, pfx))
        col_btn.clicked.connect(partial(
            lambda p, _: self._add_field(self._lyr(getattr(self, f"{p}_layer_cb"))), pfx))
        del_btn.clicked.connect(partial(
            lambda p, _: self._delete_rows(
                getattr(self, f'{p}_tbl'), self._lyr(getattr(self, f'{p}_layer_cb')), p), pfx))
        for b in (add_btn, edit_btn, col_btn): abl.addWidget(b)
        abl.addStretch(); abl.addWidget(del_btn)
        vl.addWidget(ab)

        # Table
        tbl_w = QWidget(); tbl_w.setStyleSheet("background:transparent;")
        tbl_vl = QVBoxLayout(tbl_w); tbl_vl.setContentsMargins(16, 8, 16, 16)
        tbl = self._mktbl(); setattr(self, f"{pfx}_tbl", tbl)
        tbl_vl.addWidget(tbl)
        vl.addWidget(tbl_w, 1)

        # Live search filter
        def _filter(text, t=tbl):
            txt = (text or "").lower().strip()
            for r in range(t.rowCount()):
                vis = not txt or any(
                    txt in (t.item(r, c).text() if t.item(r, c) else "").lower()
                    for c in range(t.columnCount()))
                t.setRowHidden(r, not vis)
        search.textChanged.connect(_filter)

        if add_to_nav:
            self.tabs.addTab(w, label)
        return w

    def _build_skeleton_tab(self):
        """Skeleton records list — header data for each skeleton"""
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        vl.addWidget(ContentTitle("Skeletons",
                                  "Individual burial records — open Bone Form for detailed inventory"))

        # Action strip
        ab = QWidget(); ab.setObjectName("actionBar")
        abl = QHBoxLayout(ab); abl.setContentsMargins(24, 6, 24, 6); abl.setSpacing(8)
        add_btn  = QPushButton("＋ New skeleton");   add_btn.setObjectName("btn_primary")
        edit_btn = QPushButton("✏ Edit selected");   edit_btn.setObjectName("btn_secondary")
        form_btn = QPushButton("📋 Open bone form"); form_btn.setObjectName("btn_secondary")
        col_btn  = QPushButton("＋ Column");          col_btn.setObjectName("btn_ghost")
        del_btn  = QPushButton("🗑 Delete");          del_btn.setObjectName("btn_danger")
        add_btn.clicked.connect(self._add_skeleton)
        edit_btn.clicked.connect(lambda: self._edit_row('ske'))
        form_btn.clicked.connect(self._open_bone_form)
        col_btn.clicked.connect(lambda: self._add_field(self._lyr(self.ske_layer_cb)))
        del_btn.clicked.connect(lambda: self._delete_rows(self.ske_tbl, self._lyr(self.ske_layer_cb), 'ske'))
        for b in (add_btn, edit_btn, form_btn, col_btn): abl.addWidget(b)
        abl.addStretch(); abl.addWidget(del_btn)
        vl.addWidget(ab)

        # Search
        srch_w = QWidget(); srch_w.setStyleSheet("background:transparent;")
        srch_l = QHBoxLayout(srch_w); srch_l.setContentsMargins(24, 6, 24, 4); srch_l.setSpacing(0)
        self._ske_search = SearchInput("Search skeletons…")
        srch_l.addWidget(self._ske_search)
        vl.addWidget(srch_w)

        # Table
        tbl_w = QWidget(); tbl_w.setStyleSheet("background:transparent;")
        tbl_vl = QVBoxLayout(tbl_w); tbl_vl.setContentsMargins(16, 4, 16, 16)
        self.ske_tbl = self._mktbl()
        self.ske_tbl.setProperty("_fids", [])
        tbl_vl.addWidget(self.ske_tbl)
        vl.addWidget(tbl_w, 1)

        def _filter(text, t=self.ske_tbl):
            txt = (text or "").lower().strip()
            for r in range(t.rowCount()):
                vis = not txt or any(
                    txt in (t.item(r, c).text() if t.item(r, c) else "").lower()
                    for c in range(t.columnCount()))
                t.setRowHidden(r, not vis)
        self._ske_search.textChanged.connect(_filter)
        return w


    def _ensure_field(self, lyr, name, qtype):
        """Add a field to a layer if it doesn't already have it."""
        if lyr is not None and lyr.fields().indexOf(name) < 0:
            try:
                lyr.dataProvider().addAttributes([QgsField(name, qtype)])
                lyr.updateFields()
            except Exception:
                pass

    def _import_match_photos(self):
        """Scan a folder of artifact photos named like 'BAR23-101.004 (1)',
        copy them into the project, and match each to an Artifact Detail record
        by context + object number (one main photo shown per artifact; all
        photos go to Media → Photos)."""
        import shutil, re
        folder = QFileDialog.getExistingDirectory(self, "Select the folder of artifact photos")
        if not folder:
            return
        lyr = self._lyr(getattr(self, 'artdet_layer_cb', None))
        if not lyr:
            lyr = self._create_simple_layer('artifact_details', path=self._current_gpkg_path())
            if lyr is None:
                QMessageBox.warning(self, "", "Set or create an Artifact Details layer first "
                                    "(Layer Configuration → Artifact Detail)."); return
            self._refresh_combos()
            for i in range(self.artdet_layer_cb.count()):
                if self.artdet_layer_cb.itemData(i) == lyr.id():
                    self.artdet_layer_cb.setCurrentIndex(i); break
        self._ensure_field(lyr, 'context_num', QVariant.Int)
        self._ensure_field(lyr, 'find_num', QVariant.Int)
        self._ensure_field(lyr, 'image_path', QVariant.String)
        gpkg = self._current_gpkg_path()
        base = os.path.dirname(gpkg) if gpkg else user_data_dir()
        dest = os.path.join(base, "ArchManager_media", "artifacts")
        try: os.makedirs(dest, exist_ok=True)
        except Exception: pass
        # Parse SITE-CONTEXT.OBJ (PHOTO) — the context.object pair plus optional (n)
        pat = re.compile(r'(\d+)\s*\.\s*(\d+)\s*(?:\((\d+)\))?')
        exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif')
        groups = {}
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(exts): continue
            m = pat.search(os.path.splitext(fn)[0])
            if not m: continue
            ctx = int(m.group(1)); obj = int(m.group(2)); ph = int(m.group(3) or 1)
            groups.setdefault((ctx, obj), []).append((ph, os.path.join(folder, fn)))
        if not groups:
            QMessageBox.information(self, "Photo import",
                "No photos matched the naming pattern, e.g. BAR23-101.004 (1).jpg"); return
        if not isinstance(getattr(self, '_photo_registry', None), dict):
            self._photo_registry = {'photos': [], 'drawings': [], 'refs': []}
        self._photo_registry.setdefault('photos', [])
        idx_img = lyr.fields().indexOf('image_path')
        idx_find = lyr.fields().indexOf('find_num')
        existing = {}
        for f in lyr.getFeatures():
            existing[(safe_int(f, 'context_num'), safe_int(f, 'find_num'))] = f.id()
        copied = matched = created = 0
        lyr.startEditing()
        for (ctx, obj), photos in sorted(groups.items()):
            photos.sort()
            main_path = None
            for ph, src in photos:
                dst = os.path.join(dest, os.path.basename(src))
                try:
                    if os.path.abspath(src) != os.path.abspath(dst) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
                    copied += 1
                except Exception:
                    dst = src
                if main_path is None: main_path = dst
                self._photo_registry['photos'].append(
                    {'path': dst, 'context': str(ctx), 'caption': f"Artifact {ctx}.{obj:03d} ({ph})"})
            fid = existing.get((ctx, obj))
            if fid is not None:
                if idx_img >= 0: lyr.changeAttributeValue(fid, idx_img, main_path)
                matched += 1
            else:
                feat = QgsFeature(lyr.fields())
                feat.setAttribute('context_num', ctx)
                if idx_find >= 0: feat.setAttribute('find_num', obj)
                if idx_img >= 0: feat.setAttribute('image_path', main_path)
                lyr.addFeature(feat); created += 1
        lyr.commitChanges()
        self._save_gallery_registry(); self._load_gallery_registry()
        try: self._load_artdet_list()
        except Exception: pass
        QMessageBox.information(self, "Photo import",
            f"Copied {copied} photo(s) into the project gallery.\n"
            f"Matched {matched} existing and created {created} new artifact record(s).\n\n"
            f"One photo is shown per artifact; all photos are in Media → Photos.")

    def _build_artdet_tab(self):
        """Artifact detail sub-form: image + full description per artifact ID"""
        w = QWidget(); w.setStyleSheet("background:transparent;")
        outer_vl = QVBoxLayout(w); outer_vl.setContentsMargins(0, 0, 0, 0); outer_vl.setSpacing(0)
        outer_vl.addWidget(ContentTitle("Artifact Detail",
                                        "Image and extended description for each artifact find"))
        _tb = QHBoxLayout(); _tb.setContentsMargins(16, 0, 16, 0)
        _imp = QPushButton("📷  Import && match photos…"); _imp.setObjectName("btn_primary")
        _imp.setCursor(Qt.PointingHandCursor)
        _imp.setToolTip("Pick a folder of photos named like 'BAR23-101.004 (1).jpg' — "
                        "they are copied into the project and matched to artifacts by "
                        "context.object number")
        _imp.clicked.connect(self._import_match_photos)
        _tb.addStretch(); _tb.addWidget(_imp)
        outer_vl.addLayout(_tb)
        body = QWidget(); body.setStyleSheet("background:transparent;")
        main = QHBoxLayout(body); main.setContentsMargins(16, 8, 16, 16); main.setSpacing(12)
        outer_vl.addWidget(body, 1)
        # Left: artifact list
        left=QWidget(); lv=QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        lbl = QLabel("Select artifact"); lbl.setObjectName("h4"); lv.addWidget(lbl)
        self.artdet_list=QTableWidget()
        self.artdet_list.setColumnCount(3)
        self.artdet_list.setHorizontalHeaderLabels(["ID","Context","Type"])
        self.artdet_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.artdet_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.artdet_list.setMaximumWidth(240)
        self.artdet_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.artdet_list.itemSelectionChanged.connect(self._on_artdet_select)
        lv.addWidget(self.artdet_list,1)
        reload_art=QPushButton("↻ Reload list"); reload_art.setObjectName("btn_secondary"); reload_art.clicked.connect(self._load_artdet_list)
        lv.addWidget(reload_art)
        main.addWidget(left)
        # Right: detail form + image
        right=QWidget(); rv=QVBoxLayout(right); rv.setContentsMargins(0,0,0,0)
        # Header showing selected artifact
        self.artdet_header=QLabel("<i>Select an artifact to see/edit its detail record</i>")
        self.artdet_header.setObjectName("infoBox")
        self.artdet_header.setWordWrap(True); rv.addWidget(self.artdet_header)
        # Image area
        self.artdet_img_label=QLabel()
        self.artdet_img_label.setMinimumHeight(180); self.artdet_img_label.setAlignment(Qt.AlignCenter)
        self.artdet_img_label.setObjectName("imageSlot")
        self.artdet_img_label.setText("📷  No image")
        rv.addWidget(self.artdet_img_label)
        img_row=QHBoxLayout()
        pick_img=QPushButton("📷 Set image…"); pick_img.setObjectName("btn_secondary"); pick_img.clicked.connect(self._pick_artdet_image)
        clear_img=QPushButton("✕ Clear"); clear_img.setObjectName("btn_danger"); clear_img.clicked.connect(self._clear_artdet_image)
        img_row.addWidget(pick_img); img_row.addWidget(clear_img); img_row.addStretch()
        rv.addLayout(img_row)
        # Fields
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        form_w=QWidget(); ff=QFormLayout(form_w); ff.setSpacing(4)
        self._artdet_fields={}
        field_defs=[
            ("detailed_description","Detailed description"),
            ("condition","Condition"),
            ("material_detail","Material detail"),
            ("provenance","Provenance"),
            ("dimensions","Dimensions (L×W×H)"),
            ("parallels","Parallels / comparanda"),
            ("notes","Notes"),
        ]
        for fname,flabel in field_defs:
            te=QTextEdit(); te.setMaximumHeight(60)
            te.setPlaceholderText(flabel)
            self._artdet_fields[fname]=te; ff.addRow(flabel+":",te)
        scroll.setWidget(form_w); rv.addWidget(scroll,1)
        # Save / new buttons
        sbr=QHBoxLayout()
        save_btn=QPushButton("💾 Save detail record")
        save_btn.setObjectName("btn_primary")
        save_btn.clicked.connect(self._save_artdet)
        del_btn=QPushButton("🗑 Delete record"); del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._delete_artdet)
        for b in [save_btn,del_btn]: sbr.addWidget(b)
        rv.addLayout(sbr)
        main.addWidget(right,1)
        self._artdet_image_path=""
        self._artdet_current_id=None
        return w

    def _load_artdet_list(self):
        art_lyr=self._lyr(self.art_layer_cb)
        if not art_lyr: return
        fnames=[f.name() for f in art_lyr.fields()]
        # Identify key columns
        id_fn    = next((f for f in ['id','fid','artifact_id'] if f in fnames), fnames[0] if fnames else None)
        ctx_fn   = next((f for f in ['context_num','ctx_num','context_id'] if f in fnames), None)
        type_fn  = next((f for f in ['type','material','description'] if f in fnames), None)
        feats=list(art_lyr.getFeatures())
        self.artdet_list.setRowCount(len(feats))
        self.artdet_list.setProperty("_art_ids",[f.id() for f in feats])
        self.artdet_list.setProperty("_art_nums",[])
        art_nums=[]
        for ri,feat in enumerate(feats):
            aid=feat.attribute(id_fn) if id_fn else feat.id()
            ctx=feat.attribute(ctx_fn) if ctx_fn else ""
            typ=feat.attribute(type_fn) if type_fn else ""
            art_nums.append(aid)
            for ci,v in enumerate([aid,ctx,typ]):
                self.artdet_list.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))
        self.artdet_list.setProperty("_art_nums",art_nums)

    def _on_artdet_select(self):
        rows=self.artdet_list.selectionModel().selectedRows()
        if not rows: return
        ri=rows[0].row()
        art_nums=self.artdet_list.property("_art_nums") or []
        if ri>=len(art_nums): return
        aid=art_nums[ri]
        self._artdet_current_id=aid
        # Update header
        items=[self.artdet_list.item(ri,c) for c in range(3)]
        vals=[it.text() if it else "" for it in items]
        self.artdet_header.setText(f"<b>Artifact ID {vals[0]}</b>  |  Context: {vals[1]}  |  {vals[2]}")
        # Load existing detail record
        for te in self._artdet_fields.values(): te.clear()
        self._artdet_image_path=""
        self.artdet_img_label.setText("No image")
        det_lyr=self._lyr(self.artdet_layer_cb)
        if not det_lyr: return
        for feat in det_lyr.getFeatures():
            try:
                if str(feat.attribute('artifact_id'))==str(aid):
                    for fname,te in self._artdet_fields.items():
                        v=feat.attribute(fname)
                        if v: te.setPlainText(str(v))
                    ip=feat.attribute('image_path')
                    if ip and str(ip).strip():
                        self._artdet_image_path=str(ip)
                        self._show_artdet_image(str(ip))
                    break
            except Exception: pass

    def _pick_artdet_image(self):
        p,_=QFileDialog.getOpenFileName(self,"Select image","","Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if p: self._artdet_image_path=p; self._show_artdet_image(p)

    def _show_artdet_image(self,path):
        if not path or not os.path.exists(path):
            self.artdet_img_label.setText("Image not found"); return
        px=QPixmap(path)
        if px.isNull(): self.artdet_img_label.setText("Cannot load image"); return
        self.artdet_img_label.setPixmap(px.scaled(self.artdet_img_label.width()-4,
            self.artdet_img_label.height()-4, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _clear_artdet_image(self):
        self._artdet_image_path=""; self.artdet_img_label.setText("No image")

    def _save_artdet(self):
        if self._artdet_current_id is None:
            QMessageBox.warning(self,"","Select an artifact first."); return
        det_lyr=self._lyr(self.artdet_layer_cb)
        if not det_lyr: QMessageBox.warning(self,"","Set artifact_details layer first."); return
        # Find art context_num
        art_lyr=self._lyr(self.art_layer_cb); ctx_num=None
        if art_lyr:
            for feat in art_lyr.getFeatures():
                fnames=[f.name() for f in art_lyr.fields()]
                id_fn=next((f for f in ['id','fid','artifact_id'] if f in fnames), fnames[0] if fnames else None)
                ctx_fn=next((f for f in ['context_num','ctx_num'] if f in fnames), None)
                try:
                    if str(feat.attribute(id_fn))==str(self._artdet_current_id):
                        ctx_num=feat.attribute(ctx_fn) if ctx_fn else None; break
                except Exception: pass
        # Delete existing
        det_lyr.startEditing()
        to_del=[f.id() for f in det_lyr.getFeatures()
                if str(f.attribute('artifact_id'))==str(self._artdet_current_id)]
        det_lyr.deleteFeatures(to_del)
        # Add new
        fields=det_lyr.fields()
        feat=QgsFeature(fields)
        feat.setAttribute('artifact_id',coerce(self._artdet_current_id,QVariant.Int))
        if ctx_num is not None: feat.setAttribute('context_num',coerce(ctx_num,QVariant.Int))
        feat.setAttribute('image_path',self._artdet_image_path or "")
        for fname,te in self._artdet_fields.items():
            feat.setAttribute(fname,te.toPlainText())
        det_lyr.addFeature(feat)
        ok=det_lyr.commitChanges()
        if ok: self._msg(f"Artifact detail saved (ID {self._artdet_current_id})")
        else: det_lyr.rollBack(); self._msg("Save failed")

    def _delete_artdet(self):
        if self._artdet_current_id is None: return
        det_lyr=self._lyr(self.artdet_layer_cb)
        if not det_lyr: return
        det_lyr.startEditing()
        to_del=[f.id() for f in det_lyr.getFeatures()
                if str(f.attribute('artifact_id'))==str(self._artdet_current_id)]
        if not to_del: self._msg("No detail record found"); return
        det_lyr.deleteFeatures(to_del); det_lyr.commitChanges()
        for te in self._artdet_fields.values(): te.clear()
        self.artdet_img_label.setText("No image")
        self._msg(f"Detail record deleted")


    def _build_context_detail_tab(self):
        """Cross-reference view: select a context, see all linked data."""
        from qgis.PyQt.QtWidgets import QSplitter, QTreeWidget, QTreeWidgetItem
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # Page header
        vl.addWidget(ContentTitle("Context View",
                                  "All linked finds and relationships for a single context"))

        # Selector bar
        sel_w = QWidget(); sel_w.setStyleSheet("background:transparent;")
        top = QHBoxLayout(sel_w); top.setContentsMargins(24, 8, 24, 4); top.setSpacing(8)
        ctx_lbl = QLabel("Context #:"); ctx_lbl.setObjectName("mutedXs")
        self.ctxdet_cb = QComboBox(); self.ctxdet_cb.setEditable(True)
        self.ctxdet_cb.setMinimumWidth(120)
        show_btn = QPushButton("Show all linked data"); show_btn.setObjectName("btn_secondary")
        show_btn.clicked.connect(self._load_context_detail)
        pdf_ctx = QPushButton("📄 Export context PDF"); pdf_ctx.setObjectName("btn_purple")
        pdf_ctx.clicked.connect(self._export_context_pdf)
        self.ctxdet_norel = QCheckBox("Highlight contexts with no relationships")
        top.addWidget(ctx_lbl); top.addWidget(self.ctxdet_cb)
        top.addWidget(show_btn); top.addWidget(pdf_ctx); top.addStretch()
        top.addWidget(self.ctxdet_norel)
        vl.addWidget(sel_w)

        # Info banner
        self.ctxdet_header = QLabel("<i>Select a context number and click Show</i>")
        self.ctxdet_header.setObjectName("infoBox")
        self.ctxdet_header.setWordWrap(True)
        hdr_w = QWidget(); hdr_w.setStyleSheet("background:transparent;")
        hdr_l = QHBoxLayout(hdr_w); hdr_l.setContentsMargins(24, 4, 24, 8)
        hdr_l.addWidget(self.ctxdet_header)
        vl.addWidget(hdr_w)

        # Sub-tabs for linked data
        self.ctxdet_tabs = QTabWidget()
        self.ctxdet_tabs.setObjectName("subTabs")

        self.ctxdet_pot_tbl = self._mktbl()
        self.ctxdet_tabs.addTab(self.ctxdet_pot_tbl, "🏺 Pottery")

        self.ctxdet_art_tbl = self._mktbl()
        self.ctxdet_tabs.addTab(self.ctxdet_art_tbl, "⚱ Artifacts")

        self.ctxdet_ske_tbl = self._mktbl()
        self.ctxdet_tabs.addTab(self.ctxdet_ske_tbl, "💀 Skeletons")

        self.ctxdet_per_tbl = self._mktbl()
        self.ctxdet_tabs.addTab(self.ctxdet_per_tbl, "📅 Periods & Dates")

        self.ctxdet_rel_tbl = self._mktbl()
        self.ctxdet_tabs.addTab(self.ctxdet_rel_tbl, "🔗 Strat. Relations")

        vl.addWidget(self.ctxdet_tabs, 1)
        return w

    def _load_context_detail(self):
        from .dock import REL_LABELS
        num_str=self.ctxdet_cb.currentText().strip()
        if not num_str: QMessageBox.warning(self,"","Enter a context number."); return
        try: num=int(num_str)
        except Exception: QMessageBox.warning(self,"","Context number must be an integer."); return

        ctx=self.ctx_data.get(num,{})
        info_parts=[f"<b>Context {num}</b>"]
        for k in ['type','period','description']:
            v=ctx.get(k,'')
            if v: info_parts.append(f"{k.title()}: <b>{v}</b>")
        self.ctxdet_header.setText("  |  ".join(info_parts))

        nf_ctx=self.ctx_num_field.currentText()

        def fill_linked(lyr,lcb,nfcb,tbl):
            tbl.clearContents(); tbl.setRowCount(0)
            lyr2=self._lyr(lcb); nf=nfcb.currentText()
            if not lyr2 or nf=="— none —": return
            fnames=[f.name() for f in lyr2.fields()]
            tbl.setColumnCount(len(fnames)); tbl.setHorizontalHeaderLabels(fnames)
            feats=[f for f in lyr2.getFeatures()
                   if (lambda v: v==num)(self._safe_int(f,nf) or -1)]
            tbl.setRowCount(len(feats))
            for ri,feat in enumerate(feats):
                for ci,fn in enumerate(fnames):
                    v=feat.attribute(fn)
                    tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

        fill_linked(None,self.pot_layer_cb,self.pot_num_field,self.ctxdet_pot_tbl)
        fill_linked(None,self.art_layer_cb,self.art_num_field,self.ctxdet_art_tbl)
        fill_linked(None,self.ske_layer_cb,self.ske_num_field,self.ctxdet_ske_tbl)

        # Periods summary — collect from all layers
        periods={}
        for lcb,nfcb,src_name in [
            (self.pot_layer_cb,self.pot_num_field,"Pottery"),
            (self.art_layer_cb,self.art_num_field,"Artifact"),
            (self.ske_layer_cb,self.ske_num_field,"Skeleton"),
        ]:
            lyr2=self._lyr(lcb); nf=nfcb.currentText()
            if not lyr2 or nf=="— none —": continue
            fnames=[f.name() for f in lyr2.fields()]
            per_fields=[f for f in fnames if any(k in f.lower() for k in ['period','date','century','phase'])]
            for feat in lyr2.getFeatures():
                try:
                    if self._safe_int(feat,nf)!=num: continue
                except Exception: continue
                for pf in per_fields:
                    v=str(feat.attribute(pf) or '').strip()
                    if v and v.lower() not in ('null','none',''):
                        key=(v,pf)
                        if key not in periods: periods[key]={'source':src_name,'field':pf,'value':v,'count':0}
                        periods[key]['count']+=1
        # Context own period
        ctx_lyr=self._lyr(self.ctx_layer_cb); pf=self.ctx_per_field.currentText()
        if ctx_lyr and pf!="— none —":
            for feat in ctx_lyr.getFeatures():
                try:
                    if self._safe_int(feat,nf_ctx)!=num: continue
                except Exception: continue
                v=str(feat.attribute(pf) or '').strip()
                if v and v.lower() not in ('null','none',''):
                    key=(v,'context')
                    if key not in periods: periods[key]={'source':'Context','field':'period','value':v,'count':1}

        self.ctxdet_per_tbl.setColumnCount(3)
        self.ctxdet_per_tbl.setHorizontalHeaderLabels(["Period / Date","From","Count"])
        rows_p=sorted(periods.values(), key=lambda x: x['value'])
        self.ctxdet_per_tbl.setRowCount(len(rows_p))
        for ri,d in enumerate(rows_p):
            self.ctxdet_per_tbl.setItem(ri,0,QTableWidgetItem(d['value']))
            self.ctxdet_per_tbl.setItem(ri,1,QTableWidgetItem(d['source']))
            self.ctxdet_per_tbl.setItem(ri,2,QTableWidgetItem(str(d['count'])))

        # Relationships
        all_r=self.relationships+getattr(self,'layer_rels',[])
        ctx_rels=[r for r in all_r if r['from_ctx']==num or r['to_ctx']==num]
        self.ctxdet_rel_tbl.setColumnCount(3)
        self.ctxdet_rel_tbl.setHorizontalHeaderLabels(["Context A","Relationship","Context B"])
        self.ctxdet_rel_tbl.setRowCount(len(ctx_rels))
        for ri,r in enumerate(ctx_rels):
            self.ctxdet_rel_tbl.setItem(ri,0,QTableWidgetItem(str(r['from_ctx'])))
            self.ctxdet_rel_tbl.setItem(ri,1,QTableWidgetItem(REL_LABELS.get(r['rel_type'],r['rel_type'])))
            self.ctxdet_rel_tbl.setItem(ri,2,QTableWidgetItem(str(r['to_ctx'])))

        self._msg(f"Context {num}: {self.ctxdet_pot_tbl.rowCount()} pottery, "
                  f"{self.ctxdet_art_tbl.rowCount()} artifacts, "
                  f"{self.ctxdet_ske_tbl.rowCount()} skeletons, "
                  f"{len(ctx_rels)} rels")

    def _build_bone_form_tab(self):
        import os
        from .bone_view import SkeletonView, JS_MAP, STATUS_REMAP
        self._js_map = JS_MAP; self._status_remap = STATUS_REMAP
        w=QWidget(); vl=QVBoxLayout(w); vl.setContentsMargins(4,4,4,4); vl.setSpacing(4)
        hdr=QGroupBox("Skeleton"); hf=QFormLayout(hdr); hf.setSpacing(3)
        hr=QHBoxLayout()
        self.bone_form_ske_cb=QComboBox(); self.bone_form_ske_cb.setEditable(True)
        self.bone_form_ske_cb.currentTextChanged.connect(self._load_bone_form)
        self.bone_form_type=QComboBox()
        self.bone_form_type.addItems(['Adult','Child-Adolescent','Young Child','Perinatal-Infant'])
        self.bone_form_grave=QLineEdit(); self.bone_form_site=QLineEdit()
        self.bone_form_age=QComboBox(); self.bone_form_age.addItems(AGE_GROUPS)
        self.bone_form_sex=QComboBox(); self.bone_form_sex.addItems(SEX_OPTIONS)
        self.bone_form_notes=QLineEdit()
        hr.addWidget(QLabel("Skeleton #:")); hr.addWidget(self.bone_form_ske_cb)
        hr.addWidget(QLabel("Form:")); hr.addWidget(self.bone_form_type)
        hr.addWidget(QLabel("Grave:")); hr.addWidget(self.bone_form_grave)
        hr.addWidget(QLabel("Site:")); hr.addWidget(self.bone_form_site)
        hf.addRow(hr); hr2=QHBoxLayout()
        hr2.addWidget(QLabel("Age:")); hr2.addWidget(self.bone_form_age)
        hr2.addWidget(QLabel("Sex:")); hr2.addWidget(self.bone_form_sex)
        hr2.addWidget(QLabel("Notes:")); hr2.addWidget(self.bone_form_notes,1)
        hf.addRow(hr2); vl.addWidget(hdr)
        br2=QHBoxLayout()
        save=QPushButton("💾  Save bone record to layer")
        save.setObjectName("btn_primary")
        save.clicked.connect(self._save_bone_form)
        clear=QPushButton("Clear all"); clear.clicked.connect(self._clear_bone_form)
        for b in [save,clear]: br2.addWidget(b)
        vl.addLayout(br2)
        plugin_dir=os.path.dirname(os.path.abspath(__file__))
        svg_path=os.path.join(plugin_dir,'skeleton_custom.svg')
        self._skel_view=SkeletonView(parent=w)
        vl.addWidget(self._skel_view,1)
        return w

    def _after_load_bone_view(self, ske_num):
        if not hasattr(self,'_skel_view'): return
        bone_lyr=self._lyr(self.bone_layer_cb)
        if not bone_lyr: return
        rmap={'Complete':'complete','Fragmentary':'frag',
              'Precise ID/side unknown':'unknown','Highly Crushed/distorted':'crushed',
              'Sampled (14C/DNA/isotopes)':'sampled','Sampled':'sampled',
              'Estimated':'estimated','Tooth found isolated':'isolated'}
        jm=getattr(self,'_js_map',{})
        rev={(v[1],v[2],v[3]):k for k,v in jm.items()}
        data={}
        for feat in bone_lyr.getFeatures():
            try:
                if self._safe_int(feat,'skeleton_num')!=ske_num: continue
                bone=str(feat.attribute('bone') or ''); side=str(feat.attribute('side') or '')
                seg=str(feat.attribute('segment') or ''); status=str(feat.attribute('status') or '')
                bid=rev.get((bone,side,seg))
                if bid and status: data[bid]=rmap.get(status,'none')
            except Exception: pass
        self._skel_view.load_data(data)

    def _build_rel_tab(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        title = ContentTitle("Stratigraphic Relationships",
                             "Links between contexts — from the Harris Matrix and layer fields")
        vl.addWidget(title)

        # Info card
        info_frame = QFrame(); info_frame.setObjectName("infoCard")
        info_h = QHBoxLayout(info_frame); info_h.setContentsMargins(14, 10, 14, 10); info_h.setSpacing(8)
        info_icon = QLabel("ℹ"); info_icon.setFixedWidth(18)
        info_icon.setStyleSheet("font-size:15px;background:transparent;")
        info_txt = QLabel("Add relationships in Grid & Drawing → Harris Matrix, then click ▶ Build Matrix.\n"
                          "Relationships from layer fields appear automatically when you load data.")
        info_txt.setWordWrap(True)
        info_h.addWidget(info_icon); info_h.addWidget(info_txt, 1)
        body = QWidget(); body.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(body); bv.setContentsMargins(24, 12, 24, 24); bv.setSpacing(12)
        bv.addWidget(info_frame)

        # Action row
        act = QHBoxLayout(); act.setSpacing(8)
        d = QPushButton("🗑  Delete selected (manual only)")
        d.setObjectName("btn_danger"); d.clicked.connect(self._del_rel)
        act.addStretch(); act.addWidget(d)
        bv.addLayout(act)

        self.rel_tbl = QTableWidget(0, 4)
        self.rel_tbl.setHorizontalHeaderLabels(["Context A", "Relationship", "Context B", "Source"])
        self.rel_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rel_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rel_tbl.setAlternatingRowColors(True)
        self.rel_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rel_tbl.verticalHeader().setVisible(False)
        bv.addWidget(self.rel_tbl, 1)

        vl.addWidget(body, 1)
        return w

    def _build_import_tab(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        vl.addWidget(ContentTitle("Import Data",
                                  "Bring in existing records from Excel or CSV files"))
        body = QWidget(); body.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(body); bv.setContentsMargins(32, 16, 32, 32); bv.setSpacing(16)

        # Info card
        info_frame = QFrame(); info_frame.setObjectName("infoCard")
        il = QHBoxLayout(info_frame); il.setContentsMargins(14, 10, 14, 10); il.setSpacing(8)
        ii = QLabel("ℹ"); ii.setFixedWidth(18); ii.setStyleSheet("font-size:15px;background:transparent;")
        it = QLabel("Column names are auto-matched to your layer fields. "
                    "You can adjust the mapping in the preview dialog before confirming.")
        it.setWordWrap(True)
        il.addWidget(ii); il.addWidget(it, 1)
        bv.addWidget(info_frame)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        xl = QPushButton("📂  Open Excel (.xlsx)…"); xl.setObjectName("btn_primary")
        xl.clicked.connect(self._imp_xl)
        cv = QPushButton("📂  Open CSV…"); cv.setObjectName("btn_secondary")
        cv.clicked.connect(self._imp_csv)
        cad = QPushButton("📐  Import CAD / DXF…"); cad.setObjectName("btn_secondary")
        cad.setCursor(Qt.PointingHandCursor)
        cad.clicked.connect(self._import_cad_drawing)
        cad.setToolTip("Import a DXF/DWG drawing and attach it to the drawings layer")
        btn_row.addWidget(xl); btn_row.addWidget(cv); btn_row.addWidget(cad); btn_row.addStretch()
        bv.addLayout(btn_row)
        bv.addStretch()
        vl.addWidget(body, 1)
        self.tabs.addTab(w, "Import")

    @staticmethod
    def _mktbl():
        t=QTableWidget()
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.setAlternatingRowColors(True); return t

    def _msg(self, txt, error=False):
        self.sb.showMessage(txt, 4000)
        if hasattr(self, '_toast'):
            self._toast.show_msg(txt, error=error)

    # ── Project creation ──────────────────────────────────────────────────────
    def _create_project(self):
        from qgis.PyQt.QtWidgets import QInputDialog
        site,ok2=QInputDialog.getText(self,'New Project','Site code (e.g. ANF-A):'); 
        if not ok2: return
        self._current_site=site.strip() or 'SITE'
        default=self._current_site.replace(' ','_').lower()+'.gpkg'
        path,_=QFileDialog.getSaveFileName(self,'Create GeoPackage',default,'GeoPackage (*.gpkg)')
        if not path: return
        if not path.endswith('.gpkg'): path+='.gpkg'
        action=QgsVectorFileWriter.CreateOrOverwriteFile
        for tname,schema in SCHEMAS.items():
            fields=QgsFields()
            for fname,ftype in schema: fields.append(QgsField(fname,ftype))
            # contexts = Polygon (draw your excavation squares on the map)
            geom=QgsWkbTypes.Polygon if tname=='contexts' else QgsWkbTypes.NoGeometry
            opts=QgsVectorFileWriter.SaveVectorOptions()
            opts.driverName='GPKG'; opts.fileEncoding='UTF-8'
            opts.layerName=tname; opts.actionOnExistingFile=action
            QgsVectorFileWriter.create(path,fields,geom,
                QgsCoordinateReferenceSystem('EPSG:4326'),
                QgsCoordinateTransformContext(),opts)
            action=QgsVectorFileWriter.CreateOrOverwriteLayer
            uri=f"{path}|layername={tname}"
            dn=f"{getattr(self,'_current_site','SITE')}_{tname}"
            lyr=QgsVectorLayer(uri,dn,'ogr')
            if lyr.isValid(): QgsProject.instance().addMapLayer(lyr)
        self._refresh_combos()
        for cb,name in [(self.ctx_layer_cb,'contexts'),(self.pot_layer_cb,'pottery'),
                        (self.art_layer_cb,'artifacts'),(self.ske_layer_cb,'skeletons'),
                        (self.bone_layer_cb,'bone_inventory'),(self.artdet_layer_cb,'artifact_details')]:
            for i in range(cb.count()):
                if name in cb.itemText(i).lower(): cb.setCurrentIndex(i); break
        self._on_ctx_layer()
        for lcb,fcb in [(self.pot_layer_cb,self.pot_num_field),
                        (self.art_layer_cb,self.art_num_field),
                        (self.ske_layer_cb,self.ske_num_field)]:
            self._fill_fcb(lcb,fcb)
        self._msg(f"Project created: {path}")
        try: self._log_history('create_project', os.path.basename(path), 0, site)
        except Exception: pass
        QMessageBox.information(self,"Done",
            "All tables created.\n\n"
            "• contexts = Polygon layer — draw your excavation squares on the QGIS map\n"
            "• Use Contexts tab to add context records\n"
            "• Use Bone Form tab to record skeleton inventories\n"
            "• Use Import to load your existing CSV/Excel data")

    # ── Layer management ──────────────────────────────────────────────────────
    def _vlayers(self):
        return dm_vlayers()

    def _create_artdet_layer(self):
        """Add artifact_details table to an existing GeoPackage."""
        path,_=QFileDialog.getOpenFileName(self,"Select GeoPackage","","GeoPackage (*.gpkg)")
        if not path: return
        schema=SCHEMAS.get('artifact_details',[])
        fields=QgsFields()
        for fname,ftype in schema: fields.append(QgsField(fname,ftype))
        opts=QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName='GPKG'; opts.fileEncoding='UTF-8'
        opts.layerName='artifact_details'
        opts.actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.create(path,fields,QgsWkbTypes.NoGeometry,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsCoordinateTransformContext(),opts)
        uri=f"{path}|layername=artifact_details"
        site=getattr(self,'_current_site','SITE')
        dn=f"{site}_artifact_details"
        lyr=QgsVectorLayer(uri,dn,'ogr')
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            self._refresh_combos()
            # Auto-select the new layer
            for i in range(self.artdet_layer_cb.count()):
                if 'artifact_details' in self.artdet_layer_cb.itemText(i).lower():
                    self.artdet_layer_cb.setCurrentIndex(i); break
            self._msg("artifact_details layer created and loaded")
        else:
            QMessageBox.warning(self,"","Failed to create layer — check GeoPackage path.")

    def _update_site_badge(self):
        site = getattr(self, '_current_site', '')
        if not hasattr(self, '_site_badge'): return
        if site:
            n = sum(1 for cb in [self.ctx_layer_cb, self.pot_layer_cb,
                                  self.art_layer_cb, self.ske_layer_cb,
                                  self.bone_layer_cb]
                    if cb is not None and cb.currentData() is not None)
            self._site_badge.set_connected(site, n)
        else:
            self._site_badge.set_disconnected()

    def _scan_sites(self):
        """Detect site prefixes from loaded layers."""
        sites = detect_sites(self._vlayers())
        self.site_select_cb.blockSignals(True)
        self.site_select_cb.clear()
        if sites:
            for s in sites:
                self.site_select_cb.addItem(s)
            if len(sites) == 1:
                self.site_select_cb.setCurrentIndex(0)
            self._msg(f"Found {len(sites)} site(s): {', '.join(sites)}")
        else:
            self.site_select_cb.addItem("(no sites detected)")
            self._msg("No sites found — open a GeoPackage first")
        self.site_select_cb.blockSignals(False)

    def _connect_site(self):
        """Auto-fill all layer dropdowns for the selected site prefix."""
        prefix = self.site_select_cb.currentText().strip()
        if not prefix or prefix.startswith('('):
            self._msg("Select a site first", error=True); return
        layers = self._vlayers()
        TABLE_CB_MAP = [
            ('contexts',              self.ctx_layer_cb),
            ('pottery',               self.pot_layer_cb),
            ('artifacts',             self.art_layer_cb),
            ('crates',                self.crate_layer_cb),
            ('skeletons',             self.ske_layer_cb),
            ('bone_inventory',        self.bone_layer_cb),
            ('artifact_details',      self.artdet_layer_cb),
            ('drawings',              self.draw_layer_cb),
            ('edit_history',          self.hist_layer_cb),
            ('context_relationships', self.ctx_rel_layer_cb),
            ('excavation_grids',      self.grid_layer_cb),
        ]
        connected = 0
        for table, cb in TABLE_CB_MAP:
            if cb is None: continue
            lid = find_layer(layers, prefix, table)
            if lid:
                for i in range(cb.count()):
                    if cb.itemData(i) == lid:
                        cb.setCurrentIndex(i); connected += 1; break
        self._current_site = prefix
        try: self._on_ctx_layer()
        except Exception: pass
        for lcb, fcb in [(self.pot_layer_cb, self.pot_num_field),
                         (self.art_layer_cb, self.art_num_field),
                         (self.ske_layer_cb, self.ske_num_field)]:
            try: self._fill_fcb(lcb, fcb)
            except Exception: pass
        if hasattr(self, '_update_site_badge'):
            self._update_site_badge()
        self._msg(f"Connected {connected} layers for site '{prefix}'")
        try: self._log_history('connect_site', prefix, 0, f"{connected} layers")
        except Exception: pass
        try: self._update_completion()
        except Exception: pass
        try: self._home_refresh_map()
        except Exception: pass
        try: self._load_site_photo()
        except Exception: pass
        try: self._load_gallery_registry()
        except Exception: pass

    def _open_gpkg_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GeoPackage", "", "GeoPackage (*.gpkg)")
        if not path: return
        # Block all combo signals to prevent crash during layer refresh
        _cbs = [getattr(self, a, None) for a in [
            'ctx_layer_cb','pot_layer_cb','art_layer_cb','ske_layer_cb',
            'bone_layer_cb','artdet_layer_cb','draw_layer_cb','hist_layer_cb',
            'ctx_rel_layer_cb','grid_layer_cb','site_select_cb',
            'pot_num_field','art_num_field','ske_num_field'
        ]]
        for _cb in _cbs:
            if _cb is not None: _cb.blockSignals(True)
        try:
            loaded = dm_open_gpkg(path)
            self._refresh_combos()
            self._scan_sites()
            for _cb in _cbs:
                if _cb is not None: _cb.blockSignals(False)
            if (self.site_select_cb.count() == 1 and
                    not self.site_select_cb.itemText(0).startswith('(')):
                self._connect_site()
            n = len(loaded)
            self._msg(f"Loaded {n} layer{'s' if n!=1 else ''} from {os.path.basename(path)}")
        except Exception as _e:
            for _cb in _cbs:
                if _cb is not None: _cb.blockSignals(False)
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Open GeoPackage",
                f"Error loading site:\n{str(_e)}\n\nIf switching sites, reload QGIS layers first.")


    def _create_simple_layer(self, table_name, path=None):
        """Generic: add a known table to a GeoPackage (prompts if path not given)."""
        if not path:
            path,_=QFileDialog.getOpenFileName(self,"Select GeoPackage","","GeoPackage (*.gpkg)")
        if not path: return None
        schema=SCHEMAS.get(table_name,[])
        if not schema: QMessageBox.warning(self,"",f"No schema for '{table_name}'"); return
        fields=QgsFields()
        for fname,ftype in schema: fields.append(QgsField(fname,ftype))
        opts=QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName='GPKG'; opts.fileEncoding='UTF-8'
        opts.layerName=table_name
        opts.actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.create(path,fields,QgsWkbTypes.NoGeometry,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsCoordinateTransformContext(),opts)
        site=getattr(self,'_current_site','SITE')
        uri=f"{path}|layername={table_name}"
        lyr=QgsVectorLayer(uri,f"{site}_{table_name}",'ogr')
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr); self._refresh_combos()
            self._msg(f"'{table_name}' layer created")
            return lyr
        QMessageBox.warning(self,"","Failed to create layer.")
        return None

    def _create_crates_layer(self):
        """Create a crates layer (in the connected GeoPackage) and select it."""
        lyr = self._create_simple_layer("crates", path=self._current_gpkg_path())
        if lyr is not None and hasattr(self, "crate_layer_cb"):
            for i in range(self.crate_layer_cb.count()):
                if self.crate_layer_cb.itemData(i) == lyr.id():
                    self.crate_layer_cb.setCurrentIndex(i); break
        self._reload_crates()

    def _refresh_combos(self):
        try:
            layers=self._vlayers()
        except Exception:
            return
        for cb in [self.ctx_layer_cb]:
            prev=cb.currentData(); cb.blockSignals(True); cb.clear()
            for l in layers: cb.addItem(l.name(),l.id())
            for i in range(cb.count()):
                if cb.itemData(i)==prev: cb.setCurrentIndex(i); break
            cb.blockSignals(False)
        ad_cb_list=[self.pot_layer_cb,self.art_layer_cb,self.ske_layer_cb,self.bone_layer_cb]
        for _cb in ['artdet_layer_cb','draw_layer_cb','hist_layer_cb','grid_layer_cb','ctx_rel_layer_cb','crate_layer_cb']:
            if hasattr(self,_cb): ad_cb_list.append(getattr(self,_cb))
        for cb in ad_cb_list:
            prev=cb.currentData(); cb.blockSignals(True); cb.clear()
            cb.addItem("— none —",None)
            for l in layers: cb.addItem(l.name(),l.id())
            for i in range(cb.count()):
                if cb.itemData(i)==prev: cb.setCurrentIndex(i); break
            cb.blockSignals(False)
        self._on_ctx_layer()
        for lcb,fcb in [(self.pot_layer_cb,self.pot_num_field),
                        (self.art_layer_cb,self.art_num_field),
                        (self.ske_layer_cb,self.ske_num_field)]:
            self._fill_fcb(lcb,fcb)

    def _lyr(self, cb):
        return lyr_from_cb(cb)

    def _on_ctx_layer(self):
        fcbs = [self.ctx_num_field,self.ctx_type_field,self.ctx_per_field,
                self.ctx_desc_field,self.ctx_above_field,self.ctx_below_field,self.ctx_eq_field]
        for fcb in fcbs:
            fcb.clear(); fcb.addItem("— none —")
        lyr=self._lyr(self.ctx_layer_cb)
        if not lyr: return
        try:
            fnames=[f.name() for f in lyr.fields()]
        except RuntimeError:
            self._connected_layer=None; return
        for fcb in fcbs:
            fcb.addItems(fnames)
        self._as(self.ctx_num_field,  ['context_num','ctx_num','number','num','id','fid','no'])
        self._as(self.ctx_type_field, ['type','context_type','kind'])
        self._as(self.ctx_per_field,  ['period','date','phase','date_period'])
        self._as(self.ctx_desc_field, ['description','desc','notes','note'])
        self._as(self.ctx_above_field,['above','is_above','over','overlies','above_ctx','later'])
        self._as(self.ctx_below_field,['below','is_below','under','underlies','below_ctx','earlier','cut_by','is_cut_by'])
        self._as(self.ctx_eq_field,   ['equals','equal','same','contemporary','equals_ctx','contemporaneous'])
        # Disconnect previous layer signal safely
        if self._connected_layer is not None:
            try: self._connected_layer.selectionChanged.disconnect(self._on_qgis_sel)
            except Exception: pass
        self._connected_layer=None
        try:
            lyr.selectionChanged.connect(self._on_qgis_sel)
            self._connected_layer=lyr
        except Exception:
            pass

    def _fill_fcb(self,lcb,fcb,*a):
        fcb.clear(); fcb.addItem("— none —"); lyr=self._lyr(lcb)
        if lyr:
            fcb.addItems([f.name() for f in lyr.fields()])
            self._as(fcb,['context_num','ctx_num','context_id','num','number'])

    def _as(self,cb,cands):
        items=[cb.itemText(i).lower() for i in range(cb.count())]
        for c in cands:
            if c.lower() in items: cb.setCurrentIndex(items.index(c.lower())); return

    # ── Load data ─────────────────────────────────────────────────────────────
    def _load_all_base(self):
        self._load_ctx(); self._read_layer_rels(); self._load_rels_from_gpkg(); self._fill_ctx_tbl()
        for p in ['pot','art']: self._reload_linked(p)
        self._fill_ske_tbl(); self._refresh_ske_cb()
        if hasattr(self,'artdet_list'): self._load_artdet_list()
        # Populate context detail combobox
        if hasattr(self,'ctxdet_cb'):
            self.ctxdet_cb.clear()
            for n in sorted(self.ctx_data.keys()): self.ctxdet_cb.addItem(str(n),n)
        if hasattr(self,'_site_badge'): self._update_site_badge()
        if hasattr(self,'_refresh_home_stats'): self._refresh_home_stats()
        self._msg("Data loaded")

    def _safe(self,feat,fname):
        if fname and fname!="— none —":
            try: return str(feat.attribute(fname) or '')
            except Exception: pass
        return ''


    def _load_rels_from_gpkg(self):
        """Load manual relationships from context_relationships GeoPackage table."""
        lyr=self._lyr(self.ctx_rel_layer_cb) if hasattr(self,'ctx_rel_layer_cb') else None
        if not lyr: return
        loaded=0
        for feat in lyr.getFeatures():
            try:
                f=self._safe_int(feat,'from_ctx')
                t=self._safe_int(feat,'to_ctx')
                rt=str(feat.attribute('rel_type') or 'above')
                if f and t:
                    rel={'from_ctx':f,'to_ctx':t,'rel_type':rt,'source':'gpkg'}
                    # Avoid duplicates
                    exists=any(r['from_ctx']==f and r['to_ctx']==t and r['rel_type']==rt
                               for r in self.relationships)
                    if not exists:
                        self.relationships.append(rel); loaded+=1
            except Exception: pass
        if loaded: self._msg(f"Loaded {loaded} relationships from GeoPackage")

    def _load_ctx(self):
        self.ctx_data={}; lyr=self._lyr(self.ctx_layer_cb); nf=self.ctx_num_field.currentText()
        if not lyr or nf=="— none —": return
        tf=self.ctx_type_field.currentText(); pf=self.ctx_per_field.currentText(); df=self.ctx_desc_field.currentText()
        for feat in lyr.getFeatures():
            try: num=int(feat.attribute(nf))
            except Exception: continue
            self.ctx_data[num]={'num':num,'fid':feat.id(),'type':self._safe(feat,tf),
                                'period':self._safe(feat,pf),'description':self._safe(feat,df)}
        nums=sorted(self.ctx_data)
        for cb in [self.rel_from,self.rel_to]:
            cb.clear()
            for n in nums: cb.addItem(str(n),n)
        for p in ['pot','art']:
            fcb=getattr(self,f"{p}_fcb"); fcb.clear(); fcb.addItem("All")
            for n in nums: fcb.addItem(str(n))

    def _fill_ctx_tbl(self):
        lyr=self._lyr(self.ctx_layer_cb)
        if not lyr: return
        fnames=[f.name() for f in lyr.fields()]; feats=list(lyr.getFeatures())
        self.ctx_tbl.setColumnCount(len(fnames)); self.ctx_tbl.setHorizontalHeaderLabels(fnames)
        self.ctx_tbl.setRowCount(len(feats)); self.ctx_tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn); self.ctx_tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    def _fill_ske_tbl(self):
        lyr=self._lyr(self.ske_layer_cb)
        if not lyr: return
        fnames=[f.name() for f in lyr.fields()]; feats=list(lyr.getFeatures())
        self.ske_tbl.setColumnCount(len(fnames)); self.ske_tbl.setHorizontalHeaderLabels(fnames)
        self.ske_tbl.setRowCount(len(feats)); self.ske_tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn); self.ske_tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    def _refresh_ske_cb(self):
        lyr=self._lyr(self.ske_layer_cb)
        self.bone_form_ske_cb.blockSignals(True); self.bone_form_ske_cb.clear()
        if lyr:
            for feat in lyr.getFeatures():
                try:
                    num=feat.attribute('skeleton_num')
                    self.bone_form_ske_cb.addItem(str(num),num)
                except Exception: pass
        self.bone_form_ske_cb.blockSignals(False)

    def _reload_linked(self,pfx,*a):
        lcb=getattr(self,f"{pfx}_layer_cb"); nfcb=getattr(self,f"{pfx}_num_field")
        tbl=getattr(self,f"{pfx}_tbl"); fcb=getattr(self,f"{pfx}_fcb")
        lyr=self._lyr(lcb); nf=nfcb.currentText()
        if not lyr or nf=="— none —": tbl.setRowCount(0); return
        flt=fcb.currentText(); fnames=[f.name() for f in lyr.fields()]
        tbl.setColumnCount(len(fnames)); tbl.setHorizontalHeaderLabels(fnames); feats=[]
        for feat in lyr.getFeatures():
            try:
                if flt!="All" and str(int(feat.attribute(nf)))!=flt: continue
            except Exception: continue
            feats.append(feat)
        tbl.setRowCount(len(feats)); tbl.setProperty("_fids",[f.id() for f in feats])
        for ri,feat in enumerate(feats):
            for ci,fn in enumerate(fnames):
                v=feat.attribute(fn); tbl.setItem(ri,ci,QTableWidgetItem(fmt_cell(v)))

    # ── Read layer relationships ───────────────────────────────────────────────
    def _read_layer_rels(self):
        self.layer_rels=[]; lyr=self._lyr(self.ctx_layer_cb); nf=self.ctx_num_field.currentText()
        if not lyr or nf=="— none —": return
        af=self.ctx_above_field.currentText(); bf=self.ctx_below_field.currentText(); ef=self.ctx_eq_field.currentText()
        if all(x=="— none —" for x in [af,bf,ef]): return
        def parse_refs(val):
            if not val or str(val).strip() in ('','NULL','None'): return []
            nums=[]
            for p in re.split(r'[,;/\s]+',str(val).strip()):
                p=p.strip()
                try: nums.append(int(float(p)))
                except Exception: pass
            return nums
        seen=set()
        for feat in lyr.getFeatures():
            try: src=int(feat.attribute(nf))
            except Exception: continue
            pairs=[]
            if af!="— none —":
                for t in parse_refs(feat.attribute(af)): pairs.append((src,t,'above'))
            if bf!="— none —":
                for t in parse_refs(feat.attribute(bf)): pairs.append((src,t,'below'))
            if ef!="— none —":
                for t in parse_refs(feat.attribute(ef)): pairs.append((src,t,'equals'))
            for f,t,rt in pairs:
                key=(min(f,t),max(f,t),rt) if rt=='equals' else (f,t,rt)
                if key not in seen:
                    seen.add(key)
                    self.layer_rels.append({'from_ctx':f,'to_ctx':t,'rel_type':rt,'source':'layer'})
        self._msg(f"Read {len(self.layer_rels)} rels from layer"); self._refresh_rel_tbl()

    # ── Add/Edit records ──────────────────────────────────────────────────────
    def _schema_for(self, lyr): return schema_for(lyr)

    def _write_feat_base(self,lyr,vals,fid=None):
        lyr.startEditing(); fields=lyr.fields()
        if fid is None:
            feat=QgsFeature(fields)
            for k,v in vals.items():
                fi=fields.indexFromName(k)
                if fi<0: continue
                feat.setAttribute(k,coerce(v,fields.at(fi).type()))
            lyr.addFeature(feat)
        else:
            for k,v in vals.items():
                fi=fields.indexFromName(k)
                if fi<0: continue
                lyr.changeAttributeValue(fid,fi,coerce(v,fields.at(fi).type()))
        ok=lyr.commitChanges()
        if not ok: lyr.rollBack(); self._msg("Save failed")

    def _add_ctx(self):
        lyr=self._lyr(self.ctx_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Create or load a context layer first."); return
        dlg=RecordDialog(self._schema_for(lyr),title="Add Context",parent=self)
        if dlg.exec_()!=QDialog.Accepted: return
        self._write_feat(lyr,dlg.values()); self._load_all()

    def _edit_row_base(self,pfx):
        if pfx=='ctx': tbl=self.ctx_tbl; lyr=self._lyr(self.ctx_layer_cb)
        elif pfx=='ske': tbl=self.ske_tbl; lyr=self._lyr(self.ske_layer_cb)
        else: tbl=getattr(self,f"{pfx}_tbl"); lyr=self._lyr(getattr(self,f"{pfx}_layer_cb"))
        if not lyr: return
        rows=tbl.selectionModel().selectedRows()
        if not rows: QMessageBox.information(self,"","Select a row first."); return
        ri=rows[0].row(); fids=tbl.property("_fids") or []
        if ri>=len(fids): return
        fid=fids[ri]; feat=lyr.getFeature(fid)
        defs={f.name():feat.attribute(f.name()) for f in lyr.fields()}
        dlg=RecordDialog(self._schema_for(lyr),defaults=defs,title="Edit Record",parent=self,
                         extra_options={'crate': self._crate_labels()})
        if dlg.exec_()!=QDialog.Accepted: return
        self._write_feat(lyr,dlg.values(),fid=fid)
        if pfx=='ctx': self._load_all()
        elif pfx=='ske': self._fill_ske_tbl()
        else: self._reload_linked(pfx)

    def _add_linked(self,pfx):
        lyr=self._lyr(getattr(self,f"{pfx}_layer_cb"))
        if not lyr: QMessageBox.warning(self,"",f"Set the {pfx} layer first."); return
        fcb=getattr(self,f"{pfx}_fcb"); nf=getattr(self,f"{pfx}_num_field").currentText()
        defs={nf:fcb.currentText()} if nf!="— none —" and fcb.currentText()!="All" else {}
        dlg=RecordDialog(self._schema_for(lyr),defaults=defs,title="Add Record",parent=self,
                         extra_options={'crate': self._crate_labels()})
        if dlg.exec_()!=QDialog.Accepted: return
        self._write_feat(lyr,dlg.values()); self._reload_linked(pfx)

    def _add_skeleton(self):
        lyr=self._lyr(self.ske_layer_cb)
        if not lyr: QMessageBox.warning(self,"","Set the skeletons layer first."); return
        dlg=RecordDialog(self._schema_for(lyr),title="New Skeleton Record",parent=self)
        if dlg.exec_()!=QDialog.Accepted: return
        self._write_feat(lyr,dlg.values()); self._fill_ske_tbl(); self._refresh_ske_cb()

    def _add_field(self,lyr):
        if not lyr: QMessageBox.warning(self,"","No layer selected."); return
        dlg=AddFieldDialog(self)
        if dlg.exec_()!=QDialog.Accepted: return
        name,qtype=dlg.get_field()
        if not name: return
        if lyr.fields().indexFromName(name)>=0:
            QMessageBox.warning(self,"",f"Column '{name}' already exists."); return
        ok=lyr.dataProvider().addAttributes([QgsField(name,qtype)]); lyr.updateFields()
        if ok:
            self._msg(f"Added column '{name}'")
            self._on_ctx_layer()  # refresh
            for lcb,fcb in [(self.pot_layer_cb,self.pot_num_field),(self.art_layer_cb,self.art_num_field),(self.ske_layer_cb,self.ske_num_field)]:
                self._fill_fcb(lcb,fcb)
            self._load_all()
        else: QMessageBox.warning(self,"","Failed to add column.")

    # ── Skeleton bone form ────────────────────────────────────────────────────
    def _open_bone_form(self):
        """Switch to bone form tab with currently selected skeleton loaded"""
        rows=self.ske_tbl.selectionModel().selectedRows()
        if rows:
            ri=rows[0].row(); fids=self.ske_tbl.property("_fids") or []
            lyr=self._lyr(self.ske_layer_cb)
            if lyr and ri<len(fids):
                feat=lyr.getFeature(fids[ri])
                try:
                    num=feat.attribute('skeleton_num')
                    idx=self.bone_form_ske_cb.findData(num)
                    if idx>=0: self.bone_form_ske_cb.setCurrentIndex(idx)
                except Exception: pass
        self._switch_nav(5)  # Recording Sheet composite tab
        if hasattr(self, '_recording_subtabs'):
            self._recording_subtabs.setCurrentIndex(2)  # Bone Form sub-tab
        try:
            n=int(self.bone_form_ske_cb.currentText()); self._after_load_bone_view(n)
        except Exception: pass

    def _load_bone_form(self):
        """Load existing bone data from bone_inventory layer for selected skeleton"""
        ske_num_text=self.bone_form_ske_cb.currentText()
        if not ske_num_text: return
        try: ske_num=int(ske_num_text)
        except Exception: return
        # Load header from skeletons layer
        ske_lyr=self._lyr(self.ske_layer_cb)
        if ske_lyr:
            for feat in ske_lyr.getFeatures():
                try:
                    if int(feat.attribute('skeleton_num'))==ske_num:
                        self.bone_form_grave.setText(str(feat.attribute('grave') or ''))
                        self.bone_form_site.setText(str(feat.attribute('site') or ''))
                        ag=str(feat.attribute('age_group') or '')
                        idx=self.bone_form_age.findText(ag)
                        if idx>=0: self.bone_form_age.setCurrentIndex(idx)
                        sx=str(feat.attribute('sex') or '')
                        idx=self.bone_form_sex.findText(sx)
                        if idx>=0: self.bone_form_sex.setCurrentIndex(idx)
                        self.bone_form_notes.setText(str(feat.attribute('field_notes') or ''))
                        ft=str(feat.attribute('form_type') or '')
                        idx=self.bone_form_type.findText(ft)
                        if idx>=0: self.bone_form_type.setCurrentIndex(idx)
                        break
                except Exception: pass
        # Reset all dropdowns
        for cb in self._bone_widgets.values(): cb.setCurrentIndex(0)
        # Load bone_inventory
        bone_lyr=self._lyr(self.bone_layer_cb)
        if not bone_lyr: return
        for feat in bone_lyr.getFeatures():
            try:
                if int(feat.attribute('skeleton_num'))!=ske_num: continue
                bone=str(feat.attribute('bone') or '')
                side=str(feat.attribute('side') or '')
                seg =str(feat.attribute('segment') or '')
                status=str(feat.attribute('status') or '')
                key=(bone,side,seg)
                if key in self._bone_widgets:
                    idx=self._bone_widgets[key].findText(status)
                    if idx>=0: self._bone_widgets[key].setCurrentIndex(idx)
            except Exception: pass
        if hasattr(self,'_after_load_bone_view'):
            try: n=int(self.bone_form_ske_cb.currentText()); self._after_load_bone_view(n)
            except Exception: pass

    def _save_bone_form(self):
        """Save bone inventory — one record per bone status, with safe error handling."""
        ske_num_text = self.bone_form_ske_cb.currentText()
        if not ske_num_text:
            QMessageBox.warning(self, "", "Select a skeleton number first.")
            return
        try:
            ske_num = int(ske_num_text)
        except (ValueError, TypeError):
            QMessageBox.warning(self, "", "Skeleton # must be an integer.")
            return
        bone_lyr = self._lyr(self.bone_layer_cb)
        if not bone_lyr:
            QMessageBox.warning(self, "",
                "Set the bone_inventory layer in Layer Configuration first.")
            return

        # Collect bone data
        sv = self._skel_view.get_data() if hasattr(self, '_skel_view') else {}
        if not sv and hasattr(self, '_bone_widgets'):
            sv = {}
            for key, cb in self._bone_widgets.items():
                try:
                    status = cb.currentText()
                    if status and status != '—':
                        bid = 'b_' + '_'.join(str(k).lower() for k in key if k)
                        sv[bid] = {'status': status}
                except Exception:
                    continue
        if not sv:
            QMessageBox.information(self, "",
                "No bone status set — nothing to save.\n"
                "Click bones to mark their condition first.")
            return

        # Map bone IDs → (region, bone, side, segment)
        js_map = {
            'b_cranium': ('Cranium','Frontal','—',''),
            'b_skull': ('Cranium','Skull','—',''),
            'b_mandible': ('Face','Mandible','—',''),
            'b_teeth': ('Teeth','Teeth','—',''),
            'b_teeth_chart': ('Teeth','Teeth','—',''),
            'b_vc': ('Cervical','Cervical','—',''),
            'b_vt': ('Thoracic','Thoracic','—',''),
            'b_vl': ('Lumbar','Lumbar','—',''),
            'b_sacrum': ('Sacrum','Sacrum','—',''),
            'b_ribs_r': ('Ribs','Ribs','R',''), 'b_ribs_l': ('Ribs','Ribs','L',''),
            'b_clav_r': ('Upper Limb','Clavicle','R',''), 'b_clav_l': ('Upper Limb','Clavicle','L',''),
            'b_scap_r': ('Upper Limb','Scapula','R',''), 'b_scap_l': ('Upper Limb','Scapula','L',''),
            'b_hum_r_px':('Upper Limb','Humerus','R','Px'),'b_hum_r_in':('Upper Limb','Humerus','R','In'),'b_hum_r_di':('Upper Limb','Humerus','R','Di'),
            'b_hum_l_px':('Upper Limb','Humerus','L','Px'),'b_hum_l_in':('Upper Limb','Humerus','L','In'),'b_hum_l_di':('Upper Limb','Humerus','L','Di'),
            'b_rad_r_px':('Upper Limb','Radius','R','Px'),'b_rad_r_in':('Upper Limb','Radius','R','In'),'b_rad_r_di':('Upper Limb','Radius','R','Di'),
            'b_rad_l_px':('Upper Limb','Radius','L','Px'),'b_rad_l_in':('Upper Limb','Radius','L','In'),'b_rad_l_di':('Upper Limb','Radius','L','Di'),
            'b_uln_r_px':('Upper Limb','Ulna','R','Px'),'b_uln_r_in':('Upper Limb','Ulna','R','In'),'b_uln_r_di':('Upper Limb','Ulna','R','Di'),
            'b_uln_l_px':('Upper Limb','Ulna','L','Px'),'b_uln_l_in':('Upper Limb','Ulna','L','In'),'b_uln_l_di':('Upper Limb','Ulna','L','Di'),
            'b_carp_r':('Upper Limb','Carpals','R',''), 'b_carp_l':('Upper Limb','Carpals','L',''),
            'b_meta_r':('Upper Limb','Metacarpals','R',''),'b_meta_l':('Upper Limb','Metacarpals','L',''),
            'b_ph_hand_r':('Upper Limb','Ph.Hand','R',''),'b_ph_hand_l':('Upper Limb','Ph.Hand','L',''),
            'b_cox_r':('Lower Limb','Os Coxae','R',''),'b_cox_l':('Lower Limb','Os Coxae','L',''),
            'b_fem_r_px':('Lower Limb','Femur','R','Px'),'b_fem_r_in':('Lower Limb','Femur','R','In'),'b_fem_r_di':('Lower Limb','Femur','R','Di'),
            'b_fem_l_px':('Lower Limb','Femur','L','Px'),'b_fem_l_in':('Lower Limb','Femur','L','In'),'b_fem_l_di':('Lower Limb','Femur','L','Di'),
            'b_pat_r':('Lower Limb','Patella','R',''),'b_pat_l':('Lower Limb','Patella','L',''),
            'b_tib_r_px':('Lower Limb','Tibia','R','Px'),'b_tib_r_in':('Lower Limb','Tibia','R','In'),'b_tib_r_di':('Lower Limb','Tibia','R','Di'),
            'b_tib_l_px':('Lower Limb','Tibia','L','Px'),'b_tib_l_in':('Lower Limb','Tibia','L','In'),'b_tib_l_di':('Lower Limb','Tibia','L','Di'),
            'b_fib_r_px':('Lower Limb','Fibula','R','Px'),'b_fib_r_in':('Lower Limb','Fibula','R','In'),'b_fib_r_di':('Lower Limb','Fibula','R','Di'),
            'b_fib_l_px':('Lower Limb','Fibula','L','Px'),'b_fib_l_in':('Lower Limb','Fibula','L','In'),'b_fib_l_di':('Lower Limb','Fibula','L','Di'),
        }
        status_label_map = {
            'complete':'Complete', 'frag':'Fragmentary',
            'unknown':'Precise ID/side unknown', 'crushed':'Highly Crushed/distorted',
            'sampled':'Sampled', 'estimated':'Estimated', 'isolated':'Tooth found isolated',
        }

        try:
            bone_lyr.startEditing()
            # Delete existing records for this skeleton
            to_del = [f.id() for f in bone_lyr.getFeatures()
                      if self._safe_int(f, 'skeleton_num') == ske_num]
            if to_del:
                bone_lyr.deleteFeatures(to_del)

            fields = bone_lyr.fields()
            field_names = {f.name() for f in fields}
            saved_count = 0

            for bid, binfo in sv.items():
                status_raw = binfo.get('status', '') if isinstance(binfo, dict) else str(binfo)
                if not status_raw or status_raw == 'none':
                    continue
                status_label = status_label_map.get(status_raw, status_raw)
                if bid in js_map:
                    region, bone, side, seg = js_map[bid]
                elif '_r' in bid and ('RIBS_R' in bid or 'RIBS_L' in bid):
                    side = 'R' if 'RIBS_R' in bid else 'L'
                    parts = bid.split('_r')
                    rib_num = parts[-1] if len(parts) > 1 else ''
                    region, bone, seg = 'Ribs', f'Rib {rib_num}', ''
                else:
                    region, bone, side, seg = '?', bid, '?', ''

                feat = QgsFeature(fields)
                if 'skeleton_num' in field_names: feat.setAttribute('skeleton_num', ske_num)
                if 'region' in field_names:       feat.setAttribute('region', region)
                if 'bone' in field_names:         feat.setAttribute('bone', bone)
                if 'side' in field_names:         feat.setAttribute('side', side)
                if 'segment' in field_names:      feat.setAttribute('segment', seg)
                if 'status' in field_names:       feat.setAttribute('status', status_label)
                if 'notes' in field_names and isinstance(binfo, dict):
                    extras = {k: v for k, v in binfo.items() if k != 'status' and v}
                    if extras:
                        try: feat.setAttribute('notes', json.dumps(extras)[:500])
                        except Exception: pass
                if bone_lyr.addFeature(feat):
                    saved_count += 1

            ok = bone_lyr.commitChanges()
            if ok:
                self._msg(f"✓ Saved {saved_count} bone record(s) for skeleton {ske_num}")
            else:
                bone_lyr.rollBack()
                err = bone_lyr.commitErrors() if hasattr(bone_lyr, 'commitErrors') else []
                err_text = "; ".join(str(e) for e in err)[:200] if err else "Unknown error"
                self._msg(f"Save failed: {err_text}", error=True)
                QMessageBox.warning(self, "Save failed",
                    f"Could not save bone records.\n\nDetails: {err_text}")
        except Exception as e:
            try: bone_lyr.rollBack()
            except Exception: pass
            self._msg(f"Save error: {e}", error=True)
            QMessageBox.critical(self, "Save error", f"Exception while saving:\n{e}")

    def _safe_int(self,feat,fname):
        try: return int(feat.attribute(fname))
        except Exception: return None

    def _clear_bone_form(self):
        if hasattr(self,'_skel_view'): self._skel_view.clear_all()
        for cb in self._bone_widgets.values(): cb.setCurrentIndex(0)
        self.bone_form_grave.clear(); self.bone_form_site.clear(); self.bone_form_notes.clear()

    # ── Relationships ─────────────────────────────────────────────────────────
    def _delete_rows_base(self, tbl, lyr, pfx):
        if not lyr: return
        rows=tbl.selectionModel().selectedRows()
        if not rows: QMessageBox.information(self,"","Select row(s) to delete."); return
        fids=tbl.property("_fids") or []
        to_del=[fids[r.row()] for r in rows if r.row()<len(fids)]
        if not to_del: return
        reply=QMessageBox.question(self,"Delete",f"Delete {len(to_del)} record(s) permanently?",QMessageBox.Yes|QMessageBox.No)
        if reply!=QMessageBox.Yes: return
        lyr.startEditing()
        if lyr.deleteFeatures(to_del): lyr.commitChanges(); self._msg(f"Deleted {len(to_del)} record(s)")
        else: lyr.rollBack(); self._msg("Delete failed")
        if pfx=='ctx': self._load_all()
        elif pfx=='ske': self._fill_ske_tbl()
        else: self._reload_linked(pfx)

    def _add_rel(self):
        f=self.rel_from.currentData(); t=self.rel_to.currentData(); rt=self.rel_type_cb.currentText()
        if f is None or t is None or f==t: QMessageBox.warning(self,"","Select two different contexts."); return
        self.relationships.append({'from_ctx':f,'to_ctx':t,'rel_type':rt,'source':'manual'})
        self._save_rels(); self._refresh_rel_tbl(); self._msg(f"Added: {f} {rt} {t}")

    def _write_rel_to_layer(self, from_ctx, to_ctx, rel_type):
        """Persist relationship to context_relationships GeoPackage table."""
        lyr=self._lyr(self.ctx_rel_layer_cb) if hasattr(self,'ctx_rel_layer_cb') else None
        if not lyr: return
        from qgis.core import QgsFeature
        feat=QgsFeature(lyr.fields())
        def sa(fn,v):
            try: feat.setAttribute(fn,v)
            except Exception: pass
        sa('from_ctx',coerce(from_ctx,QVariant.Int))
        sa('to_ctx',coerce(to_ctx,QVariant.Int))
        sa('rel_type',rel_type)
        sa('source','manual')
        lyr.startEditing(); lyr.addFeature(feat); lyr.commitChanges()


    def _del_rel(self):
        rows=self.rel_tbl.selectionModel().selectedRows()
        for i in sorted([r.row() for r in rows],reverse=True):
            if 0<=i<len(self.relationships): self.relationships.pop(i)
        self._save_rels(); self._refresh_rel_tbl()

    def _save_rels(self):
        QgsProject.instance().writeEntry("ArchManager","rels",json.dumps(self.relationships))

    def _refresh_rel_tbl(self):
        all_r=self.relationships+self.layer_rels
        self.rel_tbl.setRowCount(len(all_r))
        for i,r in enumerate(all_r):
            self.rel_tbl.setItem(i,0,QTableWidgetItem(str(r['from_ctx'])))
            self.rel_tbl.setItem(i,1,QTableWidgetItem(REL_LABELS.get(r['rel_type'],r['rel_type'])))
            self.rel_tbl.setItem(i,2,QTableWidgetItem(str(r['to_ctx'])))
            src=r.get('source','manual')
            item=QTableWidgetItem(src)
            item.setForeground(QColor('#888888') if src=='layer' else QColor('#2a6a2a'))
            self.rel_tbl.setItem(i,3,item)

    # ── Matrix ────────────────────────────────────────────────────────────────
    def _build_matrix(self):
        self._load_ctx(); all_rels=self.relationships+self.layer_rels
        self.hv.build(list(self.ctx_data.values()),all_rels,self._on_node_click)
        self._refresh_rel_tbl(); self.hv.fit()

    def _on_node_click(self,num):
        if self._block: return
        self.hv.highlight(num); lyr=self._lyr(self.ctx_layer_cb); nf=self.ctx_num_field.currentText()
        if lyr and nf!="— none —":
            self._block=True; lyr.removeSelection()
            for feat in lyr.getFeatures():
                try:
                    if int(feat.attribute(nf))==num:
                        lyr.select(feat.id()); self.iface.mapCanvas().panToSelected(lyr); break
                except Exception: continue
            self._block=False
        for p in ['pot','art']:
            cb=getattr(self,f"{p}_fcb")
            idx=cb.findText(str(num))
            if idx>=0: cb.setCurrentIndex(idx)
            self._reload_linked(p)
        self._msg(f"Context {num} selected")

    def _on_ctx_tbl_sel(self):
        rows=self.ctx_tbl.selectionModel().selectedRows()
        if not rows: return
        ri=rows[0].row(); fids=self.ctx_tbl.property("_fids") or []
        if ri>=len(fids): return
        lyr=self._lyr(self.ctx_layer_cb); nf=self.ctx_num_field.currentText()
        if not lyr or nf=="— none —": return
        feat=lyr.getFeature(fids[ri])
        try: num=int(feat.attribute(nf))
        except Exception: return
        self._block=True; self.hv.highlight(num)
        lyr.removeSelection(); lyr.select(fids[ri])
        self.iface.mapCanvas().panToSelected(lyr)
        self._flash_feature(lyr, fids[ri]); self._block=False

    def _on_qgis_sel(self,sel,desel,clear):
        if self._block or not sel: return
        lyr=self._lyr(self.ctx_layer_cb); nf=self.ctx_num_field.currentText()
        if not lyr or nf=="— none —": return
        try:
            feat=lyr.getFeature(list(sel)[0]); num=int(feat.attribute(nf))
            self._block=True; self.hv.highlight(num); self._block=False
        except Exception: pass

    def _flash_feature(self, lyr, fid, zoom=False):
        """Flash (and optionally zoom to) a feature on the QGIS map canvas.
        No-op for non-spatial layers or missing geometry."""
        if lyr is None or fid is None:
            return
        try:
            canvas = self.iface.mapCanvas()
            if zoom:
                try:
                    canvas.zoomToFeatureIds(lyr, [fid])
                except Exception:
                    lyr.removeSelection(); lyr.select(fid); canvas.panToSelected(lyr)
            canvas.flashFeatureIds(lyr, [fid])
        except Exception:
            pass

    def _zoom_ctx(self):
        lyr=self._lyr(self.ctx_layer_cb)
        if not lyr: return
        canvas=self.iface.mapCanvas()
        try: canvas.zoomToSelected(lyr)
        except Exception: canvas.panToSelected(lyr)
        sel=list(lyr.selectedFeatureIds())
        if sel: self._flash_feature(lyr, sel[0], zoom=False)

    # ── Import ────────────────────────────────────────────────────────────────
    def _run_import(self,sheets):
        tgts=[(l.name(),l.id()) for l in self._vlayers()]
        if not tgts: QMessageBox.warning(self,"","No vector layers in project."); return
        dlg=ImportDialog(sheets,tgts,parent=self)
        if dlg.exec_()!=QDialog.Accepted: return
        headers,rows,mapping=dlg.get_mapping()
        if not mapping: QMessageBox.warning(self,"","No columns mapped."); return
        lid=dlg.get_layer_id(); lyr=QgsProject.instance().mapLayer(lid)
        if not lyr: return
        fields=lyr.fields(); lyr.startEditing(); added=0; errors=0
        for row in rows:
            if not any(str(row[ci]).strip() for ci in mapping if ci<len(row)): continue
            feat=QgsFeature(fields)
            for ci,fname in mapping.items():
                val=row[ci] if ci<len(row) else ''; fi=fields.indexFromName(fname)
                if fi<0: continue
                feat.setAttribute(fname,coerce(val,fields.at(fi).type()))
            if lyr.addFeature(feat): added+=1
            else: errors+=1
        ok=lyr.commitChanges()
        if not ok: lyr.rollBack()
        msg=f"Imported {added} records into '{lyr.name()}'"
        if errors: msg+=f" ({errors} failed)"
        self._msg(msg); QMessageBox.information(self,"Import complete",msg); self._load_all()

    def _imp_xl(self):
        p,_=QFileDialog.getOpenFileName(self,"Open Excel","","Excel (*.xlsx)")
        if not p: return
        try: sheets=read_xlsx(p)
        except Exception as e: QMessageBox.critical(self,"Error",str(e)); return
        if not sheets: QMessageBox.warning(self,"","No data found."); return
        self._run_import(sheets)
        try:
            total=sum(len(v[1]) for v in sheets.values())
            self._log_history('import_excel', os.path.basename(p), 0, f"{total} rows, {len(sheets)} sheet(s)")
        except Exception: pass

    def _imp_csv(self):
        p,_=QFileDialog.getOpenFileName(self,"Open CSV","","CSV (*.csv *.txt)")
        if not p: return
        try:
            with open(p,newline='',encoding='utf-8-sig') as f: rows=list(csv.reader(f))
            if len(rows)<2: raise ValueError("Need at least header + 1 data row")
            mc=max(len(r) for r in rows); rows=[r+['']*(mc-len(r)) for r in rows]
            self._run_import({"Data":(rows[0],rows[1:])})
            try: self._log_history('import_csv', os.path.basename(p), 0, f"{len(rows)-1} rows")
            except Exception: pass
        except Exception as e: QMessageBox.critical(self,"Error",str(e))

    def _export_pdf(self):
        from .pdf_export import ReportDesignerDialog, export_pdf
        dlg=ReportDesignerDialog(self)
        # Pre-fill site from project
        dlg._site.setText(getattr(self,'_current_site',''))
        # Use the uploaded dashboard site photo as the cover hero by default
        _sp = getattr(self, '_site_photo_path', None)
        if _sp:
            try: dlg._cover_img.setText(_sp)
            except Exception: pass
        if dlg.exec_()!=QDialog.Accepted: return
        opts=dlg.get_options()
        path,_=QFileDialog.getSaveFileName(self,"Save PDF Report","report.pdf","PDF (*.pdf)")
        if not path: return
        if not path.endswith('.pdf'): path+='.pdf'
        self._msg("Exporting PDF…")
        try:
            ok=export_pdf(path,opts,self)
            if ok:
                self._msg(f"PDF exported: {os.path.basename(path)}")
                try: self._log_history('export_pdf', os.path.basename(path), 0, opts.get('site',''))
                except Exception: pass
            else:  self._msg("PDF export failed — check permissions")
        except Exception as e:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.critical(self,"Export error",str(e))

    def _exp_svg(self):
        p,_=QFileDialog.getSaveFileName(self,"Export SVG","","SVG (*.svg)")
        if p: self.hv.export_svg(p)
    def _exp_png(self):
        p,_=QFileDialog.getSaveFileName(self,"Export PNG","","PNG (*.png)")
        if not p: return
        try:
            sc=self.hv._sc
            rect=sc.itemsBoundingRect()
            if rect.isEmpty(): self._msg("Matrix is empty — build it first"); return
            rect=rect.adjusted(-30,-30,30,30)
            px=QPixmap(int(rect.width()*2),int(rect.height()*2))
            px.fill(QColor('#fffdf5'))
            pp2=QPainter(px); pp2.setRenderHint(QPainter.Antialiasing); pp2.scale(2,2)
            sc.render(pp2,source=rect); pp2.end()
            px.save(p); self._msg(f"Matrix exported: {os.path.basename(p)}")
        except Exception as e:
            QMessageBox.critical(self,"Export error",str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# NEW FEATURE METHODS — appended below existing class
# ═══════════════════════════════════════════════════════════════════════════════

PERIOD_ORDER=['Prehistoric','Early Bronze Age','Middle Bronze Age','Late Bronze Age','Iron Age','Persian','Hellenistic','Roman','Byzantine','Early Islamic','Crusader','Medieval','Mamluk','Ottoman','Modern','Unknown']
PERIOD_COLORS=['#8B7355','#CD853F','#DAA520','#B8860B','#808000','#6B8E23','#2E8B57','#20B2AA','#4169E1','#6A5ACD','#9932CC','#C71585','#DC143C','#FF8C00','#888','#bbb']
