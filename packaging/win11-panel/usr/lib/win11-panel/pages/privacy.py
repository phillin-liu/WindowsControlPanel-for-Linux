"""privacy.py — 隐私和安全性（对应 Win11 → 隐私和安全性）
位置服务 / 摄像头和麦克风 / 防火墙 (ufw/firewalld) / 杀毒 (clamav)。
"""
import os

from PyQt5.QtWidgets import QLabel, QPushButton

import utils
from widgets import BasePage, SettingRow, ToggleSwitch, Card, confirm_box, info_box


class PrivacyPage(BasePage):
    def __init__(self):
        super().__init__("隐私和安全性", "位置、摄像头、麦克风、防火墙和防病毒。")
        self._build()

    def _build(self):
        # 安全卡
        c = self.add_card("安全性")
        self.fw_toggle = ToggleSwitch()
        self.fw_toggle.toggled.connect(self._toggle_firewall)
        c.add(SettingRow("防火墙", "阻止未经授权的网络访问 (ufw/firewalld)",
                         trailing=self.fw_toggle, icon="privacy"))
        self.fw_note = QLabel("")
        self.fw_note.setObjectName("subText")
        c.layout().addWidget(self.fw_note)

        self.av_label = QLabel("检测中…")
        av_row = SettingRow("防病毒保护", "Windows Defender 的等价物 (ClamAV)",
                            icon="privacy")
        scan_btn = QPushButton("扫描主目录")
        scan_btn.clicked.connect(self._scan_virus)
        av_row.layout().addWidget(scan_btn)
        c.add(av_row)
        c.layout().addWidget(self.av_label)

        # 位置
        c2 = self.add_card("应用权限")
        loc = utils.gget("org.gnome.system.location", "enabled", "false") == "true"
        loc_toggle = ToggleSwitch(loc)
        loc_toggle.toggled.connect(
            lambda v: utils.gset("org.gnome.system.location", "enabled",
                                 "true" if v else "false"))
        c2.add(SettingRow("位置服务", "允许应用获取位置 (GNOME)",
                          trailing=loc_toggle, icon="privacy"))

        cam_status = self._cameras()
        c2.add(SettingRow("摄像头", cam_status or "未检测到摄像头设备", icon="privacy"))
        mic_status = self._mics()
        c2.add(SettingRow("麦克风", mic_status or "未检测到麦克风设备", icon="sound"))

        flat_note = QLabel("提示：Flatpak 应用具有完善的权限沙箱，可用 flatpak 命令管理：\n"
                           "flatpak permission-list — 查看应用权限\n"
                           "flatpak override --user --nosocket=wayland APP — 修改权限")
        flat_note.setObjectName("subText")
        flat_note.setWordWrap(True)
        c2.layout().addWidget(flat_note)

        # 密码/加密占位说明
        c3 = self.add_card("设备安全")
        c3.add(SettingRow("磁盘加密", "全盘加密需要在安装系统时启用 (LUKS)", icon="privacy"))
        c3.add(SettingRow("安全启动", "UEFI Secure Boot 状态: " + self._secure_boot(),
                          icon="privacy"))
        self.add_stretch()

    # ---------------------------------------------------------------- 工具
    def _cameras(self):
        if os.path.isdir("/dev"):
            cams = [f for f in os.listdir("/dev") if f.startswith("video")]
            if cams:
                return f"检测到 {len(cams)} 个摄像头设备 ({', '.join(cams[:4])})"
        ok, out, _ = utils.run(["lsusb"], timeout=5)
        if ok and "camera" in out.lower():
            return "检测到 USB 摄像头"
        return ""

    def _mics(self):
        ok, out, _ = utils.run(["arecord", "-l"], timeout=5)
        if ok and out.strip():
            count = out.count("card ")
            return f"检测到 {count} 个录音设备"
        return ""

    def _secure_boot(self) -> str:
        path = "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
        data = utils.read_text(path)
        if data:
            return "启用" if data.strip()[-1:] == "\x01" else "未启用"
        # od 方式读取最后一个字节
        ok, out, _ = utils.run(["od", "-An", "-tu1", "-j5", path], timeout=5)
        if ok and out.strip():
            return "启用" if out.strip().split()[-1] == "1" else "未启用"
        return "不可用 (BIOS 或非 EFI)"

    def _toggle_firewall(self, on: bool):
        if utils.have("ufw"):
            if not confirm_box(self, "防火墙",
                               f"{'启用' if on else '禁用'} ufw 防火墙？"):
                self.fw_toggle.setChecked(not on, animate=False)
                return
            ok, _o, err = utils.run_root(["ufw", "enable" if on else "disable"])
            self.fw_note.setText("" if ok else err)
        elif utils.have("firewall-cmd"):
            ok, _o, err = utils.run_root(["systemctl",
                                          "start" if on else "stop", "firewalld"])
            if on:
                utils.run_root(["firewall-cmd", "--add-service=ssh", "--permanent"])
            self.fw_note.setText("" if ok else err)
        else:
            info_box(self, "提示", "未安装防火墙工具。推荐: sudo apt install gufw")
            self.fw_toggle.setChecked(False, animate=False)

    def _scan_virus(self):
        if not utils.have("clamscan"):
            info_box(self, "提示", "未安装 ClamAV: sudo apt install clamav")
            return
        self.av_label.setText("正在扫描主目录，请稍候…")
        ok, out, _ = utils.run(["clamscan", "-r", "--quiet",
                                os.path.expanduser("~")], timeout=3600)
        if ok:
            self.av_label.setText("扫描完成，未发现威胁。")
        else:
            self.av_label.setText(f"扫描发现问题或失败:\n{out[:500]}")

    def on_show(self):
        # 防火墙状态
        active = False
        if utils.have("ufw"):
            ok, out, _ = utils.run_root(["ufw", "status"])
            if not ok:
                ok, out, _ = utils.run(["systemctl", "is-active", "ufw"], timeout=5)
                active = ok and out.strip() == "active"
            else:
                active = out.startswith("Status: active") or "激活" in out
        elif utils.have("firewall-cmd"):
            ok, out, _ = utils.run(["firewall-cmd", "--state"], timeout=5)
            active = ok and out.strip() == "running"
        self.fw_toggle.setChecked(active, animate=False)
        # 杀毒状态
        if utils.have("clamscan"):
            ok, _o, _e = utils.run(["systemctl", "is-active", "clamav-daemon"],
                                   timeout=5)
            self.av_label.setText("ClamAV 已安装 · 守护进程: " +
                                  ("运行中" if ok and _o.strip() == "active" else "未运行"))
        else:
            self.av_label.setText("未安装 ClamAV。Linux 桌面环境下通常无需常驻杀毒。")
