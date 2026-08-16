"""privacy.py — 隐私和安全性（对应 Win11 → 隐私和安全性）
位置服务 / 摄像头和麦克风 / 防火墙 (ufw/firewalld) / 杀毒 (clamav)。
"""
import os
import time

from PyQt5.QtWidgets import (QLabel, QPushButton, QDialog, QDialogButtonBox,
                             QVBoxLayout, QHBoxLayout, QRadioButton,
                             QLineEdit, QFileDialog)

import utils
from utils import AsyncCommand
from widgets import BasePage, SettingRow, ToggleSwitch, confirm_box, info_box


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
        av_row = SettingRow("防病毒保护", "防病毒软件 (ClamAV)",
                            icon="privacy")
        self.scan_btn = QPushButton("扫描主目录")
        self.scan_btn.clicked.connect(self._scan_virus)
        av_row.layout().addWidget(self.scan_btn)
        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.clicked.connect(self._stop_scan)
        av_row.layout().addWidget(self.stop_btn)
        c.add(av_row)
        self.av_label.setWordWrap(True)
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

        flat_note = QLabel("提示：Flatpak 应用具有完善的权限沙箱，"
                           "可在「管理工具」中查看应用列表，"
                           "应用卸载请在「程序」类别中操作。")
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
                # 用户取消确认框：静默回滚开关，不触发本函数
                self.fw_toggle.set_checked_silent(not on)
                return
            ok, _o, err = utils.run_root(["ufw", "enable" if on else "disable"])
            if ok:
                self.fw_note.setText("")
            else:
                # 认证被取消或命令失败：回滚开关并提示
                self.fw_toggle.set_checked_silent(not on)
                self.fw_note.setText(err or "操作失败")
        elif utils.have("firewall-cmd"):
            ok, _o, err = utils.run_root(["systemctl",
                                          "start" if on else "stop", "firewalld"])
            if ok and on:
                utils.run_root(["firewall-cmd", "--add-service=ssh", "--permanent"])
            if ok:
                self.fw_note.setText("")
            else:
                self.fw_toggle.set_checked_silent(not on)
                self.fw_note.setText(err or "操作失败")
        else:
            info_box(self, "提示", "未安装防火墙工具，推荐安装 gufw（可在应用商店搜索安装）。")
            self.fw_toggle.set_checked_silent(False)

    def _scan_virus(self):
        if not utils.have("clamscan"):
            info_box(self, "提示", "未安装防病毒软件，推荐安装 ClamAV（可在应用商店搜索安装）。")
            return
        ok_status, _, _ = utils.run(["clamscan", "--version"], timeout=10)
        if not ok_status:
            self.av_label.setText("clamscan 无法运行。")
            return
        # 1) 让用户选择扫描范围
        dlg = QDialog(self)
        dlg.setWindowTitle("选择扫描范围")
        dlg.setMinimumWidth(380)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("为了避免扫描时间过长，请选择扫描范围："))
        home = os.path.expanduser("~")
        # 默认扫描常用目录 (大多数用户的高风险文件都在这)
        docs = os.path.join(home, "Documents")
        downloads = os.path.join(home, "Downloads")
        desktop = os.path.join(home, "Desktop")
        targets = [d for d in (downloads, desktop, docs) if os.path.isdir(d)]
        rb1 = QRadioButton(f"常用目录 (推荐)\n  扫描: {', '.join(targets) or '无可用目录'}")
        rb1.setChecked(True)
        rb2 = QRadioButton("完整主目录 (可能耗时数小时)")
        rb3 = QRadioButton("自定义路径…")
        v.addWidget(rb1)
        v.addWidget(rb2)
        v.addWidget(rb3)
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("/path/to/scan")
        path_edit.setEnabled(False)
        browse_btn = QPushButton("浏览…")
        browse_btn.setEnabled(False)
        browse_btn.clicked.connect(
            lambda: self._browse_directory(path_edit))
        path_row = QHBoxLayout()
        path_row.addWidget(path_edit, 1)
        path_row.addWidget(browse_btn)
        v.addLayout(path_row)
        rb3.toggled.connect(lambda on: (path_edit.setEnabled(on),
                                        browse_btn.setEnabled(on)))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not dlg.exec_():
            return
        if rb1.isChecked():
            scan_paths = targets
        elif rb2.isChecked():
            scan_paths = [home]
        else:
            p = path_edit.text().strip()
            if not p or not os.path.isdir(p):
                info_box(self, "提示", "路径无效或不存在。")
                return
            scan_paths = [p]
        if not scan_paths:
            info_box(self, "提示", "没有可扫描的目录。")
            return
        # 2) 病毒库缺失时先异步更新（图形授权框提权，界面不卡顿）
        import glob as _g
        self._scan_paths = scan_paths
        self._scan_t0 = time.time()
        self._scan_count = 0
        self._scan_last = ""
        self._scan_stopping = False
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        db_files = _g.glob("/var/lib/clamav/*.cvd") + _g.glob("/var/lib/clamav/*.cld")
        if not db_files:
            self._scan_mode = "freshclam"
            self._scan_out = ""
            self.av_label.setText("病毒库未初始化，正在更新病毒库（可能需要几分钟）…")
            self._scan_cmd = AsyncCommand(self)
            self._scan_cmd.output.connect(self._on_scan_out)
            self._scan_cmd.finished.connect(self._on_scan_done)
            self._scan_cmd.failed.connect(self._on_scan_fail)
            self._scan_cmd.start(["freshclam"], as_root=True)
        else:
            self._start_clamscan()

    def _start_clamscan(self):
        """构建并启动扫描。优先 clamd 守护进程（病毒库常驻内存、启动快），否则 clamscan。"""
        self._scan_mode = "clamscan"
        self._scan_t0 = time.time()
        self._scan_count = 0
        self._scan_last = ""
        self._scan_out = ""
        scan_paths = self._scan_paths
        self.av_label.setText("正在启动扫描引擎（首次加载病毒库约需半分钟，请耐心等待）…")
        clamd_ctl = "/run/clamav/clamd.ctl"
        if utils.have("clamdscan") and (os.path.exists(clamd_ctl) or
                                        os.path.exists("/var/run/clamav/clamd.ctl")):
            # clamd 已在内存中加载病毒库, multiscan 可多线程并行扫描
            cmd = ["clamdscan", "--fdpass", "--multiscan"] + scan_paths
        else:
            # 不加 --infected, 保留逐文件输出以实时显示进度
            cmd = ["clamscan", "-r"]
            # 排除体积大且风险低的缓存/开发目录, 避免扫描时间过长
            for d in (".cache", "snap", ".local/share/Trash", ".npm", ".cargo",
                      "go/pkg", ".rustup", ".git", "node_modules", ".m2",
                      ".gradle", ".vscode", "__pycache__", ".conda",
                      ".android", ".thumbnails", ".venv", "venv"):
                cmd.extend(["--exclude-dir", d])
            # 跳过超大文件 (真实恶意软件体积通常很小)
            cmd.extend(["--max-filesize=100M", "--max-scansize=150M",
                        "--max-recursion=10"])
            cmd.extend(scan_paths)
        self._scan_cmd = AsyncCommand(self)
        self._scan_cmd.output.connect(self._on_scan_out)
        self._scan_cmd.finished.connect(self._on_scan_done)
        self._scan_cmd.failed.connect(self._on_scan_fail)
        self._scan_cmd.start(cmd, as_root=False)

    def _browse_directory(self, edit: QLineEdit):
        """打开图形化目录选取窗口，选中后填入输入框"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择扫描目录", os.path.expanduser("~"))
        if directory:
            edit.setText(directory)

    def _on_scan_out(self, text: str):
        # 基于新增文本累计进度, 不受历史截断影响; 忽略命令回显行
        for line in text.splitlines():
            if line.endswith(": OK") or " FOUND" in line:
                self._scan_count += 1
                self._scan_last = line
        self._scan_out += text
        lines = self._scan_out.splitlines()
        if len(lines) > 300:
            self._scan_out = "\n".join(lines[-300:])
        if getattr(self, "_scan_mode", "") == "freshclam":
            last = next((l for l in reversed(lines)
                         if l.strip() and not l.startswith(("$ ", "[完成]"))), "")
            self.av_label.setText(f"正在更新病毒库，请稍候…\n{last[-90:]}")
            return
        elapsed = max(0, int(time.time() - self._scan_t0))
        mm, ss = divmod(elapsed, 60)
        if self._scan_count == 0:
            self.av_label.setText(
                f"正在启动扫描引擎并加载病毒库… 用时 {mm:02d}:{ss:02d}\n"
                "（病毒库加载约需半分钟，属正常现象，可随时停止）")
        else:
            cur = self._scan_last.rsplit(": ", 1)[0] if self._scan_last else ""
            self.av_label.setText(
                f"扫描进行中… 已扫描 {self._scan_count} 个文件 | 用时 {mm:02d}:{ss:02d}\n"
                f"当前: {cur}")

    def _on_scan_done(self, ok: bool, code: int):
        if getattr(self, "_scan_stopping", False):
            return  # 用户主动停止, 由 _stop_scan 负责收尾
        if getattr(self, "_scan_mode", "") == "freshclam":
            if not ok:
                self.av_label.setText(
                    "病毒库更新未完成（可能已取消授权）。\n"
                    "请再次点击「扫描主目录」重试。")
                self.scan_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self._scan_cmd = None
                return
            self._start_clamscan()
            return
        import re as _re
        # clamscan 退出码: 0=干净, 1=发现感染, 2=错误
        m = _re.search(r"Infected files:\s*(\d+)", self._scan_out)
        infected = int(m.group(1)) if m else 0
        m2 = _re.search(r"Scanned files:\s*(\d+)", self._scan_out)
        total = int(m2.group(1)) if m2 else getattr(self, "_scan_count", 0)
        combined = self._scan_out
        elapsed = max(1, int(time.time() - self._scan_t0))
        if "No supported database files" in combined or "LibClamAV Error" in combined:
            self.av_label.setText(
                "病毒库未初始化，请点击「扫描主目录」重试，\n"
                "系统会在授权后自动更新病毒库 (需要管理员密码)。")
        elif infected > 0:
            found = [l for l in combined.splitlines() if " FOUND" in l][-8:]
            self.av_label.setText(
                f"扫描完成，发现 {infected} 个可疑文件"
                f"（共扫描 {total} 个文件，用时 {elapsed} 秒）。\n"
                + "\n".join(found))
        elif ok:
            self.av_label.setText(
                f"扫描完成，未发现威胁。\n共扫描 {total} 个文件，用时 {elapsed} 秒。")
        else:
            self.av_label.setText(f"扫描异常 (退出码 {code})。")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._scan_cmd = None

    def _on_scan_fail(self, err: str):
        self.av_label.setText(f"扫描启动失败: {err}")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _stop_scan(self):
        if not getattr(self, "_scan_cmd", None):
            return
        self._scan_stopping = True
        try:
            if self._scan_cmd._proc and self._scan_cmd._proc.state() != 0:
                self._scan_cmd._proc.kill()
                self._scan_cmd._proc.waitForFinished(3000)
        except Exception:
            pass
        self._scan_stopping = False
        self.av_label.setText("扫描已停止。")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._scan_cmd = None

    def on_show(self):
        # 防火墙状态 (全部免 root 查询，避免每次进入页面都弹认证框)
        active = False
        if utils.have("ufw"):
            ok, out, _ = utils.run(["systemctl", "is-active", "ufw"], timeout=5)
            if ok and out.strip() == "active":
                active = True
            else:
                # ufw status 需要 root；非 root 下尝试，失败则视为未知（保持当前显示）
                ok2, out2, _ = utils.run(["ufw", "status"], timeout=5)
                active = ok2 and (out2.startswith("Status: active") or "激活" in out2)
        elif utils.have("firewall-cmd"):
            ok, out, _ = utils.run(["firewall-cmd", "--state"], timeout=5)
            active = ok and out.strip() == "running"
        # 静默刷新开关状态，不触发 _toggle_firewall
        self.fw_toggle.set_checked_silent(active)
        # 杀毒状态
        if utils.have("clamscan"):
            ok, _o, _e = utils.run(["systemctl", "is-active", "clamav-daemon"],
                                   timeout=5)
            self.av_label.setText("ClamAV 已安装 · 守护进程: " +
                                  ("运行中" if ok and _o.strip() == "active" else "未运行"))
        else:
            self.av_label.setText("未安装 ClamAV。Linux 桌面环境下通常无需常驻杀毒。")
