"""harris_view.py — Harris Matrix layout and interactive view"""
from qgis.PyQt.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsObject, QFileDialog
from qgis.PyQt.QtCore import Qt, QRectF, pyqtSignal
from qgis.PyQt.QtGui import (
    QColor, QPen, QBrush, QPainterPath, QFont, QPainter, QPixmap, QImage
)
from qgis.PyQt.QtSvg import QSvgGenerator

from .styles import CLR, FONT_MONO

BOX_W, BOX_H, H_GAP, V_GAP, PAD = 80, 28, 16, 42, 36

CTX_COLORS = {
    'fill':'#b8d4c8','cut':'#e8b99a','deposit':'#d4c89a','layer':'#c4b8d8',
    'wall':'#d8c8a8','floor':'#e0d4b0','pit':'#d4a8a8','trench':'#f0d898',
    'surface':'#a8d4c0','feature':'#c4a8d4','rubble':'#c8c8b8','other':'#d8d8d0',
}

def compute_layout(contexts,relationships):
    ids=[c['num'] for c in contexts]
    if not ids: return {}
    out={i:[] for i in ids}
    for r in relationships:
        f,t,rt=r['from_ctx'],r['to_ctx'],r['rel_type']
        if f not in out or t not in out: continue
        if rt in ('above','cuts'):        out[f].append(t)
        elif rt in ('below','is_cut_by'): out[t].append(f)
    memo,vis={},set()
    def lvl(n):
        if n in memo: return memo[n]
        if n in vis: return 0
        vis.add(n); memo[n]=max((lvl(c) for c in out.get(n,[])),default=-1)+1
        vis.discard(n); return memo[n]
    for i in ids: lvl(i)
    groups={}
    for i in ids: groups.setdefault(memo.get(i,0),[]).append(i)
    levels=sorted(groups,reverse=True)
    mpr=max(len(g) for g in groups.values())
    W=max(540,PAD*2+mpr*(BOX_W+H_GAP)-H_GAP); pos={}
    for ri,lv in enumerate(levels):
        row=groups[lv]; rw=len(row)*(BOX_W+H_GAP)-H_GAP; sx=(W-rw)/2
        for ci,nid in enumerate(row):
            pos[nid]=(sx+ci*(BOX_W+H_GAP),PAD+ri*(BOX_H+V_GAP))
    return pos

# ── Graphics ──────────────────────────────────────────────────────────────────
class ContextNode(QGraphicsObject):
    node_clicked=pyqtSignal(int)
    def __init__(self,num,ctx,x,y):
        super().__init__()
        self.num,self.ctx,self._hi=num,ctx,False
        self.setPos(x,y); self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"Context {num}\nType: {ctx.get('type','—')}\nPeriod: {ctx.get('period','—')}")
    def boundingRect(self): return QRectF(0,0,BOX_W,BOX_H)
    def paint(self,painter,option,widget=None):
        # Classic B&W style — white boxes, black borders, no color fill
        painter.setRenderHint(QPainter.Antialiasing)
        fill   = QColor('#e8f0ff') if self._hi else QColor('#ffffff')
        border = QColor('#1144cc') if self._hi else QColor('#111111')
        pen_w  = 1.8 if self._hi else 0.8
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(border, pen_w))
        painter.drawRect(0, 0, BOX_W, BOX_H)   # square corners like reference
        # Context number (bold, centered top half)
        painter.setPen(QPen(QColor('#000000')))
        f1 = QFont('Arial', max(5, int(BOX_H * 0.32))); f1.setBold(True)
        painter.setFont(f1)
        painter.drawText(QRectF(1, 1, BOX_W-2, BOX_H*0.56), Qt.AlignCenter, str(self.num))
        # Type abbreviation (tiny, bottom half)
        t = self.ctx.get('type','')[:3]
        if t:
            painter.setPen(QPen(QColor('#555555')))
            f2 = QFont('Arial', max(4, int(BOX_H * 0.24))); painter.setFont(f2)
            painter.drawText(QRectF(1, BOX_H*0.54, BOX_W-2, BOX_H*0.44), Qt.AlignCenter, t)
    def mousePressEvent(self,e): self.node_clicked.emit(self.num)
    def set_hi(self,on): self._hi=on; self.update()

class HarrisView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._sc=QGraphicsScene(); self.setScene(self._sc)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._bg_color = QColor('#F8F5EE')  # default light
        self._line_hex = '#2E2A26'
        self._text_hex = '#6F655B'
        self.setBackgroundBrush(QBrush(self._bg_color))
        self.setMinimumHeight(300); self._nodes={}

    def update_theme(self, bg_hex, line_hex='#2E2A26', text_hex='#6F655B'):
        self._bg_color = QColor(bg_hex)
        self._line_hex = line_hex
        self._text_hex = text_hex
        self.setBackgroundBrush(QBrush(self._bg_color))
        self.viewport().update()
    def wheelEvent(self,e):
        f=1.15 if e.angleDelta().y()>0 else 1/1.15; self.scale(f,f)
    def build(self,contexts,relationships,on_click):
        self._sc.clear(); self._nodes={}
        if not contexts:
            t=self._sc.addText("No contexts — add them in the Contexts tab, then click Build Matrix.")
            t.setDefaultTextColor(QColor(getattr(self, '_text_hex', '#888'))); return
        pos=compute_layout(contexts,relationships)
        # ── Classic B&W lines ──
        _lhex = getattr(self, '_line_hex', '#2E2A26')
        line_pen=QPen(QColor(_lhex),1.2)
        dash_pen=QPen(QColor(_lhex),1.0,Qt.DashLine)
        for r in relationships:
            f,t,rt=r['from_ctx'],r['to_ctx'],r['rel_type']
            contemp=rt in ('contemporary','equals')
            if rt in ('below','is_cut_by'): f,t=t,f
            if f not in pos or t not in pos: continue
            p1x,p1y=pos[f]; p2x,p2y=pos[t]
            if contemp:
                base=max(p1y,p2y)+BOX_H+10
                for off in (0,4):
                    path=QPainterPath(); my=base+off
                    path.moveTo(p1x+BOX_W/2,p1y+BOX_H); path.lineTo(p1x+BOX_W/2,my)
                    path.lineTo(p2x+BOX_W/2,my);         path.lineTo(p2x+BOX_W/2,p2y+BOX_H)
                    self._sc.addPath(path,dash_pen)
            else:
                mid=(p1y+BOX_H+p2y)/2; path=QPainterPath()
                path.moveTo(p1x+BOX_W/2,p1y+BOX_H); path.lineTo(p1x+BOX_W/2,mid)
                path.lineTo(p2x+BOX_W/2,mid);        path.lineTo(p2x+BOX_W/2,p2y)
                self._sc.addPath(path,line_pen)
        # ── Classic B&W boxes ──
        for ctx in contexts:
            n=ctx['num']
            if n not in pos: continue
            x,y=pos[n]; node=ContextNode(n,ctx,x,y)
            node.node_clicked.connect(on_click); self._sc.addItem(node); self._nodes[n]=node
        r=self._sc.itemsBoundingRect(); mx=r.center().x()
        fl=QFont('Arial',7,QFont.Bold)
        for txt,yoff in [('▲  LATER',r.top()-22),('▼  EARLIER',r.bottom()+6)]:
            it=self._sc.addText(txt); it.setFont(fl)
            it.setDefaultTextColor(QColor(getattr(self, '_text_hex', '#888888')))
            it.setPos(mx-it.boundingRect().width()/2,yoff)
    def highlight(self,num):
        for n,nd in self._nodes.items(): nd.set_hi(n==num)
    def fit(self): self.fitInView(self._sc.itemsBoundingRect().adjusted(-PAD,-PAD,PAD,PAD),Qt.KeepAspectRatio)
    def export_svg(self,path):
        from qgis.PyQt.QtSvg import QSvgGenerator
        rect=self._sc.itemsBoundingRect().adjusted(-PAD,-PAD,PAD,PAD)
        gen=QSvgGenerator(); gen.setFileName(path); gen.setSize(rect.size().toSize()); gen.setViewBox(rect)
        p=QPainter(gen); p.setRenderHint(QPainter.Antialiasing); self._sc.render(p,source=rect); p.end()
    def export_png(self,path):
        rect=self._sc.itemsBoundingRect().adjusted(-PAD,-PAD,PAD,PAD)
        img=QImage(int(rect.width()*2),int(rect.height()*2),QImage.Format_ARGB32)
        img.fill(QColor('#fffdf5'))
        p=QPainter(img); p.setRenderHint(QPainter.Antialiasing); p.scale(2,2)
        self._sc.render(p,source=rect); p.end(); img.save(path)

# ── Dialogs ───────────────────────────────────────────────────────────────────