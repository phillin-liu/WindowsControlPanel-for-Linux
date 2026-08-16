"""update.py — 软件更新（对应 Win11 → Windows 更新）
基于 apt：检查更新 / 安装更新 / 更新历史。
"""
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QLabel, QPushButton, QPlainTextEdit, QVBoxLayout,
                             QWidget, QHBoxLayout)

import utils
from widgets import BasePage, SettingRow, confirm_box, info_box
from utils import AsyncCommand

HISTORY_LOG = "/var/log/apt/history.log"


def _upgradable():
    """返回可升级包 [(名称, 版本)]"""
    ok, out, _ = utils.run(["apt", "list", "--upgradable", "-a"], timeout=30)
    pkgs = []
    if ok:
        for line in out.splitlines():
            if "/" not in line or "正在列表" in line or "Listing" in line:
                continue
            name_ver = line.split()[0]
            m = re.search(r"(\S+)/\S+\s+(\S+)", line)
            if m:
                pkgs.append((m.group(1), m.group(2)))
    return pkgs


class UpdatePage(BasePage):
    def __init__(self):
        super().__init__("软件更新", "检查并安装系统更新 (apt)。")
        self._cmd = None
        self._build()

    def _build(self):
        c = self.add_card("更新状态")
        h = QHBoxLayout()
        self.status_label = QLabel("尚未检查更新")
        self.status_label.setObjectName("bigValue")
        check_btn = QPushButton("检查更新")
        check_btn.setObjectName("accentBtn")
        check_btn.clicked.connect(self._check)
        self.install_btn = QPushButton("全部安装")
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self._install)
        h.addWidget(self.status_label, 1)
        h.addWidget(check_btn)
        h.addWidget(self.install_btn)
        wrap = QWidget()
        wrap.setLayout(h)
        c.layout().addWidget(wrap)

        c2 = self.add_card("可更新的包")
        self.pkg_card = c2
        self.pkg_card.layout().addWidget(QLabel("点击“检查更新”查看可用更新。"))

        c3 = self.add_card("更新输出")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(240)
        self.log.setPlaceholderText("apt 输出将显示在这里…")
        c3.layout().addWidget(self.log)

        c4 = self.add_card("更新历史")
        self.history_label = QLabel("")
        self.history_label.setObjectName("subText")
        self.history_label.setWordWrap(True)
        self.history_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        c4.layout().addWidget(self.history_label)

        self.add_stretch()

    # ---------------------------------------------------------------- 操作
    def _check(self):
        self.status_label.setText("正在检查更新 (需要管理员授权)…")
        self.log.clear()
        self._cmd = AsyncCommand(self)
        self._cmd.output.connect(self._append_log)
        self._cmd.failed.connect(lambda e: self._append_log(f"[错误] {e}\n"))
        self._cmd.finished.connect(lambda _ok, _c: self._list_upgradable())
        self._cmd.start(["apt-get", "update"], as_root=True)

    def _list_upgradable(self):
        self.status_label.setText("正在获取可更新包列表…")
        lay = self.pkg_card.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        pkgs = _upgradable()
        if pkgs:
            self.status_label.setText(f"有 {len(pkgs)} 个可更新的包")
            self.install_btn.setEnabled(True)
            for name, ver in pkgs[:100]:
                lay.addWidget(SettingRow(name, f"新版本: {ver}", icon="update"))
            if len(pkgs) > 100:
                lay.addWidget(QLabel(f"… 以及其他 {len(pkgs) - 100} 个包"))
        else:
            self.status_label.setText("系统已是最新 ✓")
            self.install_btn.setEnabled(False)
            lay.addWidget(QLabel("没有可用更新。"))
        self._refresh_history()

    def _install(self):
        if not confirm_box(self, "安装更新",
                           "将执行 apt-get upgrade --yes 安装全部更新，确定吗？"):
            return
        self.install_btn.setEnabled(False)
        self._append_log("\n=== 开始安装更新 ===\n")
        self._cmd = AsyncCommand(self)
        self._cmd.output.connect(self._append_log)
        self._cmd.finished.connect(self._after_install)
        self._cmd.start(["apt-get", "upgrade", "--yes"], as_root=True)

    def _after_install(self, ok, _code):
        self._append_log("\n=== 更新完成 ===\n" if ok else "\n=== 更新失败 ===\n")
        self._list_upgradable()

    def _append_log(self, text: str):
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.End)

    def _refresh_history(self):
        text = utils.read_text(HISTORY_LOG)
        if not text:
            self.history_label.setText("暂无更新历史 (/var/log/apt/history.log)。")
            return
        blocks = text.strip().split("\n\n")[-5:]
        rows = []
        for b in reversed(blocks):
            start = re.search(r"Start-Date: (.+)", b)
            acts = re.search(r"Upgrade: (.+)", b)
            if start:
                desc = acts.group(1)[:120] if acts else "(索引更新)"
                rows.append(f"{start.group(1)}  {desc}")
        self.history_label.setText("\n".join(rows) if rows else "暂无记录")

    def on_show(self):
        self._refresh_history()
