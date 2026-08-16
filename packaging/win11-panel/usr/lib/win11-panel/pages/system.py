"""system.py — 系统信息页（控制面板 → 系统和安全 → 系统）"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QPushButton, QHBoxLayout, QLineEdit,
                             QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout,
                             QApplication)

import utils
from widgets import BasePage, SettingRow, Card, confirm_box, info_box


def rename_host_dialog(parent):
    """重命名主机名对话框（系统页/关于页共用）"""
    name = utils.hostname()
    dlg = QDialog(parent)
    dlg.setWindowTitle("重命名这台电脑")
    v = QVBoxLayout(dlg)
    edit = QLineEdit(name)
    edit.setMaxLength(64)
    v.addWidget(edit)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    if dlg.exec_() and edit.text().strip() and edit.text() != name:
        ok, _o, err = utils.run_root(["hostnamectl", "set-hostname", edit.text().strip()])
        if ok:
            info_box(parent, "成功", "主机名已修改，部分显示将在重启后生效。")
        else:
            info_box(parent, "失败", f"修改失败：{err}")


class AboutPage(BasePage):
    """系统信息（对应控制面板 → 系统和安全 → 系统）"""
    def __init__(self):
        super().__init__("系统信息", "设备规格和系统信息。")
        self._build()

    def _build(self):
        osr = utils.os_release()
        ram = utils.ram_info()
        card = self.add_card("设备规格")
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        rows = [
            ("设备名称", utils.hostname()),
            ("处理器", f"{utils.cpu_model()} ({utils.cpu_cores()} 核)"),
            ("机带 RAM", f"{ram['used']} MB / {ram['total']} MB"),
            ("显卡", utils.gpu_info()),
            ("设备 ID", utils.read_first_line("/etc/machine-id") or "不可用"),
            ("系统类型", f"{os.uname().machine}, {utils.kernel_version()} 内核"),
        ]
        for k, v in rows:
            val = QLabel(v)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setWordWrap(True)
            form.addRow(k, val)
        card.layout().addLayout(form)

        card2 = self.add_card("系统信息")
        form2 = QFormLayout()
        form2.setSpacing(8)
        rows2 = [
            ("操作系统", osr.get("PRETTY_NAME", "Linux")),
            ("发行版 ID", osr.get("ID", "-")),
            ("版本", osr.get("VERSION", osr.get("VERSION_ID", "-"))),
            ("桌面环境", utils.desktop_env()),
            ("会话类型", utils.session_type()),
            ("当前用户", utils.current_user()["name"]),
        ]
        for k, v in rows2:
            val = QLabel(v)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form2.addRow(k, val)
        card2.layout().addLayout(form2)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("复制规格")
        copy_btn.clicked.connect(self._copy)
        rename_btn = QPushButton("重命名这台电脑")
        rename_btn.clicked.connect(self._rename)
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(rename_btn)
        btn_row.addStretch(1)
        card2.layout().addLayout(btn_row)

    def _spec_text(self) -> str:
        osr = utils.os_release()
        ram = utils.ram_info()
        return (f"设备名称: {utils.hostname()}\n"
                f"处理器: {utils.cpu_model()} ({utils.cpu_cores()} 核)\n"
                f"机带 RAM: {ram['used']} MB / {ram['total']} MB\n"
                f"显卡: {utils.gpu_info()}\n"
                f"操作系统: {osr.get('PRETTY_NAME', 'Linux')}\n"
                f"内核: {utils.kernel_version()}\n"
                f"桌面环境: {utils.desktop_env()} ({utils.session_type()})")

    def _copy(self):
        QApplication.clipboard().setText(self._spec_text())
        info_box(self, "已复制", "设备规格已复制到剪贴板。")

    def _rename(self):
        rename_host_dialog(self)

    def on_show(self):
        pass
