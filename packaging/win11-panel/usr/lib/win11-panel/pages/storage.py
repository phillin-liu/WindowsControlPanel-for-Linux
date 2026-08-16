"""storage.py — 存储设置（对应 Win11 → 系统 → 存储）
基于 df / lsblk / apt 缓存 / journalctl。
"""
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QPushButton, QHBoxLayout, QProgressBar, QWidget)

import utils
from widgets import BasePage, SettingRow, confirm_box, info_box


def _df_rows():
    ok, out, _ = utils.run(["df", "-h", "--output=source,fstype,size,used,avail,pcent,target",
                            "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs"], timeout=10)
    rows = []
    if not ok:
        return rows
    lines = out.splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 7:
            rows.append({"source": parts[0], "fstype": parts[1], "size": parts[2],
                         "used": parts[3], "avail": parts[4], "pcent": parts[5],
                         "target": parts[6]})
    return rows


class StoragePage(BasePage):
    def __init__(self):
        super().__init__("存储", "存储空间、驱动器和清理建议。")
        self._build()

    def _build(self):
        c = self.add_card("存储使用情况")
        self._disk_area = c.layout()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(lambda: self.on_show())
        c.layout().addWidget(refresh)

        c2 = self.add_card("清理建议")
        self.cache_row = SettingRow("应用包缓存 (apt)", "下载的 .deb 安装包缓存",
                                    trailing=QPushButton("清理"), icon="storage")
        self.cache_row.findChildren(QPushButton)[0].clicked.connect(self._clean_apt)
        c2.add(self.cache_row)
        c2.add_divider()
        journal_btn = QPushButton("清理")
        journal_btn.clicked.connect(self._clean_journal)
        self.journal_row = SettingRow("系统日志 (journal)", "systemd 日志占用空间",
                                      trailing=journal_btn, icon="storage")
        c2.add(self.journal_row)
        c2.add_divider()
        trash_btn = QPushButton("清空")
        trash_btn.clicked.connect(self._clean_trash)
        self.trash_row = SettingRow("回收站", "已删除的文件",
                                    trailing=trash_btn, icon="storage")
        c2.add(self.trash_row)

        c3 = self.add_card("驱动器")
        ok, out, _ = utils.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL"], timeout=5)
        if ok:
            txt = QLabel(out)
            txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
            txt.setStyleSheet("font-family: monospace;")
            c3.layout().addWidget(txt)
        else:
            c3.layout().addWidget(QLabel("无法读取 lsblk 输出。"))
        self.add_stretch()

    def _clean_apt(self):
        if not confirm_box(self, "清理 apt 缓存", "将执行 apt-get clean，删除已下载的安装包缓存。"):
            return
        ok, _o, err = utils.run_root(["apt-get", "clean"])
        if ok:
            info_box(self, "完成", "apt 缓存已清理。")
            self.on_show()
        else:
            info_box(self, "失败", err)

    def _clean_journal(self):
        if not confirm_box(self, "清理系统日志", "将保留最近 100MB 日志，更早的将被删除。"):
            return
        ok, _o, err = utils.run_root(["journalctl", "--vacuum-size=100M"])
        if ok:
            info_box(self, "完成", "日志已清理。")
            self.on_show()
        else:
            info_box(self, "失败", err)

    def _clean_trash(self):
        import os
        trash = os.path.expanduser("~/.local/share/Trash")
        if not os.path.isdir(trash):
            info_box(self, "提示", "回收站为空。")
            return
        if not confirm_box(self, "清空回收站", "永久删除回收站中的所有文件？"):
            return
        ok, _o, err = utils.run(["rm", "-rf", trash], timeout=30)
        if ok:
            info_box(self, "完成", "回收站已清空。")
            self.on_show()

    def on_show(self):
        # 磁盘使用进度条
        while self._disk_area.count() > 1:
            item = self._disk_area.takeAt(self._disk_area.count() - 1)
            if item.widget():
                item.widget().deleteLater()
        for r in _df_rows():
            row = QHBoxLayout()
            info = QLabel(f"{r['target']}  ·  {r['source']} ({r['fstype']})")
            info.setMinimumWidth(300)
            bar = QProgressBar()
            pct = int(r["pcent"].rstrip("%"))
            bar.setValue(pct)
            if pct > 90:
                bar.setProperty("invertedColor", True)
            txt = QLabel(f"{r['used']} / {r['size']} ({r['pcent']})")
            row.addWidget(info, 1)
            row.addWidget(bar, 1)
            row.addWidget(txt)
            holder = _wrap(row)
            self._disk_area.addWidget(holder)
        # 缓存大小
        btn = self.cache_row.findChildren(QPushButton)[0]
        apt_size = utils.dir_size("/var/cache/apt/archives") if os.path.isdir("/var/cache/apt/archives") else 0
        btn.setText(f"清理 ({utils.human_size(apt_size)})")
        try:
            btn.clicked.disconnect()
        except TypeError:
            pass
        btn.clicked.connect(self._clean_apt)
        ok, out, _ = utils.run(["journalctl", "--disk-usage"], timeout=5)
        if ok:
            m = re.search(r"([\d.]+[KMG]?)\s*archived", out)
            self.journal_row.findChildren(QLabel)[1].setText(
                f"systemd 日志占用 ({m.group(1)})" if m else out)
        trash_size = utils.dir_size(os.path.expanduser("~/.local/share/Trash"))
        if trash_size:
            self.trash_row.findChildren(QLabel)[1].setText(
                f"已删除的文件 ({utils.human_size(trash_size)})")


def _wrap(layout):
    w = QWidget()
    w.setLayout(layout)
    return w
