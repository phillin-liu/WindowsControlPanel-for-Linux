"""notifications.py — 通知设置（对应 Win11 → 系统 → 通知）
GNOME 下直接控制 gsettings；其他桌面环境记录面板级配置。
"""
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QLabel

import utils
from widgets import BasePage, ToggleSwitch, SettingRow, Card

_GNOME = "org.gnome.desktop.notifications"


class NotificationsPage(BasePage):
    def __init__(self):
        super().__init__("通知", "来自应用和系统的警报。")
        self._qs = QSettings("Win11Panel", "Win11Panel")
        self._build()

    def _build(self):
        c = self.add_card("通知")
        self.master = ToggleSwitch(self._get_master())
        self.master.toggled.connect(self._set_master)
        c.add(SettingRow("通知", "获取来自应用和系统的通知提醒", trailing=self.master,
                         icon="notifications"))

        self.dnd = ToggleSwitch(self._qs.value("dnd", False, type=bool))
        self.dnd.toggled.connect(self._set_dnd)
        c.add_divider()
        c.add(SettingRow("勿扰模式", "横幅通知静音，转到通知中心",
                         trailing=self.dnd, icon="notifications"))
        c.add_divider()
        self.lock_notify = ToggleSwitch(
            utils.gget(_GNOME, "show-in-lock-screen", "true") == "true")
        self.lock_notify.toggled.connect(
            lambda v: utils.gset(_GNOME, "show-in-lock-screen",
                                 "true" if v else "false"))
        c.add(SettingRow("在锁屏界面上显示通知", "在锁屏时显示通知内容",
                         trailing=self.lock_notify, icon="notifications"))

        self._apps_card = self.add_card("来自应用的通知")
        tip = QLabel("以下列出常用应用，GNOME 环境下可按应用开关通知。")
        tip.setObjectName("subText")
        self._apps_card.layout().addWidget(tip)
        self.add_stretch()

    def _get_master(self) -> bool:
        if utils.have("gsettings"):
            return utils.gget(_GNOME, "show-banners", "true") == "true"
        return self._qs.value("notify_master", True, type=bool)

    def _set_master(self, on: bool):
        utils.gset(_GNOME, "show-banners", "true" if on else "false")
        self._qs.setValue("notify_master", on)

    def _set_dnd(self, on: bool):
        self._qs.setValue("dnd", on)

    def on_show(self):
        # 刷新应用列表
        lay = self._apps_card.layout()
        while lay.count() > 1:
            item = lay.takeAt(1)
            w = item.widget()
            if w:
                w.deleteLater()
        if utils.have("gsettings"):
            ok, out, _ = utils.run(["gsettings", "get", _GNOME, "application-children"])
            children = out.strip("[]").replace("'", "").split(", ") if ok and out.startswith("[") else []
            for appid in children[:20]:
                path = f"/org/gnome/desktop/notifications/application/{appid}/"
                enabled = utils.gget("org.gnome.desktop.notifications.application:"
                                     + path, "enable", "true") == "true"
                tg = ToggleSwitch(enabled)
                tg.toggled.connect(
                    lambda v, p=path: utils.gset(
                        "org.gnome.desktop.notifications.application:" + p,
                        "enable", "true" if v else "false"))
                self._apps_card.add(SettingRow(appid.replace(".desktop", ""),
                                               "", trailing=tg))
        else:
            apps = utils.list_desktop_apps()[:15]
            for a in apps:
                key = f"notify_app/{a['appid']}"
                tg = ToggleSwitch(self._qs.value(key, True, type=bool))
                tg.toggled.connect(lambda v, k=key: self._qs.setValue(k, v))
                self._apps_card.add(SettingRow(a["title"], "", trailing=tg))
