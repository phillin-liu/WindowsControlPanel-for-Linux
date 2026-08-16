"""apps.py — 应用管理（对应 Win11 → 应用）
已安装应用 / 卸载 (apt/flatpak) / 启动 / 开机自启。
"""
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QLabel, QPushButton, QLineEdit, QHBoxLayout,
                             QVBoxLayout, QDialog, QDialogButtonBox,
                             QListWidget, QListWidgetItem, QAbstractItemView)

import utils
from widgets import BasePage, SettingRow, Card, confirm_box, info_box

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")


def _package_of_desktop(path: str) -> str:
    """通过 dpkg -S 找到提供该 .desktop 的包"""
    ok, out, _ = utils.run(["dpkg", "-S", path], timeout=10)
    if ok and ":" in out:
        return out.split(":")[0]
    return ""


class AppDetailDialog(QDialog):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle(entry["title"])
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        icon = QLabel()
        icon.setPixmap(QIcon.fromTheme(entry["icon"],
                                       QIcon.fromTheme("application-x-executable"))
                       .pixmap(48, 48))
        name = QLabel(entry["title"])
        name.setStyleSheet("font-size:18px;font-weight:600;")
        desc = QLabel(entry["desc"] or "无描述")
        desc.setObjectName("subText")
        desc.setWordWrap(True)
        path = QLabel(entry["path"])
        path.setObjectName("subText")
        path.setWordWrap(True)
        v.addWidget(icon)
        v.addWidget(name)
        v.addWidget(desc)
        v.addWidget(path)
        h = QHBoxLayout()
        launch = QPushButton("启动")
        launch.setObjectName("accentBtn")
        launch.clicked.connect(self._launch)
        h.addWidget(launch)
        self.uninstall = QPushButton("卸载")
        self.uninstall.setObjectName("dangerBtn")
        self.uninstall.clicked.connect(self._uninstall)
        h.addWidget(self.uninstall)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        h.addWidget(close)
        v.addLayout(h)

    def _launch(self):
        utils.launch_app(self.entry)
        self.accept()

    def _uninstall(self):
        pkg = _package_of_desktop(self.entry["path"])
        if pkg:
            if confirm_box(self, "卸载应用",
                           f"确定卸载 {self.entry['title']} 吗？此操作不可恢复。"):
                ok, _o, err = utils.run_root(["apt-get", "purge", "-y", pkg])
                info_box(self, "完成" if ok else "失败",
                         f"{self.entry['title']} 已卸载。" if ok else (err or "卸载失败"))
        elif utils.have("flatpak"):
            ok, out, _e = utils.run(["flatpak", "list", "--app", "--columns=application"],
                                    timeout=10)
            appid = self.entry.get("appid", "")
            if ok and appid and appid in out:
                if confirm_box(self, "卸载 Flatpak 应用",
                               f"确定卸载 {self.entry['title']} ({appid}) 吗？此操作不可恢复。"):
                    ok2, _o2, err2 = utils.run_root(["flatpak", "uninstall", "-y", appid])
                    info_box(self, "完成" if ok2 else "失败",
                             f"{self.entry['title']} 已卸载。" if ok2 else (err2 or "卸载失败"))
            else:
                info_box(self, "提示", "无法确定该应用的安装来源，无法自动卸载。"
                         f"\n桌面文件: {self.entry['path']}")
        else:
            info_box(self, "提示", "无法确定该应用的安装来源，无法自动卸载。"
                     f"\n桌面文件: {self.entry['path']}")


class AppsPage(BasePage):
    def __init__(self):
        super().__init__("应用", "已安装的应用、默认应用和开机自启。")
        self._apps = []
        self._build()

    def _build(self):
        c = self.add_card("已安装的应用")
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索应用…")
        self._search.textChanged.connect(self._rebuild_list)
        c.layout().addWidget(self._search)
        self._list_card = c
        self._list = QListWidget()
        self._list.setIconSize(QSize(28, 28))
        self._list.itemDoubleClicked.connect(self._open_detail)
        c.layout().addWidget(self._list)

        # 开机自启
        c2 = self.add_card("启动")
        add_btn = QPushButton("添加自启应用…")
        add_btn.clicked.connect(self._add_autostart)
        c2.add(SettingRow("开机自启", "登录时自动启动的应用 (~/.config/autostart)",
                          trailing=add_btn, icon="apps"))
        self._autostart_card = self.add_card("自启应用列表")
        self.add_stretch()

    def _rebuild_list(self, text=""):
        self._list.clear()
        text = text.strip().lower()
        for a in self._apps:
            if text and text not in a["title"].lower() and text not in a["appid"].lower():
                continue
            item = QListWidgetItem(
                QIcon.fromTheme(a["icon"], QIcon.fromTheme("application-x-executable")),
                a["title"])
            item.setData(Qt.UserRole, a)
            self._list.addItem(item)

    def _open_detail(self, item):
        entry = item.data(Qt.UserRole)
        dlg = AppDetailDialog(entry, self)
        dlg.exec_()
        self.on_show()

    # ---------------------------------------------------------------- 自启
    def _autostart_files(self):
        if not os.path.isdir(AUTOSTART_DIR):
            return []
        return sorted(f for f in os.listdir(AUTOSTART_DIR)
                      if f.endswith(".desktop"))

    def _add_autostart(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("添加自启应用")
        dlg.setMinimumSize(420, 480)
        v = QVBoxLayout(dlg)
        lw = QListWidget()
        for a in self._apps:
            it = QListWidgetItem(
                QIcon.fromTheme(a["icon"], QIcon.fromTheme("application-x-executable")),
                a["title"])
            it.setData(Qt.UserRole, a)
            lw.addItem(it)
        lw.setSelectionMode(QAbstractItemView.SingleSelection)
        v.addWidget(lw)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec_() and lw.currentItem():
            entry = lw.currentItem().data(Qt.UserRole)
            os.makedirs(AUTOSTART_DIR, exist_ok=True)
            dst = os.path.join(AUTOSTART_DIR, os.path.basename(entry["path"]))
            try:
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(utils.read_text(entry["path"]))
                info_box(self, "完成", f"已添加自启：{entry['title']}")
                self.on_show()
            except OSError as e:
                info_box(self, "失败", str(e))

    def _toggle_autostart(self, fname: str, enabled: bool):
        src = os.path.join(AUTOSTART_DIR, fname)
        if enabled and fname.endswith(".disabled"):
            os.rename(src, src.removesuffix(".disabled"))
        elif not enabled and not fname.endswith(".disabled"):
            os.rename(src, src + ".disabled")
        self.on_show()

    def _remove_autostart(self, fname: str):
        if not confirm_box(self, "移除自启", f"移除 {fname} ？"):
            return
        os.remove(os.path.join(AUTOSTART_DIR, fname))
        self.on_show()

    def on_show(self):
        self._apps = utils.list_desktop_apps()
        self._rebuild_list(self._search.text())
        # 刷新自启列表
        lay = self._autostart_card.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        files = self._autostart_files()
        if not files:
            lay.addWidget(QLabel("暂无自启应用。"))
            return
        for fname in files:
            entry = utils.parse_desktop_file(os.path.join(AUTOSTART_DIR, fname))
            enabled = not fname.endswith(".disabled")
            from widgets import ToggleSwitch
            tg = ToggleSwitch(enabled)
            tg.toggled.connect(lambda v, f=fname: self._toggle_autostart(f, v))
            rm = QPushButton("移除")
            rm.clicked.connect(lambda _x, f=fname: self._remove_autostart(f))
            row = SettingRow(entry["title"] or fname, fname,
                             trailing=tg, icon="apps")
            row.layout().addWidget(rm)
            lay.addWidget(row)
