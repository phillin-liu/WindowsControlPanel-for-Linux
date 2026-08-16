#!/usr/bin/env python3
"""控制面板 — Linux 复刻版 (经典控制面板风格) — 入口"""
import sys
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

# 允许从任意目录启动
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import theme
from main_window import MainWindow
from app_icon import build_app_icon


def main():
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("控制面板")
    app.setOrganizationName("Win11Panel")
    # 使用自定义程序图标 (饼图 + 开关 + 滑块, 浅蓝背景)
    app.setWindowIcon(QIcon(build_app_icon(256)))
    theme.apply_theme(app)

    win = MainWindow()
    win.setWindowIcon(QIcon(build_app_icon(256)))
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
