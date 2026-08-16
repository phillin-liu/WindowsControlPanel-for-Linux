"""theme.py — Win11 Fluent 风格主题管理（明暗模式 / 强调色 / 字体缩放）"""
import os
import re
import subprocess

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication

FONT_STACK = ["Segoe UI Variable Display", "Segoe UI", "Noto Sans CJK SC",
              "WenQuanYi Micro Hei", "Microsoft YaHei UI", "Ubuntu", "sans-serif"]

# Win11 默认强调色
ACCENTS = ["#0067C0", "#0078D4", "#4CC2FF", "#00B7C3", "#038387", "#107C10",
           "#498205", "#8CBD18", "#C19C00", "#CA5010", "#DA3B01", "#EF6950",
           "#E3008C", "#BF0077", "#9A0089", "#744DA9", "#8764B8", "#6B69D6",
           "#7A7574", "#4C4A48", "#69797E", "#4A5459"]

_settings = QSettings("Win11Panel", "Win11Panel")


# ============================================================
# 系统主题检测 (GNOME / KDE / XFCE / GTK)
# ============================================================
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _gsettings(schema: str, key: str) -> str | None:
    """读取 gsettings 值 (需安装 dconf/gsettings)"""
    try:
        r = subprocess.run(["gsettings", "get", schema, key],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            v = r.stdout.strip()
            return v if v and v != "" else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _kreadconfig(group: str, key: str) -> str | None:
    """读取 KDE 配置"""
    try:
        r = subprocess.run(["kreadconfig5", "--group", group,
                            "--key", key], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        r = subprocess.run(["kreadconfig6", "--group", group,
                            "--key", key], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _parse_color(s: str) -> str | None:
    """解析各种颜色格式为 #RRGGBB"""
    if not s:
        return None
    s = s.strip().strip("'").strip('"')
    # 已经是 hex
    if _HEX_RE.match(s):
        return "#" + _HEX_RE.match(s).group(1)
    # rgb(r,g,b)
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s, re.I)
    if m:
        return "#{:02X}{:02X}{:02X}".format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def detect_system_accent() -> str | None:
    """检测系统强调色, 返回 #RRGGBB; 失败返回 None"""
    # 1) GNOME: org.gnome.desktop.interface accent-color (GNOME 42+)
    v = _gsettings("org.gnome.desktop.interface", "accent-color")
    c = _parse_color(v) if v else None
    if c:
        return c
    # 2) GNOME 经典主题
    theme_name = (_gsettings("org.gnome.desktop.interface", "gtk-theme") or "").lower()
    for default in ("blue", "Yaru", "adwaita"):
        if default.lower() in theme_name:
            return "#0078D4" if default.lower() == "blue" else "#E95420"
    # 3) KDE Plasma: colors/Button/BackgroundNormal 等
    for k in ("colors:Button/BackgroundNormal", "Colors:Button/BackgroundNormal"):
        v = _kreadconfig("General", k)
        c = _parse_color(v) if v else None
        if c:
            return c
    # 4) Ubuntu Yaru / 桌面环境
    if os.environ.get("XDG_CURRENT_DESKTOP", "").lower() in ("ubuntu:gnome", "ubuntu"):
        return "#E95420"
    if "kde" in os.environ.get("XDG_SESSION_DESKTOP", "").lower():
        # KDE 默认蓝
        v = _kreadconfig("KDE", "AccentColor")
        c = _parse_color(v) if v else None
        return c or "#0078D4"
    # 5) Cinnamon / XFCE
    v = _gsettings("org.cinnamon.desktop.interface", "accent-color")
    c = _parse_color(v) if v else None
    if c:
        return c
    return None


def detect_system_dark() -> bool | None:
    """检测系统明暗模式; 失败返回 None"""
    # 1) GNOME
    v = _gsettings("org.gnome.desktop.interface", "color-scheme")
    if v:
        return "dark" in v.lower()
    # 2) KDE
    v = _kreadconfig("General", "ColorScheme")
    if v:
        return "dark" in v.lower() or "breeze dark" in v.lower()
    # 3) Cinnamon
    v = _gsettings("org.cinnamon.desktop.interface", "gtk-theme")
    if v and "dark" in v.lower():
        return True
    # 4) 通过 gsettings 看 gnome 主题是否为 dark
    v = _gsettings("org.gnome.desktop.interface", "gtk-theme")
    if v and "dark" in v.lower():
        return True
    return None


def follow_system_theme(force: bool = False) -> dict:
    """返回系统当前主题 (dark, accent); 当 force=True 时覆盖用户设置
    用户已手动设置时 (QSettings 有值) 不自动跟随, 除非 force=True
    """
    user_accent = _settings.value("theme/accent", None, type=str)
    user_dark = _settings.value("theme/dark", None, type=bool)
    accent = user_accent if (user_accent and not force) else (detect_system_accent() or "#0067C0")
    if user_dark is None or force:
        dark = detect_system_dark()
        if dark is None:
            dark = False
    else:
        dark = user_dark
    return {"dark": bool(dark), "accent": accent}


def load_theme() -> dict:
    """加载主题: 用户没显式设置 (QSettings 无值) 时自动跟随系统"""
    follow_accent = _settings.value("theme/_follow_accent", False, type=bool)
    # 跟随模式下每次都重新检测系统色 (无需重启)
    if follow_accent:
        sys_accent = detect_system_accent() or "#0067C0"
        # 同步到设置 (供 UI 显示)
        _settings.setValue("theme/accent", sys_accent)
    else:
        sys_accent = detect_system_accent() or "#0067C0"
    sys_dark = detect_system_dark()
    if sys_dark is None:
        sys_dark = False
    user_accent = _settings.value("theme/accent", None, type=str)
    user_dark_raw = _settings.value("theme/dark", None)
    if user_dark_raw is None:
        user_dark = sys_dark
    else:
        if isinstance(user_dark_raw, str):
            user_dark = user_dark_raw.lower() in ("true", "1", "yes")
        else:
            user_dark = bool(user_dark_raw)
    return {"dark": user_dark,
            "accent": user_accent if user_accent else sys_accent,
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
    # 强调色透明变体 (用于 hover/selected 背景)
    ar, ag, ab = QColor(accent).red(), QColor(accent).green(), QColor(accent).blue()
    a10 = f"rgba({ar},{ag},{ab},0.10)"
    a18 = f"rgba({ar},{ag},{ab},0.18)"
    a08 = f"rgba({ar},{ag},{ab},0.08)"
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

/* 按钮 - 默认使用强调色作为次按钮边框/悬停色 */
QPushButton {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 5px; padding: {px(6)}px {px(14)}px; font-size: {px(13)}px; }}
QPushButton:hover {{ background: {a10}; border-color: {accent}; }}
QPushButton:pressed {{ background: {a18}; }}
QPushButton:disabled {{ color: {c['subtext']}; }}
QPushButton#accentBtn {{ background: {accent}; color: {c['on_accent']};
                         border: 1px solid {accent}; font-weight: 600; }}
QPushButton#accentBtn:hover {{ background: {QColor(accent).darker(110).name()}; }}
QPushButton#dangerBtn {{ color: #C42B1C; }}

/* 下拉框 */
QComboBox {{ background: {c['input']}; border: 1px solid {c['border']};
             border-radius: 5px; padding: {px(5)}px {px(10)}px; min-width: {px(140)}px; }}
QComboBox:hover {{ border-color: {accent}; }}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: {px(24)}px; }}
QComboBox::down-arrow {{ image: none; border-left: {px(4)}px solid transparent;
    border-right: {px(4)}px solid transparent; border-top: {px(5)}px solid {c['subtext']}; }}
QComboBox QAbstractItemView {{ background: {c['card']}; border: 1px solid {c['border']};
    selection-background-color: {a18}; selection-color: {c['text']};
    border-radius: 6px; outline: none; }}

/* 滑块 - 全部用主题色 */
QSlider::groove:horizontal {{ height: {px(4)}px; background: {c['border']};
                              border-radius: {px(2)}px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: {px(2)}px; }}
QSlider::handle:horizontal {{ width: {px(16)}px; height: {px(16)}px; margin: -{px(7)}px 0;
    border-radius: {px(8)}px; background: {accent};
    border: {px(2)}px solid {c['card']}; }}
QSlider::handle:horizontal:hover {{ background: {QColor(accent).lighter(110).name()}; }}
QSlider::groove:vertical {{ width: {px(4)}px; background: {c['border']};
                            border-radius: {px(2)}px; }}
QSlider::add-page:vertical {{ background: {accent}; border-radius: {px(2)}px; }}

/* 进度条 - 全部用主题色 */
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
QScrollBar::handle:vertical:hover {{ background: {accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: {px(12)}px; margin: {px(2)}px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: {px(4)}px;
                                 min-width: {px(30)}px; }}
QScrollBar::handle:horizontal:hover {{ background: {accent}; }}

/* 文本编辑 */
QPlainTextEdit, QTextEdit {{ background: {c['input']}; border: 1px solid {c['border']};
    border-radius: 6px; font-family: 'Cascadia Mono', 'Noto Sans Mono CJK SC', monospace;
    font-size: {px(12)}px; }}
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {accent}; }}

QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {accent};
            padding: {px(4)}px {px(8)}px; border-radius: 4px; }}

QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 6px; top: -1px; }}
QTabBar::tab {{ padding: {px(6)}px {px(16)}px; border-top-left-radius: 6px;
                border-top-right-radius: 6px; color: {c['subtext']}; }}
QTabBar::tab:hover {{ color: {c['text']}; }}
QTabBar::tab:selected {{ background: {c['card']}; color: {accent};
    border-bottom: 2px solid {accent}; }}

/* 复选框 - 用主题色 */
QCheckBox {{ spacing: {px(8)}px; }}
QCheckBox::indicator {{ width: {px(16)}px; height: {px(16)}px;
                        border-radius: 4px; border: 1px solid {c['subtext']};
                        background: {c['card']}; }}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent};
    image: none; }}

/* 单选框 - 用主题色 */
QRadioButton::indicator {{ width: {px(16)}px; height: {px(16)}px; border-radius: 8px;
                           border: 1px solid {c['subtext']};
                           background: {c['card']}; }}
QRadioButton::indicator:hover {{ border-color: {accent}; }}
QRadioButton::indicator:checked {{ border: {px(5)}px solid {accent}; background: {c['card']}; }}

/* 输入框 - 用主题色 */
QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit, QDateEdit {{ background: {c['input']};
    border: 1px solid {c['border']}; border-radius: 5px; padding: {px(4)}px {px(8)}px; }}
QSpinBox:hover, QDoubleSpinBox:hover, QDateTimeEdit:hover,
QTimeEdit:hover, QDateEdit:hover {{ border-color: {accent}; }}
QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus,
QTimeEdit:focus, QDateEdit:focus {{ border-color: {accent}; }}
QSpinBox::up-button, QSpinBox::down-button,
QTimeEdit::up-button, QTimeEdit::down-button,
QDateEdit::up-button, QDateEdit::down-button {{ border: none; background: transparent;
                                                width: {px(16)}px; }}
QSpinBox::up-button:hover, QTimeEdit::up-button:hover, QDateEdit::up-button:hover,
QSpinBox::down-button:hover, QTimeEdit::down-button:hover,
QDateEdit::down-button:hover {{ background: {a10}; }}

/* 列表 - 用主题色 */
QListWidget::item:hover {{ background: {a08}; }}
QListWidget::item:selected {{ background: {a18}; color: {c['text']}; }}

/* 树 - 用主题色 */
QTreeWidget::item:hover {{ background: {a08}; }}
QTreeWidget::item:selected {{ background: {a18}; color: {c['text']}; }}

/* 表格 - 用主题色 */
QTableWidget::item:selected {{ background: {a18}; color: {c['text']}; }}
QHeaderView::section {{ background: {c['bg']}; color: {c['text']};
    border: none; border-bottom: 1px solid {c['border']};
    padding: {px(5)}px {px(8)}px; font-weight: 600; }}
QHeaderView::section:hover {{ color: {accent}; }}

/* 分组框 */
QGroupBox {{ border: 1px solid {c['border']}; border-radius: 6px;
             margin-top: {px(14)}px; padding-top: {px(8)}px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: {px(10)}px; padding: 0 {px(4)}px;
                    color: {accent}; }}

/* 菜单 */
QMenu {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 6px;
         padding: {px(4)}px; }}
QMenu::item {{ padding: {px(6)}px {px(20)}px; border-radius: 4px; }}
QMenu::item:selected {{ background: {a18}; color: {c['text']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: {px(4)}px 0; }}

/* ---------------- 经典控制面板 (Control Panel) ---------------- */
QFrame#topbar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
QFrame#subbar {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}

/* 经典控制面板的链接颜色 - 跟随系统主题色 */
QLabel#cplSubtitle {{ color: {accent}; font-size: {px(15)}px; font-weight: 500;
                       padding: 0; background: transparent; }}
QLabel#cplPageTitle {{ font-size: {px(21)}px; font-weight: 600; padding: 0 0 {px(6)}px 0; }}
QLabel#crumbSep {{ color: {c['subtext']}; padding: 0 {px(4)}px; background: transparent; }}

/* "查看方式" 链接 - 跟随主题色 */
QLabel#cplModeLabel {{ color: {accent}; font-size: {px(13)}px; background: transparent; }}
QLabel#cplModeCaret {{ color: {accent}; font-size: {px(10)}px; background: transparent; }}

/* 类别标题 - 跟随主题色 */
QPushButton#cplCatTitle {{ color: {accent}; background: transparent; border: none;
    text-align: left; padding: 0; font-size: {px(14)}px; font-weight: 600; }}
QPushButton#cplCatTitle:hover {{ text-decoration: underline; opacity: 0.8; }}

QPushButton#linkBtn {{ color: {accent}; background: transparent; border: none;
    text-align: left; padding: {px(1)}px 0; font-size: {px(13)}px; }}
QPushButton#linkBtn:hover {{ color: {QColor(accent).lighter(120).name()}; text-decoration: underline; }}
QPushButton#linkBtn:pressed {{ color: {QColor(accent).darker(120).name()}; }}

QPushButton#crumbBtn {{ color: {accent}; background: transparent; border: none;
    padding: {px(2)}px {px(3)}px; font-size: {px(13)}px; }}
QPushButton#crumbBtn:hover {{ background: {a10}; border-radius: 4px; }}

QPushButton#navArrow {{ color: {c['text']}; background: transparent; border: none;
    border-radius: 15px; font-size: {px(18)}px; font-weight: 600; }}
QPushButton#navArrow:hover {{ background: {a10}; }}
QPushButton#navArrow:disabled {{ color: {c['border']}; }}

QFrame#cplCard {{ background: {c['card']}; border: 1px solid {c['border']};
                  border-radius: 6px; }}

QListWidget {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 6px; outline: none; }}
QListWidget::item {{ padding: {px(4)}px; border-radius: 4px; }}

QTreeWidget {{ background: {c['card']}; border: 1px solid {c['border']};
               border-radius: 6px; outline: none;
               alternate-background-color: {c['bg']}; }}

QTableWidget {{ background: {c['card']}; border: 1px solid {c['border']};
                border-radius: 6px; gridline-color: {c['border']};
                alternate-background-color: {c['bg']}; }}

/* 自定义开关 ToggleSwitch - 用主题色 */
QLabel#toggleTrack {{ background: {c['border']}; border-radius: 9px; }}
QLabel#toggleKnob {{ background: {c['card']}; border-radius: 8px;
                      border: 1px solid {c['border']}; }}
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
