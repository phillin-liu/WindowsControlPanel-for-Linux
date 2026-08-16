"""main_window.py — Windows 经典控制面板 (Control Panel) 外壳
原版复刻：地址栏面包屑 + 后退/前进 + 查看方式(类别/大图标/小图标) + 搜索 + 类别主页。
"""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QLineEdit, QLabel, QStackedWidget, QFrame,
                             QSizePolicy, QPushButton, QComboBox, QListWidget,
                             QListWidgetItem, QAbstractItemView, QListView,
                             QGridLayout, QScrollArea)

import theme
from widgets import draw_icon, draw_tile_icon, info_box

# ---------------------------------------------------------------- CPL 注册表
# (类别id, 类别名, 图标, 主色, 常用链接数, [(条目id, 条目名, 图标, 功能页key 或 None)])
CPL_CATEGORIES = [
    ("sys", "系统和安全", "shield", "#D83B01", 3, [
        ("maintenance", "安全和维护", "shield", "privacy"),
        ("winupdate", "系统更新", "update", "update"),
        ("firewall", "防火墙", "shield", "privacy"),
        ("system", "系统", "system", "about"),
        ("power", "电源选项", "power", "power"),
        ("storage_spaces", "存储空间", "storage", "storage"),
        ("file_history", "文件历史记录", "storage", None),
        ("backup", "备份和还原", "storage", None),
        ("admin_tools", "管理工具", "usb", "admin"),
        ("recovery", "恢复", "power", None),
        ("bitlocker", "驱动器加密", "shield", None),
        ("troubleshoot", "查找并解决问题", "search", None),
    ]),
    ("net", "网络和 Internet", "network", "#0078D4", 2, [
        ("netcenter", "网络和共享中心", "network", "network"),
        ("inet_options", "Internet 选项", "network", "network"),
        ("homegroup", "家庭组", "network", None),
    ]),
    ("hardware", "硬件和声音", "sound", "#107C10", 3, [
        ("devices_printers", "设备和打印机", "usb", "bluetooth"),
        ("devmgmt", "设备管理器", "usb", "devices"),
        ("autoplay", "自动播放", "usb", None),
        ("sound", "声音", "sound", "sound"),
        ("mouse", "鼠标", "accessibility", "accessibility"),
        ("hw_power", "电源选项", "power", "power"),
        ("display", "显示", "display", "display"),
    ]),
    ("programs", "程序", "apps", "#7719AA", 2, [
        ("prog_features", "程序和功能", "apps", "apps"),
        ("default_programs", "默认程序", "apps", None),
        ("gadgets", "桌面小工具", "apps", None),
    ]),
    ("users", "用户账户", "accounts", "#0067C0", 2, [
        ("user_accounts", "用户账户", "accounts", "accounts"),
        ("credential", "凭据管理器", "accounts", None),
        ("mail", "邮件 (Mail)", "accounts", None),
    ]),
    ("personal", "外观和个性化", "personalization", "#C239B3", 3, [
        ("personalization", "个性化", "personalization", "personalization"),
        ("disp2", "显示", "display", "display"),
        ("taskbar", "任务栏和导航", "personalization", None),
        ("folder_options", "文件资源管理器选项", "storage", None),
        ("fonts", "字体", "language", None),
    ]),
    ("clock", "时钟和区域", "time", "#00838F", 2, [
        ("datetime", "日期和时间", "time", "time_language"),
        ("region", "区域", "language", "time_language"),
        ("language", "语言", "language", "time_language"),
    ]),
    ("ease", "轻松使用", "accessibility", "#4A5459", 3, [
        ("ease_center", "轻松使用设置中心", "accessibility", "accessibility"),
        ("optimize_disp", "优化视频显示", "display", "display"),
        ("mouse2", "更改鼠标工作方式", "accessibility", "accessibility"),
        ("speech", "语音识别", "sound", None),
    ]),
]

# 扁平条目索引: id -> dict
CPL_ITEMS = {}
for _cid, _cname, _cicon, _ccolor, _n, _items in CPL_CATEGORIES:
    for _iid, _iname, _iicon, _page in _items:
        CPL_ITEMS[_iid] = {"id": _iid, "title": _iname, "icon": _iicon,
                           "page": _page, "cat": _cid, "cat_name": _cname,
                           "cat_color": _ccolor}

FEATURE_PAGES = ["display", "sound", "notifications", "power", "storage",
                 "about", "bluetooth", "network", "personalization", "apps",
                 "accounts", "time_language", "gaming", "privacy", "update",
                 "devices", "admin", "accessibility"]


class LinkButton(QPushButton):
    """经典蓝色超链接按钮"""
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("linkBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)


class CrumbButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("crumbBtn")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)


class ItemIconButton(QWidget):
    """大图标/小图标条目按钮"""
    def __init__(self, item, icon_size=48):
        super().__init__()
        self.item = item
        self.setCursor(Qt.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 6)
        v.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(draw_tile_icon(item["icon"], item["cat_color"], icon_size))
        icon.setFixedSize(icon_size + 8, icon_size + 8)
        icon.setAlignment(Qt.AlignCenter)
        v.addWidget(icon, 0, Qt.AlignHCenter)
        name = QLabel(item["title"])
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignHCenter)
        name.setStyleSheet("font-size: 12px;")
        v.addWidget(name, 0, Qt.AlignHCenter)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.window().open_item(self.item)
        super().mousePressEvent(e)


class HomePage(QScrollArea):
    """主页：经典 Windows 控制面板 8 大类别 + 蓝色链接（原版复刻）"""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 18, 28, 18)
        outer.setSpacing(0)

        # 标题行（查看方式在顶部工具栏的下拉框中，这里不再重复）
        title = QLabel("调整计算机的设置")
        title.setObjectName("cplSubtitle")
        outer.addWidget(title)
        outer.addSpacing(10)

        # 类别列表（按图片双列布局 - 与原版一致）
        # 左列: 系统安全/网络/硬件/程序；右列: 用户/个性化/时钟/轻松使用
        for i in range(0, len(CPL_CATEGORIES), 2):
            row = QHBoxLayout()
            row.setSpacing(40)  # 双列间距
            # 左列
            cid, cname, cicon, ccolor, nlinks, items = CPL_CATEGORIES[i]
            row.addWidget(self._category_row(cid, cname, cicon, ccolor, nlinks, items), 1)
            # 右列（如果存在）
            if i + 1 < len(CPL_CATEGORIES):
                cid2, cname2, cicon2, ccolor2, nlinks2, items2 = CPL_CATEGORIES[i + 1]
                row.addWidget(self._category_row(cid2, cname2, cicon2, ccolor2, nlinks2, items2), 1)
            # 转成 widget
            w = QWidget()
            w.setLayout(row)
            w.setContentsMargins(0, 0, 0, 8)
            outer.addWidget(w)
        outer.addStretch(1)
        self.setWidget(content)

    def _category_row(self, cid, cname, cicon, ccolor, nlinks, items):
        """单个类别：左侧大图标 + 右侧绿色标题 + 蓝色链接列表"""
        row = QHBoxLayout()
        row.setSpacing(12)

        # 图标区域 - 使用真实的"原版"图标 (小图标32px, 留出空白方框效果)
        icon_box = QLabel()
        icon_box.setFixedSize(48, 48)
        # 使用分类彩色图标，但尺寸稍小更接近原版
        icon_box.setPixmap(draw_tile_icon(cicon, ccolor, 44))
        icon_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        row.addWidget(icon_box, 0, Qt.AlignTop)

        # 文字区域
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        # 绿色标题 (与图片一致: #107C10 类似的深绿)
        title_btn = QPushButton(cname)
        title_btn.setObjectName("cplCatTitle")
        title_btn.setCursor(Qt.PointingHandCursor)
        title_btn.clicked.connect(lambda _c, k=cid: self.win.navigate(("cat", k)))
        text_col.addWidget(title_btn)

        # 蓝色链接列表
        for it in items[:nlinks]:
            link = LinkButton(it[1])
            link.clicked.connect(lambda _c, k=it[0]: self.win.open_item(CPL_ITEMS[k]))
            text_col.addWidget(link)

        row.addLayout(text_col, 1)
        # 转成 widget
        w = QWidget()
        w.setLayout(row)
        w.setContentsMargins(0, 0, 0, 12)
        return w


class AllItemsPage(QWidget):
    """所有控制面板项：大图标 / 小图标 视图"""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._items = list(CPL_ITEMS.values())
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 16, 28, 16)
        v.setSpacing(8)
        self.title = QLabel("所有控制面板项")
        self.title.setObjectName("cplPageTitle")
        v.addWidget(self.title)
        self.view_combo = win.view_combo
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setMovement(QListView.Static)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setWordWrap(True)
        self.list.itemClicked.connect(self._clicked)
        v.addWidget(self.list, 1)
        self.set_mode("large")

    def set_mode(self, mode: str):
        if mode == "large":
            size = 48
            self.list.setViewMode(QListWidget.IconMode)
            self.list.setIconSize(QSize(size, size))
            self.list.setGridSize(QSize(size + 92, size + 52))
            self.list.setSpacing(8)
            self.list.setWordWrap(True)
        elif mode == "small":
            size = 28
            self.list.setViewMode(QListWidget.IconMode)
            self.list.setIconSize(QSize(size, size))
            self.list.setGridSize(QSize(220, 40))
            self.list.setSpacing(4)
            self.list.setWordWrap(False)
        else:  # list: 单列列表，图标+文字左对齐
            size = 22
            self.list.setViewMode(QListWidget.ListMode)
            self.list.setIconSize(QSize(size, size))
            self.list.setGridSize(QSize(0, 34))   # 宽度自适应
            self.list.setSpacing(2)
            self.list.setWordWrap(False)
        self._rebuild(self.win.search_edit.text())

    def _clicked(self, item):
        self.win.open_item(item.data(Qt.UserRole))

    def _rebuild(self, text=""):
        self.list.clear()
        text = text.strip().lower()
        for it in self._items:
            if text and text not in it["title"].lower():
                continue
            size = self.list.iconSize().width()
            icon = QIcon(draw_tile_icon(it["icon"], it["cat_color"], size))
            li = QListWidgetItem(icon, it["title"])
            li.setData(Qt.UserRole, it)
            self.list.addItem(li)

    def filter_text(self, text):
        self._rebuild(text)


class CategoryPage(QScrollArea):
    """类别详情页：该类别下所有条目（大图标）"""
    def __init__(self, win, cid):
        super().__init__()
        self.win = win
        cat = next(c for c in CPL_CATEGORIES if c[0] == cid)
        _cid, cname, cicon, ccolor, _n, items = cat
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 16, 28, 16)
        outer.setSpacing(12)
        title = QLabel(cname)
        title.setObjectName("cplPageTitle")
        outer.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, it in enumerate(items):
            entry = CPL_ITEMS[it[0]]
            btn = ItemIconButton(entry, 48)
            grid.addWidget(btn, i // 3, i % 3)
        outer.addLayout(grid)
        outer.addStretch(1)
        self.setWidget(content)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("控制面板")
        self.resize(1000, 680)
        self.setMinimumSize(QSize(800, 520))

        self._hist = []
        self._hist_idx = -1

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- 顶栏：后退/前进 + 面包屑
        topbar = QFrame()
        topbar.setObjectName("topbar")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(8, 4, 12, 4)
        tb.setSpacing(4)
        self.back_btn = QPushButton("‹")
        self.back_btn.setObjectName("navArrow")
        self.back_btn.setFixedSize(30, 30)
        self.back_btn.setToolTip("后退")
        self.back_btn.clicked.connect(self.go_back)
        self.fwd_btn = QPushButton("›")
        self.fwd_btn.setObjectName("navArrow")
        self.fwd_btn.setFixedSize(30, 30)
        self.fwd_btn.setToolTip("前进")
        self.fwd_btn.clicked.connect(self.go_forward)
        tb.addWidget(self.back_btn)
        tb.addWidget(self.fwd_btn)
        self.crumb_bar = QHBoxLayout()
        self.crumb_bar.setSpacing(0)
        tb.addLayout(self.crumb_bar)
        tb.addStretch(1)
        root.addWidget(topbar)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        root.addWidget(divider)

        # ---------------- 次栏：查看方式 + 搜索
        subbar = QFrame()
        subbar.setObjectName("subbar")
        sb = QHBoxLayout(subbar)
        sb.setContentsMargins(16, 4, 16, 4)
        sb.setSpacing(8)
        sb.addWidget(QLabel("查看方式:"))
        self.view_combo = QComboBox()
        self.view_combo.addItem("类别", "category")
        self.view_combo.addItem("大图标", "large")
        self.view_combo.addItem("小图标", "small")
        self.view_combo.addItem("列表", "list")
        self.view_combo.currentIndexChanged.connect(self._view_changed)
        sb.addWidget(self.view_combo)
        sb.addStretch(1)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索控制面板项…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(240)
        self.search_edit.textChanged.connect(self._search_changed)
        sb.addWidget(self.search_edit)
        root.addWidget(subbar)

        # ---------------- 内容区
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.home_page = HomePage(self)
        self.all_page = AllItemsPage(self)
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.all_page)

        self._cat_pages = {}
        self._feature_pages = {}
        self._register_features()

        self.navigate(("home",))

    # ---------------------------------------------------------------- 页面注册
    def _register_features(self):
        from pages import (display, sound, notifications, power, storage,
                           bluetooth, network, personalization, apps, accounts,
                           time_language, gaming, accessibility, privacy,
                           update, devices, admin)
        makers = {
            "display": display.DisplayPage,
            "sound": sound.SoundPage,
            "notifications": notifications.NotificationsPage,
            "power": power.PowerPage,
            "storage": storage.StoragePage,
            "about": system_about,
            "bluetooth": bluetooth.BluetoothPage,
            "network": network.NetworkPage,
            "personalization": personalization.PersonalizationPage,
            "apps": apps.AppsPage,
            "accounts": accounts.AccountsPage,
            "time_language": time_language.TimeLanguagePage,
            "gaming": gaming.GamingPage,
            "privacy": privacy.PrivacyPage,
            "update": update.UpdatePage,
            "devices": devices.DevicesPage,
            "admin": admin.AdminPage,
            "accessibility": accessibility.AccessibilityPage,
        }
        for key, maker in makers.items():
            page = maker()
            page.nav_requested.connect(self.navigate)
            self._feature_pages[key] = page
            self.stack.addWidget(page)

    # ---------------------------------------------------------------- 导航
    def navigate(self, dest, push=True):
        if push and self._hist and self._hist[self._hist_idx] == dest:
            return
        page = self._show_dest(dest)
        if page is None:
            return
        if push:
            self._hist = self._hist[:self._hist_idx + 1]
            self._hist.append(dest)
            self._hist_idx = len(self._hist) - 1
        self._update_chrome()

    def _show_dest(self, dest):
        kind = dest[0]
        if kind == "home":
            self.stack.setCurrentWidget(self.home_page)
            self.view_combo.blockSignals(True)
            self.view_combo.setCurrentIndex(0)
            self.view_combo.blockSignals(False)
            return self.home_page
        if kind == "all":
            self.stack.setCurrentWidget(self.all_page)
            return self.all_page
        if kind == "cat":
            cid = dest[1]
            if cid not in self._cat_pages:
                self._cat_pages[cid] = CategoryPage(self, cid)
                self.stack.addWidget(self._cat_pages[cid])
            self.stack.setCurrentWidget(self._cat_pages[cid])
            return self._cat_pages[cid]
        if kind == "item":
            key = dest[1]
            page = self._feature_pages.get(key)
            if page is None:
                item = next((i for i in CPL_ITEMS.values() if i["page"] == key), None)
                title = item["title"] if item else key
                info_box(self, title, f"“{title}”功能暂不可用。")
                return None
            self.stack.setCurrentWidget(page)
            page.on_show()
            return page
        return None

    def open_item(self, item: dict):
        if item["page"]:
            self.navigate(("item", item["page"]))
        else:
            info_box(self, item["title"],
                     f"“{item['title']}”在当前系统上暂未提供。\n"
                     f"相近功能可查看: {item['cat_name']} 类别下的其他项目。")

    def go_back(self):
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._show_dest(self._hist[self._hist_idx])
            self._update_chrome()

    def go_forward(self):
        if self._hist_idx < len(self._hist) - 1:
            self._hist_idx += 1
            self._show_dest(self._hist[self._hist_idx])
            self._update_chrome()

    # ---------------------------------------------------------------- UI 状态
    def _update_chrome(self):
        self.back_btn.setEnabled(self._hist_idx > 0)
        self.fwd_btn.setEnabled(self._hist_idx < len(self._hist) - 1)
        # 清空面包屑
        while self.crumb_bar.count():
            it = self.crumb_bar.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        dest = self._hist[self._hist_idx] if self._hist else ("home",)
        kind = dest[0]
        crumbs = [("控制面板", ("home",))]
        if kind == "all":
            crumbs.append(("所有控制面板项", None))
        elif kind == "cat":
            cname = next(c[1] for c in CPL_CATEGORIES if c[0] == dest[1])
            crumbs.append((cname, ("cat", dest[1])))
        elif kind == "item":
            page_key = dest[1]
            # 找到该项目所属类别
            owner = next((it for it in CPL_ITEMS.values() if it["page"] == page_key), None)
            if owner:
                crumbs.append((owner["cat_name"], ("cat", owner["cat"])))
            title = self._page_title(page_key)
            crumbs.append((title, None))
        for i, (text, target) in enumerate(crumbs):
            if i:
                sep = QLabel("›")
                sep.setObjectName("crumbSep")
                self.crumb_bar.addWidget(sep)
            btn = CrumbButton(text)
            if target:
                btn.clicked.connect(lambda _c, t=target: self.navigate(t))
            else:
                btn.setStyleSheet("color: palette(text); font-weight: normal;")
                btn.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.crumb_bar.addWidget(btn)
        self.crumb_bar.addStretch(1)

    def _page_title(self, key) -> str:
        page = self._feature_pages.get(key)
        if page:
            # BasePage 第一个内容控件是标题 QLabel
            from widgets import BasePage
            if isinstance(page, BasePage):
                w = page.widget().layout().itemAt(0)
                if w and w.widget():
                    return w.widget().text()
        return key

    # ---------------------------------------------------------------- 交互
    def _view_changed(self, idx):
        mode = self.view_combo.itemData(idx)
        if mode == "category":
            self.navigate(("home",))
        else:
            self.navigate(("all",))
            self.all_page.set_mode(mode)

    def _search_changed(self, text):
        if text.strip():
            # 搜索在"所有控制面板项"页展示；类别模式切到小图标视图
            if self.view_combo.currentData() in (None, "category"):
                self.view_combo.blockSignals(True)
                self.view_combo.setCurrentIndex(self.view_combo.findData("small"))
                self.view_combo.blockSignals(False)
            cur = self._hist[self._hist_idx] if self._hist else None
            if cur != ("all",):
                self.navigate(("all",))
            self.all_page.set_mode(self.view_combo.currentData() or "small")
            self.all_page.filter_text(text)
        else:
            self.all_page.filter_text("")

    def refresh_nav_icons(self):
        pass  # 经典控制面板为纯白底，无彩色图标需随主题刷新


def system_about():
    from pages.system import AboutPage
    return AboutPage()
