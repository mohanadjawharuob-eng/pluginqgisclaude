"""bone_view.py v6 — PNG-shaped coloring, individual bones, individual ribs per zone"""
import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QToolButton, QFrame, QSlider, QSpinBox
)
from qgis.PyQt.QtCore import Qt, QRectF, QPoint, pyqtSignal
from qgis.PyQt.QtGui import (
    QColor, QPen, QBrush, QPainter, QPixmap, QFont, QTransform,
    QImage
)

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Statuses ──────────────────────────────────────────────────────────────────
STATUSES = [
    ('none',     '—',  'Clear'),
    ('complete', '■',  'Complete'),
    ('frag',     '▨',  'Fragmentary'),
    ('unknown',  '?',  'Precise ID unknown'),
    ('crushed',  '✕',  'Crushed / Distorted'),
    ('sampled',  '◎',  'Sampled (14C/DNA)'),
    ('estimated','~',  'Estimated'),
    ('isolated', '○',  'Isolated find'),
]
STATUS_ICON  = {s[0]:s[1] for s in STATUSES}
STATUS_LABEL = {s[0]:s[2] for s in STATUSES}
STATUS_REMAP = {
    'complete':'Complete','frag':'Fragmentary','unknown':'Precise ID/side unknown',
    'crushed':'Highly Crushed/distorted','sampled':'Sampled (14C/DNA/isotopes)',
    'estimated':'Estimated','isolated':'Tooth found isolated',
}
STATUS_FILL = {
    'none':      QColor(0,0,0,0),
    'complete':  QColor(70,70,70,200),
    'frag':      QColor(120,120,120,150),
    'unknown':   QColor(180,180,180,160),
    'crushed':   QColor(140,50,50,200),
    'sampled':   QColor(230,175,0,200),
    'estimated': QColor(100,100,200,170),
    'isolated':  QColor(200,80,80,180),
}
STATUS_PEN = {
    'none':     (QColor(0,0,0,0),     Qt.SolidLine, 0),
    'complete': (QColor(20,20,20,240),Qt.SolidLine, 1.5),
    'frag':     (QColor(50,50,50,200),Qt.DashLine,  1.5),
    'unknown':  (QColor(80,80,80,180),Qt.DotLine,   1.5),
    'crushed':  (QColor(120,20,20,240),Qt.SolidLine,2.0),
    'sampled':  (QColor(150,110,0,240),Qt.SolidLine,1.5),
    'estimated':(QColor(60,60,160,200),Qt.DashDotLine,1.5),
    'isolated': (QColor(160,40,40,220),Qt.SolidLine,1.5),
}

JS_MAP = {}


def _load_px(num, w, h, flip=False):
    """Load bone PNG, scale, optionally flip. Returns (outline_px, fill_px)."""
    outline_path = os.path.join(PLUGIN_DIR, f'Appendix_1A-{num}.png')
    fill_path    = os.path.join(PLUGIN_DIR, f'Appendix_1A-{num}_fill.png')
    def _scale(path):
        if not os.path.exists(path):
            px = QPixmap(w,h); px.fill(QColor(0,0,0,0)); return px
        px = QPixmap(path).scaled(w,h,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        if flip: px = px.transformed(QTransform().scale(-1,1))
        return px
    return _scale(outline_path), _scale(fill_path)


def _apply_status_to_px(outline_px: QPixmap, fill_px: QPixmap,
                         status: str, brush_strokes=None) -> QPixmap:
    """
    Paint status color onto the bone SHAPE (fill mask), then draw outline on top.
    Result: the bone body is colored, bone lines are visible over the color.
    No rectangles — only the actual bone shape is painted.
    """
    if status == 'none' and not brush_strokes:
        return outline_px

    result = QPixmap(outline_px.size())
    result.fill(QColor(0, 0, 0, 0))
    p = QPainter(result)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    fill_col = STATUS_FILL.get(status, QColor(0,0,0,0))
    pc, ps, pw = STATUS_PEN.get(status, (QColor(0,0,0,0), Qt.SolidLine, 0))

    # 1. Draw the FILL MASK colored with status color
    #    The fill_px is the bone interior shape (pre-computed).
    #    We draw it, then recolor it using SourceAtop.
    if not fill_px.isNull() and fill_px.width() > 0:
        # Draw fill mask
        p.drawPixmap(0, 0, fill_px)
        # Recolor with status color (SourceAtop = only where fill_px has alpha)
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        if status == 'crushed':
            p.fillRect(result.rect(), QColor(120,40,40,180))
            # Hatching
            p.setPen(QPen(QColor(180,60,60,200), 0.8))
            step = 4
            for t in range(-result.height(), result.width()+result.height(), step):
                p.drawLine(t, 0, t+result.height(), result.height())
        elif fill_col.alpha() > 0:
            p.fillRect(result.rect(), fill_col)

    # 2. Brush strokes — paint additional filled circles, clipped to bone shape
    if brush_strokes and not fill_px.isNull():
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        darker = fill_col.darker(140) if fill_col.alpha()>0 else QColor(60,60,60,220)
        p.setBrush(QBrush(darker)); p.setPen(QPen(Qt.NoPen))
        for bx, by, br in brush_strokes:
            p.drawEllipse(QRectF(bx-br, by-br, br*2, br*2))

    # 3. Draw bone OUTLINE on top (SourceOver keeps lines visible)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.drawPixmap(0, 0, outline_px)

    p.end()
    return result


# ── BoneWidget — one bone element ─────────────────────────────────────────────
class BoneWidget(QWidget):
    """Single bone: click to set status, drag in brush mode for partial."""
    changed = pyqtSignal(str)

    LABEL_H = 13

    def __init__(self, bone_id, base_px, label,
                 get_mode_fn, get_brush_fn, parent=None):
        super().__init__(parent)
        self.bone_id   = bone_id
        # Unpack tuple FIRST before accessing .width()/.height()
        if isinstance(base_px, tuple):
            self._outline_px, self._fill_px = base_px
        else:
            self._outline_px = base_px
            self._fill_px    = base_px
        self._base_px  = self._outline_px
        self._disp_px  = self._outline_px
        self.label     = label
        self.get_mode  = get_mode_fn
        self.get_brush = get_brush_fn
        self._status   = 'none'
        self._strokes  = []
        self._pressing = False
        pw, ph = self._outline_px.width(), self._outline_px.height()
        self._pw = pw; self._ph = ph
        self.setFixedSize(pw + 4, ph + self.LABEL_H + 4)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            f"{label}\n"
            f"Click = apply current mode to whole bone\n"
            f"🖌 Brush: drag to mark partial area\n"
            f"Right-click = clear")

    def paintEvent(self, _):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            # Bone image
            p.drawPixmap(2, self.LABEL_H + 2, self._disp_px)
            # Label
            p.setFont(QFont('Arial', 6))
            p.setPen(QPen(QColor('#222')))
            p.drawText(QRectF(0, 0, self._pw+4, self.LABEL_H),
                       Qt.AlignCenter, self.label)
        except Exception:
            pass

    def _refresh(self):
        self._disp_px = _apply_status_to_px(
            self._outline_px, self._fill_px,
            self._status, self._strokes or None)
        self.update()

    def mousePressEvent(self, e):
        try:
            mode = self.get_mode()
            if e.button() == Qt.RightButton:
                self._status = 'none'; self._strokes = []
            elif mode == 'brush':
                self._pressing = True
                if self._status == 'none': self._status = 'frag'
                bx = e.pos().x()-2; by = e.pos().y()-self.LABEL_H-2
                self._strokes.append((bx, by, self.get_brush()))
            else:
                self._status = 'none' if self._status == mode else mode
                self._strokes = []
            self._refresh(); self.changed.emit(self.bone_id)
        except Exception: pass
        e.accept()

    def mouseMoveEvent(self, e):
        try:
            if self._pressing and self.get_mode() == 'brush':
                bx = e.pos().x()-2; by = e.pos().y()-self.LABEL_H-2
                self._strokes.append((bx, by, self.get_brush()))
                self._refresh()
        except Exception: pass
        e.accept()

    def mouseReleaseEvent(self, e):
        self._pressing = False
        self.changed.emit(self.bone_id); e.accept()

    def get_data(self):
        return {'status': self._status, 'strokes': self._strokes}

    def load_data(self, d):
        self._status  = d.get('status','none')
        self._strokes = d.get('strokes',[])
        self._refresh()

    def clear(self):
        self._status='none'; self._strokes=[]; self._refresh()


# ── RibWidget — full rib group with 12 individually-clickable ribs ────────────
class RibWidget(QWidget):
    """
    Shows full rib cage PNG. Overlays 12 horizontal coloured bands,
    one per rib. Each rib is independently clickable.
    The bone PNG is drawn on top of the bands so lines stay visible.
    """
    changed = pyqtSignal(str)

    def __init__(self, base_id, file_num, flip,
                 get_mode_fn, get_brush_fn, parent=None):
        super().__init__(parent)
        self.base_id   = base_id
        self.get_mode  = get_mode_fn
        self.get_brush = get_brush_fn
        _ld = _load_px(file_num, 90, 180, flip)
        self._outline_px, self._fill_px = _ld if isinstance(_ld, tuple) else (_ld, _ld)
        self._px = self._outline_px
        self._w  = self._outline_px.width()
        self._h  = self._outline_px.height()
        self._n        = 12
        self._statuses = ['none'] * 12
        self._strokes  = [[] for _ in range(12)]
        self._pressing = False
        self._last_rib = -1
        TITLE_H = 13
        self.TITLE_H = TITLE_H
        self.setFixedSize(self._w + 4, self._h + TITLE_H + 4)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click on a rib to mark it\nRight-click to clear")

    def _rib_at(self, py):
        content_y = py - self.TITLE_H - 2
        if content_y < 0: return -1
        r = int(content_y * self._n / self._h)
        return max(0, min(self._n-1, r))

    def _rib_rect(self, r):
        rh = self._h / self._n
        return QRectF(2, self.TITLE_H + 2 + r*rh, self._w, rh)

    def paintEvent(self, _):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.fillRect(self.rect(), QColor('#ffffff'))

            # Draw status fills per rib UNDER the bone image
            for r in range(self._n):
                st = self._statuses[r]
                if st == 'none': continue
                rect = self._rib_rect(r)
                fill = STATUS_FILL.get(st, QColor(0,0,0,0))
                if st == 'crushed':
                    p.fillRect(rect, QColor(120,40,40,80))
                    p.setPen(QPen(QColor(120,30,30,160), 0.7))
                    step=4; x0=int(rect.left()); y0=int(rect.top())
                    x1=int(rect.right()); y1=int(rect.bottom()); rh=int(rect.height())
                    for t in range(0,x1-x0+rh,step):
                        p.drawLine(x0+t,y0,x0,y0+t)
                    for t in range(0,x1-x0+rh,step):
                        p.drawLine(x0+t,y1,x1,y1-(t if t<rh else rh))
                elif fill.alpha() > 0:
                    # Draw fill using the rib band clipped to bone fill mask
                    p.fillRect(rect, fill)
                # Brush strokes
                if self._strokes[r]:
                    darker = fill.darker(120) if fill.alpha()>0 else QColor(80,80,80,180)
                    p.setPen(QPen(Qt.NoPen)); p.setBrush(QBrush(darker))
                    for bx,by,br in self._strokes[r]:
                        p.drawEllipse(QRectF(2+bx-br, self.TITLE_H+2+r*(self._h/self._n)+by-br,
                                             br*2, br*2))

            # Draw bone OUTLINE on top (lines visible over fill)
            p.drawPixmap(2, self.TITLE_H+2, self._outline_px)

            # Rib divider lines and labels
            p.setFont(QFont('Arial', 4))
            for r in range(self._n):
                rect = self._rib_rect(r)
                st   = self._statuses[r]
                if st != 'none':
                    pc,ps,pw = STATUS_PEN.get(st,(QColor(0,0,0,0),Qt.SolidLine,0))
                    if pw > 0:
                        p.setPen(QPen(pc, pw, ps))
                        p.setBrush(QBrush(QColor(0,0,0,0)))
                        p.drawRect(rect.adjusted(1,0,-1,0))
                    # Icon
                    ico = STATUS_ICON.get(st,'')
                    if ico and ico != '—':
                        p.setPen(QPen(pc))
                        p.setFont(QFont('Arial',max(4,int(rect.height()//2))))
                        p.drawText(rect, Qt.AlignTop|Qt.AlignRight, ico)
                        p.setFont(QFont('Arial',4))
                # Rib number label
                p.setPen(QPen(QColor(180,180,180,200)))
                p.drawText(QRectF(3, rect.top()+1, 14, rect.height()-1),
                           Qt.AlignLeft|Qt.AlignVCenter, str(r+1))
                # Divider
                p.setPen(QPen(QColor(200,200,200,60), 0.4))
                p.drawLine(int(rect.left()), int(rect.bottom()),
                           int(rect.right()), int(rect.bottom()))

            # Title
            p.setPen(QPen(QColor('#222')))
            p.setFont(QFont('Arial',6))
            side = 'R' if 'RIBS_R' in self.base_id else 'L'
            p.drawText(QRectF(0,0,self._w+4,self.TITLE_H),
                       Qt.AlignCenter, f"Ribs {side}")
        except Exception: pass

    def mousePressEvent(self, e):
        try:
            r = self._rib_at(e.pos().y())
            if r < 0: return
            mode = self.get_mode()
            if e.button() == Qt.RightButton:
                self._statuses[r]='none'; self._strokes[r]=[]
            elif mode == 'brush':
                self._pressing=True; self._last_rib=r
                if self._statuses[r]=='none': self._statuses[r]='frag'
                rect=self._rib_rect(r)
                bx=e.pos().x()-2; by=e.pos().y()-rect.top()
                self._strokes[r].append((bx,by,self.get_brush()))
            else:
                self._statuses[r]='none' if self._statuses[r]==mode else mode
                self._strokes[r]=[]
            self.update()
            self.changed.emit(f"{self.base_id}_r{r+1}")
        except Exception: pass
        e.accept()

    def mouseMoveEvent(self, e):
        try:
            if self._pressing and self.get_mode()=='brush':
                r=self._rib_at(e.pos().y())
                if r<0: return
                rect=self._rib_rect(r)
                bx=e.pos().x()-2; by=e.pos().y()-rect.top()
                if self._statuses[r]=='none': self._statuses[r]='frag'
                self._strokes[r].append((bx,by,self.get_brush()))
                self.update()
        except Exception: pass
        e.accept()

    def mouseReleaseEvent(self, e):
        self._pressing=False; e.accept()

    def get_data(self):
        return {f"{self.base_id}_r{i+1}":
                {'status':self._statuses[i],'strokes':self._strokes[i]}
                for i in range(self._n)}

    def load_data(self, data):
        for i in range(self._n):
            k=f"{self.base_id}_r{i+1}"
            if k in data:
                self._statuses[i]=data[k].get('status','none')
                self._strokes[i] =data[k].get('strokes',[])
            else:
                self._statuses[i]='none'; self._strokes[i]=[]
        self.update()

    def clear(self):
        self._statuses=['none']*12; self._strokes=[[]for _ in range(12)]; self.update()

    def all_ids(self):
        return [f"{self.base_id}_r{i+1}" for i in range(12)]


# ── Section header ────────────────────────────────────────────────────────────
class SectionHeader(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setStyleSheet("background:#2a2a2a;border-radius:2px;margin-top:4px;")
        l=QHBoxLayout(self); l.setContentsMargins(10,0,10,0)
        lb=QLabel(text)
        lb.setStyleSheet("color:#c8a860;font-weight:bold;font-size:9px;letter-spacing:1px;")
        l.addWidget(lb)


# ── Bone catalogue: (id, file, w, h, flip, label) ────────────────────────────
BONES = [
    # SKULL (4)
    ('skull',        '4',80,80,False,'Skull frontal'),
    ('skull_lat_R',  '4',64,64,False,'Lateral R'),
    ('skull_lat_L',  '4',64,64,True, 'Lateral L'),
    ('skull_inf',    '4',64,64,False,'Inferior'),
    ('skull_sup',    '4',64,64,True, 'Superior'),
    # TEETH (3)
    ('teeth',        '3',80,44,False,'Teeth chart'),
    ('mandible',     '3',68,34,False,'Mandible'),
    # VERTEBRAE (5) — separate by region
    ('vc',           '5',28,52,False,'Cervical C1-7'),
    ('vt',           '5',28,72,False,'Thoracic T1-12'),
    ('vl',           '5',28,44,False,'Lumbar L1-5'),
    ('sacrum',       '5',32,36,False,'Sacrum'),
    ('coccyx',       '5',24,24,False,'Coccyx'),
    # STERNUM (5 — same file, different crop concept)
    ('sternum',      '5',26,46,False,'Sternum'),
    # CLAVICLE + SCAPULA (13)
    ('clav_R',       '13',62,22,False,'Clavicle R'),
    ('clav_L',       '13',62,22,True, 'Clavicle L'),
    ('scap_R',       '13',56,56,False,'Scapula R'),
    ('scap_L',       '13',56,56,True, 'Scapula L'),
    # HUMERUS (8) — bilateral
    ('hum_R_px',     '8',26,34,False,'Humerus R Px'),
    ('hum_R_in',     '8',24,42,False,'Humerus R Sh'),
    ('hum_R_di',     '8',26,30,False,'Humerus R Di'),
    ('hum_L_px',     '8',26,34,True, 'Humerus L Px'),
    ('hum_L_in',     '8',24,42,True, 'Humerus L Sh'),
    ('hum_L_di',     '8',26,30,True, 'Humerus L Di'),
    # RADIUS (9)
    ('rad_R_px',     '9',22,28,False,'Radius R Px'),
    ('rad_R_in',     '9',20,38,False,'Radius R Sh'),
    ('rad_R_di',     '9',22,26,False,'Radius R Di'),
    ('rad_L_px',     '9',22,28,True, 'Radius L Px'),
    ('rad_L_in',     '9',20,38,True, 'Radius L Sh'),
    ('rad_L_di',     '9',22,26,True, 'Radius L Di'),
    # ULNA (9)
    ('uln_R_px',     '9',22,30,False,'Ulna R Px'),
    ('uln_R_in',     '9',20,40,False,'Ulna R Sh'),
    ('uln_R_di',     '9',22,26,False,'Ulna R Di'),
    ('uln_L_px',     '9',22,30,True, 'Ulna L Px'),
    ('uln_L_in',     '9',20,40,True, 'Ulna L Sh'),
    ('uln_L_di',     '9',22,26,True, 'Ulna L Di'),
    # CARPALS (9)
    ('carp_R',       '9',40,30,False,'Carpals R'),
    ('carp_L',       '9',40,30,True, 'Carpals L'),
    # METACARPALS + PHALANGES HAND (10)
    ('meta_R',       '10',44,36,False,'Metacarpals R'),
    ('ph_H_R',       '10',44,44,False,'Hand Ph. R'),
    ('meta_L',       '10',44,36,True, 'Metacarpals L'),
    ('ph_H_L',       '10',44,44,True, 'Hand Ph. L'),
    # PELVIS (11)
    ('ilium_R',      '11',52,54,False,'Ilium R'),
    ('ischium_R',    '11',44,42,False,'Ischium R'),
    ('pubis_R',      '11',38,32,False,'Pubis R'),
    ('ilium_L',      '11',52,54,True, 'Ilium L'),
    ('ischium_L',    '11',44,42,True, 'Ischium L'),
    ('pubis_L',      '11',38,32,True, 'Pubis L'),
    # FEMUR (12)
    ('fem_R_px',     '12',32,34,False,'Femur R Px'),
    ('fem_R_in',     '12',28,50,False,'Femur R Sh'),
    ('fem_R_di',     '12',32,32,False,'Femur R Di'),
    ('fem_L_px',     '12',32,34,True, 'Femur L Px'),
    ('fem_L_in',     '12',28,50,True, 'Femur L Sh'),
    ('fem_L_di',     '12',32,32,True, 'Femur L Di'),
    # PATELLA (12)
    ('pat_R',        '12',20,20,False,'Patella R'),
    ('pat_L',        '12',20,20,True, 'Patella L'),
    # TIBIA (12)
    ('tib_R_px',     '12',28,30,False,'Tibia R Px'),
    ('tib_R_in',     '12',24,46,False,'Tibia R Sh'),
    ('tib_R_di',     '12',28,28,False,'Tibia R Di'),
    ('tib_L_px',     '12',28,30,True, 'Tibia L Px'),
    ('tib_L_in',     '12',24,46,True, 'Tibia L Sh'),
    ('tib_L_di',     '12',28,28,True, 'Tibia L Di'),
    # FIBULA (12)
    ('fib_R_px',     '12',18,28,False,'Fibula R Px'),
    ('fib_R_in',     '12',16,44,False,'Fibula R Sh'),
    ('fib_R_di',     '12',18,24,False,'Fibula R Di'),
    ('fib_L_px',     '12',18,28,True, 'Fibula L Px'),
    ('fib_L_in',     '12',16,44,True, 'Fibula L Sh'),
    ('fib_L_di',     '12',18,24,True, 'Fibula L Di'),
    # TARSALS + METATARSALS + FOOT PHALANGES (10)
    ('tars_R',       '10',40,30,False,'Tarsals R'),
    ('mets_R',       '10',40,32,False,'Metatarsals R'),
    ('ph_F_R',       '10',40,30,False,'Foot Ph. R'),
    ('tars_L',       '10',40,30,True, 'Tarsals L'),
    ('mets_L',       '10',40,32,True, 'Metatarsals L'),
    ('ph_F_L',       '10',40,30,True, 'Foot Ph. L'),
]

# Build JS_MAP
for b in BONES:
    JS_MAP[b[0]] = ('—', b[5], '—', '')
for side in ('R','L'):
    for i in range(1,13):
        JS_MAP[f"RIBS_{side}_r{i}"] = ('Ribs', f'Rib {i}', side, '')

SECTIONS = [
    ('CRANIUM',         ['skull','skull_lat_R','skull_lat_L','skull_inf','skull_sup']),
    ('TEETH',           ['teeth','mandible']),
    ('VERTEBRAE',       ['vc','vt','vl','sacrum','coccyx','sternum']),
    ('CLAVICLE & SCAPULA',['clav_R','clav_L','scap_R','scap_L']),
    ('RIBS RIGHT',      ['__RIB_R__']),
    ('RIBS LEFT',       ['__RIB_L__']),
    ('HUMERUS',         ['hum_R_px','hum_R_in','hum_R_di','hum_L_px','hum_L_in','hum_L_di']),
    ('RADIUS',          ['rad_R_px','rad_R_in','rad_R_di','rad_L_px','rad_L_in','rad_L_di']),
    ('ULNA',            ['uln_R_px','uln_R_in','uln_R_di','uln_L_px','uln_L_in','uln_L_di']),
    ('CARPALS',         ['carp_R','carp_L']),
    ('METACARPALS & HAND',['meta_R','ph_H_R','meta_L','ph_H_L']),
    ('PELVIS R',        ['ilium_R','ischium_R','pubis_R']),
    ('PELVIS L',        ['ilium_L','ischium_L','pubis_L']),
    ('FEMUR',           ['fem_R_px','fem_R_in','fem_R_di','fem_L_px','fem_L_in','fem_L_di']),
    ('PATELLA',         ['pat_R','pat_L']),
    ('TIBIA',           ['tib_R_px','tib_R_in','tib_R_di','tib_L_px','tib_L_in','tib_L_di']),
    ('FIBULA',          ['fib_R_px','fib_R_in','fib_R_di','fib_L_px','fib_L_in','fib_L_di']),
    ('TARSALS & FOOT',  ['tars_R','mets_R','ph_F_R','tars_L','mets_L','ph_F_L']),
]


# ── Main view ─────────────────────────────────────────────────────────────────
class SkeletonView(QWidget):
    status_changed = pyqtSignal(str, str)

    def __init__(self, svg_path=None, parent=None):
        super().__init__(parent)
        self._mode       = 'complete'
        self._brush_size = 8
        self._items      = {}
        self._ribs       = {}
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
        vl.addWidget(self._toolbar())
        vl.addWidget(self._form(), 1)

    def _toolbar(self):
        bar = QFrame()
        bar.setStyleSheet("background:#1e1e1e;border-bottom:1px solid #c8a860;")
        hl = QHBoxLayout(bar); hl.setContentsMargins(6,3,6,3); hl.setSpacing(4)
        hl.addWidget(QLabel("<b style='color:#c8a860;font-size:9px;'>STATUS:</b>"))
        self._btns = {}
        cols = {'none':'#444','complete':'#2a4a2a','frag':'#2a2a4a','unknown':'#3a3a3a',
                'crushed':'#4a1a1a','sampled':'#5a4800','estimated':'#1a2a4a','isolated':'#4a1a1a'}
        for key,icon,lbl in STATUSES:
            b=QToolButton(); b.setText(icon); b.setToolTip(lbl)
            b.setCheckable(True); b.setChecked(key==self._mode)
            c=cols.get(key,'#444')
            b.setStyleSheet(
                f"QToolButton{{background:{c};color:#ccc;border:1.5px solid #555;"
                f"border-radius:2px;padding:3px 6px;font-size:11px;min-width:20px;}}"
                f"QToolButton:checked{{border:2px solid #c8a860;color:#fff;font-weight:bold;}}"
                f"QToolButton:hover{{background:#333;color:#fff;}}")
            b.clicked.connect(lambda _,k=key:self._mode_set(k))
            self._btns[key]=b; hl.addWidget(b)
        sep=QFrame(); sep.setFrameStyle(QFrame.VLine)
        sep.setStyleSheet("color:#444;"); hl.addWidget(sep)
        bb=QToolButton(); bb.setText("🖌"); bb.setToolTip("Brush — drag to mark partial area")
        bb.setCheckable(True)
        bb.setStyleSheet("QToolButton{background:#7a3a00;color:#ffc;border:1.5px solid #555;"
                         "border-radius:2px;padding:3px 6px;font-size:11px;min-width:20px;}"
                         "QToolButton:checked{border:2px solid #c8a860;}"
                         "QToolButton:hover{background:#a04a00;}")
        bb.clicked.connect(lambda _:self._mode_set('brush'))
        self._btns['brush']=bb; hl.addWidget(bb)
        hl.addWidget(QLabel("<small style='color:#888;'> Sz:</small>"))
        sl=QSlider(Qt.Horizontal); sl.setRange(2,24); sl.setValue(8); sl.setFixedWidth(55)
        sp=QSpinBox(); sp.setRange(2,24); sp.setValue(8); sp.setFixedWidth(36)
        sl.valueChanged.connect(lambda v:(sp.setValue(v),setattr(self,'_brush_size',v)))
        sp.valueChanged.connect(sl.setValue)
        hl.addWidget(sl); hl.addWidget(sp); hl.addStretch()
        hl.addWidget(QLabel("<small style='color:#555;'>Right-click=clear</small>"))
        return bar

    def _mode_set(self, k):
        self._mode=k
        for key,btn in self._btns.items(): btn.setChecked(key==k)

    def _form(self):
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#f5f2eb;}")
        w=QWidget(); w.setStyleSheet("background:#f5f2eb;")
        vl=QVBoxLayout(w); vl.setContentsMargins(8,6,8,8); vl.setSpacing(4)
        bd={b[0]:b for b in BONES}
        for sec,ids in SECTIONS:
            vl.addWidget(SectionHeader(sec))
            row=QFrame()
            row.setStyleSheet("background:#fff;border:1px solid #e0d8c8;"
                              "border-radius:3px;padding:2px;")
            hl=QHBoxLayout(row); hl.setContentsMargins(6,6,6,6)
            hl.setSpacing(8); hl.setAlignment(Qt.AlignLeft|Qt.AlignTop)
            for bid in ids:
                if bid == '__RIB_R__':
                    rw=RibWidget('RIBS_R','6',False,
                                 lambda:self._mode, lambda:self._brush_size)
                    rw.changed.connect(self._on_ch); hl.addWidget(rw); self._ribs['RIBS_R']=rw
                elif bid == '__RIB_L__':
                    rw=RibWidget('RIBS_L','7',False,
                                 lambda:self._mode, lambda:self._brush_size)
                    rw.changed.connect(self._on_ch); hl.addWidget(rw); self._ribs['RIBS_L']=rw
                elif bid in bd:
                    _,fn,bw,bh,fl,lb=bd[bid]
                    px=_load_px(fn,bw,bh,fl)   # returns (outline,fill) tuple
                    bwg=BoneWidget(bid,px,lb,lambda:self._mode,lambda:self._brush_size)
                    bwg.changed.connect(self._on_ch); hl.addWidget(bwg); self._items[bid]=bwg
            hl.addStretch(); vl.addWidget(row)
        vl.addStretch(); scroll.setWidget(w); return scroll

    def _on_ch(self, bone_id):
        self.status_changed.emit(bone_id, bone_id)

    def get_data(self):
        d={}
        for bid,w in self._items.items():
            r=w.get_data()
            if r['status']!='none' or r['strokes']: d[bid]=r
        for rw in self._ribs.values(): d.update({k:v for k,v in rw.get_data().items()
                                                  if v['status']!='none' or v['strokes']})
        return d

    def load_data(self, data):
        for bid,w in self._items.items():
            w.load_data(data[bid]) if bid in data else w.clear()
        for rw in self._ribs.values(): rw.load_data(data)

    def clear_all(self):
        for w in self._items.values(): w.clear()
        for rw in self._ribs.values(): rw.clear()

    def render_to_pixmap(self, W=900, H=1400):
        sc=self.findChild(QScrollArea)
        if not sc:
            px=QPixmap(W,H); px.fill(QColor('#f5f2eb')); return px
        c=sc.widget()
        px=QPixmap(max(W,c.width()),max(H,c.height())); px.fill(QColor('#f5f2eb'))
        p=QPainter(px); c.render(p); p.end()
        return px.scaled(W,H,Qt.KeepAspectRatio,Qt.SmoothTransformation)
