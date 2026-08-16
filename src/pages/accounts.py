"""accounts.py — 账户（对应 Win11 → 账户）
当前用户信息 / 其他用户管理 (useradd/userdel 需 root) / 修改密码。
"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QLabel, QPushButton, QHBoxLayout, QLineEdit,
                             QDialog, QDialogButtonBox, QVBoxLayout, QComboBox)

import theme
import utils
from widgets import BasePage, SettingRow, Card, confirm_box, info_box


def _system_users():
    """列出普通用户 (uid >= 1000 且非 nologin)"""
    users = []
    for line in utils.read_text("/etc/passwd").splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue
        name, _pw, uid, _gid, gecos, home, shell = parts[:7]
        try:
            if int(uid) >= 1000 and "nologin" not in shell and "false" not in shell:
                users.append({"name": name, "uid": uid, "gecos": gecos,
                              "home": home, "shell": shell})
        except ValueError:
            continue
    return users


class _InputDlg(QDialog):
    def __init__(self, title, label, parent=None, password=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(340)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(label))
        self.edit = QLineEdit()
        if password:
            self.edit.setEchoMode(QLineEdit.Password)
        v.addWidget(self.edit)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


class AccountsPage(BasePage):
    def __init__(self):
        super().__init__("账户", "你的账户、其他用户和登录选项。")
        self._build()

    def _build(self):
        # 当前用户
        u = utils.current_user()
        c = self.add_card("你的信息")
        h = QHBoxLayout()
        h.setSpacing(16)
        avatar = QLabel(u["name"][:1].upper())
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"background:{theme.accent_of(theme.load_theme())};"
            f"color:white;border-radius:32px;"
            f"font-size:28px;font-weight:600;")
        h.addWidget(avatar)
        col = QVBoxLayout()
        name = QLabel(u["name"])
        name.setStyleSheet("font-size:18px;font-weight:600;")
        sub = QLabel(f"{u['gecos'] or '本地账户'} · UID {u['uid']}")
        sub.setObjectName("subText")
        groups = QLabel(f"用户组: {u['groups']}")
        groups.setObjectName("subText")
        groups.setWordWrap(True)
        col.addWidget(name)
        col.addWidget(sub)
        col.addWidget(groups)
        h.addLayout(col, 1)
        c.layout().addLayout(h)

        pwd_btn = QPushButton("更改我的密码")
        pwd_btn.setObjectName("accentBtn")
        pwd_btn.clicked.connect(self._change_pwd)
        c.add(SettingRow("登录选项", "更改当前用户密码", trailing=pwd_btn,
                         icon="accounts"))

        # 其他用户
        c2 = self.add_card("其他用户")
        self._users_card = c2
        add_btn = QPushButton("添加用户")
        add_btn.clicked.connect(self._add_user)
        c2.layout().addWidget(add_btn, alignment=Qt.AlignLeft)

        tip = QLabel("用户管理需要管理员权限 (通过 pkexec 授权)。")
        tip.setObjectName("subText")
        self.body.addWidget(tip)
        self.add_stretch()

    def _change_pwd(self):
        dlg = _InputDlg("更改密码", "输入当前用户的新密码：", self, password=True)
        if dlg.exec_() and dlg.edit.text():
            u = utils.current_user()
            cmd = f"echo '{u['name']}:{dlg.edit.text()}' | chpasswd"
            ok, _o, err = utils.run_root(["sh", "-c", cmd])
            info_box(self, "完成" if ok else "失败",
                     "密码已修改。" if ok else err)

    def _add_user(self):
        dlg = _InputDlg("添加用户", "输入新用户名：", self)
        if not (dlg.exec_() and dlg.edit.text().strip()):
            return
        name = dlg.edit.text().strip()
        ok, _o, err = utils.run_root(["useradd", "-m", "-s", "/bin/bash", name])
        if ok:
            run_root_pwd = _InputDlg("设置密码", f"为 {name} 设置密码：", self, password=True)
            if run_root_pwd.exec_() and run_root_pwd.edit.text():
                utils.run_root(["sh", "-c",
                                f"echo '{name}:{run_root_pwd.edit.text()}' | chpasswd"])
            info_box(self, "完成", f"用户 {name} 已创建。")
            self.on_show()
        else:
            info_box(self, "失败", err)

    def _del_user(self, name: str):
        if not confirm_box(self, "删除用户",
                           f"将删除用户 {name} 及其主目录，此操作不可恢复。确定吗？"):
            return
        ok, _o, err = utils.run_root(["userdel", "-r", name])
        if ok:
            self.on_show()
        else:
            info_box(self, "失败", err)

    def _set_admin(self, name: str, make_admin: bool):
        group = "sudo" if os.path.exists("/etc/sudoers.d") else "wheel"
        ok, _o, err = utils.run_root(
            ["gpasswd", "-a" if make_admin else "-d", name, group])
        if not ok:
            info_box(self, "失败", err)
        self.on_show()

    def on_show(self):
        lay = self._users_card.layout()
        # 保留添加按钮（最后一个控件）
        add_btn = None
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w and isinstance(w, QPushButton):
                add_btn = w
        me = utils.current_user()["name"]
        for u in _system_users():
            if u["name"] == me:
                continue
            h = SettingRow(u["name"], f"UID {u['uid']} · {u['home']}",
                           icon="accounts")
            del_btn = QPushButton("删除")
            del_btn.setObjectName("dangerBtn")
            del_btn.clicked.connect(lambda _x, n=u["name"]: self._del_user(n))
            admin_btn = QPushButton("设为管理员")
            admin_btn.clicked.connect(lambda _x, n=u["name"]: self._set_admin(n, True))
            h.layout().addWidget(admin_btn)
            h.layout().addWidget(del_btn)
            lay.addWidget(h)
        if lay.count() == 0:
            lay.addWidget(QLabel("没有其他用户。"))
        if add_btn:
            lay.addWidget(add_btn, alignment=Qt.AlignLeft)
        else:
            btn = QPushButton("添加用户")
            btn.clicked.connect(self._add_user)
            lay.addWidget(btn, alignment=Qt.AlignLeft)
