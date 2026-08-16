#!/usr/bin/env python3
"""开发自测：离屏启动并遍历控制面板所有页面（不打包进 deb）"""
import sys
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

import theme
from main_window import MainWindow, CPL_CATEGORIES, FEATURE_PAGES

app = QApplication(sys.argv)
theme.apply_theme(app)
win = MainWindow()
win.show()

errors = []

def walk_pages():
    dests = [("home",), ("all",)]
    dests += [("cat", c[0]) for c in CPL_CATEGORIES]
    dests += [("item", k) for k in FEATURE_PAGES]
    for dest in dests:
        try:
            win.navigate(dest)
            app.processEvents()
            print(f"  [OK] {dest}")
        except Exception as e:
            errors.append((dest, repr(e)))
            print(f"  [FAIL] {dest}: {e!r}")
    # 前进/后退
    try:
        win.go_back()
        win.go_forward()
        print("  [OK] back/forward")
    except Exception as e:
        errors.append(("nav", repr(e)))
        print(f"  [FAIL] nav: {e!r}")
    # 主题切换
    try:
        theme.save_theme(dark=True)
        theme.apply_theme(app)
        theme.save_theme(dark=False)
        theme.apply_theme(app)
        print("  [OK] theme switch")
    except Exception as e:
        errors.append(("theme", repr(e)))
        print(f"  [FAIL] theme: {e!r}")
    print("RESULT:", "PASS" if not errors else f"{len(errors)} ERRORS")
    app.quit()

QTimer.singleShot(300, walk_pages)
QTimer.singleShot(60000, app.quit)  # 兜底退出
app.exec_()
sys.exit(1 if errors else 0)
