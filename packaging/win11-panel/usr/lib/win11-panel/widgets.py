"""widgets.py — 公共控件：Win11 风格开关 / 卡片 / 设置行 / 页面基类 / 图标绘制"""
from PyQt5.QtCore import Qt, QSize, QRectF, QTimer, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath, QFont
from PyQt5.QtWidgets import (QApplication, QFrame, QWidget, QLabel, QHBoxLayout,
                             QVBoxLayout, QPushButton, QSizePolicy, QScrollArea,
                             QMessageBox)

import theme


# ---------------------------------------------------------------- 图标绘制
def draw_icon(name: str, color: QColor, size: int = 20) -> QPixmap:
    """用 QPainter 绘制简约线性图标（类似 Win11 Fluent 风格）"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, max(1.4, size / 13.0), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    # 各图标绘制函数
    def _laptop():
        p.drawRoundedRect(QRectF(s*0.12, s*0.22, s*0.76, s*0.5), 2, 2)
        p.drawLine(int(s*0.06), int(s*0.82), int(s*0.94), int(s*0.82))
    def _monitor():
        p.drawRoundedRect(QRectF(s*0.12, s*0.18, s*0.76, s*0.52), 2, 2)
        p.drawLine(int(s*0.5), int(s*0.70), int(s*0.5), int(s*0.82))
        p.drawLine(int(s*0.34), int(s*0.82), int(s*0.66), int(s*0.82))
    def _speaker():
        path = QPainterPath()
        path.moveTo(s*0.28, s*0.40); path.lineTo(s*0.40, s*0.40)
        path.lineTo(s*0.54, s*0.26); path.lineTo(s*0.54, s*0.74)
        path.lineTo(s*0.40, s*0.60); path.lineTo(s*0.28, s*0.60); path.closeSubpath()
        p.drawPath(path)
        p.drawArc(QRectF(s*0.60, s*0.30, s*0.12, s*0.40), -60*16, 120*16)
        p.drawArc(QRectF(s*0.68, s*0.20, s*0.20, s*0.60), -55*16, 110*16)
    def _bell():
        path = QPainterPath()
        path.moveTo(s*0.30, s*0.52); path.lineTo(s*0.30, s*0.44)
        path.arcTo(QRectF(s*0.32, s*0.16, s*0.36, s*0.32), 180, -180)
        path.lineTo(s*0.70, s*0.52); path.lineTo(s*0.74, s*0.60); p.drawPath(path)
        p.drawLine(int(s*0.26), int(s*0.60), int(s*0.74), int(s*0.60))
        p.drawArc(QRectF(s*0.44, s*0.62, s*0.12, s*0.12), 180, -180)
    def _power():
        p.drawLine(int(s*0.5), int(s*0.20), int(s*0.5), int(s*0.46))
        p.drawArc(QRectF(s*0.28, s*0.30, s*0.44, s*0.44), 40*16, 280*16)
    def _disks():
        for i, y in enumerate((0.18, 0.46)):
            p.drawRoundedRect(QRectF(s*0.16, s*y, s*0.68, s*0.28), 2, 2)
            p.setBrush(color); p.drawEllipse(QRectF(s*0.24, s*y+s*0.10, s*0.07, s*0.07)); p.setBrush(Qt.NoBrush)
    def _info():
        p.drawEllipse(QRectF(s*0.14, s*0.14, s*0.72, s*0.72))
        p.drawLine(int(s*0.5), int(s*0.42), int(s*0.5), int(s*0.72))
        p.drawPoint(int(s*0.5), int(s*0.30))
    def _bluetooth():
        path = QPainterPath()
        path.moveTo(s*0.42, s*0.14); path.lineTo(s*0.42, s*0.86)
        path.moveTo(s*0.58, s*0.26); path.lineTo(s*0.42, s*0.46); path.lineTo(s*0.62, s*0.64)
        path.lineTo(s*0.42, s*0.84); path.moveTo(s*0.42, s*0.16); path.lineTo(s*0.62, s*0.36)
        p.drawPath(path)
    def _wifi():
        p.drawArc(QRectF(s*0.10, s*0.14, s*0.80, s*0.80), 215*16, 110*16)
        p.drawArc(QRectF(s*0.22, s*0.30, s*0.56, s*0.56), 215*16, 110*16)
        p.drawArc(QRectF(s*0.34, s*0.46, s*0.32, s*0.32), 215*16, 110*16)
    def _brush():
        p.drawRoundedRect(QRectF(s*0.20, s*0.14, s*0.28, s*0.28), 2, 2)
        p.drawRoundedRect(QRectF(s*0.52, s*0.14, s*0.28, s*0.28), 2, 2)
        p.drawRoundedRect(QRectF(s*0.20, s*0.46, s*0.28, s*0.28), 2, 2)
        p.setBrush(color); p.drawRoundedRect(QRectF(s*0.52, s*0.46, s*0.28, s*0.28), 2, 2); p.setBrush(Qt.NoBrush)
    def _grid():
        for cx, cy in ((0.18, 0.18), (0.55, 0.18), (0.18, 0.55), (0.55, 0.55)):
            p.drawRoundedRect(QRectF(s*cx, s*cy, s*0.27, s*0.27), 2, 2)
    def _person():
        p.drawEllipse(QRectF(s*0.34, s*0.14, s*0.32, s*0.32))
        p.drawArc(QRectF(s*0.20, s*0.56, s*0.60, s*0.60), 0, 180*16)
    def _clock():
        p.drawEllipse(QRectF(s*0.14, s*0.14, s*0.72, s*0.72))
        p.drawLine(int(s*0.5), int(s*0.28), int(s*0.5), int(s*0.50))
        p.drawLine(int(s*0.5), int(s*0.50), int(s*0.68), int(s*0.58))
    def _gamepad():
        p.drawRoundedRect(QRectF(s*0.08, s*0.30, s*0.84, s*0.42), s*0.18, s*0.18)
        p.drawLine(int(s*0.26), int(s*0.42), int(s*0.26), int(s*0.60))
        p.drawLine(int(s*0.17), int(s*0.51), int(s*0.35), int(s*0.51))
        p.drawEllipse(QRectF(s*0.60, s*0.40, s*0.07, s*0.07))
        p.drawEllipse(QRectF(s*0.72, s*0.52, s*0.07, s*0.07))
    def _access():
        p.drawEllipse(QRectF(s*0.43, s*0.12, s*0.14, s*0.14))
        p.drawLine(int(s*0.16), int(s*0.34), int(s*0.84), int(s*0.34))
        p.drawLine(int(s*0.5), int(s*0.34), int(s*0.5), int(s*0.60))
        p.drawArc(QRectF(s*0.24, s*0.52, s*0.52, s*0.40), 20*16, 140*16)
    def _shield():
        path = QPainterPath()
        path.moveTo(s*0.5, s*0.12); path.lineTo(s*0.84, s*0.26); path.lineTo(s*0.84, s*0.52)
        path.arcTo(QRectF(s*0.30, s*0.40, s*0.40, s*0.48), 90, -180)
        path.lineTo(s*0.16, s*0.52); path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(s*0.40), int(s*0.50), int(s*0.48), int(s*0.60))
        p.drawLine(int(s*0.48), int(s*0.60), int(s*0.64), int(s*0.42))
    def _update():
        p.drawArc(QRectF(s*0.16, s*0.16, s*0.68, s*0.68), 30*16, 280*16)
        p.drawLine(int(s*0.5), int(s*0.10), int(s*0.62), int(s*0.20))
        p.drawLine(int(s*0.5), int(s*0.10), int(s*0.44), int(s*0.24))
    def _lang():
        p.drawRoundedRect(QRectF(s*0.12, s*0.18, s*0.76, s*0.64), 2, 2)
        f = QFont(); f.setPixelSize(int(s*0.42)); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, "文")
        p.setPen(pen)
    def _usb():
        p.drawLine(int(s*0.5), int(s*0.86), int(s*0.5), int(s*0.30))
        p.drawLine(int(s*0.5), int(s*0.50), int(s*0.34), int(s*0.50))
        p.drawEllipse(QRectF(s*0.26, s*0.42, s*0.10, s*0.16))
        p.drawLine(int(s*0.5), int(s*0.60), int(s*0.66), int(s*0.60))
        p.drawLine(int(s*0.66), int(s*0.60), int(s*0.66), int(s*0.48))
        p.drawLine(int(s*0.60), int(s*0.48), int(s*0.72), int(s*0.48))
        p.drawLine(int(s*0.72), int(s*0.48), int(s*0.72), int(s*0.60))
        p.drawLine(int(s*0.5), int(s*0.30), int(s*0.42), int(s*0.38))
        p.drawLine(int(s*0.5), int(s*0.30), int(s*0.58), int(s*0.38))
        p.drawLine(int(s*0.5), int(s*0.30), int(s*0.5), int(s*0.22))
    def _search():
        p.drawEllipse(QRectF(s*0.18, s*0.18, s*0.48, s*0.48))
        p.drawLine(int(s*0.56), int(s*0.56), int(s*0.80), int(s*0.80))
    def _chevron():
        p.drawLine(int(s*0.34), int(s*0.26), int(s*0.62), int(s*0.5))
        p.drawLine(int(s*0.62), int(s*0.5), int(s*0.34), int(s*0.74))

    funcs = {"system": _laptop, "display": _monitor, "sound": _speaker,
             "notifications": _bell, "power": _power, "storage": _disks,
             "about": _info, "bluetooth": _bluetooth, "network": _wifi,
             "personalization": _brush, "apps": _grid, "accounts": _person,
             "time": _clock, "gaming": _gamepad, "accessibility": _access,
             "privacy": _shield, "update": _update, "language": _lang,
             "usb": _usb, "search": _search, "chevron": _chevron}
    fn = funcs.get(name, _info)
    try:
        fn()
    finally:
        p.end()
    return pm


# ---------------------------------------------------------------- Win11 风格开关
class ToggleSwitch(QWidget):
    """Windows 11 风格开关（带滑动动画）"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_anim)
        if not theme.load_theme()["reduce_motion"]:
            self._anim.setDuration(120)

    def _on_anim(self, v):
        self._pos = v
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, c: bool, animate=True):
        if c == self._checked:
            return
        self._checked = c
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(1.0 if c else 0.0)
            self._anim.start()
        else:
            self._pos = 1.0 if c else 0.0
            self.update()
        self.toggled.emit(c)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, _e):
        t = theme.load_theme()
        c = theme.palette_colors(t["dark"], t["high_contrast"])
        accent = QColor(theme.accent_of(t))
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h, w = self.height(), self.width()
        rect = QRectF(0.5, 0.5, w - 1, h - 1)
        p.setBrush(accent if self._checked else QColor(c["card"]))
        p.setPen(QPen(accent if self._checked else QColor(c["subtext"]), 1.4))
        p.drawRoundedRect(rect, h / 2, h / 2)
        # 圆点：关闭时稍小、灰色；打开时稍大、强调色反色
        d_off, d_on = h - 10, h - 8
        d = d_off + (d_on - d_off) * self._pos
        x = 5 + self._pos * (w - 10 - d)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(c["on_accent"]) if self._checked else QColor(c["subtext"]))
        p.drawEllipse(QRectF(x, (h - d) / 2, d, d))
        p.end()


# ---------------------------------------------------------------- 卡片 / 行
class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 12, 16, 12)
        self._lay.setSpacing(8)
        self._title = None
        if title:
            self._title = QLabel(title)
            self._title.setObjectName("cardTitle")
            self._lay.addWidget(self._title)

    def layout(self) -> QVBoxLayout:
        return self._lay

    def add(self, w):
        self._lay.addWidget(w)
        return w

    def add_stretch(self):
        self._lay.addStretch(1)

    def add_divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        self._lay.addWidget(line)
        return line


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)


class SettingRow(QWidget):
    """Win11 设置行：图标 + 标题/副标题 + 右侧控件"""
    clicked = pyqtSignal()

    def __init__(self, title: str, subtitle: str = "", trailing=None,
                 icon: str = "", selectable=False, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor if selectable else Qt.ArrowCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(12)
        self._icon_key = icon
        self._icon_label = None
        if icon:
            ic = QLabel()
            ic.setPixmap(draw_icon(icon, QColor("#5B5B5B"), 18))
            ic.setFixedSize(24, 24)
            ic.setAlignment(Qt.AlignCenter)
            lay.addWidget(ic)
            self._icon_label = ic
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("rowTitle")
        text_col.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("subText")
            s.setWordWrap(True)
            text_col.addWidget(s)
        lay.addLayout(text_col, 1)
        if trailing is not None:
            lay.addSpacing(8)
            lay.addWidget(trailing, 0, Qt.AlignRight | Qt.AlignVCenter)
        if selectable:
            self._arrow = QLabel("›")
            self._arrow.setObjectName("subText")
            lay.addWidget(self._arrow)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.cursor() == Qt.PointingHandCursor:
            self.clicked.emit()
        super().mousePressEvent(e)

    def refresh_icon(self):
        t = theme.load_theme()
        c = theme.palette_colors(t["dark"], t["high_contrast"])
        if self._icon_label:
            self._icon_label.setPixmap(draw_icon(
                getattr(self, "_icon_key", ""), QColor(c["subtext"]), 18))


class BasePage(QScrollArea):
    """页面基类：大标题 + 可滚动内容"""
    navigated = pyqtSignal()
    nav_requested = pyqtSignal(str)  # 请求跳转到其他页面

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(32, 24, 32, 32)
        v.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("pageTitle")
        v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("pageSubtitle")
            s.setWordWrap(True)
            v.addWidget(s)
            v.addSpacing(4)
        self.body = v
        self.setWidget(content)

    def add_card(self, title: str = "") -> Card:
        c = Card(title)
        self.body.addWidget(c)
        return c

    def add_section(self, text: str):
        l = QLabel(text)
        l.setObjectName("sectionTitle")
        self.body.addWidget(l)
        return l

    def add_stretch(self):
        self.body.addStretch(1)

    def on_show(self):
        """页面显示时刷新数据（子类重写）"""
        self.navigated.emit()


def info_box(parent, title, text):
    QMessageBox.information(parent, title, text)


def warn_box(parent, title, text):
    QMessageBox.warning(parent, title, text)


def confirm_box(parent, title, text) -> bool:
    return QMessageBox.question(parent, title, text,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes
