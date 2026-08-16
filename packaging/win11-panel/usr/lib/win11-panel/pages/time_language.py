"""time_language.py — 时间和语言（对应 Win11 → 时间和语言）
基于 timedatectl / localectl。
"""
import re

from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtWidgets import (QLabel, QComboBox, QDateTimeEdit, QPushButton,
                             QHBoxLayout)

import utils
from widgets import BasePage, SettingRow, ToggleSwitch, info_box


def _timedate() -> dict:
    ok, out, _ = utils.run(["timedatectl"], timeout=5)
    info = {}
    if ok:
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    return info


def _timezones():
    ok, out, _ = utils.run(["timedatectl", "list-timezones"], timeout=10)
    return out.splitlines() if ok else ["Asia/Shanghai"]


class TimeLanguagePage(BasePage):
    def __init__(self):
        super().__init__("时间和语言", "时间、时区、语言和区域。")
        self._build()

    def _build(self):
        c = self.add_card("日期和时间")
        self.clock = QLabel("")
        self.clock.setObjectName("bigValue")
        c.layout().addWidget(self.clock)
        self.ntp_toggle = ToggleSwitch()
        self.ntp_toggle.toggled.connect(self._set_ntp)
        c.add(SettingRow("自动设置时间", "使用 NTP 网络时间同步 (timedatectl)",
                         trailing=self.ntp_toggle, icon="time"))

        self.tz_combo = QComboBox()
        self.tz_combo.setEditable(True)
        self.tz_combo.setMinimumWidth(260)
        self.tz_combo.currentTextChanged.connect(self._set_tz)
        c.add(SettingRow("时区", "更改系统时区", trailing=self.tz_combo, icon="time"))

        h = QHBoxLayout()
        self.dt_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        set_btn = QPushButton("设置时间")
        set_btn.clicked.connect(self._set_time)
        h.addWidget(self.dt_edit)
        h.addWidget(set_btn)
        h.addStretch(1)
        wrap = self._wrap(h)
        c.add(SettingRow("手动设置时间", "关闭自动同步后可手动设置",
                         icon="time"))
        c.layout().addWidget(wrap)

        c2 = self.add_card("语言和区域")
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(260)
        apply_btn = QPushButton("应用语言")
        apply_btn.clicked.connect(self._apply_lang)
        c2.add(SettingRow("系统语言", "更改系统语言 (需要重新登录)",
                          trailing=apply_btn, icon="language"))
        c2.layout().addWidget(self.lang_combo)
        self.locale_label = QLabel("")
        self.locale_label.setObjectName("subText")
        c2.layout().addWidget(self.locale_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self.add_stretch()

    def _wrap(self, layout):
        from PyQt5.QtWidgets import QWidget
        w = QWidget()
        w.setLayout(layout)
        return w

    def _tick(self):
        self.clock.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss  dddd"))

    def _set_ntp(self, on: bool):
        ok, _o, err = utils.run_root(["timedatectl", "set-ntp",
                                      "true" if on else "false"])
        if not ok:
            info_box(self, "失败", err)

    def _set_tz(self, tz: str):
        tz = tz.strip()
        if not tz or "/" not in tz:
            return
        ok, _o, err = utils.run_root(["timedatectl", "set-timezone", tz])
        if not ok:
            info_box(self, "失败", err)

    def _set_time(self):
        ok, _o, err = utils.run_root(["timedatectl", "set-time",
                                      self.dt_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")])
        if not ok:
            info_box(self, "失败", f"{err}\n提示：请先关闭“自动设置时间”。")

    def _apply_lang(self):
        lang = self.lang_combo.currentText()
        if not lang:
            return
        from widgets import confirm_box
        if not confirm_box(self, "更改系统语言",
                           f"将系统语言设置为 {lang}？需要重新登录后生效。"):
            return
        ok, _o, err = utils.run_root(["update-locale", f"LANG={lang}"])
        info_box(self, "完成" if ok else "失败",
                 "语言已设置，重新登录后生效。" if ok else err)

    def on_show(self):
        info = _timedate()
        if info:
            ntp = info.get("NTP service", "")
            active = ("active" in ntp) or ("是" in ntp) or ("yes" in ntp.lower())
            self.ntp_toggle.setChecked(active, animate=False)
            tz = info.get("Time zone", "")
            tz = re.sub(r"\s*\(.*\)", "", tz).strip()
            if tz and self.tz_combo.findText(tz) < 0:
                self.tz_combo.addItem(tz)
            if tz:
                self.tz_combo.blockSignals(True)
                self.tz_combo.setCurrentText(tz)
                self.tz_combo.blockSignals(False)
        # 时区列表（延后填充避免启动慢）
        if self.tz_combo.count() < 5:
            tzs = _timezones()
            cur = self.tz_combo.currentText()
            self.tz_combo.blockSignals(True)
            self.tz_combo.clear()
            self.tz_combo.addItems(tzs)
            if cur:
                self.tz_combo.setCurrentText(cur)
            self.tz_combo.blockSignals(False)
        # 语言
        ok, out, _ = utils.run(["localectl", "status"], timeout=5)
        if ok:
            for line in out.splitlines():
                if line.startswith("LANG"):
                    self.locale_label.setText(f"当前: {line.strip()}")
        if self.lang_combo.count() == 0:
            self.lang_combo.addItems(_locales())
            cur_lang = ""
            if ok:
                m = re.search(r"LANG=([\w_.@]+)", out)
                if m:
                    cur_lang = m.group(1)
            if cur_lang and self.lang_combo.findText(cur_lang) >= 0:
                self.lang_combo.setCurrentText(cur_lang)
        self._tick()


def _locales():
    ok, out, _ = utils.run(["locale", "-a"], timeout=5)
    locs = []
    if ok:
        for l in out.splitlines():
            if l.endswith(".utf8") or l.endswith(".UTF-8"):
                locs.append(l.replace(".utf8", ".UTF-8"))
    return sorted(set(locs)) or ["zh_CN.UTF-8", "en_US.UTF-8"]
