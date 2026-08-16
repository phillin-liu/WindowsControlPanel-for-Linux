"""theme.py — Win11 Fluent 风格主题管理（明暗模式 / 强调色 / 字体缩放）"""
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication

FONT_STACK = ["Segoe UI Variable Display", "Segoe UI", "Noto Sans CJK SC",
              "WenQuanYi Micro Hei", "Microsoft YaHei UI", "Ubuntu", "sans-serif"]

ACCENTS = ["#0067C0", "#0078D4", "#4CC2FF", "#00B7C3", "#038387", "#107C10",
           "#498205", "#8CBD18", "#C19C00", "#CA5010", "#DA3B01", "#EF6950",
           "#E3008C", "#BF0077", "#9A0089", "#744DA9", "#8764B8", "#6B69D6",
           "#7A7574", "#4C4A48", "#69797E", "#4A5459"]

_settings = QSettings("Win11Panel", "Win11Panel")


def load_theme() -> dict:
    return {"dark": _settings.value("theme/dark", False, type=bool),
            "accent": _settings.value("theme/accent", "#0067C0", type=str),
            "font_scale": _settings.value("theme/font_scale", 1.0, type=float),
            "high_contrast": _settings.value("theme/high_contrast", False, type=bool),
            "reduce_motion": _settings.value("theme/reduce_motion", False, type=bool)}


def save_theme(**kw):
    for k, v in kw.items():
        _settings.setValue(f"theme/{k}", v)


def palette_colors(dark: bool, high_contrast: bool = False) -> dict:
    if high_contrast:
        return {
            "bg": "#000000", "card": "#000000", "border": "#FFFFFF", "text": "#FFFFFF",
            "subtext": "#FFFFFF", "hover": "#2A2A2A", "selected": "#3A3A3A",
            "accent": "#FFFF00", "on_accent": "#000000", "input": "#1B1B1B",
        }
    if dark:
        return {
            "bg": "#202020", "card": "#2C2C2C", "border": "#3D3D3D", "text": "#FFFFFF",
            "subtext": "#CFCFCF", "hover": "rgba(255,255,255,0.06)",
            "selected": "rgba(76,194,255,0.15)", "accent": "#4CC2FF",
            "on_accent": "#000000", "input": "#333333",
        }
    return {
        "bg": "#F3F3F3", "card": "#FBFBFB", "border": "#E5E5E5", "text": "#1A1A1A",
        "subtext": "#5F5F5F", "hover": "rgba(0,0,0,0.045)",
        "selected": "rgba(0,103,192,0.10)", "accent": "#0067C0",
        "on_accent": "#FFFFFF", "input": "#FFFFFF",
    }


def accent_of(theme: dict) -> str:
    """暗色模式使用更亮的强调色"""
    if theme["dark"] and not theme["high_contrast"]:
        base = QColor(theme["accent"])
        if base.lightness() < 140:
            base = base.lighter(190)
        return base.name()
    return theme["accent"]


def build_qss(theme: dict) -> str:
    c = palette_colors(theme["dark"], theme["high_contrast"])
    accent = accent_of(theme)
    s = theme["font_scale"]
    px = lambda n: int(n * s)
    return f"""
* {{ font-family: {', '.join(FONT_STACK)}; outline: none; }}
QMainWindow, QDialog {{ background: {c['bg']}; }}
QWidget {{ color: {c['text']}; font-size: {px(13)}px; }}
QLabel {{ background: transparent; }}
QLabel#pageTitle {{ font-size: {px(21)}px; font-weight: 600; }}
QLabel#pageSubtitle {{ color: {c['subtext']}; font-size: {px(13)}px; }}
QLabel#sectionTitle {{ font-size: {px(15)}px; font-weight: 600; padding: 2px 0; }}
QLabel#cardTitle {{ font-size: {px(14)}px; font-weight: 600; }}
QLabel#subText {{ color: {c['subtext']}; font-size: {px(12)}px; }}
QLabel#bigValue {{ font-size: {px(18)}px; font-weight: 600; }}

QFrame#card {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 8px; }}
QFrame#divider {{ background: {c['border']}; border: none; max-height: 1px; }}

/* 侧边栏导航 */
QWidget#navItem {{ border-radius: 6px; padding: 0; }}
QWidget#navItem:hover {{ background: {c['hover']}; }}
QWidget#navItem[selected="true"] {{ background: {c['selected']};
    border-left: 3px solid {accent}; }}
QLabel#navText {{ font-size: {px(14)}px; padding: 0; background: transparent; }}
QLabel#navIcon, QLabel#navArrow {{ background: transparent; }}

/* 搜索框 */
QLineEdit {{ background: {c['input']}; border: 1px solid {c['border']};
             border-radius: {px(16)}px; padding: {px(6)}px {px(14)}px;
             font-size: {px(13)}px; selection-background-color: {accent}; }}
QLineEdit:focus {{ border-color: {accent}; }}

/* 按钮 */
QPushButton {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 5px; padding: {px(6)}px {px(14)}px; font-size: {px(13)}px; }}
QPushButton:hover {{ background: {c['hover']}; border-color: {c['subtext']}; }}
QPushButton:pressed {{ background: {c['border']}; }}
QPushButton:disabled {{ color: {c['subtext']}; }}
QPushButton#accentBtn {{ background: {accent}; color: {c['on_accent']};
                         border: 1px solid {accent}; font-weight: 600; }}
QPushButton#accentBtn:hover {{ opacity: 0.9; }}
QPushButton#dangerBtn {{ color: #C42B1C; }}

/* 下拉框 */
QComboBox {{ background: {c['input']}; border: 1px solid {c['border']};
             border-radius: 5px; padding: {px(5)}px {px(10)}px; min-width: {px(140)}px; }}
QComboBox:hover {{ border-color: {c['subtext']}; }}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: {px(24)}px; }}
QComboBox::down-arrow {{ image: none; border-left: {px(4)}px solid transparent;
    border-right: {px(4)}px solid transparent; border-top: {px(5)}px solid {c['subtext']}; }}
QComboBox QAbstractItemView {{ background: {c['card']}; border: 1px solid {c['border']};
    selection-background-color: {c['selected']}; selection-color: {c['text']};
    border-radius: 6px; outline: none; }}

/* 滑块 */
QSlider::groove:horizontal {{ height: {px(4)}px; background: {c['border']};
                              border-radius: {px(2)}px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: {px(2)}px; }}
QSlider::handle:horizontal {{ width: {px(16)}px; height: {px(16)}px; margin: -{px(7)}px 0;
    border-radius: {px(8)}px; background: {accent}; border: {px(4)}px solid {accent}; }}
QSlider::handle:horizontal:hover {{ background: {c['card']}; }}
QSlider::groove:vertical {{ width: {px(4)}px; background: {c['border']};
                            border-radius: {px(2)}px; }}
QSlider::add-page:vertical {{ background: {accent}; border-radius: {px(2)}px; }}

/* 进度条 */
QProgressBar {{ background: {c['border']}; border: none; border-radius: {px(3)}px;
                text-align: center; font-size: {px(11)}px; color: {c['text']};
                max-height: {px(8)}px; }}
QProgressBar::chunk {{ background: {accent}; border-radius: {px(3)}px; }}
QProgressBar[invertedColor="true"]::chunk {{ background: #C42B1C; }}

/* 滚动区 */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: {px(12)}px; margin: {px(2)}px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: {px(4)}px;
                               min-height: {px(30)}px; }}
QScrollBar::handle:vertical:hover {{ background: {c['subtext']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: {px(12)}px; margin: {px(2)}px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: {px(4)}px;
                                 min-width: {px(30)}px; }}

/* 文本编辑 */
QPlainTextEdit, QTextEdit {{ background: {c['input']}; border: 1px solid {c['border']};
    border-radius: 6px; font-family: 'Cascadia Mono', 'Noto Sans Mono CJK SC', monospace;
    font-size: {px(12)}px; }}
QPlainTextEdit:focus {{ border-color: {accent}; }}

QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']};
            padding: {px(4)}px {px(8)}px; border-radius: 4px; }}

QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 6px; top: -1px; }}
QTabBar::tab {{ padding: {px(6)}px {px(16)}px; border-top-left-radius: 6px;
                border-top-right-radius: 6px; }}
QTabBar::tab:selected {{ background: {c['card']}; }}
QCheckBox {{ spacing: {px(8)}px; }}
QCheckBox::indicator {{ width: {px(16)}px; height: {px(16)}px;
                        border-radius: 4px; border: 1px solid {c['subtext']}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent};
    image: url(none); }}
QRadioButton::indicator {{ width: {px(16)}px; height: {px(16)}px; border-radius: 8px;
                           border: 1px solid {c['subtext']}; }}
QRadioButton::indicator:checked {{ border: {px(5)}px solid {accent}; background: {c['card']}; }}
QSpinBox, QDoubleSpinBox, QDateTimeEdit {{ background: {c['input']};
    border: 1px solid {c['border']}; border-radius: 5px; padding: {px(4)}px {px(8)}px; }}
QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {{ border-color: {accent}; }}

/* ---------------- 经典控制面板 (Control Panel) ---------------- */
QFrame#topbar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
QFrame#subbar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
QLabel#cplSubtitle {{ color: {c['subtext']}; font-size: {px(13)}px; }}
QLabel#cplPageTitle {{ font-size: {px(21)}px; font-weight: 600; padding: 0 0 {px(6)}px 0; }}
QLabel#crumbSep {{ color: {c['subtext']}; padding: 0 {px(4)}px; background: transparent; }}

QPushButton#linkBtn {{ color: #0066CC; background: transparent; border: none;
    text-align: left; padding: {px(1)}px 0; font-size: {px(13)}px; }}
QPushButton#linkBtn:hover {{ color: #3399FF; }}
QPushButton#linkBtn:pressed {{ color: #004C99; }}

QPushButton#crumbBtn {{ color: #0066CC; background: transparent; border: none;
    padding: {px(2)}px {px(3)}px; font-size: {px(13)}px; }}
QPushButton#crumbBtn:hover {{ background: rgba(0,102,204,0.10); border-radius: 4px; }}

QPushButton#navArrow {{ color: {c['text']}; background: transparent; border: none;
    border-radius: 15px; font-size: {px(18)}px; font-weight: 600; }}
QPushButton#navArrow:hover {{ background: rgba(0,102,204,0.12); }}
QPushButton#navArrow:disabled {{ color: {c['border']}; }}

QFrame#cplCard {{ background: {c['card']}; border: 1px solid {c['border']};
                  border-radius: 6px; }}

QListWidget {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 6px; outline: none; }}
QListWidget::item {{ padding: {px(4)}px; border-radius: 4px; }}
QListWidget::item:hover {{ background: rgba(0,102,204,0.08); }}
QListWidget::item:selected {{ background: rgba(0,102,204,0.18); }}

QTreeWidget {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 6px; outline: none;
               alternate-background-color: {c['bg']}; }}
QTreeWidget::item:hover {{ background: rgba(0,102,204,0.08); }}
QTreeWidget::item:selected {{ background: rgba(0,102,204,0.18); }}

QTableWidget {{ background: {c['card']}; border: 1px solid {c['border']};
                border-radius: 6px; gridline-color: {c['border']};
                alternate-background-color: {c['bg']}; }}
QTableWidget::item:selected {{ background: rgba(0,102,204,0.18); }}
QHeaderView::section {{ background: {c['bg']}; color: {c['text']};
    border: none; border-bottom: 1px solid {c['border']};
    padding: {px(5)}px {px(8)}px; font-weight: 600; }}
"""


def apply_theme(app: QApplication):
    theme = load_theme()
    font = QFont(FONT_STACK[0], int(10 * theme["font_scale"]))
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(build_qss(theme))
    pal = app.palette()
    c = palette_colors(theme["dark"], theme["high_contrast"])
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.Base, QColor(c["input"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(accent_of(theme)))
    app.setPalette(pal)
