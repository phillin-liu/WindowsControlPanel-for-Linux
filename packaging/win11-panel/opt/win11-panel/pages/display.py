"""display.py — 显示设置（对应 Win11 → 系统 → 显示）
基于 xrandr (X11) / brightnessctl / gsettings 实现。
"""
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QComboBox, QLabel, QSlider, QVBoxLayout,
                             QHBoxLayout, QPushButton, QGridLayout)

import utils
from widgets import BasePage, ToggleSwitch, SettingRow


def _parse_xrandr():
    """解析 xrandr 输出。返回 [ {name, connected, current_mode, modes[...], rotation} ]"""
    ok, out, _ = utils.run(["xrandr"], timeout=5)
    if not ok:
        return []
    outputs, cur = [], None
    for line in out.splitlines():
        m = re.match(r"^(\S+) connected (?:primary )?", line)
        if m or " disconnected " in line:
            name = line.split()[0]
            cur = {"name": name, "connected": " connected" in line,
                   "current_mode": "", "modes": [], "rotation": "normal"}
            rot = re.search(r"\b(normal|left|right|inverted)\b", line)
            if rot:
                cur["rotation"] = rot.group(1)
            outputs.append(cur)
            continue
        if cur is None or not cur["connected"]:
            continue
        m = re.match(r"^\s+(\d+x\d+)\s+[\d.+\s]+(?:\*|\+)", line)
        if m:
            mode = m.group(1)
            rates = re.findall(r"(\d+\.\d+)([*+]?)", line)
            rate_str = ""
            best = None
            for rate, mark in rates:
                if "*" in mark:
                    best = rate
                    break
            rate_str = f"@{best}Hz" if best else ""
            cur["modes"].append(f"{mode}{rate_str}")
        if "*" in line and not cur["current_mode"]:
            pass
    return outputs


class DisplayPage(BasePage):
    def __init__(self):
        super().__init__("显示", "显示器、亮度、夜间模式、分辨率、缩放。")
        self._build()
        self.refresh()

    def _build(self):
        # 亮度
        c = self.add_card("亮度和颜色")
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(5, 100)
        self.bright_slider.sliderReleased.connect(self._set_brightness)
        self.bright_label = QLabel("--%")
        h = QHBoxLayout()
        h.addWidget(QLabel("亮度"))
        h.addWidget(self.bright_slider, 1)
        h.addWidget(self.bright_label)
        c.layout().addLayout(h)
        night = ToggleSwitch(utils.gget("org.gnome.settings-daemon.plugins.color",
                                        "night-light-enabled") == "true")
        night.toggled.connect(self._toggle_night)
        c.add(SettingRow("夜间模式", "屏幕色调变暖，帮助入睡 (需要 redshift 或 GNOME)",
                         trailing=night, icon="display"))

        # 每个显示器一张卡
        self.outputs_area = QVBoxLayout()
        self.body.addLayout(self.outputs_area)

        # 缩放
        scale_card = self.add_card("缩放")
        self.scale_combo = QComboBox()
        for s in ("100%", "125%", "150%", "175%", "200%"):
            self.scale_combo.addItem(s, s.rstrip("%"))
        self.scale_combo.currentIndexChanged.connect(self._set_scale)
        scale_card.add(SettingRow("缩放比例", "更改文本、应用等项目的大小 (xrandr 缩放)",
                                  trailing=self.scale_combo, icon="display"))

        # 方向说明
        tip = QLabel("提示：分辨率/方向修改基于 xrandr，仅支持 X11 会话。"
                     "Wayland 会话下请使用桌面环境自带的显示设置。")
        tip.setObjectName("subText")
        tip.setWordWrap(True)
        self.body.addWidget(tip)
        self.add_stretch()

    # ---------------------------------------------------------------- 刷新
    def refresh(self):
        # 清空旧输出卡
        while self.outputs_area.count():
            item = self.outputs_area.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        outputs = _parse_xrandr()
        if not outputs:
            card = self.add_card_to(self.outputs_area, "未检测到显示器")
            card.layout().addWidget(QLabel(
                "无法通过 xrandr 获取显示器信息（Wayland 会话或未安装 x11-xserver-utils）。"))
        for out in outputs:
            if not out["connected"]:
                continue
            card = self.add_card_to(self.outputs_area, out["name"])
            grid = QGridLayout()
            grid.setSpacing(10)
            grid.addWidget(QLabel("分辨率"), 0, 0)
            mode_combo = QComboBox()
            seen = set()
            for m in out["modes"]:
                if m not in seen:
                    seen.add(m)
                    mode_combo.addItem(m)
            mode_combo.setCurrentText(out["current_mode"] or
                                      (out["modes"][0] if out["modes"] else ""))
            mode_combo.currentTextChanged.connect(
                lambda m, n=out["name"]: self._set_mode(n, m))
            grid.addWidget(mode_combo, 0, 1)
            grid.addWidget(QLabel("方向"), 1, 0)
            rot_combo = QComboBox()
            for r, txt in (("normal", "横向"), ("left", "纵向(左)"),
                           ("right", "纵向(右)"), ("inverted", "倒置")):
                rot_combo.addItem(txt, r)
            idx = [i for i, (r, _t) in enumerate((("normal", ""), ("left", ""),
                                                  ("right", ""), ("inverted", "")))
                   if r == out["rotation"]]
            if idx:
                rot_combo.setCurrentIndex(idx[0])
            rot_combo.currentIndexChanged.connect(
                lambda i, n=out["name"], cb=rot_combo: self._set_rotation(n, cb.currentData()))
            grid.addWidget(rot_combo, 1, 1)
            grid.setColumnStretch(2, 1)
            card.layout().addLayout(grid)
        # 亮度
        self._refresh_brightness()
        # cur = ... 已死代码, 删除
        pass

    def add_card_to(self, lay, title):
        from widgets import Card
        card = Card(title)
        lay.addWidget(card)
        return card

    def _refresh_brightness(self):
        max_f = min_f = None
        bl_dir = "/sys/class/backlight"
        if os.path.isdir(bl_dir):
            for d in os.listdir(bl_dir):
                base = f"{bl_dir}/{d}"
                try:
                    mx = int(utils.read_first_line(f"{base}/max_brightness"))
                    cur = int(utils.read_first_line(f"{base}/brightness"))
                    if mx > 0:
                        max_f, min_f = mx, cur
                        break
                except (ValueError, OSError):
                    continue
        if max_f is None and utils.have("brightnessctl"):
            ok, out, _ = utils.run(["brightnessctl", "-m", "info"], timeout=5)
            if ok and "," in out:
                parts = out.split(",")
                try:
                    cur = int(parts[3])
                    mx = int(parts[4])
                    if mx > 0:
                        self.bright_slider.setValue(int(cur / mx * 100))
                        self.bright_label.setText(f"{int(cur / mx * 100)}%")
                except (ValueError, IndexError):
                    pass
            return
        if max_f:
            pct = int(min_f / max_f * 100)
            self.bright_slider.setValue(pct)
            self.bright_label.setText(f"{pct}%")
        else:
            # 无可用亮度接口
            self.bright_slider.setEnabled(False)
            self.bright_label.setText("不可用")

    # ---------------------------------------------------------------- 操作
    def _set_brightness(self):
        pct = self.bright_slider.value()
        self.bright_label.setText(f"{pct}%")
        applied = False
        bl_dir = "/sys/class/backlight"
        if os.path.isdir(bl_dir):
            for d in os.listdir(bl_dir):
                base = f"{bl_dir}/{d}"
                try:
                    mx = int(utils.read_first_line(f"{base}/max_brightness"))
                    if mx > 0:
                        utils.run_root(["sh", "-c",
                                        f"echo {int(mx * pct / 100)} > {base}/brightness"])
                        applied = True
                except (ValueError, OSError):
                    continue
        if not applied and utils.have("brightnessctl"):
            utils.run(["brightnessctl", "set", f"{pct}%"], timeout=5)

    def _toggle_night(self, on: bool):
        if utils.have("redshift"):
            if on:
                utils.run(["sh", "-c", "redshift -O 4200 -P >/dev/null 2>&1 &"])
            else:
                utils.run(["redshift", "-x"])
        utils.gset("org.gnome.settings-daemon.plugins.color", "night-light-enabled",
                   "true" if on else "false")

    def _set_mode(self, output: str, mode: str):
        res = mode.split("@")[0]
        ok, _o, err = utils.run(["xrandr", "--output", output, "--mode", res], timeout=5)
        if not ok:
            from widgets import warn_box
            warn_box(self, "失败", f"设置分辨率失败：{err}")

    def _set_rotation(self, output: str, rot: str):
        ok, _o, err = utils.run(["xrandr", "--output", output, "--rotate", rot], timeout=5)
        if not ok:
            from widgets import warn_box
            warn_box(self, "失败", f"设置方向失败：{err}")

    def _set_scale(self, idx):
        val = self.scale_combo.itemData(idx)
        if not val:
            return
        factor = float(val) / 100.0
        utils.gset("org.gnome.desktop.interface", "text-scaling-factor", str(factor))
        outputs = _parse_xrandr()
        for out in outputs:
            if out["connected"]:
                utils.run(["xrandr", "--output", out["name"], "--scale", str(factor)],
                          timeout=5)

    def on_show(self):
        self.refresh()
