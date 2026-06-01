"""styles.py v3 — Excavation Night (dark) + Archaeological Studio (light)"""

# ── Dark Mode — "Excavation Night" ────────────────────────────────────────────
# Inspired by: night excavations, basalt, bronze tools, deep ocean archaeology
CLR = {
    # Core backgrounds
    "bg_root":      "#121417",   # Obsidian — main background
    "bg_panel":     "#1C2126",   # Basalt Gray — secondary background
    "bg_card":      "#232A30",   # Volcanic Stone — card/panel
    "bg_card_2":    "#2A3340",   # raised card
    "bg_hover":     "#2E3845",
    "bg_input":     "#1C2126",
    "bg_table":     "#1A2028",
    "bg_row_alt":   "#212830",
    "bg_row_sel":   "#2D4A3A",   # deep green tint for selection

    # Borders
    "border":       "#343C44",   # Ash Gray
    "border_soft":  "#2C343C",
    "border_strong":"#3E4852",

    # Text
    "text":         "#E8E4DC",   # Warm White
    "text_dim":     "#A7A29A",   # Stone Gray
    "text_muted":   "#68707A",   # Muted Ash
    "text_inv":     "#121417",

    # Accents
    "accent":       "#D4A94D",   # Excavation Gold — primary
    "accent_hover": "#B8892D",
    "accent_text":  "#1A1200",   # dark text on gold buttons
    "accent_2":     "#8D6E42",   # Aged Bronze — secondary/export
    "accent_2_h":   "#7A5C32",
    "accent_3":     "#4FA0A8",   # Maritime Teal — GIS/data
    "accent_warn":  "#E0A83A",   # Amber
    "accent_red":   "#C45B52",   # Oxide Red
    "accent_red_h": "#A8453A",

    # Status
    "status_ok":    "#7FA36A",   # Moss Green
    "status_warn":  "#E0A83A",   # Amber
    "status_err":   "#C45B52",   # Oxide Red
    "status_info":  "#6BA7D6",   # Glacier Blue

    # Pills
    "pill_green":   "#7FA36A",
    "pill_purple":  "#8D6E42",
    "pill_cyan":    "#4FA0A8",
    "pill_amber":   "#E0A83A",
    "pill_red":     "#C45B52",

    # Sidebar always stays dark (Deep Charcoal)
    "sidebar_bg":        "#0D0F12",
    "sidebar_text":      "#E8E4DC",
    "sidebar_text_dim":  "#A7A29A",
    "sidebar_active_bg": "#1C2126",
}

# Backwards-compat aliases
CLR.update({
    "bg_dark":          CLR["bg_root"],
    "bg_content":       CLR["bg_panel"],
    "bg_white":         CLR["bg_card"],
    "accent_gold":      CLR["accent"],
    "accent_gold_light":CLR["accent_hover"],
    "accent_blue":      CLR["accent_3"],
    "accent_green":     CLR["accent"],
    "accent_purple":    CLR["accent_2"],
    "text_primary":     CLR["text"],
    "text_secondary":   CLR["text_dim"],
    "text_dark":        CLR["text_inv"],
    "border_dark":      CLR["border"],
    "border_gold":      CLR["accent"],
    "row_a":            CLR["bg_table"],
    "row_b":            CLR["bg_row_alt"],
})

FONT_SANS    = "Inter, 'Segoe UI', Arial, sans-serif"
FONT_MONO    = "'JetBrains Mono', 'Courier New', monospace"
FONT_SIZE_XS = "10px"
FONT_SIZE_SM = "11px"
FONT_SIZE_MD = "12px"
FONT_SIZE_LG = "14px"
FONT_SIZE_XL = "18px"
FONT_SIZE_XXL= "24px"

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24
RADIUS = "8px"
RADIUS_SM= "5px"
RADIUS_LG= "12px"


# ──────────────────────────────────────────────────────────────────────────────
# GLOBAL ROOT QSS — applied to the whole plugin window
# ──────────────────────────────────────────────────────────────────────────────
ROOT_QSS = f"""
QMainWindow, QWidget#root, QWidget#content {{
    background: {CLR['bg_panel']};
    color: {CLR['text']};
    font-family: {FONT_SANS};
    font-size: {FONT_SIZE_SM};
}}
QLabel {{
    color: {CLR['text']};
    background: transparent;
    font-family: {FONT_SANS};
}}
QToolTip {{
    background: {CLR['bg_card_2']};
    color: {CLR['text']};
    border: 1px solid {CLR['border_strong']};
    padding: 6px 10px;
    border-radius: 4px;
    font-size: {FONT_SIZE_SM};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {CLR['border_strong']};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {CLR['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {CLR['border_strong']};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {CLR['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {CLR['bg_input']};
    color: {CLR['text']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS_SM};
    padding: 7px 10px;
    font-size: {FONT_SIZE_SM};
    min-height: 22px;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {CLR['accent']};
}}
QComboBox {{
    background: {CLR['bg_input']};
    color: {CLR['text']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS_SM};
    padding: 6px 28px 6px 10px;
    font-size: {FONT_SIZE_SM};
    min-height: 22px;
}}
QComboBox:hover {{ border: 1px solid {CLR['border_strong']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {CLR['bg_card_2']};
    color: {CLR['text']};
    border: 1px solid {CLR['border_strong']};
    selection-background-color: {CLR['bg_row_sel']};
    selection-color: {CLR['text']};
    outline: none;
}}
QCheckBox {{
    color: {CLR['text']};
    font-size: {FONT_SIZE_SM};
    spacing: 8px;
}}
QGroupBox {{
    color: {CLR['text']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS};
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px; top: -2px;
    padding: 0 6px;
    color: {CLR['text_dim']};
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR — left nav rail with icon+label items (Image 4 style)
# ──────────────────────────────────────────────────────────────────────────────
SIDEBAR_QSS = f"""
QWidget#sidebar {{
    background: {CLR['bg_root']};
    border-right: 1px solid {CLR['border']};
}}
QWidget#sidebar QScrollArea, QWidget#sidebar QWidget {{
    background: {CLR['bg_root']};
}}
QWidget#sidebar QLabel {{
    color: {CLR['text_dim']};
    font-size: {FONT_SIZE_SM};
}}
QWidget#sidebar QLabel#brand {{
    color: {CLR['text']};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QWidget#sidebar QLabel#brand_sub {{
    color: {CLR['text_muted']};
    font-size: {FONT_SIZE_XS};
}}
"""

# Big sidebar nav button (Home / Contexts / Pottery etc.)
NAV_ITEM_QSS = f"""
QPushButton#navItem {{
    background: transparent;
    color: {CLR['text_dim']};
    border: none;
    border-left: 3px solid transparent;
    padding: 11px 16px;
    text-align: left;
    font-size: {FONT_SIZE_SM};
    font-weight: 500;
    min-height: 46px;
}}
QPushButton#navItem:checked {{
    background: {CLR['bg_card']};
    color: {CLR['text']};
    border-left: 3px solid {CLR['accent']};
    font-weight: 600;
}}
QPushButton#navItem:hover:!checked {{
    background: {CLR['bg_card']};
    color: {CLR['text']};
    border-left: 3px solid {CLR['border_strong']};
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# CARDS  —  used everywhere for content blocks
# ──────────────────────────────────────────────────────────────────────────────
CARD_QSS = f"""
QFrame#card {{
    background: {CLR['bg_card']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS};
}}
QFrame#card QLabel {{ background: transparent; }}
QFrame#cardHeader {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {CLR['border']};
}}
QLabel#cardTitle {{
    color: {CLR['text']};
    font-size: {FONT_SIZE_LG};
    font-weight: 600;
}}
QLabel#cardSub {{
    color: {CLR['text_dim']};
    font-size: {FONT_SIZE_SM};
}}
QLabel#statBig {{
    color: {CLR['text']};
    font-size: 28px;
    font-weight: 700;
}}
QLabel#statLabel {{
    color: {CLR['text_dim']};
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
}}
QLabel#statDelta {{
    color: {CLR['accent']};
    font-size: {FONT_SIZE_XS};
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# TABLE — flat dark table matching mockup
# ──────────────────────────────────────────────────────────────────────────────
TABLE_QSS = f"""
QTableWidget {{
    background: {CLR['bg_table']};
    alternate-background-color: {CLR['bg_row_alt']};
    color: {CLR['text']};
    gridline-color: {CLR['border_soft']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS_SM};
    selection-background-color: {CLR['bg_row_sel']};
    selection-color: {CLR['text']};
    font-size: {FONT_SIZE_SM};
}}
QTableWidget::item {{ padding: 8px 10px; border: none; }}
QTableWidget::item:selected {{
    background: {CLR['bg_row_sel']};
    color: {CLR['text']};
}}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {CLR['bg_card_2']};
    color: {CLR['text_dim']};
    border: none;
    border-bottom: 1px solid {CLR['border']};
    border-right: 1px solid {CLR['border_soft']};
    padding: 9px 10px;
    font-weight: 600;
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}
QHeaderView::section:last {{ border-right: none; }}
"""


# ──────────────────────────────────────────────────────────────────────────────
# CONTENT/MAIN AREA — top toolbar, tabs etc.
# ──────────────────────────────────────────────────────────────────────────────
CONTENT_QSS = f"""
QWidget#content {{ background: {CLR['bg_panel']}; }}

QFrame#topbar {{
    background: {CLR['bg_panel']};
    border-bottom: 1px solid {CLR['border']};
}}
QLabel#pageTitle {{
    color: {CLR['text']};
    font-size: 20px;
    font-weight: 700;
}}
QLabel#pageSub {{
    color: {CLR['text_dim']};
    font-size: {FONT_SIZE_SM};
}}

/* Hidden tab bar — sub-tabs only */
QTabWidget::pane {{
    border: none;
    background: {CLR['bg_panel']};
}}
QTabBar::tab {{
    background: transparent;
    color: {CLR['text_dim']};
    padding: 8px 16px;
    border: none;
    font-size: {FONT_SIZE_SM};
    min-width: 80px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background: {CLR['bg_card']};
    color: {CLR['text']};
    border-bottom: 2px solid {CLR['accent']};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {CLR['text']}; }}
"""

STATUS_BAR_QSS = f"""
QStatusBar {{
    background: {CLR['bg_root']};
    color: {CLR['text_dim']};
    border-top: 1px solid {CLR['border']};
    font-size: {FONT_SIZE_XS};
    padding: 4px 12px;
    min-height: 28px;
}}
QStatusBar::item {{ border: none; }}
"""


# ──────────────────────────────────────────────────────────────────────────────
# BUTTON helpers
# ──────────────────────────────────────────────────────────────────────────────
def btn_style(bg: str, hover: str = None, text: str = "#ffffff",
              tall: bool = False, small: bool = False) -> str:
    """Backwards-compatible button style helper."""
    h = "36px" if tall else ("24px" if small else "30px")
    hov = hover or bg
    return (
        f"QPushButton {{"
        f"background:{bg};color:{text};border:none;"
        f"border-radius:{RADIUS_SM};padding:6px 14px;"
        f"font-size:{FONT_SIZE_SM};font-family:{FONT_SANS};font-weight:500;"
        f"min-height:{h};}}"
        f"QPushButton:hover{{background:{hov};}}"
        f"QPushButton:pressed{{background:{bg};}}"
        f"QPushButton:disabled{{background:{CLR['bg_card']};color:{CLR['text_muted']};}}"
    )


BTN_PRIMARY = (
    f"QPushButton {{background:{CLR['accent']};color:{CLR['accent_text']};"
    f"border:none;border-radius:{RADIUS_SM};padding:8px 16px;"
    f"font-size:{FONT_SIZE_SM};font-weight:700;min-height:32px;}}"
    f"QPushButton:hover{{background:{CLR['accent_hover']};}}"
    f"QPushButton:disabled{{background:{CLR['bg_card']};color:{CLR['text_muted']};}}"
)
BTN_SECONDARY = (
    f"QPushButton {{background:{CLR['bg_card_2']};color:{CLR['text']};"
    f"border:1px solid {CLR['border_strong']};border-radius:{RADIUS_SM};"
    f"padding:8px 16px;font-size:{FONT_SIZE_SM};font-weight:500;min-height:32px;}}"
    f"QPushButton:hover{{background:{CLR['bg_hover']};border-color:{CLR['accent']};}}"
    f"QPushButton:disabled{{color:{CLR['text_muted']};}}"
)
BTN_PURPLE = (
    f"QPushButton {{background:{CLR['accent_2']};color:#F5F2EA;"
    f"border:none;border-radius:{RADIUS_SM};padding:8px 16px;"
    f"font-size:{FONT_SIZE_SM};font-weight:600;min-height:32px;}}"
    f"QPushButton:hover{{background:{CLR['accent_2_h']};}}"
)
BTN_DANGER = (
    f"QPushButton {{background:{CLR['accent_red']};color:#F5F2EA;"
    f"border:none;border-radius:{RADIUS_SM};padding:8px 16px;"
    f"font-size:{FONT_SIZE_SM};font-weight:600;min-height:32px;}}"
    f"QPushButton:hover{{background:{CLR['accent_red_h']};}}"
)
BTN_GHOST = (
    f"QPushButton {{background:transparent;color:{CLR['text_dim']};"
    f"border:1px solid {CLR['border']};border-radius:{RADIUS_SM};"
    f"padding:8px 14px;font-size:{FONT_SIZE_SM};min-height:32px;}}"
    f"QPushButton:hover{{background:{CLR['bg_card_2']};color:{CLR['text']};"
    f"border-color:{CLR['accent']};}}"
)


# Backwards-compat aliases
NAV_BTN_QSS = NAV_ITEM_QSS
PAD_LG_STR = str(PAD_LG)


def section_header_qss(accent: str = None) -> str:
    """Legacy helper — returns a QLabel stylesheet for section headers."""
    return (
        f"color:{CLR['text_dim']};font-size:{FONT_SIZE_XS};"
        f"font-weight:600;text-transform:uppercase;letter-spacing:1.2px;"
        f"background:transparent;padding:8px 0 4px 0;"
    )


# ── Compat aliases for older tab code ────────────────────────────────────────
APP_QSS   = ROOT_QSS
TAB_QSS   = CONTENT_QSS
INPUT_QSS = f"""
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {CLR['bg_input']};
    color: {CLR['text']};
    border: 1px solid {CLR['border']};
    border-radius: {RADIUS_SM};
    padding: 6px 10px;
    font-size: {FONT_SIZE_SM};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {CLR['accent']}; }}
"""

def stat_card_qss(accent=None):
    accent = accent or CLR['accent']
    return (
        f"QFrame{{background:{CLR['bg_card']};border:1px solid {CLR['border']};"
        f"border-radius:{RADIUS};}}"
    )

# Map old btn_style(variant) → new colors if called with a single variant string
_BTN_VARIANTS = {
    'primary': (CLR['accent'], CLR['accent_hover'], '#053019'),
    'success': (CLR['accent'], CLR['accent_hover'], '#053019'),
    'neutral': (CLR['bg_card_2'], CLR['bg_hover'], CLR['text']),
    'danger':  (CLR['accent_red'], CLR['accent_red_h'], '#ffffff'),
    'purple':  (CLR['accent_2'], CLR['accent_2_h'], '#ffffff'),
    'gold':    (CLR['bg_card_2'], CLR['bg_hover'], CLR['text']),
}

_orig_btn_style = btn_style
def btn_style(bg, hover=None, text="#ffffff", tall=False, small=False):
    """Accept either (variant) or (bg, hover, text)."""
    if hover is None and bg in _BTN_VARIANTS:
        b, h, t = _BTN_VARIANTS[bg]
        return _orig_btn_style(b, h, t, tall=tall, small=small)
    return _orig_btn_style(bg, hover, text, tall=tall, small=small)


# ── Light Mode — "Archaeological Studio" ─────────────────────────────────────
# Inspired by: limestone, parchment, excavation dust, bronze accents
LIGHT_CLR = {
    # Core backgrounds
    "bg_root":      "#F5F2EA",   # Soft Ivory — main background
    "bg_panel":     "#E7DFCF",   # Warm Sand — secondary background
    "bg_card":      "#FCFAF5",   # Stone White — card/panel
    "bg_card_2":    "#EDE8DC",   # deeper cream
    "bg_hover":     "#DDD5C5",
    "bg_input":     "#FCFAF5",
    "bg_table":     "#F8F5EE",
    "bg_row_alt":   "#EDE8DC",
    "bg_row_sel":   "#D0DCC8",   # soft olive selection

    # Borders
    "border":       "#C8BFAF",   # Dust Gray
    "border_soft":  "#DDDBD5",
    "border_strong":"#A89880",

    # Text
    "text":         "#2E2A26",   # Charcoal
    "text_dim":     "#6F655B",   # Muted Brown Gray
    "text_muted":   "#A39A8E",   # Soft Stone Gray
    "text_inv":     "#F5F2EA",

    # Accents
    "accent":       "#C89B3C",   # Archaeology Gold — primary
    "accent_hover": "#A87B28",
    "accent_text":  "#1A1200",   # dark text on gold buttons
    "accent_2":     "#8C6B3F",   # Oxidized Bronze — secondary
    "accent_2_h":   "#7A5830",
    "accent_3":     "#4F7C82",   # Ancient Teal — GIS/data
    "accent_warn":  "#D28B26",   # Amber Clay
    "accent_red":   "#B54A3F",   # Burnt Red
    "accent_red_h": "#9A3A30",

    # Status
    "status_ok":    "#6B8F5A",   # Olive Green
    "status_warn":  "#D28B26",   # Amber Clay
    "status_err":   "#B54A3F",   # Burnt Red
    "status_info":  "#5C7FA3",   # Slate Blue

    # Pills
    "pill_green":   "#6B8F5A",
    "pill_purple":  "#8C6B3F",
    "pill_cyan":    "#4F7C82",
    "pill_amber":   "#D28B26",
    "pill_red":     "#B54A3F",

    # Sidebar always stays dark (Deep Taupe in light mode)
    "sidebar_bg":        "#5D5348",
    "sidebar_text":      "#F5F2EA",
    "sidebar_text_dim":  "#C8BFAF",
    "sidebar_active_bg": "#6E6258",
}
LIGHT_CLR.update({
    "bg_dark":          LIGHT_CLR["bg_root"],
    "bg_content":       LIGHT_CLR["bg_panel"],
    "bg_white":         LIGHT_CLR["bg_card"],
    "accent_gold":      LIGHT_CLR["accent"],
    "accent_gold_light":LIGHT_CLR["accent_hover"],
    "accent_blue":      LIGHT_CLR["accent_3"],
    "accent_green":     LIGHT_CLR["accent"],
    "accent_purple":    LIGHT_CLR["accent_2"],
    "text_primary":     LIGHT_CLR["text"],
    "text_secondary":   LIGHT_CLR["text_dim"],
    "text_dark":        LIGHT_CLR["text_inv"],
    "border_dark":      LIGHT_CLR["border"],
    "border_gold":      LIGHT_CLR["accent"],
    "row_a":            LIGHT_CLR["bg_table"],
    "row_b":            LIGHT_CLR["bg_row_alt"],
})


def build_root_qss(c):
    """Build ROOT_QSS parameterised with colour dict c."""
    return f"""
QMainWindow, QWidget#root, QWidget#content {{
    background: {c['bg_panel']};
    color: {c['text']};
    font-family: {FONT_SANS};
    font-size: {FONT_SIZE_SM};
}}
QLabel {{
    color: {c['text']};
    background: transparent;
    font-family: {FONT_SANS};
}}
QToolTip {{
    background: {c['bg_card_2']};
    color: {c['text']};
    border: 1px solid {c['border_strong']};
    padding: 6px 10px;
    border-radius: 4px;
    font-size: {FONT_SIZE_SM};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {c['border_strong']};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border_strong']};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {c['bg_input']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: {RADIUS_SM};
    padding: 7px 10px;
    font-size: {FONT_SIZE_SM};
    min-height: 22px;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {c['accent']};
}}
QComboBox {{
    background: {c['bg_input']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: {RADIUS_SM};
    padding: 6px 28px 6px 10px;
    font-size: {FONT_SIZE_SM};
    min-height: 22px;
}}
QComboBox:hover {{ border: 1px solid {c['border_strong']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {c['bg_card_2']};
    color: {c['text']};
    border: 1px solid {c['border_strong']};
    selection-background-color: {c['bg_row_sel']};
    selection-color: {c['text']};
    outline: none;
}}
QCheckBox {{
    color: {c['text']};
    font-size: {FONT_SIZE_SM};
    spacing: 8px;
}}
QGroupBox {{
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: {RADIUS};
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px; top: -2px;
    padding: 0 6px;
    color: {c['text_dim']};
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}
"""


def build_sidebar_qss(c):
    # Sidebar always uses its own dark tokens regardless of light/dark mode
    SBG   = c.get("sidebar_bg",        c["bg_root"])
    STXT  = c.get("sidebar_text",      c["text"])
    STDIM = c.get("sidebar_text_dim",  c["text_dim"])
    SABG  = c.get("sidebar_active_bg", c["bg_card"])
    return f"""
QWidget#sidebar {{
    background: {SBG};
    border-right: 1px solid {c['border']};
}}
QWidget#sidebar QScrollArea {{
    background: {SBG};
    border: none;
}}
QWidget#sidebar QWidget {{
    background: {SBG};
}}
QWidget#sidebar QLabel {{
    color: {STDIM};
    font-size: {FONT_SIZE_SM};
}}
QWidget#sidebar QLabel#brand {{
    color: {STXT};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QWidget#sidebar QLabel#brand_sub {{
    color: {STDIM};
    font-size: {FONT_SIZE_XS};
}}
QWidget#sidebar QLabel#sectionLabel {{
    color: {STDIM};
    font-size: {FONT_SIZE_XS};
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 14px 18px 5px 18px;
}}
QWidget#sidebar QFrame#navSep {{
    background: {SABG};
    max-height: 1px;
    border: none;
    margin: 6px 20px;
}}
"""


def build_card_qss(c):
    return f"""
QFrame#card {{
    background: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: {RADIUS};
}}
QFrame#card QLabel {{ background: transparent; }}
QFrame#cardHeader {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {c['border']};
}}
QLabel#cardTitle {{
    color: {c['text']};
    font-size: {FONT_SIZE_LG};
    font-weight: 600;
}}
QLabel#cardSub {{
    color: {c['text_dim']};
    font-size: {FONT_SIZE_SM};
}}
QLabel#statBig {{
    color: {c['text']};
    font-size: 28px;
    font-weight: 700;
}}
QLabel#statLabel {{
    color: {c['text_dim']};
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
}}
QLabel#statDelta {{
    color: {c['accent']};
    font-size: {FONT_SIZE_XS};
}}
"""


def build_table_qss(c):
    return f"""
QTableWidget {{
    background: {c['bg_table']};
    alternate-background-color: {c['bg_row_alt']};
    color: {c['text']};
    gridline-color: {c['border_soft']};
    border: 1px solid {c['border']};
    border-radius: {RADIUS_SM};
    selection-background-color: {c['bg_row_sel']};
    selection-color: {c['text']};
    font-size: {FONT_SIZE_SM};
}}
QTableWidget::item {{ padding: 8px 10px; border: none; }}
QTableWidget::item:selected {{
    background: {c['bg_row_sel']};
    color: {c['text']};
}}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {c['bg_card_2']};
    color: {c['text_dim']};
    border: none;
    border-bottom: 1px solid {c['border']};
    border-right: 1px solid {c['border_soft']};
    padding: 9px 10px;
    font-weight: 600;
    font-size: {FONT_SIZE_XS};
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}
QHeaderView::section:last {{ border-right: none; }}
"""


def build_content_qss(c):
    return f"""
QWidget#content {{ background: {c['bg_panel']}; }}

QFrame#topbar {{
    background: {c['bg_panel']};
    border-bottom: 1px solid {c['border']};
}}
QLabel#pageTitle {{
    color: {c['text']};
    font-size: 20px;
    font-weight: 700;
}}
QLabel#pageSub {{
    color: {c['text_dim']};
    font-size: {FONT_SIZE_SM};
}}

/* Hidden tab bar — sub-tabs only */
QTabWidget::pane {{
    border: none;
    background: {c['bg_panel']};
}}
QTabBar::tab {{
    background: transparent;
    color: {c['text_dim']};
    padding: 8px 16px;
    border: none;
    font-size: {FONT_SIZE_SM};
    min-width: 80px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background: {c['bg_card']};
    color: {c['text']};
    border-bottom: 2px solid {c['accent']};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {c['text']}; }}
"""


def build_status_bar_qss(c):
    return f"""
QStatusBar {{
    background: {c['bg_root']};
    color: {c['text_dim']};
    border-top: 1px solid {c['border']};
    font-size: {FONT_SIZE_XS};
    padding: 4px 12px;
    min-height: 28px;
}}
QStatusBar::item {{ border: none; }}
QWidget#statusBar {{
    background: {c['sidebar_bg']};
    border-top: 1px solid {c['border']};
    color: {c['sidebar_text_dim']};
}}
"""


def build_nav_item_qss(c):
    # Nav items live on the dark sidebar — always use sidebar text tokens
    STXT  = c.get("sidebar_text",      c["text"])
    STDIM = c.get("sidebar_text_dim",  c["text_dim"])
    SABG  = c.get("sidebar_active_bg", c["bg_card"])
    return f"""
QPushButton#navItem {{
    background: transparent;
    color: {STDIM};
    border: none;
    border-left: 3px solid transparent;
    padding: 11px 16px;
    text-align: left;
    font-size: {FONT_SIZE_SM};
    font-weight: 500;
    min-height: 46px;
}}
QPushButton#navItem:checked {{
    background: {SABG};
    color: {c['accent']};
    border-left: 3px solid {c['accent']};
    font-weight: 600;
}}
QPushButton#navItem:hover:!checked {{
    background: {SABG};
    color: {STXT};
    border-left: 3px solid {c['border_strong']};
}}
QPushButton#navItem QLabel {{
    color: {STDIM};
    background: transparent;
    font-size: {FONT_SIZE_SM};
}}
"""


def _build_btn_named_qss(c):
    R = RADIUS_SM
    FS = FONT_SIZE_SM
    # Dark text on gold accent buttons for both modes
    atxt = c.get("accent_text", "#1A1200")
    return f"""
QPushButton#btn_primary {{
    background:{c['accent']};color:{atxt};
    border:none;border-radius:{R};padding:8px 16px;
    font-size:{FS};font-weight:700;min-height:32px;
}}
QPushButton#btn_primary:hover{{background:{c['accent_hover']};}}
QPushButton#btn_primary:disabled{{background:{c['bg_card']};color:{c['text_muted']};}}

QPushButton#btn_secondary {{
    background:{c['bg_card_2']};color:{c['text']};
    border:1px solid {c['border_strong']};border-radius:{R};
    padding:8px 16px;font-size:{FS};font-weight:500;min-height:32px;
}}
QPushButton#btn_secondary:hover{{background:{c['bg_hover']};border-color:{c['accent']};}}
QPushButton#btn_secondary:disabled{{color:{c['text_muted']};}}

QPushButton#btn_ghost {{
    background:transparent;color:{c['text_dim']};
    border:1px solid {c['border']};border-radius:{R};
    padding:8px 14px;font-size:{FS};min-height:32px;
}}
QPushButton#btn_ghost:hover{{background:{c['bg_card_2']};color:{c['text']};border-color:{c['accent']};}}

QPushButton#btn_purple {{
    background:{c['accent_2']};color:#F5F2EA;
    border:none;border-radius:{R};padding:8px 16px;
    font-size:{FS};font-weight:600;min-height:32px;
}}
QPushButton#btn_purple:hover{{background:{c['accent_2_h']};}}

QPushButton#btn_danger {{
    background:{c['accent_red']};color:#F5F2EA;
    border:none;border-radius:{R};padding:8px 16px;
    font-size:{FS};font-weight:600;min-height:32px;
}}
QPushButton#btn_danger:hover{{background:{c['accent_red_h']};}}
"""


def build_misc_qss(c):
    """Semantic, theme-aware rules for in-tab labels, search boxes, detail
    panels and composite sub-tabs. Replaces the old hardcoded inline styles so
    every tab restyles correctly when the theme toggles."""
    R = RADIUS_SM
    return f"""
/* ── Typographic scale (page + section headings) ─────────────────────── */
QLabel#h1 {{ font-size:22px; font-weight:700; color:{c['text']}; background:transparent; }}
QLabel#h2 {{ font-size:18px; font-weight:700; color:{c['text']}; background:transparent; }}
QLabel#h3 {{ font-size:15px; font-weight:700; color:{c['text']}; background:transparent; }}
QLabel#h4 {{ font-size:13px; font-weight:700; color:{c['text']}; background:transparent; }}
QLabel#secTitle {{ font-size:20px; font-weight:700; color:{c['text']}; background:transparent; }}
QLabel#secSub {{ font-size:12px; color:{c['text_dim']}; background:transparent; }}

/* ── Muted / supporting text ─────────────────────────────────────────── */
QLabel#muted    {{ font-size:11px; color:{c['text_dim']};   background:transparent; }}
QLabel#mutedXs  {{ font-size:10px; color:{c['text_dim']};   background:transparent; }}
QLabel#mutedSm  {{ font-size:10px; color:{c['text_muted']}; background:transparent; }}
QLabel#bodyText {{ font-size:11px; color:{c['text']};       background:transparent; }}
QLabel#formLabel {{ font-size:10px; color:{c['text']};      background:transparent; }}
QLabel#accentLabel {{ font-size:12px; font-weight:600; color:{c['accent']}; background:transparent; }}

/* ── Small framed elements ───────────────────────────────────────────── */
QLabel#infoBox {{
    background:{c['bg_card_2']}; color:{c['text']};
    padding:8px 12px; border-radius:{R}; font-size:{FONT_SIZE_SM};
}}
QLabel#chipHeader {{
    background:{c['bg_card_2']}; color:{c['accent']};
    padding:6px 12px; border-radius:{R};
    font-size:{FONT_SIZE_SM}; font-weight:600;
}}
QLabel#imageSlot {{
    background:{c['bg_input']}; color:{c['text_dim']};
    border:1px solid {c['border']}; border-radius:{R};
}}
QFrame#hsep {{ background:{c['border']}; max-height:1px; border:none; }}
QFrame#navSep {{
    background:{c.get('sidebar_active_bg', c['border'])};
    max-height:1px; border:none;
    margin:6px 18px;
}}

/* ── Page/section content headers ────────────────────────────────────── */
QWidget#pageHeader {{ background:transparent; }}
QWidget#pageHeader QLabel#secTitle {{
    font-size:20px; font-weight:700; color:{c['text']}; background:transparent;
}}
QWidget#pageHeader QLabel#secSub {{
    font-size:{FONT_SIZE_SM}; color:{c['text_dim']}; background:transparent;
}}

/* ── Search box (icon + line edit inside a rounded frame) ────────────── */
QFrame#searchBox {{
    background:{c['bg_input']}; border:1px solid {c['border']};
    border-radius:{R};
}}
QFrame#searchBox QLineEdit {{
    background:transparent; border:none; color:{c['text']};
    font-size:{FONT_SIZE_SM};
}}
QFrame#searchBox QLabel {{ color:{c['text_dim']}; font-size:14px; background:transparent; }}

/* ── Gallery list ──────────────────────────────────────────────────── */
QListWidget#gallery {{
    background:{c['bg_table']};
    border:1px solid {c['border']};
    border-radius:{RADIUS};
}}
QListWidget#gallery::item {{
    background:{c['bg_card']};
    border:1px solid {c['border']};
    border-radius:6px;
    padding:4px; margin:4px;
    color:{c['text']};
}}
QListWidget#gallery::item:selected {{
    background:{c['bg_row_sel']};
    border:1px solid {c['accent']};
}}
QListWidget#gallery::item:hover:!selected {{
    background:{c['bg_hover']};
    border:1px solid {c['border_strong']};
}}

/* ── Detail panel key/value rows ─────────────────────────────────────── */
QLabel#detailKey {{
    color:{c['text_muted']}; font-size:10px; font-weight:600;
    letter-spacing:1px; background:transparent; text-transform:uppercase;
}}
QLabel#detailVal {{ color:{c['text']}; font-size:{FONT_SIZE_MD}; background:transparent; }}
QLabel#detailEmpty {{
    color:{c['text_muted']}; font-size:{FONT_SIZE_SM};
    background:transparent; padding:20px 0;
}}

/* ── Action bar strip ────────────────────────────────────────────────── */
QWidget#actionBar {{
    background:{c['bg_panel']};
    border-bottom:1px solid {c['border']};
}}
QWidget#actionBar QLabel {{
    color:{c['text_dim']}; font-size:{FONT_SIZE_SM}; background:transparent;
}}

/* ── Tab content page ────────────────────────────────────────────────── */
QWidget#tabPage {{ background:transparent; }}

/* ── Info/status cards ───────────────────────────────────────────────── */
QFrame#infoCard {{
    background:{c['bg_card_2']};
    border-left:3px solid {c['accent']};
    border-radius:{R};
}}
QFrame#infoCard QLabel {{ color:{c['text']}; background:transparent; font-size:{FONT_SIZE_SM}; }}
QFrame#warnCard {{
    background:{c['bg_card_2']};
    border-left:3px solid {c['accent_warn']};
    border-radius:{R};
}}
QFrame#warnCard QLabel {{ color:{c['text']}; background:transparent; font-size:{FONT_SIZE_SM}; }}

/* ── Progress bar ────────────────────────────────────────────────────── */
QProgressBar {{
    background:{c['bg_card_2']};
    border:none; border-radius:6px;
    text-align:center; color:{c['text']};
    font-size:{FONT_SIZE_XS}; font-weight:600;
    min-height:14px;
}}
QProgressBar::chunk {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {c['accent']}, stop:1 {c['accent_hover']});
    border-radius:6px;
}}

/* ── Composite sub-tabs (Harris/Drawings/Grid, Artifacts, Recording) ──── */
QTabWidget#subTabs::pane {{
    border:none;
    border-top:1px solid {c['border']};
    background:transparent;
    top:-1px;
}}
QTabWidget#subTabs > QTabBar {{ background:transparent; }}
QTabWidget#subTabs > QTabBar::tab {{
    background:transparent; color:{c['text_dim']};
    padding:9px 20px; border:none;
    border-bottom:2px solid transparent;
    font-size:{FONT_SIZE_SM}; font-weight:500;
    min-width:90px; margin-right:2px;
}}
QTabWidget#subTabs > QTabBar::tab:selected {{
    color:{c['accent']};
    border-bottom:2px solid {c['accent']};
    font-weight:700;
    background:{c['bg_card']};
}}
QTabWidget#subTabs > QTabBar::tab:hover:!selected {{
    color:{c['text']};
    background:{c['bg_hover']};
}}

/* ── Collapsible section buttons ─────────────────────────────────────── */
QPushButton#collapseBtn {{
    background:{c['bg_card']}; color:{c['text_dim']};
    border:none; border-top:1px solid {c['border']};
    padding:8px 14px; font-size:{FONT_SIZE_SM}; font-weight:600;
    text-align:left;
}}
QPushButton#collapseBtn:checked {{ color:{c['text']}; }}
QPushButton#collapseBtn:hover {{ background:{c['bg_card_2']}; }}

/* ── Small icon tool buttons ─────────────────────────────────────────── */
QToolButton#iconBtn {{
    background:{c['bg_card_2']}; color:{c['text']};
    border:none; border-radius:{R}; font-size:13px;
}}
QToolButton#iconBtn:hover {{ background:{c['bg_hover']}; }}

/* ── Empty state ─────────────────────────────────────────────────────── */
QLabel#emptyState {{
    color:{c['text_muted']}; font-size:{FONT_SIZE_SM};
    background:transparent; padding:32px 0;
}}

/* ── Status bar message ──────────────────────────────────────────────── */
QLabel#statusMsg {{
    color:{c['text_dim']}; font-size:10px;
    background:transparent; padding:4px 0;
}}
QLabel#statusMsgOk  {{ color:{c['status_ok']};  font-size:10px; background:transparent; }}
QLabel#statusMsgErr {{ color:{c['status_err']}; font-size:10px; background:transparent; }}

/* ── History tab user input ──────────────────────────────────────────── */
QLineEdit#histUserInput {{
    background:{c['bg_input']}; color:{c['text']};
    border:1px solid {c['border']};
    border-left:3px solid {c['accent']};
    border-radius:4px; padding:6px 10px;
    font-size:{FONT_SIZE_SM};
}}

/* ── Photo / image placeholders ──────────────────────────────────────── */
QLabel#photoPlaceholder {{
    border:2px dashed {c['border_strong']};
    border-radius:8px; color:{c['text_muted']};
    font-size:13px; background:{c['bg_card']};
}}

/* ── Map placeholder (no canvas) ─────────────────────────────────────── */
QLabel#mapPlaceholder {{
    border:2px dashed {c['border']}; border-radius:8px;
    color:{c['text_muted']}; background:transparent;
}}
"""


def build_all_qss(c):
    """Build complete application QSS from a colour dict c."""
    btn_fallback = f"""
QPushButton {{
    background: {c['bg_card_2']};
    color: {c['text']};
    border: 1px solid {c['border_strong']};
    border-radius: 5px;
    padding: 7px 14px;
    font-size: 11px;
    font-weight: 500;
    min-height: 30px;
}}
QPushButton:hover {{ background: {c['bg_hover']}; }}
QPushButton:disabled {{ color: {c['text_muted']}; }}
QFrame {{ background: transparent; }}
QWidget {{ background: transparent; color: {c['text']}; }}
"""
    return (
        btn_fallback
        + build_root_qss(c)
        + build_sidebar_qss(c)
        + build_card_qss(c)
        + build_table_qss(c)
        + build_content_qss(c)
        + build_status_bar_qss(c)
        + build_nav_item_qss(c)
        + _build_btn_named_qss(c)
        + build_misc_qss(c)
    )
