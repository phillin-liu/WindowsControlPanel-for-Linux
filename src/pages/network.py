"""network.py — 网络和 Internet（对应 Win11 → 网络和 Internet）
基于 NetworkManager (nmcli)。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QPushButton, QLineEdit, QDialog,
                             QDialogButtonBox, QVBoxLayout, QComboBox)

import utils
from widgets import BasePage, ToggleSwitch, SettingRow, Card, confirm_box, info_box


def _wifi_enabled() -> bool:
    ok, out, _ = utils.run(["nmcli", "radio", "wifi"], timeout=5)
    return ok and out.strip().startswith("enabled")


def _scan_wifi():
    """返回 [(in_use, ssid, signal, security)]"""
    ok, out, _ = utils.run(
        ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
         "device", "wifi", "list", "--rescan", "yes"], timeout=25)
    nets = []
    if not ok:
        return nets
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 4:
            in_use = parts[0] == "*"
            ssid = parts[1]
            if not ssid:
                continue
            try:
                signal = int(parts[2])
            except ValueError:
                signal = 0
            sec = parts[3]
            nets.append((in_use, ssid, signal, sec))
    nets.sort(key=lambda n: (not n[0], -n[2]))
    return nets


def _known_connections():
    ok, out, _ = utils.run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE",
                            "connection", "show"], timeout=10)
    conns = []
    if ok:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                conns.append({"name": parts[0], "type": parts[1],
                              "device": parts[2]})
    return conns


class WifiPasswordDialog(QDialog):
    def __init__(self, ssid, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"连接到 {ssid}")
        self.setMinimumWidth(360)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"输入网络 {ssid} 的安全密钥："))
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)
        v.addWidget(self.pwd)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


class NetworkPage(BasePage):
    def __init__(self):
        super().__init__("网络和 Internet", "Wi-Fi、以太网、VPN、代理和飞行模式。")
        self._build()

    def _build(self):
        # 状态卡
        c = self.add_card("连接状态")
        self.status_label = QLabel("检查中…")
        c.layout().addWidget(self.status_label)

        # Wi-Fi
        cw = self.add_card("Wi-Fi")
        self.wifi_toggle = ToggleSwitch(_wifi_enabled())
        self.wifi_toggle.toggled.connect(self._toggle_wifi)
        cw.add(SettingRow("Wi-Fi", "连接到无线网络 (需要 NetworkManager)",
                          trailing=self.wifi_toggle, icon="network"))
        refresh = QPushButton("刷新网络列表")
        refresh.clicked.connect(lambda: self.on_show())
        cw.layout().addWidget(refresh, alignment=Qt.AlignLeft)
        self.wifi_list_card = cw

        # 以太网
        ce = self.add_card("以太网")
        self.eth_label = QLabel("检查中…")
        ce.layout().addWidget(self.eth_label)

        # VPN
        cv = self.add_card("VPN")
        self.vpn_card = cv

        # 代理
        cp = self.add_card("代理")
        self.proxy_combo = QComboBox()
        for key, txt in (("none", "自动检测设置 (无代理)"),
                         ("manual", "手动设置代理")):
            self.proxy_combo.addItem(txt, key)
        self.proxy_combo.currentIndexChanged.connect(self._set_proxy)
        cp.add(SettingRow("代理设置", "配置 HTTP/HTTPS 代理 (GNOME 系统代理)",
                          trailing=self.proxy_combo, icon="network"))
        self.proxy_hint = QLabel("手动模式：通过 gsettings org.gnome.system.proxy 配置详细参数")
        self.proxy_hint.setObjectName("subText")
        self.proxy_hint.setWordWrap(True)
        cp.layout().addWidget(self.proxy_hint)

        # 飞行模式
        ca = self.add_card()
        self.air_toggle = ToggleSwitch(False)
        self.air_toggle.toggled.connect(self._toggle_airplane)
        ca.add(SettingRow("飞行模式", "关闭所有无线通信 (Wi-Fi/蓝牙)",
                          trailing=self.air_toggle, icon="network"))
        self.add_stretch()

    # ---------------------------------------------------------------- Wi-Fi
    def _toggle_wifi(self, on: bool):
        # nmcli 可由普通用户操作（经 polkit 授权），无需 pkexec 弹窗
        ok, _o, err = utils.run(["nmcli", "radio", "wifi", "on" if on else "off"],
                                timeout=5)
        if not ok:
            self.wifi_toggle.set_checked_silent(not on)
            info_box(self, "失败", err or "无法切换 Wi-Fi。")

    def _connect_wifi(self, ssid: str, secured: bool):
        pwd = ""
        if secured:
            dlg = WifiPasswordDialog(ssid, self)
            if not dlg.exec_():
                return
            pwd = dlg.pwd.text()
        if pwd:
            ok, _o, err = utils.run(["nmcli", "device", "wifi", "connect", ssid,
                                     "password", pwd], timeout=30)
        else:
            ok, _o, err = utils.run(["nmcli", "device", "wifi", "connect", ssid],
                                    timeout=30)
        if ok:
            info_box(self, "已连接", f"已连接到 {ssid}")
        else:
            info_box(self, "连接失败", err or "请检查密码后重试。")
        self.on_show()

    def _forget_wifi(self, name: str):
        if not confirm_box(self, "忘记网络", f"删除已保存的网络 {name}？"):
            return
        utils.run(["nmcli", "connection", "delete", name], timeout=10)
        self.on_show()

    def _toggle_vpn(self, name: str, active: bool):
        if active:
            utils.run(["nmcli", "connection", "down", name], timeout=20)
        else:
            utils.run(["nmcli", "connection", "up", name], timeout=30)
        self.on_show()

    def _set_proxy(self, idx):
        mode = self.proxy_combo.itemData(idx)
        utils.gset("org.gnome.system.proxy", "mode", mode)

    def _toggle_airplane(self, on: bool):
        """飞行模式：关闭/开启 Wi-Fi 与 WWAN 无线电（蓝牙单独在蓝牙页控制）"""
        ok, _o, err = utils.run(["nmcli", "radio", "all", "off" if on else "on"],
                                timeout=5)
        # 蓝牙用 rfkill 普通 try（多数系统允许普通用户软阻塞，失败不影响主功能）
        if on:
            utils.run(["rfkill", "block", "bluetooth"], timeout=5)
        if not ok:
            self.air_toggle.set_checked_silent(not on)
            info_box(self, "失败", err or "无法切换飞行模式。")
        self.on_show()

    # ---------------------------------------------------------------- 刷新
    def on_show(self):
        if not utils.have("nmcli"):
            self.status_label.setText("未检测到网络管理器 (NetworkManager)。"
                                      "请在应用商店或软件中心安装后使用。")
            return
        # 状态
        ok, out, _ = utils.run(["nmcli", "general", "status"], timeout=5)
        if ok:
            lines = out.splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                state = parts[0] if parts else "未知"
                self.status_label.setText(f"网络状态: {state}")
        # Wi-Fi (静默刷新，避免触发 _toggle_wifi)
        self.wifi_toggle.set_checked_silent(_wifi_enabled())
        self._rebuild_wifi()
        # 以太网
        ok, out, _ = utils.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE",
                                "device", "status"], timeout=5)
        eth = "未检测到以太网设备"
        if ok:
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "ethernet":
                    eth = f"{parts[0]} — {parts[2]}"
                    break
        self.eth_label.setText(eth)
        # VPN / 已知连接
        lay = self.vpn_card.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        conns = _known_connections()
        vpn_conns = [c for c in conns if "vpn" in c["type"].lower()
                     or "wireguard" in c["type"].lower()]
        for c in vpn_conns:
            active = c["device"] and c["device"] != "--"
            row = SettingRow(c["name"], c["type"], icon="network",
                             trailing=QPushButton("断开" if active else "连接"))
            row.findChildren(QPushButton)[0].clicked.connect(
                lambda _x, n=c["name"], a=active: self._toggle_vpn(n, a))
            lay.addWidget(row)
        if not vpn_conns:
            lay.addWidget(QLabel("没有已配置的 VPN 连接。可通过 nmcli 或桌面网络设置添加。"))
        # 代理回显
        mode = utils.gget("org.gnome.system.proxy", "mode", "none")
        i = self.proxy_combo.findData(mode)
        if i >= 0:
            self.proxy_combo.blockSignals(True)
            self.proxy_combo.setCurrentIndex(i)
            self.proxy_combo.blockSignals(False)

    def _rebuild_wifi(self):
        # 清除旧的 Wi-Fi 行（保留开关和刷新按钮，即前 2 个控件）
        lay = self.wifi_list_card.layout()
        while lay.count() > 2:
            item = lay.takeAt(lay.count() - 1)
            if item.widget():
                item.widget().deleteLater()
        if not _wifi_enabled():
            lay.addWidget(QLabel("Wi-Fi 已关闭。"))
            return
        seen = set()
        for in_use, ssid, signal, sec in _scan_wifi():
            if ssid in seen:
                continue
            seen.add(ssid)
            label = f"信号 {signal}%  ·  {'已连接' if in_use else ('受保护' if sec else '开放')}"
            btn = QPushButton("连接" if not in_use else "已连接")
            btn.setEnabled(not in_use)
            row = SettingRow(ssid, label, icon="network", trailing=btn)
            btn.clicked.connect(lambda _x, s=ssid, p=bool(sec): self._connect_wifi(s, p))
            lay.addWidget(row)
