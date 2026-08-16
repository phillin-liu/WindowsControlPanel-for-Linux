"""personalization.py — 个性化（对应 Win11 → 个性化）
壁纸 / 明暗主题 / 强调色 / 锁屏背景。
支持 GNOME (gsettings)、KDE (plasma-apply-*)、XFCE、feh 回退。
"""
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import (QLabel, QPushButton, QFileDialog, QHBoxLayout,
                             QVBoxLayout, QGridLayout, QApplication, QWidget)

import theme
import utils
from widgets import BasePage, SettingRow, info_box

WALLPAPER_DIRS = ["/usr/share/backgrounds",
                  "/usr/share/wallpapers",
                  os.path.expanduser("~/Pictures")]


def _set_wallpaper(path: str) -> bool:
    uri = f"file://{path}"
    de = utils.desktop_env().lower()
    if "gnome" in de:
        ok1 = utils.gset("org.gnome.desktop.background", "picture-uri", uri)
        utils.gset("org.gnome.desktop.background", "picture-uri-dark", uri)
        if ok1:
            return True
    if "kde" in de and utils.have("plasma-apply-wallpaper"):
        ok, _o, _e = utils.run(["plasma-apply-wallpaper", path], timeout=10)
        if ok:
            return True
    if "xfce" in de and utils.have("xfconf-query"):
        ok, _o, _e = utils.run(["xfconf-query", "-c", "xfce4-desktop",
                                "-p", "/backdrop/screen0/monitor0/workspace0/last-image",
                                "-s", path], timeout=10)
        if ok:
            return True
    if utils.have("feh"):
        ok, _o, _e = utils.run(["feh", "--bg-fill", path], timeout=10)
        if ok:
            return True
    return False


def _wallpaper_files() -> list:
    files = []
    for d in WALLPAPER_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _dirs, names in os.walk(d):
            for n in names:
                if n.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    files.append(os.path.join(root, n))
            if len(files) > 60 or root != d:
                break
    return files[:36]


class WallpaperButton(QLabel):
    """壁纸缩略图按钮"""
    chosen = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.setFixedSize(140, 84)
        self.setCursor(Qt.PointingHandCursor)
        self.setScaledContents(True)
        pm = QPixmap(path)
        if not pm.isNull():
            self.setPixmap(pm.scaled(140, 84, Qt.KeepAspectRatioByExpanding,
                                     Qt.SmoothTransformation))
        else:
            self.setText("无法预览")
            self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 6px; border: 1px solid rgba(128,128,128,0.4);")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.chosen.emit(self.path)


class PersonalizationPage(BasePage):
    def __init__(self):
        super().__init__("个性化", "背景、颜色、主题和锁屏。")
        self._build()

    def _build(self):
        # 当前壁纸
        c = self.add_card("背景")
        h = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(220, 124)
        self.preview.setStyleSheet("border-radius:8px;background:#ccc;")
        h.addWidget(self.preview)
        col = QVBoxLayout()
        browse = QPushButton("浏览图片…")
        browse.setObjectName("accentBtn")
        browse.clicked.connect(self._browse_wallpaper)
        col.addWidget(browse)
        h.addLayout(col, 1)
        c.layout().addLayout(h)
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, f in enumerate(_wallpaper_files()):
            btn = WallpaperButton(f)
            btn.chosen.connect(self._apply_wallpaper)
            grid.addWidget(btn, i // 4, i % 4)
        holder = QWidget()
        holder.setLayout(grid)
        c.layout().addWidget(holder)

        # 颜色
        c2 = self.add_card("颜色")
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("选择模式:"))
        self.light_btn = QPushButton("浅色")
        self.dark_btn = QPushButton("深色")
        self.light_btn.clicked.connect(lambda: self._set_mode(False))
        self.dark_btn.clicked.connect(lambda: self._set_mode(True))
        mode_row.addWidget(self.light_btn)
        mode_row.addWidget(self.dark_btn)
        mode_row.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(mode_row)
        c2.layout().addWidget(wrap)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(8)
        self._accent_btns = []
        for hexcolor in theme.ACCENTS:
            b = QPushButton()
            b.setFixedSize(30, 30)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"background: {hexcolor}; border-radius: 15px; border: 2px solid rgba(0,0,0,0.15);")
            b.clicked.connect(lambda _x, h=hexcolor: self._set_accent(h))
            accent_row.addWidget(b)
            self._accent_btns.append(b)
        accent_row.addStretch(1)
        wrap2 = QWidget()
        wrap2.setLayout(accent_row)
        c2.layout().addWidget(wrap2)

        # 锁屏
        c3 = self.add_card("锁屏界面")
        browse_lock = QPushButton("选择锁屏图片…")
        browse_lock.clicked.connect(self._browse_lockscreen)
        c3.add(SettingRow("锁屏背景", "更换锁屏壁纸 (GNOME)",
                          trailing=browse_lock, icon="personalization"))
        self.add_stretch()

    # ---------------------------------------------------------------- 壁纸
    def _refresh_preview(self):
        de = utils.desktop_env().lower()
        uri = ""
        if "gnome" in de:
            uri = utils.gget("org.gnome.desktop.background", "picture-uri-dark")
            if not uri or uri == "@@":
                uri = utils.gget("org.gnome.desktop.background", "picture-uri")
        if uri.startswith("file://"):
            path = uri[7:]
            pm = QPixmap(path)
            if not pm.isNull():
                self.preview.setPixmap(pm.scaled(220, 124,
                                                 Qt.KeepAspectRatioByExpanding,
                                                 Qt.SmoothTransformation))

    def _apply_wallpaper(self, path: str):
        if _set_wallpaper(path):
            self._refresh_preview()
        else:
            info_box(self, "提示",
                     "未能自动应用壁纸：未检测到支持的桌面环境 (GNOME/KDE/XFCE/feh)。")

    def _browse_wallpaper(self):
        path, _f = QFileDialog.getOpenFileName(
            self, "选择壁纸", os.path.expanduser("~"),
            "图片 (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            self._apply_wallpaper(path)

    def _browse_lockscreen(self):
        path, _f = QFileDialog.getOpenFileName(
            self, "选择锁屏图片", os.path.expanduser("~"),
            "图片 (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            ok = utils.gset("org.gnome.desktop.screensaver", "picture-uri",
                            f"file://{path}")
            info_box(self, "提示" if not ok else "完成",
                     "已设置。" if ok else "仅 GNOME 支持锁屏图片设置。")

    # ---------------------------------------------------------------- 主题
    def _set_mode(self, dark: bool):
        theme.save_theme(dark=dark)
        app = QApplication.instance()
        theme.apply_theme(app)
        win = self.window()
        if hasattr(win, "refresh_nav_icons"):
            win.refresh_nav_icons()
        # 同步系统主题
        de = utils.desktop_env().lower()
        if "gnome" in de:
            utils.gset("org.gnome.desktop.interface", "color-scheme",
                       "prefer-dark" if dark else "default")
        elif "kde" in de and utils.have("plasma-apply-colorscheme"):
            scheme = "BreezeDark" if dark else "BreezeLight"
            utils.run(["plasma-apply-colorscheme", scheme], timeout=10)

    def _set_accent(self, hexcolor: str):
        theme.save_theme(accent=hexcolor)
        app = QApplication.instance()
        theme.apply_theme(app)
        win = self.window()
        if hasattr(win, "refresh_nav_icons"):
            win.refresh_nav_icons()

    def on_show(self):
        self._refresh_preview()
