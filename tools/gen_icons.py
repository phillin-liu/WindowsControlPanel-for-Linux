#!/usr/bin/env python3
"""gen_icons.py — 用 widgets.draw_icon/draw_tile_icon 生成所有 PNG 图标文件
运行后在 src/icons/ 下生成：
  - monochrome/{name}-{size}-{color}.png  (单色图标，适配明暗主题)
  - tiles/{name}-{size}.png               (彩色磁贴图标，分类卡片用)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor
app = QApplication(sys.argv)

from widgets import draw_icon, draw_tile_icon

ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "icons")
MONO_DIR = os.path.join(ICONS_DIR, "mono")
TILE_DIR = os.path.join(ICONS_DIR, "tiles")
os.makedirs(MONO_DIR, exist_ok=True)
os.makedirs(TILE_DIR, exist_ok=True)

# 所有图标名称
ICON_NAMES = [
    "system", "display", "sound", "notifications", "power", "storage",
    "about", "bluetooth", "network", "personalization", "apps", "accounts",
    "time", "gaming", "accessibility", "privacy", "update", "language",
    "usb", "search", "chevron",
]

# 分类颜色 (从 CPL_CATEGORIES)
CATEGORY_COLORS = {
    "shield": "#D83B01",     # 系统和安全
    "network": "#0078D4",    # 网络和 Internet
    "sound": "#107C10",      # 硬件和声音
    "apps": "#7719AA",       # 程序
    "accounts": "#0067C0",   # 用户账户
    "personalization": "#C239B3",  # 外观和个性化
    "time": "#00838F",       # 时钟和区域
    "accessibility": "#4A5459",     # 轻松使用
}

# 单色颜色 (light/dark theme 用)
MONO_COLORS = {
    "dark": "#1B1B1B",    # 深色文本/图标 (浅色背景)
    "light": "#FFFFFF",   # 白色图标 (彩色背景)
    "gray": "#6E6E6E",    # 次要图标
}

# 要导出的尺寸
MONO_SIZES = [16, 20, 24, 32]
TILE_SIZES = [40, 48, 64]

# 经典控制面板小图标 (32x32) - 模拟原版 Windows 透明背景单色图标
CLASSIC_SIZES = [32, 48]


def gen_classic():
    """生成经典控制面板图标 (32/48px, 透明背景):
    - 8 大分类: Win7 风格复合图标
    - 其余条目: Fluent 彩色线条图标 (颜色 = 所属分类色)
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
    from widgets import _draw_win7_icon, draw_icon
    import main_window as mw
    classic_dir = os.path.join(ICONS_DIR, "classic")
    os.makedirs(classic_dir, exist_ok=True)
    # 清空旧的 classic 图标
    for f in os.listdir(classic_dir):
        if f.endswith('.png'):
            os.remove(os.path.join(classic_dir, f))
    # 1) 8 大分类 Win7 复合图标
    for name in CATEGORY_COLORS:
        for size in CLASSIC_SIZES:
            pm = _draw_win7_icon(name, size)
            pm.save(os.path.join(classic_dir, f"{name}-{size}.png"), "PNG")
            print(f"  classic(cat): {name}-{size}.png")
    # 2) 所有控制面板条目图标 (彩色 Fluent 线条)
    seen = set(CATEGORY_COLORS.keys())
    for it in mw.CPL_ITEMS.values():
        iname = it["icon"]
        if iname in seen:
            continue
        seen.add(iname)
        for size in CLASSIC_SIZES:
            pm = draw_icon(iname, QColor(it["cat_color"]), size)
            pm.save(os.path.join(classic_dir, f"{iname}-{size}.png"), "PNG")
            print(f"  classic(item): {iname}-{size}.png")

def gen_mono():
    for name in ICON_NAMES:
        for size in MONO_SIZES:
            for cname, hexcol in MONO_COLORS.items():
                pm = draw_icon(name, QColor(hexcol), size)
                fpath = os.path.join(MONO_DIR, f"{name}-{size}-{cname}.png")
                pm.save(fpath, "PNG")
                print(f"  mono: {name}-{size}-{cname}.png")

def gen_tiles():
    for name, hexcol in CATEGORY_COLORS.items():
        for size in TILE_SIZES:
            pm = draw_tile_icon(name, hexcol, size)
            fpath = os.path.join(TILE_DIR, f"{name}-{size}.png")
            pm.save(fpath, "PNG")
            print(f"  tile: {name}-{size}.png  (color={hexcol})")

if __name__ == "__main__":
    print("Generating monochrome icons...")
    gen_mono()
    print(f"\nGenerating category tile icons...")
    gen_tiles()
    print(f"\nGenerating classic category icons...")
    gen_classic()
    print(f"\nDone! Icons saved to: {ICONS_DIR}")
