"""bluetooth.py — 蓝牙和其他设备（对应 Win11 → 蓝牙和其他设备）
基于 bluetoothctl / rfkill / lsusb / lpstat。
"""
import re

from PyQt5.QtWidgets import QLabel, QPushButton, QHBoxLayout

import utils
from widgets import BasePage, ToggleSwitch, SettingRow, Card, confirm_box, info_box


def _bt_blocked() -> bool:
    ok, out, _ = utils.run(["rfkill", "list", "bluetooth"], timeout=5)
    return ok and "blocked: yes" in out


def _connected_devices():
    ok, out, _ = utils.run(["bluetoothctl", "devices", "Connected"], timeout=5)
    devs = []
    if ok:
        for line in out.splitlines():
            m = re.match(r"Device\s+([0-9A-F:]+)\s+(.+)", line, re.I)
            if m:
                devs.append((m.group(1), m.group(2)))
    return devs


def _paired_devices():
    ok, out, _ = utils.run(["bluetoothctl", "devices"], timeout=5)
    devs = []
    if ok:
        for line in out.splitlines():
            m = re.match(r"Device\s+([0-9A-F:]+)\s+(.+)", line, re.I)
            if m:
                devs.append((m.group(1), m.group(2)))
    return devs


class BluetoothPage(BasePage):
    def __init__(self):
        super().__init__("蓝牙和其他设备", "蓝牙、USB 设备、打印机。")
        self._build()

    def _build(self):
        c = self.add_card("蓝牙")
        self.bt_toggle = ToggleSwitch(not _bt_blocked())
        self.bt_toggle.toggled.connect(self._toggle_bt)
        c.add(SettingRow("蓝牙", "发现和连接蓝牙设备 (需要 bluez)",
                         trailing=self.bt_toggle, icon="bluetooth"))

        c2 = self.add_card("设备")
        self._devices_card = c2

        c3 = self.add_card("USB 设备")
        self._usb_card = c3

        c4 = self.add_card("打印机和扫描仪")
        self._printer_card = c4

        tip = QLabel("提示：配对新设备请使用系统蓝牙设置（blueman-manager 等）。"
                     "此处提供开关、已连接设备管理与信息查看。")
        tip.setObjectName("subText")
        tip.setWordWrap(True)
        self.body.addWidget(tip)
        self.add_stretch()

    def _toggle_bt(self, on: bool):
        if not utils.have("rfkill"):
            info_box(self, "提示", "未安装 rfkill。")
            return
        # rfkill 软阻塞普通用户即可操作，避免每次开关都弹管理员认证
        utils.run(["rfkill", "unblock" if on else "block", "bluetooth"], timeout=5)
        utils.run(["bluetoothctl", "power", "on" if on else "off"], timeout=5)

    def _disconnect(self, mac: str, name: str):
        if not confirm_box(self, "断开设备", f"断开与 {name} 的连接？"):
            return
        ok, _o, _e = utils.run(["bluetoothctl", "disconnect", mac], timeout=10)
        self.on_show()

    def on_show(self):
        # 已连接 / 已配对设备
        lay = self._devices_card.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        connected = _connected_devices()
        paired = _paired_devices()
        if not utils.have("bluetoothctl"):
            lay.addWidget(QLabel("未安装 bluetoothctl (bluez)。"))
            return
        if not connected and not paired:
            lay.addWidget(QLabel("没有已配对的蓝牙设备。"))
        for mac, name in connected:
            row = SettingRow(name, f"已连接 · {mac}", icon="bluetooth",
                             trailing=QPushButton("断开"))
            row.findChildren(QPushButton)[0].clicked.connect(
                lambda _c, m=mac, n=name: self._disconnect(m, n))
            lay.addWidget(row)
        for mac, name in paired:
            if (mac, name) not in connected:
                lay.addWidget(SettingRow(name, f"已配对 · {mac}", icon="bluetooth",
                                         trailing=QPushButton("连接")))
                lay.itemAt(lay.count() - 1).widget().findChildren(QPushButton)[0].clicked.connect(
                    lambda _c, m=mac: self._connect(m))
        # USB
        ulay = self._usb_card.layout()
        while ulay.count():
            item = ulay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        ok, out, _ = utils.run(["lsusb"], timeout=5)
        if ok:
            for line in out.splitlines():
                m = re.search(r"\d{4}:\d{4}\s+(.+)$", line)
                if m:
                    ulay.addWidget(SettingRow(m.group(1), "", icon="usb"))
        else:
            ulay.addWidget(QLabel("无法读取 lsusb。"))
        # 打印机
        play = self._printer_card.layout()
        while play.count():
            item = play.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        ok, out, _ = utils.run(["lpstat", "-p"], timeout=5)
        if ok and out:
            for line in out.splitlines():
                if line.startswith("printer"):
                    play.addWidget(SettingRow(line.split()[1],
                                              " ".join(line.split()[2:]), icon="usb"))
        else:
            play.addWidget(QLabel("未检测到打印机（未安装 CUPS 或没有配置打印机）。"))

    def _connect(self, mac: str):
        utils.run(["bluetoothctl", "connect", mac], timeout=15)
        self.on_show()
