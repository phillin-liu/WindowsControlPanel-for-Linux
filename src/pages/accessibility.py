"""accessibility.py — 辅助功能（对应 Win11 → 辅助功能）
文本大小 / 高对比度 / 减少动画 / 光标大小。
"""
from PyQt5.QtWidgets import QLabel, QSlider, QComboBox, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt

import theme
import utils
from widgets import BasePage, SettingRow, ToggleSwitch


class AccessibilityPage(BasePage):
    def __init__(self):
        super().__init__("辅助功能", "视觉、听觉和交互辅助。")
        self._build()

    def _build(self):
        c = self.add_card("视觉辅助")
        h = QHBoxLayout()
        h.addWidget(QLabel("文本大小"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(75, 150)
        self.size_slider.setValue(int(theme.load_theme()["font_scale"] * 100))
        self.size_label = QLabel(f"{int(theme.load_theme()['font_scale'] * 100)}%")
        h.addWidget(self.size_slider, 1)
        h.addWidget(self.size_label)
        wrap = QWidget_wrap(h)
        c.layout().addWidget(wrap)
        c.layout().addWidget(QLabel("调整本面板及 GNOME 桌面的文字大小。"))
        c.layout().itemAt(c.layout().count() - 1).widget().setObjectName("subText")

        self.contrast_toggle = ToggleSwitch(theme.load_theme()["high_contrast"])
        self.contrast_toggle.toggled.connect(self._toggle_contrast)
        c.add(SettingRow("高对比度", "使用高对比度主题，方便阅读",
                         trailing=self.contrast_toggle, icon="accessibility"))

        self.motion_toggle = ToggleSwitch(theme.load_theme()["reduce_motion"])
        self.motion_toggle.toggled.connect(self._toggle_motion)
        c.add(SettingRow("减少动画", "关闭界面动画效果，降低干扰",
                         trailing=self.motion_toggle, icon="accessibility"))

        cursor_row = SettingRow("光标大小", "调整鼠标指针大小 (GNOME)",
                                trailing=None, icon="accessibility")
        self.cursor_combo = QComboBox()
        for sz, txt in ((24, "默认"), (32, "中"), (48, "大"), (64, "特大")):
            self.cursor_combo.addItem(f"{txt} ({sz})", sz)
        self.cursor_combo.currentIndexChanged.connect(
            lambda _i: utils.gset("org.gnome.desktop.interface", "cursor-size",
                                  str(self.cursor_combo.currentData())))
        cursor_row.layout().addWidget(self.cursor_combo)
        c.add(cursor_row)

        c2 = self.add_card("听觉辅助")
        mono_on = False
        if utils.have("pactl"):
            ok, out, _ = utils.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                                   timeout=5)
            # pactl 返回 "false"/"true"
            mono_on = ok and "true" in out
        mono = ToggleSwitch(mono_on)
        mono.toggled.connect(
            lambda v: utils.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@",
                                 "1" if v else "0"]))
        c2.add(SettingRow("静音", "将默认音频输出设备静音/取消静音",
                          trailing=mono, icon="sound"))
        tip = QLabel("提示：完整的单声道混音可在音频设置中配置。"
                     "讲述人、视觉警报等辅助功能可安装 orca 屏幕阅读器实现"
                     "（可在应用商店搜索安装）。")
        tip.setObjectName("subText")
        tip.setWordWrap(True)
        c2.layout().addWidget(tip)
        self.add_stretch()

    def _apply(self):
        app = QApplication.instance()
        theme.apply_theme(app)
        win = self.window()
        if hasattr(win, "refresh_nav_icons"):
            win.refresh_nav_icons()

    def _toggle_contrast(self, on: bool):
        theme.save_theme(high_contrast=on)
        self._apply()

    def _toggle_motion(self, on: bool):
        theme.save_theme(reduce_motion=on)
        self._apply()

    def on_show(self):
        t = theme.load_theme()
        self.size_slider.setValue(int(t["font_scale"] * 100))
        self.size_label.setText(f"{int(t['font_scale'] * 100)}%")

        def _on_slider(value):
            self.size_label.setText(f"{value}%")
            theme.save_theme(font_scale=value / 100.0)
            utils.gset("org.gnome.desktop.interface", "text-scaling-factor",
                       str(round(value / 100.0, 2)))
            self._apply()
        try:
            self.size_slider.sliderMoved.disconnect()
        except TypeError:
            pass
        try:
            self.size_slider.sliderReleased.disconnect()
        except TypeError:
            pass
        self.size_slider.sliderReleased.connect(
            lambda: _on_slider(self.size_slider.value()))


def QWidget_wrap(layout):
    from PyQt5.QtWidgets import QWidget
    w = QWidget()
    w.setLayout(layout)
    return w
