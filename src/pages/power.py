"""power.py — 电源和电池（对应 Win11 → 系统 → 电源和电池）
基于 powerprofilesctl / systemd / GNOME gsettings。
"""
import os

from PyQt5.QtWidgets import (QComboBox, QLabel, QPushButton, QHBoxLayout,
                             QMessageBox)

import utils
from widgets import BasePage, SettingRow, confirm_box


def _power_profile() -> str:
    if utils.have("powerprofilesctl"):
        ok, out, _ = utils.run(["powerprofilesctl", "get"], timeout=5)
        if ok:
            return out.strip()
    gov = utils.read_first_line(
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov == "performance":
        return "performance"
    if gov == "powersave":
        return "power-saver"
    return "balanced"


class PowerPage(BasePage):
    def __init__(self):
        super().__init__("电源和电池", "电源模式、睡眠和屏幕关闭时间。")
        self._build()

    def _build(self):
        c = self.add_card("电源模式")
        self.mode_combo = QComboBox()
        for key, txt in (("performance", "最佳性能"), ("balanced", "平衡"),
                         ("power-saver", "最佳能效")):
            self.mode_combo.addItem(txt, key)
        self.mode_combo.currentIndexChanged.connect(self._set_mode)
        c.add(SettingRow("电源模式", "调节 CPU 性能与能耗 (powerprofilesctl / cpufreq)",
                         trailing=self.mode_combo, icon="power"))
        self._profile_note = QLabel("")
        self._profile_note.setObjectName("subText")
        c.layout().addWidget(self._profile_note)

        c2 = self.add_card("屏幕和睡眠")
        self.screen_off = QComboBox()
        for sec, txt in ((0, "从不"), (300, "5 分钟"), (600, "10 分钟"),
                         (1800, "30 分钟"), (3600, "1 小时")):
            self.screen_off.addItem(txt, sec)
        self.screen_off.currentIndexChanged.connect(
            lambda _i: utils.gset("org.gnome.desktop.session",
                                  "idle-delay",
                                  str(self.screen_off.currentData())))
        c2.add(SettingRow("屏幕关闭时间", "空闲多久后关闭屏幕 (GNOME)",
                          trailing=self.screen_off, icon="power"))
        self.sleep_combo = QComboBox()
        for sec, txt in ((0, "从不"), (1800, "30 分钟"), (3600, "1 小时"),
                         (7200, "2 小时")):
            self.sleep_combo.addItem(txt, sec)
        self.sleep_combo.currentIndexChanged.connect(
            lambda _i: utils.gset("org.gnome.settings-daemon.plugins.power",
                                  "sleep-inactive-ac-timeout",
                                  str(self.sleep_combo.currentData())))
        c2.add(SettingRow("自动睡眠时间", "空闲多久后挂起 (GNOME)",
                          trailing=self.sleep_combo, icon="power"))

        # 电池信息
        self.batt_card = self.add_card("电池")
        self.batt_label = QLabel("未检测到电池（台式机）。")
        self.batt_label.setObjectName("subText")
        self.batt_card.layout().addWidget(self.batt_label)

        c4 = self.add_card("电源操作")
        h = QHBoxLayout()
        for text, cmd, danger in (("注销", ["gnome-session-quit", "--logout", "--no-prompt"], False),
                                  ("挂起", ["systemctl", "suspend"], False),
                                  ("重启", ["systemctl", "reboot"], True),
                                  ("关机", ["systemctl", "poweroff"], True)):
            btn = QPushButton(text)
            if danger:
                btn.setObjectName("dangerBtn")
            btn.clicked.connect(lambda _c, a=cmd, t=text: self._power_action(t, a))
            h.addWidget(btn)
        h.addStretch(1)
        c4.layout().addLayout(h)
        self.add_stretch()

    def _power_action(self, text, cmd):
        if not confirm_box(self, text, f"确定要{text}吗？未保存的工作将丢失。"):
            return
        ok, _o, _e = utils.run(cmd, timeout=5)
        if not ok:
            # 桌面会话内通常允许，失败则尝试 polkit
            ok2, _o2, err = utils.run_root(cmd)
            if not ok2:
                QMessageBox.warning(self, "失败", f"操作失败：{err}")

    def _set_mode(self, idx):
        key = self.mode_combo.itemData(idx)
        if not key:
            return
        if utils.have("powerprofilesctl"):
            ok, _o, err = utils.run(["powerprofilesctl", "set", key], timeout=5)
            self._profile_note.setText("" if ok else f"设置失败：{err}")
        else:
            gov = "performance" if key == "performance" else (
                "powersave" if key == "power-saver" else "schedutil")
            ok, _o, err = utils.run_root(
                ["sh", "-c",
                 f"echo {gov} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null"])
            self._profile_note.setText(
                "" if ok else f"需要 root 权限或系统不支持：{err}")

    def on_show(self):
        cur = _power_profile()
        i = self.mode_combo.findData(cur)
        if i >= 0:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(i)
            self.mode_combo.blockSignals(False)
        # 电池
        cap, status = "", ""
        base = "/sys/class/power_supply"
        if os.path.isdir(base):
            for d in os.listdir(base):
                t = utils.read_first_line(f"{base}/{d}/type")
                if t == "Battery":
                    try:
                        now = int(utils.read_first_line(f"{base}/{d}/energy_now")
                                  or utils.read_first_line(f"{base}/{d}/charge_now"))
                        full = int(utils.read_first_line(f"{base}/{d}/energy_full")
                                   or utils.read_first_line(f"{base}/{d}/charge_full"))
                        cap = f"{int(now / full * 100)}%"
                        status = utils.read_first_line(f"{base}/{d}/status")
                    except (ValueError, ZeroDivisionError, OSError):
                        pass
                    break
        if cap:
            self.batt_label.setText(f"电量 {cap} · {status}")
        # GNOME 空闲值回显 (用 blockSignals 避免触发 setCurrentIndex -> 写回 -> 死循环)
        for combo, key in ((self.screen_off, "org.gnome.desktop.session|idle-delay"),
                           (self.sleep_combo,
                            "org.gnome.settings-daemon.plugins.power|sleep-inactive-ac-timeout")):
            schema, gk = key.split("|")
            v = utils.gget(schema, gk)
            if v:
                try:
                    sec = int(str(v).replace("uint32 ", ""))
                    i = combo.findData(sec)
                    if i >= 0:
                        combo.blockSignals(True)
                        combo.setCurrentIndex(i)
                        combo.blockSignals(False)
                except ValueError:
                    pass
