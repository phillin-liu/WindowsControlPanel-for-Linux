#!/usr/bin/env python3
"""Windows 经典控制面板 (Control Panel) Linux 复刻版 — 入口"""
import sys
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# 允许从任意目录启动
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import theme
from main_window import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("控制面板")
    app.setOrganizationName("Win11Panel")
    app.setWindowIcon(app.style().standardIcon(app.style().SP_ComputerIcon))
    theme.apply_theme(app)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
