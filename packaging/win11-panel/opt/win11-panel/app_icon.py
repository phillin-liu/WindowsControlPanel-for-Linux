"""app_icon.py — 程序图标 (饼图 + 开关 + 滑块 风格)"""
import os
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath,
                         QPen, QPixmap, QBrush)


def build_app_icon(size: int = 256) -> QPixmap:
    """生成程序图标 QPixmap (圆角浅蓝底, 蓝橙饼图, 三开关, 滑块)"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # ---- 卡片背景: 圆角矩形 + 浅蓝渐变 + 蓝色描边
    pad = max(2, size // 64)
    rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
    radius = size * 0.18
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#CFE8F8"))
    grad.setColorAt(1.0, QColor("#A8D2EE"))
    p.fillPath(path, QBrush(grad))
    pen = QPen(QColor("#3A8FCD"))
    pen.setWidthF(max(1.5, size / 128.0))
    p.strokePath(path, pen)

    # 内边距比例
    s = size
    pie_cx, pie_cy = s * 0.32, s * 0.40
    pie_r = s * 0.22

    # ---- 饼图: 蓝色大扇形 (270°, 左侧) + 橙色扇形 (90°, 右下)
    p.save()
    p.translate(pie_cx, pie_cy)
    # 蓝色扇形: 12 点钟起, 270° 顺时针
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#2A8FD4"))
    p.drawPie(QRectF(-pie_r, -pie_r, pie_r * 2, pie_r * 2),
              90 * 16, 270 * 16)  # Qt 角度: 12 点起 0=3点
    # 橙色扇形: 3 点起, 90°
    p.setBrush(QColor("#F2A53A"))
    p.drawPie(QRectF(-pie_r, -pie_r, pie_r * 2, pie_r * 2),
              0 * 16, 90 * 16)
    # 中心高光白点
    p.setBrush(QColor(255, 255, 255, 80))
    p.drawEllipse(QPointF(0, 0), pie_r * 0.25, pie_r * 0.25)
    p.restore()

    # 饼图外环描边
    p.setPen(QPen(QColor("#1F6FA8"), max(1, s / 180.0)))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(pie_cx, pie_cy), pie_r, pie_r)

    # ---- 三个开关 (右侧)
    sw_w, sw_h = s * 0.40, s * 0.085
    sw_x = s * 0.55
    sw_r = sw_h / 2
    sw_colors = [
        (QColor("#2A8FD4"), QColor("#E9F2FA"), QColor("#FFFFFF")),  # 蓝开启
        (QColor("#2A8FD4"), QColor("#E9F2FA"), QColor("#FFFFFF")),  # 蓝开启
        (QColor("#B6D6EC"), QColor("#E9F2FA"), QColor("#7FA8C4")),  # 灰关闭
    ]
    gap = s * 0.04
    for i, (on_bg, off_bg, knob) in enumerate(sw_colors):
        y = s * 0.20 + i * (sw_h + gap)
        # 底槽
        p.setPen(Qt.NoPen)
        bg = on_bg if i < 2 else off_bg
        bg2 = on_bg.darker(115) if i < 2 else QColor("#9CBED8")
        g = QLinearGradient(sw_x, y, sw_x, y + sw_h)
        g.setColorAt(0, bg.lighter(110))
        g.setColorAt(1, bg2)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(sw_x, y, sw_w, sw_h), sw_r, sw_r)
        # 旋钮
        knob_r = sw_h * 0.42
        cx = sw_x + sw_w - sw_r - 2 if i < 2 else sw_x + sw_r + 2
        p.setBrush(knob)
        pen = QPen(QColor("#1F6FA8"), max(0.8, s / 300.0))
        p.setPen(pen)
        p.drawEllipse(QPointF(cx, y + sw_h / 2), knob_r, knob_r)
        # 旋钮高光
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(cx - knob_r * 0.25, y + sw_h / 2 - knob_r * 0.35),
                      knob_r * 0.30, knob_r * 0.20)
    p.setPen(Qt.NoPen)

    # ---- 底部滑块 (橙色填充左侧 + 蓝色轨道)
    sl_x, sl_y = s * 0.13, s * 0.80
    sl_w, sl_h = s * 0.74, s * 0.08
    sl_r = sl_h / 2
    # 蓝色轨道
    p.setBrush(QColor("#5FA7D6"))
    p.drawRoundedRect(QRectF(sl_x, sl_y, sl_w, sl_h), sl_r, sl_r)
    # 橙色填充 (~38%)
    fill_w = sl_w * 0.38
    p.setBrush(QColor("#F2A53A"))
    p.drawRoundedRect(QRectF(sl_x, sl_y, fill_w, sl_h), sl_r, sl_r)
    # 滑块手柄
    handle_r = sl_h * 0.65
    hx = sl_x + fill_w
    p.setBrush(QColor("#FFFFFF"))
    p.setPen(QPen(QColor("#1F6FA8"), max(1, s / 200.0)))
    p.drawEllipse(QPointF(hx, sl_y + sl_h / 2), handle_r, handle_r)
    # 底部滑轨阴影
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 25))
    p.drawRoundedRect(QRectF(sl_x, sl_y + sl_h + 1, sl_w, 2), 1, 1)

    p.end()
    return pm


def save_icon_set(out_dir: str):
    """保存多尺寸 PNG 图标, 用于打包 (.deb 安装后桌面图标)"""
    os.makedirs(out_dir, exist_ok=True)
    for sz in (16, 32, 48, 64, 128, 256, 512):
        pm = build_app_icon(sz)
        pm.save(os.path.join(out_dir, f"win11-panel-{sz}.png"), "PNG")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication(sys.argv)
    out = os.path.join(os.path.dirname(__file__), "icons", "app")
    save_icon_set(out)
    print(f"saved icons to {out}")
