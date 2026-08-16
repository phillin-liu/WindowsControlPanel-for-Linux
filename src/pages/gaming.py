"""gaming.py — 游戏（对应 Win11 → 游戏）
游戏模式 (电源配置) / 游戏平台检测 / 手柄 / 截图工具。
"""
import os

from PyQt5.QtWidgets import QLabel, QPushButton

import utils
from widgets import BasePage, SettingRow, ToggleSwitch, info_box

PLATFORMS = [
    ("Steam", ["steam", "steam-native"]),
    ("Lutris", ["lutris"]),
    ("Heroic Games Launcher", ["heroic"]),
    ("Bottles", ["bottles"]),
    ("Wine", ["wine"]),
    ("PlayOnLinux", ["playonlinux"]),
    ("RetroArch", ["retroarch"]),
    ("DOSBox", ["dosbox", "dosbox-x"]),
]


class GamingPage(BasePage):
    def __init__(self):
        super().__init__("游戏", "游戏模式、游戏平台和控制器。")
        self._build()

    def _build(self):
        c = self.add_card("游戏模式")
        self.gm_toggle = ToggleSwitch(self._game_mode_on())
        self.gm_toggle.toggled.connect(self._toggle_gm)
        c.add(SettingRow("游戏模式", "优化电脑以获得更好的游戏性能 (切换到性能电源模式)",
                         trailing=self.gm_toggle, icon="gaming"))
        self.gm_note = QLabel("")
        self.gm_note.setObjectName("subText")
        c.layout().addWidget(self.gm_note)

        c2 = self.add_card("已安装的游戏平台")
        self._plat_card = c2

        c3 = self.add_card("控制器")
        self._ctrl_label = QLabel("检测中…")
        c3.layout().addWidget(self._ctrl_label)

        c4 = self.add_card("截图工具")
        self._shot_label = QLabel("检测中…")
        c4.layout().addWidget(self._shot_label)

        tip = QLabel("说明：Linux 无 Xbox Game Bar / HDR 等专有功能；此处提供等价功能："
                     "游戏模式=高性能电源档位，截图可用系统工具 (flameshot 等)。")
        tip.setObjectName("subText")
        tip.setWordWrap(True)
        self.body.addWidget(tip)
        self.add_stretch()

    def _game_mode_on(self) -> bool:
        if utils.have("powerprofilesctl"):
            ok, out, _ = utils.run(["powerprofilesctl", "get"], timeout=5)
            return ok and out.strip() == "performance"
        gov = utils.read_first_line(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        return gov == "performance"

    def _toggle_gm(self, on: bool):
        if utils.have("powerprofilesctl"):
            ok, _o, err = utils.run(["powerprofilesctl", "set",
                                     "performance" if on else "balanced"], timeout=5)
            if not ok:
                self.gm_toggle.set_checked_silent(not on)
            self.gm_note.setText("" if ok else err)
        else:
            gov = "performance" if on else "schedutil"
            ok, _o, err = utils.run_root(
                ["sh", "-c",
                 f"echo {gov} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null"])
            if not ok:
                # 认证被取消或失败：回滚开关
                self.gm_toggle.set_checked_silent(not on)
            self.gm_note.setText("" if ok else f"需要 root 权限：{err}")

    def _detect_platforms(self):
        lay = self._plat_card.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        found_any = False
        for name, cmds in PLATFORMS:
            installed = next((c for c in cmds if utils.have(c)), None)
            if not installed:
                # 再查 .desktop
                for d in utils.desktop_apps_dirs():
                    if os.path.isdir(d) and any(
                            f.startswith(cmds[0].lower()) and f.endswith(".desktop")
                            for f in os.listdir(d)):
                        installed = cmds[0]
                        break
            if installed:
                found_any = True
                row = SettingRow(name, f"已安装 ({installed})", icon="gaming",
                                 selectable=installed in ("steam", "lutris", "heroic"))
                row.clicked.connect(lambda c=installed: self._launch(c))
                lay.addWidget(row)
        if not found_any:
            lay.addWidget(QLabel("未检测到游戏平台。"
                                 "可在应用商店安装 Steam，"
                                 "或安装 lutris/wine 运行游戏。"))

    def _launch(self, cmd: str):
        import subprocess
        subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_show(self):
        # 静默刷新，避免触发 _toggle_gm 造成认证弹窗
        self.gm_toggle.set_checked_silent(self._game_mode_on())
        self._detect_platforms()
        # 控制器
        ctrl = []
        if os.path.isdir("/dev/input"):
            ctrl = [f for f in os.listdir("/dev/input")
                    if f.startswith("js")]
        ok, out, _ = utils.run(["lsusb"], timeout=5)
        pads = ""
        if ok:
            import re
            for line in out.splitlines():
                if re.search(r"Gamepad|Joystick|Controller|Xbox|PlayStation", line, re.I):
                    pads = line.split(":", 2)[-1].strip()
        if ctrl:
            self._ctrl_label.setText(f"检测到手柄设备: {', '.join(ctrl)}" +
                                     (f" · {pads}" if pads else ""))
        elif pads:
            self._ctrl_label.setText(f"检测到: {pads}")
        else:
            self._ctrl_label.setText("未检测到控制器。")
        # 截图
        shots = [t for t in ("flameshot", "gnome-screenshot", "spectacle", "scrot", "grim")
                 if utils.have(t)]
        self._shot_label.setText(
            f"可用截图工具: {', '.join(shots)}" if shots else
            "未安装截图工具，推荐安装 flameshot（可在应用商店搜索安装）")
