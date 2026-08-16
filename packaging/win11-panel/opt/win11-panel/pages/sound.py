"""sound.py — 声音设置（对应 Win11 → 系统 → 声音）
基于 pactl (PulseAudio/PipeWire) 实现。
"""
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSlider, QLabel, QHBoxLayout, QComboBox, QPushButton

import utils
from widgets import BasePage, SettingRow, ToggleSwitch, info_box

TEST_SOUNDS = ["/usr/share/sounds/alsa/Front_Center.wav",
               "/usr/share/sounds/freedesktop/stereo/bell.oga"]


def _default_sink() -> str:
    ok, out, _ = utils.run(["pactl", "get-default-sink"])
    return out if ok else ""


def _volume_pct() -> int:
    ok, out, _ = utils.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    if ok:
        m = re.search(r"(\d+)%", out)
        if m:
            return int(m.group(1))
    return -1


def _muted() -> bool:
    ok, out, _ = utils.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], timeout=5)
    # pactl 返回 "Mute: yes" / "Mute: no"
    if not ok:
        return False
    o = out.lower()
    return "muted: yes" in o or "是" in o or re.search(r"\byes\b", o) is not None


def _sinks(kind="sink"):
    ok, out, _ = utils.run(["pactl", f"list", "short", f"{kind}s"])
    items = []
    if ok:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                items.append(parts[1])
    return items


class SoundPage(BasePage):
    def __init__(self):
        super().__init__("声音", "音量级别、输出、输入和声音设备。")
        self._build()
        self.refresh()

    def _build(self):
        c = self.add_card("输出")
        h = QHBoxLayout()
        h.addWidget(QLabel("音量"))
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.sliderReleased.connect(self._set_volume)
        self.vol_label = QLabel("--%")
        h.addWidget(self.vol_slider, 1)
        h.addWidget(self.vol_label)
        c.layout().addLayout(h)

        self.mute_toggle = ToggleSwitch()
        self.mute_toggle.toggled.connect(self._set_mute)
        c.add(SettingRow("静音", "将系统输出静音", trailing=self.mute_toggle,
                         icon="sound"))

        self.sink_combo = QComboBox()
        self.sink_combo.setMinimumWidth(280)
        self.sink_combo.currentTextChanged.connect(self._set_sink)
        c.add(SettingRow("输出设备", "选择播放设备", trailing=self.sink_combo,
                         icon="sound"))

        test_btn = QPushButton("测试扬声器")
        test_btn.clicked.connect(self._test)
        c.layout().addWidget(test_btn, alignment=Qt.AlignLeft)

        c2 = self.add_card("输入")
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("麦克风音量"))
        self.mic_slider = QSlider(Qt.Horizontal)
        self.mic_slider.setRange(0, 100)
        self.mic_slider.sliderReleased.connect(self._set_mic_volume)
        self.mic_label = QLabel("--%")
        h2.addWidget(self.mic_slider, 1)
        h2.addWidget(self.mic_label)
        c2.layout().addLayout(h2)
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(280)
        self.mic_combo.currentTextChanged.connect(self._set_source)
        c2.add(SettingRow("输入设备", "选择录音设备", trailing=self.mic_combo,
                          icon="sound"))

        if not utils.have("pactl"):
            tip = QLabel("未检测到音频控制组件 (pulseaudio-utils)。"
                         "请在应用商店或软件中心安装后使用声音功能。")
            tip.setObjectName("subText")
            tip.setWordWrap(True)
            self.body.addWidget(tip)
        self.add_stretch()

    def refresh(self):
        if not utils.have("pactl"):
            return
        v = _volume_pct()
        if v >= 0:
            self.vol_slider.setValue(v)
            self.vol_label.setText(f"{v}%")
        self.mute_toggle.set_checked_silent(_muted())
        cur = _default_sink()
        self.sink_combo.blockSignals(True)
        self.sink_combo.clear()
        self.sink_combo.addItems(_sinks("sink"))
        if cur:
            self.sink_combo.setCurrentText(cur)
        self.sink_combo.blockSignals(False)
        ok, src, _ = utils.run(["pactl", "get-default-source"])
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItems(_sinks("source"))
        if ok and src:
            self.mic_combo.setCurrentText(src)
        self.mic_combo.blockSignals(False)
        ok, mv, _ = utils.run(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"])
        if ok:
            m = re.search(r"(\d+)%", mv)
            if m:
                self.mic_slider.setValue(int(m.group(1)))
                self.mic_label.setText(f"{m.group(1)}%")

    def _set_volume(self):
        v = self.vol_slider.value()
        self.vol_label.setText(f"{v}%")
        utils.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%"])
        utils.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])

    def _set_mute(self, on: bool):
        utils.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if on else "0"])

    def _set_sink(self, name: str):
        if name:
            utils.run(["pactl", "set-default-sink", name])

    def _set_source(self, name: str):
        if name:
            utils.run(["pactl", "set-default-source", name])

    def _set_mic_volume(self):
        v = self.mic_slider.value()
        self.mic_label.setText(f"{v}%")
        utils.run(["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{v}%"])

    def _test(self):
        import os
        for f in TEST_SOUNDS:
            if os.path.exists(f):
                if f.endswith(".oga") and utils.have("paplay"):
                    utils.run(["paplay", f])
                elif utils.have("aplay"):
                    utils.run(["aplay", f])
                break
        else:
            info_box(self, "提示", "未找到测试音频文件。")

    def on_show(self):
        self.refresh()
