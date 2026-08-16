"""devices.py — 设备管理器（对应经典控制面板 → 设备管理器）
基于 lspci / lsusb / lsblk / /proc 组建设备树，只读 + 驱动详情。
"""
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
                             QHBoxLayout, QPlainTextEdit, QHeaderView)

import utils
from widgets import BasePage, Card

PCI_GROUPS = [
    ("显示适配器", ("VGA compatible controller", "3D controller", "Display controller")),
    ("网络适配器", ("Ethernet controller", "Network controller", "Wireless")),
    ("存储控制器", ("SATA controller", "IDE interface", "NVMe", "Mass storage",
                 "RAID bus controller", "SAS controller")),
    ("音频输入和输出", ("Audio device", "Multimedia audio controller")),
    ("通用串行总线控制器", ("USB controller",)),
    ("系统设备", ("Host bridge", "PCI bridge", "ISA bridge", "SMBus",
               "Communication controller", "System peripheral")),
]


def _lspci_items():
    ok, out, _ = utils.run(["lspci"], timeout=5)
    items = []
    if ok:
        for line in out.splitlines():
            m = re.match(r"([0-9a-f:\.]+)\s+(.+?):\s+(.+)", line)
            if m:
                items.append({"addr": m.group(1), "cls": m.group(2),
                              "desc": m.group(3)})
    return items


class DevicesPage(BasePage):
    def __init__(self):
        super().__init__("设备管理器", "查看和更新计算机的硬件信息与驱动。")
        self._build()

    def _build(self):
        card = self.add_card()
        h = QHBoxLayout()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(lambda: self.on_show())
        h.addWidget(refresh)
        h.addStretch(1)
        card.layout().addLayout(h)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["设备", "总线地址"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._show_detail)
        card.layout().addWidget(self.tree)

        c2 = self.add_card("设备详情")
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(160)
        c2.layout().addWidget(self.detail)
        hint = QLabel("提示：设备管理器为只读视图。驱动管理请使用系统包管理器 "
                      "(apt / 内核模块) 或 GNOME「附加驱动」。")
        hint.setObjectName("subText")
        hint.setWordWrap(True)
        c2.layout().addWidget(hint)
        self.add_stretch()

    def _add_group(self, parent, name, devices):
        if not devices:
            return
        g = QTreeWidgetItem(parent, [name, ""])
        g.setFlags(Qt.ItemIsEnabled)
        for d in devices:
            child = QTreeWidgetItem(g, [d["desc"], d.get("addr", "")])
            child.setData(0, Qt.UserRole, d)
        g.setExpanded(True)

    def on_show(self):
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, [utils.hostname(), ""])
        root.setFlags(Qt.ItemIsEnabled)
        font = root.font(0)
        font.setBold(True)
        root.setFont(0, font)

        # PCI 分组
        pci = _lspci_items()
        for gname, classes in PCI_GROUPS:
            devs = [d for d in pci
                    if any(c.lower() in d["cls"].lower() for c in classes)]
            self._add_group(root, gname, devs)

        # 磁盘驱动器
        ok, out, _ = utils.run(["lsblk", "-dnpo", "NAME,MODEL,SIZE,TYPE"], timeout=5)
        disks = []
        if ok:
            for line in out.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4 and parts[3].strip() == "disk":
                    disks.append({"desc": f"{parts[1] or '磁盘'} ({parts[2]})",
                                  "addr": parts[0]})
        self._add_group(root, "磁盘驱动器", disks)

        # 处理器
        cpu = utils.cpu_model()
        self._add_group(root, "处理器",
                        [{"desc": f"CPU #{i} — {cpu}", "addr": "/proc/cpuinfo"}
                         for i in range(min(utils.cpu_cores(), 32))])

        # 人体学输入设备
        inputs = []
        for name in ("js", "event"):
            for d in os.listdir(f"/dev/input/{name}") if os.path.isdir(f"/dev/input/{name}") else []:
                inputs.append({"desc": f"{name}/{d}", "addr": f"/dev/input/{name}/{d}"})
        self._add_group(root, "人体学输入设备", inputs[:12])

        root.setExpanded(True)
        self.tree.resizeColumnToContents(0)

    def _show_detail(self):
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole)
        if not data:
            self.detail.setPlainText(items[0].text(0))
            return
        if str(data.get("addr", "")).startswith("/") or ":" not in data.get("addr", ""):
            self.detail.setPlainText(f"设备: {data['desc']}\n位置: {data.get('addr', '')}")
            return
        ok, out, _ = utils.run(["lspci", "-k", "-s", data["addr"]], timeout=5)
        if ok:
            self.detail.setPlainText(out)
        else:
            self.detail.setPlainText(f"设备: {data['desc']}\n{data['addr']}")
