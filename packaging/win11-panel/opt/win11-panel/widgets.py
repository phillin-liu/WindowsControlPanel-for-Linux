"""widgets.py — 公共控件：Win11 风格开关 / 卡片 / 设置行 / 页面基类 / 图标绘制"""
import os
import math
from PyQt5.QtCore import Qt, QSize, QRectF, QTimer, QVariantAnimation, pyqtSignal, QPointF
from PyQt5.QtGui import (QPixmap, QPainter, QColor, QPen, QPainterPath, QFont,
                         QLinearGradient, QBrush, QRadialGradient, QIcon)
from PyQt5.QtWidgets import (QApplication, QFrame, QWidget, QLabel, QHBoxLayout,
                             QVBoxLayout, QPushButton, QSizePolicy, QScrollArea,
                             QMessageBox)

import theme


# ---------------------------------------------------------------- 图标资源路径
_ICONS_SEARCH_DIRS = []
def _init_icon_dirs():
    """初始化图标搜索路径 (开发模式 + 安装模式)"""
    global _ICONS_SEARCH_DIRS
    if _ICONS_SEARCH_DIRS:
        return
    # 1. 相对于当前文件 (开发模式: src/icons)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dev_icons = os.path.join(src_dir, "icons")
    if os.path.isdir(dev_icons):
        _ICONS_SEARCH_DIRS.append(dev_icons)
    # 2. 安装路径 (deb: /opt/win11-panel/icons)
    install_icons = "/opt/win11-panel/icons"
    if os.path.isdir(install_icons):
        _ICONS_SEARCH_DIRS.append(install_icons)
    # 3. 当前工作目录兜底
    cwd_icons = os.path.join(os.getcwd(), "icons")
    if os.path.isdir(cwd_icons):
        _ICONS_SEARCH_DIRS.append(cwd_icons)

_init_icon_dirs()

# 单色变体名称映射: 颜色(hex) -> variant name
_WHITE = QColor("#FFFFFF").rgb()
_BLACK = QColor("#000000").rgb()
def _guess_mono_variant(color: QColor) -> str:
    """根据颜色明度猜测使用哪个预渲染变体"""
    r, g, b = color.red(), color.green(), color.blue()
    lum = 0.299*r + 0.587*g + 0.114*b
    if lum > 200:
        return "light"   # 白色/亮色 -> 用白底反的light变体
    elif lum < 80:
        return "dark"    # 接近黑色 -> dark变体
    else:
        return "dark"    # 其他彩色用dark变体(然后自己着色)，后续可优化

_ICON_CACHE = {}  # (key) -> QPixmap 缓存

def _load_png(rel_path: str, target_size: int) -> QPixmap:
    """在搜索路径中查找 PNG 并缩放到目标尺寸 (保持比例+平滑)"""
    cache_key = (rel_path, target_size)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]
    for d in _ICONS_SEARCH_DIRS:
        fpath = os.path.join(d, rel_path)
        if os.path.isfile(fpath):
            pm = QPixmap(fpath)
            if not pm.isNull():
                if pm.width() != target_size or pm.height() != target_size:
                    pm = pm.scaled(target_size, target_size,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
                _ICON_CACHE[cache_key] = pm
                return pm
    return None

def _find_mono_png(name: str, variant: str, target_size: int) -> QPixmap:
    """查找单色图标: 精确尺寸优先，否则用最近的大尺寸缩放"""
    sizes_try = [16, 20, 24, 32]
    # 先找精确尺寸
    pm = _load_png(f"mono/{name}-{target_size}-{variant}.png", target_size)
    if pm is not None:
        return pm
    # 找比目标大的最近尺寸缩放
    for sz in sizes_try:
        if sz >= target_size:
            pm = _load_png(f"mono/{name}-{sz}-{variant}.png", target_size)
            if pm is not None:
                return pm
    # 最后用最大尺寸缩放
    pm = _load_png(f"mono/{name}-32-{variant}.png", target_size)
    return pm

def _find_tile_png(name: str, target_size: int) -> QPixmap:
    """查找彩色磁贴图标"""
    sizes_try = [40, 48, 64]
    pm = _load_png(f"tiles/{name}-{target_size}.png", target_size)
    if pm is not None:
        return pm
    for sz in sizes_try:
        if sz >= target_size:
            pm = _load_png(f"tiles/{name}-{sz}.png", target_size)
            if pm is not None:
                return pm
    return _load_png(f"tiles/{name}-64.png", target_size)


# ---------------------------------------------------------------- 图标绘制 (代码绘制版，作为回退)
def _draw_icon_painter(name: str, color: QColor, size: int = 20) -> QPixmap:
    """用 QPainter 绘制 Fluent 风格实心图标（Windows 11 控制面板风格）"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size

    # 笔画粗细随尺寸缩放 (整数)
    w = max(2, int(s / 10.0 + 0.5))
    pen = QPen(color, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)

    # ---------- 辅助函数 ----------
    def setw(mult=1.0):
        """临时改变笔宽 (整数)"""
        pen.setWidth(max(1, int(w * mult)))
        p.setPen(pen)

    def reset_pen():
        pen.setWidth(w)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
    def R(x, y, w_, h_, r):
        p.drawRoundedRect(QRectF(s*x, s*y, s*w_, s*h_), s*r, s*r)

    def F(x, y, w_, h_, r):
        path = QPainterPath()
        path.addRoundedRect(QRectF(s*x, s*y, s*w_, s*h_), s*r, s*r)
        path.closeSubpath()
        p.fillPath(path, QBrush(color))

    def C(cx, cy, r_):
        p.drawEllipse(QRectF(s*cx-s*r_, s*cy-s*r_, s*r_*2, s*r_*2))

    def FC(cx, cy, r_):
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(s*cx-s*r_, s*cy-s*r_, s*r_*2, s*r_*2))
        p.setPen(pen)

    def line(x1, y1, x2, y2):
        p.drawLine(QPointF(s*x1, s*y1), QPointF(s*x2, s*y2))

    def fill_path(path):
        p.setPen(Qt.NoPen)
        p.fillPath(path, QBrush(color))
        p.setPen(pen)

    # ---------- 图标 ----------
    def _laptop():
        # 笔记本电脑：屏幕 + 底座
        path = QPainterPath()
        path.addRoundedRect(QRectF(s*0.13, s*0.18, s*0.74, s*0.52), s*0.05, s*0.05)
        fill_path(path)
        p.drawPath(path)
        base = QPainterPath()
        base.moveTo(s*0.05, s*0.75)
        base.lineTo(s*0.95, s*0.75)
        base.lineTo(s*0.90, s*0.84)
        base.lineTo(s*0.10, s*0.84)
        base.closeSubpath()
        fill_path(base)
        p.drawPath(base)

    def _monitor():
        path = QPainterPath()
        path.addRoundedRect(QRectF(s*0.10, s*0.12, s*0.80, s*0.52), s*0.05, s*0.05)
        fill_path(path); p.drawPath(path)
        F(0.42, 0.66, 0.16, 0.08, 0.02)
        F(0.30, 0.74, 0.40, 0.05, 0.02)

    def _speaker():
        box = QPainterPath()
        box.moveTo(s*0.22, s*0.38); box.lineTo(s*0.40, s*0.38)
        box.lineTo(s*0.58, s*0.22); box.lineTo(s*0.58, s*0.78)
        box.lineTo(s*0.40, s*0.62); box.lineTo(s*0.22, s*0.62)
        box.closeSubpath()
        fill_path(box); p.drawPath(box)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(s*0.60, s*0.32, s*0.14, s*0.36), -55*16, 110*16)
        p.drawArc(QRectF(s*0.66, s*0.24, s*0.20, s*0.52), -50*16, 100*16)

    def _bell():
        bell = QPainterPath()
        # 钟顶
        bell.moveTo(s*0.24, s*0.54)
        bell.arcTo(QRectF(s*0.26, s*0.14, s*0.48, s*0.42), 180, -180)
        bell.lineTo(s*0.76, s*0.54)
        bell.quadTo(s*0.78, s*0.62, s*0.72, s*0.64)
        bell.lineTo(s*0.28, s*0.64)
        bell.quadTo(s*0.22, s*0.62, s*0.24, s*0.54)
        bell.closeSubpath()
        fill_path(bell); p.drawPath(bell)
        FC(0.5, 0.76, 0.06)

    def _power():
        setw(1.2)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(s*0.18, s*0.18, s*0.64, s*0.64), 30*16, 300*16)
        F(0.47, 0.14, 0.06, 0.30, 0.03)
        reset_pen()

    def _disks():
        for yy in (0.14, 0.44):
            r = s*0.04
            path = QPainterPath()
            path.addRoundedRect(QRectF(s*0.12, s*yy, s*0.76, s*0.22), r, r)
            fill_path(path)
            white_pen = QPen(QColor(255,255,255,200), max(1, int(w*0.6)))
            p.setPen(white_pen)
            p.drawRoundedRect(QRectF(s*0.18, s*(yy+0.07), s*0.52, s*0.08), s*0.02, s*0.02)
            p.setPen(pen)
            FC(0.80, yy+0.11, 0.04)

    def _info():
        setw(1.3)
        p.setBrush(color)
        p.drawEllipse(QRectF(s*0.12, s*0.12, s*0.76, s*0.76))
        pen_w = QPen(QColor(255,255,255), max(1, int(w*0.9)), Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_w)
        FC(0.5, 0.30, 0.045)
        line(0.5, 0.42, 0.5, 0.72)
        reset_pen()

    def _bluetooth():
        setw(1.4)
        # 蓝牙 rune 形状 (填充)
        path = QPainterPath()
        path.moveTo(s*0.44, s*0.14); path.lineTo(s*0.44, s*0.86)
        path.lineTo(s*0.70, s*0.62); path.lineTo(s*0.52, s*0.50)
        path.lineTo(s*0.70, s*0.38); path.lineTo(s*0.44, s*0.14)
        path.closeSubpath()
        p.fillPath(path, QBrush(color))
        p.drawPath(path)
        FC(0.44, 0.14, 0.035)
        FC(0.44, 0.86, 0.035)
        reset_pen()

    def _wifi():
        # 填充的扇形 WiFi
        setw(1.5)
        p.setBrush(Qt.NoBrush)
        for i, (r_, a) in enumerate(((0.42, 0), (0.30, 1), (0.18, 2))):
            p.drawArc(QRectF(s*(0.5-r_), s*(0.20), s*r_*2, s*r_*2),
                      225*16, 90*16)
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(s*0.47, s*0.65, s*0.06, s*0.06))
        reset_pen()

    def _brush():
        # 2x2 调色板色块
        colors_palette = [(0.18,0.14,QColor("#E81123")), (0.52,0.14,QColor("#FFB900")),
                          (0.18,0.48,QColor("#0078D4")), (0.52,0.48,QColor("#107C10"))]
        for cx, cy, cc in colors_palette:
            path = QPainterPath()
            path.addRoundedRect(QRectF(s*cx, s*cy, s*0.30, s*0.30), s*0.05, s*0.05)
            p.fillPath(path, QBrush(cc))
            p.drawPath(path)
        # 画笔杆
        F(0.72, 0.70, 0.18, 0.04, 0.02)

    def _grid():
        for cx, cy in ((0.18,0.14),(0.55,0.14),(0.18,0.55),(0.55,0.55)):
            path = QPainterPath()
            path.addRoundedRect(QRectF(s*cx, s*cy, s*0.27, s*0.27), s*0.05, s*0.05)
            p.fillPath(path, QBrush(color)); p.drawPath(path)

    def _person():
        # 实心圆头 + 弧形身体
        p.setBrush(color); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(s*0.34, s*0.12, s*0.32, s*0.32))
        body = QPainterPath()
        body.moveTo(s*0.16, s*0.92)
        body.arcTo(QRectF(s*0.18, s*0.52, s*0.64, s*0.64), 200, 140)
        body.closeSubpath()
        p.fillPath(body, QBrush(color)); p.drawPath(body)
        reset_pen()

    def _clock():
        setw(1.3)
        p.setBrush(color)
        p.drawEllipse(QRectF(s*0.12, s*0.12, s*0.76, s*0.76))
        wh = QPen(QColor(255,255,255), max(1, int(w*0.9)), Qt.SolidLine, Qt.RoundCap)
        p.setPen(wh); p.setBrush(Qt.NoBrush)
        line(0.5, 0.50, 0.5, 0.28)
        line(0.5, 0.50, 0.70, 0.58)
        FC(0.5, 0.50, 0.03)
        reset_pen()

    def _gamepad():
        setw(1.0)
        p.setBrush(color)
        # 手柄身体（双圆+连接矩形）
        body = QPainterPath()
        body.addEllipse(QRectF(s*0.04, s*0.30, s*0.40, s*0.44))
        body.addEllipse(QRectF(s*0.56, s*0.30, s*0.40, s*0.44))
        body.addRoundedRect(QRectF(s*0.20, s*0.38, s*0.60, s*0.28), s*0.06, s*0.06)
        p.fillPath(body, QBrush(color)); p.drawPath(body)
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(255,255,255), max(1, int(w*0.7))))
        # D-pad (left)
        line(0.20, 0.48, 0.20, 0.58)
        line(0.15, 0.53, 0.25, 0.53)
        # buttons (right)
        FC(0.78, 0.46, 0.03); FC(0.78, 0.58, 0.03)
        reset_pen()

    def _access():
        setw(1.3)
        p.setBrush(color)
        FC(0.5, 0.14, 0.06)
        # 身体: 半圆身体 + 张开手臂
        body = QPainterPath()
        body.moveTo(s*0.18, s*0.36)
        body.lineTo(s*0.82, s*0.36)
        body.lineTo(s*0.55, s*0.36)
        body.lineTo(s*0.55, s*0.60)
        body.arcTo(QRectF(s*0.30, s*0.52, s*0.40, s*0.40), 0, -180)
        body.closeSubpath()
        p.fillPath(body, QBrush(color)); p.drawPath(body)
        reset_pen()

    def _shield():
        path = QPainterPath()
        path.moveTo(s*0.50, s*0.10)
        path.cubicTo(s*0.72, s*0.18, s*0.86, s*0.24, s*0.86, s*0.24)
        path.lineTo(s*0.86, s*0.52)
        path.quadTo(s*0.86, s*0.74, s*0.50, s*0.92)
        path.quadTo(s*0.14, s*0.74, s*0.14, s*0.52)
        path.lineTo(s*0.14, s*0.24)
        path.quadTo(s*0.30, s*0.18, s*0.50, s*0.10)
        path.closeSubpath()
        p.fillPath(path, QBrush(color)); p.drawPath(path)
        # 对勾
        p.setPen(QPen(QColor(255,255,255), max(1, int(w*1.1)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        line(0.38, 0.50, 0.48, 0.60)
        line(0.48, 0.60, 0.66, 0.40)
        reset_pen()

    def _update():
        setw(1.4)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(s*0.14, s*0.14, s*0.72, s*0.72), 30*16, 300*16)
        # 箭头
        arrow = QPainterPath()
        arrow.moveTo(s*0.50, s*0.06)
        arrow.lineTo(s*0.38, s*0.22); arrow.lineTo(s*0.62, s*0.22)
        arrow.closeSubpath()
        p.fillPath(arrow, QBrush(color)); p.drawPath(arrow)
        reset_pen()

    def _lang():
        setw(1.2)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(s*0.10, s*0.14, s*0.80, s*0.70), s*0.06, s*0.06)
        p.setPen(QPen(QColor(255,255,255), max(1, int(w*0.9))))
        f = QFont(); f.setPixelSize(int(s*0.38)); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(s*0.10, s*0.18, s*0.80, s*0.58), Qt.AlignCenter, "文")
        reset_pen()

    def _usb():
        setw(1.3)
        # USB 插头形状
        body = QPainterPath()
        body.addRoundedRect(QRectF(s*0.32, s*0.18, s*0.36, s*0.22), s*0.04, s*0.04)
        body.addRect(QRectF(s*0.40, s*0.40, s*0.20, s*0.30))
        fill_path(body); p.drawPath(body)
        # 触点
        F(0.44, 0.40, 0.04, 0.14, 0.01)
        F(0.52, 0.40, 0.04, 0.10, 0.01)
        line(0.50, 0.70, 0.50, 0.82)
        FC(0.50, 0.86, 0.06)
        reset_pen()

    def _search():
        setw(1.5)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(s*0.16, s*0.16, s*0.46, s*0.46))
        line(0.48, 0.48, 0.82, 0.82)
        reset_pen()

    def _chevron():
        setw(1.4)
        p.setBrush(Qt.NoBrush)
        line(0.38, 0.28, 0.62, 0.50)
        line(0.62, 0.50, 0.38, 0.72)
        reset_pen()

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


# ---------------------------------------------------------------- 公共图标 API (优先加载 PNG，回退到代码绘制)
def draw_icon(name: str, color: QColor, size: int = 20) -> QPixmap:
    """获取图标：优先从 PNG 文件加载，不存在则用 QPainter 绘制"""
    # 1. 尝试从 PNG 加载 (白色/黑色变体)
    variant = _guess_mono_variant(color)
    pm = _find_mono_png(name, variant, size)
    if pm is not None:
        # 如果需要的颜色不是变体默认色(白/黑)，且颜色是彩色，重新着色
        # 简单处理: 如果是白色变体且需要白色，直接用; 否则用代码绘制(保证颜色准确)
        desired_rgb = color.rgb()
        if variant == "light" and desired_rgb == _WHITE:
            return pm
        if variant == "dark" and (desired_rgb == _BLACK or color.lightness() < 50):
            return pm
        # 其他颜色(如分类彩色)回退到代码绘制保证颜色正确
        # 未来可以用 QPainter::CompositionMode 重新着色
    # 2. PNG 不存在或颜色不匹配，回退到代码绘制
    return _draw_icon_painter(name, color, size)


# ---------------------------------------------------------------- 彩色方块图标 (代码绘制回退版)
def _draw_tile_icon_painter(name: str, bg_color: str, size: int = 40) -> QPixmap:
    """绘制带彩色圆角方形背景 + 白色实心符号的图标块 (Windows 11 磁贴风格)"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size

    # 1. 绘制圆角方形背景
    bg = QColor(bg_color)
    bg_path = QPainterPath()
    radius = s * 0.18
    bg_path.addRoundedRect(QRectF(0, 0, s, s), radius, radius)
    # 渐变效果
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0, bg.lighter(110))
    grad.setColorAt(1, bg.darker(105))
    p.fillPath(bg_path, QBrush(grad))

    # 2. 在中心绘制白色图标（稍小尺寸，边距）
    inner_size = int(s * 0.62)
    offset = (s - inner_size) / 2
    white = QColor(255, 255, 255)
    inner_pm = draw_icon(name, white, inner_size)
    p.drawPixmap(int(offset), int(offset), inner_pm)

    p.end()
    return pm


# ---------------------------------------------------------------- Windows 7 经典控制面板复合图标
def _draw_win7_icon(name: str, size: int) -> QPixmap:
    """绘制 Windows 7 经典控制面板 8 大分类复合图标
    参考原图：彩色渐变 + 立体阴影 + 组合图形
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    s = float(size)
    u = s / 48.0   # 单位: 基于48px缩放

    def fill(path, color):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color) if isinstance(color, str) else color)
        p.drawPath(path)

    def fill_rect(x, y, w, h, r, color):
        path = QPainterPath()
        path.addRoundedRect(QRectF(x*u, y*u, w*u, h*u), r*u, r*u)
        fill(path, color)

    def fill_ellipse(cx, cy, rx, ry, color):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color) if isinstance(color, str) else color)
        p.drawEllipse(QRectF((cx-rx)*u, (cy-ry)*u, rx*2*u, ry*2*u))

    def stroke(path, color, width=1.0):
        pen = QPen(QColor(color) if isinstance(color, str) else color)
        pen.setWidthF(width*u)
        pen.setCosmetic(False)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    if name == "shield":
        # ====== 系统和安全: 蓝色盾牌 + 橙色圆形 ======
        # 盾牌主体 (蓝色渐变)
        shield = QPainterPath()
        shield.moveTo(24*u, 6*u)
        shield.cubicTo(33*u, 10*u, 39*u, 13*u, 39*u, 13*u)
        shield.lineTo(39*u, 26*u)
        shield.quadTo(39*u, 36*u, 24*u, 43*u)
        shield.quadTo(9*u, 36*u, 9*u, 26*u)
        shield.lineTo(9*u, 13*u)
        shield.quadTo(15*u, 10*u, 24*u, 6*u)
        shield.closeSubpath()
        # 蓝色渐变填充
        grad = QLinearGradient(0, 6*u, 0, 43*u)
        grad.setColorAt(0, QColor("#5BA3E0"))
        grad.setColorAt(0.4, QColor("#2E7BC8"))
        grad.setColorAt(1, QColor("#1B5AA5"))
        p.setPen(Qt.NoPen); p.setBrush(grad); p.drawPath(shield)
        # 盾牌高光
        hl = QPainterPath()
        hl.moveTo(18*u, 15*u); hl.cubicTo(20*u, 14*u, 28*u, 14*u, 30*u, 15*u)
        hl.cubicTo(28*u, 28*u, 20*u, 28*u, 18*u, 15*u)
        p.setBrush(QColor(255,255,255,50)); p.drawPath(hl)
        # 盾牌上的白色对勾
        chk = QPen(QColor("#FFFFFF"), 2.5*u, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(chk); p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(17*u, 24*u), QPointF(22*u, 29*u))
        p.drawLine(QPointF(22*u, 29*u), QPointF(30*u, 19*u))
        # 橙色圆形 (右下角)
        fill_ellipse(34, 35, 7, 7, "#F0A030")
        fill_ellipse(34, 35, 5, 5, "#F7C060")
        # 圆形内的小图标
        p.setPen(QPen(QColor("#FFFFFF"), 2*u, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(34*u, 32*u), QPointF(34*u, 38*u))
        p.drawLine(QPointF(31*u, 35*u), QPointF(37*u, 35*u))

    elif name == "network":
        # ====== 网络和Internet: 地球 + 显示器 + 绿色网线 ======
        # 显示器 (紫蓝边框)
        mon_grad = QLinearGradient(12*u, 10*u, 12*u, 32*u)
        mon_grad.setColorAt(0, QColor("#6080C0"))
        mon_grad.setColorAt(1, QColor("#4058A0"))
        mon = QPainterPath()
        mon.addRoundedRect(QRectF(12*u, 10*u, 22*u, 18*u), 1.5*u, 1.5*u)
        fill(mon, mon_grad)
        # 屏幕
        scr = QPainterPath()
        scr.addRect(QRectF(14*u, 12*u, 18*u, 14*u))
        fill(scr, "#E8F4FC")
        # 地球在屏幕上
        fill_ellipse(23, 19, 7, 6, "#3078C0")
        fill_ellipse(23, 19, 5, 4.5, "#4A98D8")
        # 大陆 (绿色小块)
        fill_ellipse(21, 17, 2, 1.5, "#68B848")
        fill_ellipse(25, 20, 2.5, 2, "#68B848")
        # 底座
        fill_rect(18, 29, 10, 2, 0.5, "#7088B8")
        fill_rect(15, 30.5, 16, 1.5, 0.5, "#6078A8")
        # 地球 (左侧半露)
        globe_g = QRadialGradient(10*u, 22*u, 14*u)
        globe_g.setColorAt(0, QColor("#68B8E8"))
        globe_g.setColorAt(0.7, QColor("#2060A8"))
        globe_g.setColorAt(1, QColor("#104080"))
        p.setBrush(globe_g); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(0*u, 12*u, 20*u, 20*u))
        # 地球上的大陆
        fill_ellipse(7, 18, 3, 2.5, "#50A840")
        fill_ellipse(11, 24, 3.5, 3, "#50A840")
        # 网格线
        p.setPen(QPen(QColor(255,255,255,80), 0.8*u))
        p.drawArc(QRectF(0*u, 12*u, 20*u, 20*u), 0, 180*16)
        p.drawLine(QPointF(0*u,22*u), QPointF(20*u,22*u))
        # 绿色网络插头/线缆 (右下角)
        fill_rect(32, 31, 8, 6, 1, "#58A838")
        fill_rect(33, 37, 6, 3, 0.5, "#78B858")
        p.setPen(QPen(QColor("#387828"), 1*u))
        p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(34*u,31*u), QPointF(34*u,40*u))
        p.drawLine(QPointF(38*u,31*u), QPointF(38*u,40*u))

    elif name == "sound":
        # ====== 硬件和声音: 打印机 + 扬声器组合 ======
        # 打印机机身 (浅灰/白)
        p_grad = QLinearGradient(8*u, 18*u, 8*u, 38*u)
        p_grad.setColorAt(0, QColor("#E8E8EC"))
        p_grad.setColorAt(1, QColor("#C0C0C8"))
        printer = QPainterPath()
        printer.addRoundedRect(QRectF(8*u, 20*u, 26*u, 16*u), 2*u, 2*u)
        fill(printer, p_grad)
        # 出纸口
        fill_rect(12, 34, 18, 3, 0.5, "#A0A0A8")
        # 打印纸 (白色向上)
        paper = QPainterPath()
        paper.addRoundedRect(QRectF(12*u, 8*u, 18*u, 16*u), 1*u, 1*u)
        fill(paper, "#FFFFFF")
        stroke(paper, "#D0D0D8", 0.8)
        # 纸上的几行文字
        for i in range(4):
            fill_rect(14, 10+i*3, 12, 1.2, 0.3, "#C0D0E0" if i%2 else "#A0B8D0")
        # 打印机控制面板 (右侧小灯)
        fill_ellipse(30, 24, 1.2, 1.2, "#60C040")
        fill_ellipse(30, 28, 1.2, 1.2, "#E0C040")
        # 扬声器 (右下角)
        spk_box = QPainterPath()
        spk_box.moveTo(30*u, 28*u); spk_box.lineTo(36*u, 24*u)
        spk_box.lineTo(36*u, 40*u); spk_box.lineTo(30*u, 36*u)
        spk_box.closeSubpath()
        fill(spk_box, "#404048")
        # 音波
        p.setPen(QPen(QColor("#606068"), 1.2*u, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(34*u,27*u,6*u,10*u), -60*16, 120*16)

    elif name == "apps":
        # ====== 程序: 光盘盒子 (软件包装盒) ======
        # 盒子主体
        box_grad = QLinearGradient(10*u, 12*u, 10*u, 40*u)
        box_grad.setColorAt(0, QColor("#B890D8"))
        box_grad.setColorAt(1, QColor("#7040A0"))
        box = QPainterPath()
        box.addRoundedRect(QRectF(10*u, 12*u, 26*u, 26*u), 1.5*u, 1.5*u)
        fill(box, box_grad)
        # 盒子边框
        stroke(box, "#502078", 1)
        # 盒盖高光
        hl = QPainterPath()
        hl.addRoundedRect(QRectF(12*u, 14*u, 22*u, 3*u), 0.5*u, 0.5*u)
        fill(hl, QColor(255,255,255,60))
        # 盒子中露出的光盘 (CD)
        cd_cx, cd_cy, cd_r = 23, 28, 9
        # CD 银色外环
        fill_ellipse(cd_cx, cd_cy, cd_r, cd_r, "#D8D8E0")
        fill_ellipse(cd_cx, cd_cy, cd_r-1.2, cd_r-1.2, "#E8E8F0")
        # CD 反光面
        cd_grad = QLinearGradient((cd_cx-cd_r)*u, (cd_cy-cd_r)*u,
                                   (cd_cx+cd_r)*u, (cd_cy+cd_r)*u)
        cd_grad.setColorAt(0, QColor("#F0F0F8"))
        cd_grad.setColorAt(0.5, QColor("#B0C0D8"))
        cd_grad.setColorAt(1, QColor("#8098B8"))
        p.setBrush(cd_grad); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF((cd_cx-cd_r+1.5)*u, (cd_cy-cd_r+1.5)*u,
                             (cd_r*2-3)*u, (cd_r*2-3)*u))
        # CD 中心孔
        fill_ellipse(cd_cx, cd_cy, 2.5, 2.5, "#606070")
        fill_ellipse(cd_cx, cd_cy, 1.5, 1.5, "#303038")
        # 盒子前侧底部反光
        fill_rect(10, 36, 26, 2, 0, QColor(0,0,0,30))

    elif name == "accounts":
        # ====== 用户账户: 两个用户头像 ======
        # 后面的人 (蓝衣服)
        fill_ellipse(20, 17, 5.5, 5.5, "#F8D0B0")  # 头
        # 头发
        hair2 = QPainterPath()
        hair2.addEllipse(QRectF(14.5*u, 12*u, 11*u, 7*u))
        fill(hair2, "#8B6914")
        # 身体
        body2 = QPainterPath()
        body2.moveTo(10*u, 42*u)
        body2.arcTo(QRectF(11*u, 25*u, 18*u, 18*u), 200*16, 140*16)
        body2.closeSubpath()
        fill(body2, "#3070B8")
        # 头要画在身体上
        fill_ellipse(20, 17, 5.5, 5.5, "#F8D0B0")
        hair2b = QPainterPath()
        hair2b.addEllipse(QRectF(14.5*u, 11.5*u, 11*u, 7*u))
        fill(hair2b, "#8B6914")
        # 前面的人 (绿衣服)
        fill_ellipse(31, 22, 7, 7, "#F8D0B0")
        hair1 = QPainterPath()
        hair1.addEllipse(QRectF(24*u, 15*u, 14*u, 9*u))
        fill(hair1, "#3A3A3A")
        body1 = QPainterPath()
        body1.moveTo(18*u, 48*u)
        body1.arcTo(QRectF(20*u, 32*u, 22*u, 20*u), 200*16, 140*16)
        body1.closeSubpath()
        fill(body1, "#589048")
        # 头再次画上来
        fill_ellipse(31, 22, 7, 7, "#F8D0B0")
        hair1b = QPainterPath()
        hair1b.addEllipse(QRectF(24*u, 14.5*u, 14*u, 9*u))
        fill(hair1b, "#3A3A3A")
        # 橙色小盾牌 (右下角)
        shield_s = QPainterPath()
        shield_s.moveTo(40*u, 34*u)
        shield_s.lineTo(44*u, 36*u); shield_s.lineTo(44*u, 40*u)
        shield_s.quadTo(44*u, 44*u, 40*u, 46*u)
        shield_s.quadTo(36*u, 44*u, 36*u, 40*u)
        shield_s.lineTo(36*u, 36*u)
        shield_s.closeSubpath()
        fill(shield_s, "#F0A030")
        # 盾上蓝色对勾
        p.setPen(QPen(QColor("#1B5AA5"), 1.5*u, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(38*u,40*u), QPointF(39.5*u,41.5*u))
        p.drawLine(QPointF(39.5*u,41.5*u), QPointF(42*u,38.5*u))

    elif name == "personalization":
        # ====== 外观和个性化: 显示器 + 2x2彩色调色板 ======
        # 显示器 (紫色)
        mon_g = QLinearGradient(8*u, 6*u, 8*u, 28*u)
        mon_g.setColorAt(0, QColor("#A050D0"))
        mon_g.setColorAt(1, QColor("#7020A0"))
        mon = QPainterPath()
        mon.addRoundedRect(QRectF(8*u, 8*u, 22*u, 18*u), 1.5*u, 1.5*u)
        fill(mon, mon_g)
        # 屏幕
        fill_rect(10, 10, 18, 14, 0.5, "#202040")
        # 屏幕渐变紫/蓝
        scr_g = QLinearGradient(10*u, 10*u, 28*u, 24*u)
        scr_g.setColorAt(0, QColor("#6040C0"))
        scr_g.setColorAt(1, QColor("#202060"))
        p.setBrush(scr_g); p.setPen(Qt.NoPen)
        p.drawRect(QRectF(10*u,10*u,18*u,14*u))
        # 屏幕紫色三角 (抽象图形)
        tri = QPainterPath()
        tri.moveTo(10*u, 24*u); tri.lineTo(28*u, 10*u); tri.lineTo(28*u, 24*u)
        tri.closeSubpath()
        fill(tri, QColor(160,80,220,120))
        # 底座
        fill_rect(15, 26, 8, 2, 0.5, "#8040A0")
        fill_rect(12, 28, 14, 2, 0.5, "#603080")
        # 2x2 彩色调色板 (右下角)
        palette_x, palette_y, cs = 26, 24, 7
        palette_colors = [("#E82020", 0,0), ("#F8C020", 1,0),
                          ("#2080D8", 0,1), ("#20A030", 1,1)]
        for col, cx, cy in palette_colors:
            fill_rect(palette_x + cx*cs, palette_y + cy*cs, cs, cs, 0.8, col)
        # 调色板外框
        pal_box = QPainterPath()
        pal_box.addRoundedRect(
            QRectF(palette_x*u, palette_y*u, cs*2*u, cs*2*u), 1*u, 1*u)
        stroke(pal_box, "#808080", 0.8)
        # 四个色块之间的白线
        p.setPen(QPen(QColor("#FFFFFF"), 0.8*u))
        p.drawLine(QPointF((palette_x+cs)*u, palette_y*u), QPointF((palette_x+cs)*u, (palette_y+cs*2)*u))
        p.drawLine(QPointF(palette_x*u, (palette_y+cs)*u), QPointF((palette_x+cs*2)*u, (palette_y+cs)*u))

    elif name == "time":
        # ====== 时钟和区域: 地球 + 时钟 ======
        # 地球 (左后方)
        earth_g = QRadialGradient(14*u, 20*u, 16*u)
        earth_g.setColorAt(0, QColor("#70C0E8"))
        earth_g.setColorAt(0.6, QColor("#2070B8"))
        earth_g.setColorAt(1, QColor("#104880"))
        p.setBrush(earth_g); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(4*u, 12*u, 22*u, 22*u))
        # 大陆
        fill_ellipse(12, 18, 4, 3, "#58A840")
        fill_ellipse(17, 24, 5, 4, "#58A840")
        fill_ellipse(9, 26, 3, 2.5, "#58A840")
        # 时钟 (右前方)
        cx, cy, cr = 32, 28, 13
        # 时钟阴影
        p.setBrush(QColor(0,0,0,40)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF((cx-cr+1)*u, (cy-cr+1)*u, cr*2*u, cr*2*u))
        # 白色表盘
        fill_ellipse(cx, cy, cr, cr, "#F0F0F0")
        fill_ellipse(cx, cy, cr-1.5, cr-1.5, "#FFFFFF")
        # 时钟边框 (银色)
        rim = QPen(QColor("#888890")); rim.setWidthF(1.5*u); p.setPen(rim); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF((cx-cr)*u, (cy-cr)*u, cr*2*u, cr*2*u))
        # 刻度
        p.setPen(QPen(QColor("#303030"), 1*u))
        for i in range(12):
            angle = math.radians(i*30 - 90)
            x1 = cx + (cr-2)*math.cos(angle)
            y1 = cy + (cr-2)*math.sin(angle)
            x2 = cx + (cr-3.5 if i%3==0 else cr-2.8)*math.cos(angle)
            y2 = cy + (cr-3.5 if i%3==0 else cr-2.8)*math.sin(angle)
            p.drawLine(QPointF(x1*u,y1*u), QPointF(x2*u,y2*u))
        # 时针 (10:10位置)
        p.setPen(QPen(QColor("#202020"), 2*u, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx*u,cy*u), QPointF((cx-3)*u,(cy-2)*u))
        # 分针
        p.setPen(QPen(QColor("#202020"), 1.5*u, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx*u,cy*u), QPointF((cx+5)*u,(cy-3)*u))
        # 秒针 (橙色)
        p.setPen(QPen(QColor("#E04020"), 0.8*u, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx*u,cy*u), QPointF((cx-1)*u,(cy+5)*u))
        # 中心点
        fill_ellipse(cx, cy, 1, 1, "#202020")

    elif name == "accessibility":
        # ====== 轻松使用: 蓝色圆形 + 轮椅/辅助符号 ======
        cx, cy, cr = 24, 24, 18
        # 蓝色圆形 (带渐变)
        acc_g = QRadialGradient(cx*u, cy*u, cr*u)
        acc_g.setColorAt(0, QColor("#3090E0"))
        acc_g.setColorAt(0.8, QColor("#1060B8"))
        acc_g.setColorAt(1, QColor("#084080"))
        p.setBrush(acc_g); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF((cx-cr)*u, (cy-cr)*u, cr*2*u, cr*2*u))
        # 白色箭头/人形符号
        white = QColor("#FFFFFF")
        p.setPen(QPen(white, 2.5*u, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        # 圆圈 (头)
        p.setBrush(white); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF((cx-2.5)*u, (cy-12)*u, 5*u, 5*u))
        p.setPen(QPen(white, 2.8*u, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush)
        # 上半身横线 (从左到右弧形)
        p.drawArc(QRectF((cx-8)*u, (cy-8)*u, 16*u, 16*u), 40*16, 280*16)
        # 向下的箭头/身体
        p.drawLine(QPointF(cx*u, (cy-6)*u), QPointF(cx*u, (cy+6)*u))
        # 向右箭头
        p.drawLine(QPointF(cx*u, (cy-2)*u), QPointF((cx+8)*u, (cy-2)*u))
        p.drawLine(QPointF((cx+5)*u, (cy-5)*u), QPointF((cx+8)*u, (cy-2)*u))
        p.drawLine(QPointF((cx+5)*u, (cy+1)*u), QPointF((cx+8)*u, (cy-2)*u))

    p.end()
    return pm


# 重写 classic 图标的加载: 优先 PNG，否则用 Win7 复合图标绘制
_WIN7_ICONS = {"shield", "network", "sound", "apps", "accounts",
               "personalization", "time", "accessibility"}


def _find_classic_png(name: str, target_size: int) -> QPixmap:
    """查找经典控制面板用小图标 (透明背景, 彩色实心)"""
    sizes_try = [32, 48]
    pm = _load_png(f"classic/{name}-{target_size}.png", target_size)
    if pm is not None:
        return pm
    for sz in sizes_try:
        if sz >= target_size:
            pm = _load_png(f"classic/{name}-{sz}.png", target_size)
            if pm is not None:
                return pm
    pm = _load_png(f"classic/{name}-48.png", target_size)
    return pm


def draw_tile_icon(name: str, bg_color: str, size: int = 40) -> QPixmap:
    """获取控制面板条目图标：优先 classic PNG，回退代码绘制
    - size <= 48 优先 classic 透明彩色小图标 (原版风格)
    - size > 48 优先 tiles 彩色磁贴
    - 8 大分类无 PNG 时用 Win7 复合图标；其余用 Fluent 图标（透明背景彩色线条）
    """
    if size <= 48:
        pm = _find_classic_png(name, size)
        if pm is not None:
            return pm
        if name in _WIN7_ICONS:
            pm = _draw_win7_icon(name, size)
            return pm
        # 其他条目图标：彩色 Fluent 线条（透明背景）
        return _draw_icon_painter(name, QColor(bg_color), size)
    pm = _find_tile_png(name, size)
    if pm is not None:
        return pm
    return _draw_tile_icon_painter(name, bg_color, size)


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

    def set_checked_silent(self, c: bool, animate=False):
        """程序化刷新状态，不发出 toggled 信号（避免触发处理函数造成死循环）"""
        self.blockSignals(True)
        try:
            self.setChecked(c, animate=animate)
        finally:
            self.blockSignals(False)

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
        self._subtitle = None
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("subText")
            s.setWordWrap(True)
            text_col.addWidget(s)
            self._subtitle = s
        lay.addLayout(text_col, 1)
        if trailing is not None:
            lay.addSpacing(8)
            lay.addWidget(trailing, 0, Qt.AlignRight | Qt.AlignVCenter)
        if selectable:
            self._arrow = QLabel("›")
            self._arrow.setObjectName("subText")
            lay.addWidget(self._arrow)

    def set_description(self, text: str):
        """更新副标题"""
        if self._subtitle is None:
            self._subtitle = QLabel(text)
            self._subtitle.setObjectName("subText")
            self._subtitle.setWordWrap(True)
            # 找到 text_col 并插入到 title 之后
            for i in range(self.layout().count()):
                it = self.layout().itemAt(i)
                if it.layout() and it.layout().count() > 0:
                    title_item = it.layout().itemAt(0)
                    if title_item.widget() and title_item.widget().objectName() == "rowTitle":
                        it.layout().addWidget(self._subtitle)
                        return
        else:
            self._subtitle.setText(text)

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
