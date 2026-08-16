"""admin.py — 管理工具（对应经典控制面板 → 系统和安全 → 管理工具）
服务 (systemctl) / 进程 / 事件日志 (journalctl) / 磁盘 (lsblk) / 计划任务。
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton,
                             QHBoxLayout, QPlainTextEdit, QLabel, QHeaderView,
                             QAbstractItemView, QInputDialog)

import utils
from widgets import BasePage, Card, confirm_box, info_box


class AdminPage(BasePage):
    def __init__(self):
        super().__init__("管理工具", "服务、进程、事件日志、磁盘和计划任务。")
        self._build()

    def _build(self):
        # ---------------- 服务
        c = self.add_card("服务")
        h = QHBoxLayout()
        for text, fn in (("启动", lambda: self._svc_action("start")),
                         ("停止", lambda: self._svc_action("stop")),
                         ("重启", lambda: self._svc_action("restart")),
                         ("刷新", lambda: self.on_show())):
            b = QPushButton(text)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        c.layout().addLayout(h)
        self.svc_table = QTableWidget(0, 4)
        self.svc_table.setHorizontalHeaderLabels(["服务", "状态", "开机启动", "描述"])
        self.svc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.svc_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.svc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.svc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.svc_table.verticalHeader().setVisible(False)
        self.svc_table.setMaximumHeight(260)
        c.layout().addWidget(self.svc_table)

        # ---------------- 进程（任务管理器）
        c2 = self.add_card("进程")
        h2 = QHBoxLayout()
        kill_btn = QPushButton("结束进程")
        kill_btn.setObjectName("dangerBtn")
        kill_btn.clicked.connect(self._kill_process)
        h2.addWidget(kill_btn)
        self.cpu_label = QLabel("")
        h2.addWidget(self.cpu_label)
        h2.addStretch(1)
        c2.layout().addLayout(h2)
        self.proc_table = QTableWidget(0, 5)
        self.proc_table.setHorizontalHeaderLabels(["PID", "用户", "CPU%", "内存%", "命令"])
        self.proc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.proc_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.proc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.proc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setMaximumHeight(220)
        c2.layout().addWidget(self.proc_table)

        # ---------------- 事件日志
        c3 = self.add_card("事件查看器")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        c3.layout().addWidget(self.log)

        # ---------------- 磁盘管理
        c4 = self.add_card("磁盘管理")
        self.disk_label = QPlainTextEdit()
        self.disk_label.setReadOnly(True)
        self.disk_label.setMaximumHeight(160)
        c4.layout().addWidget(self.disk_label)

        # ---------------- 计划任务
        c5 = self.add_card("计划任务")
        self.cron_label = QPlainTextEdit()
        self.cron_label.setReadOnly(True)
        self.cron_label.setMaximumHeight(120)
        c5.layout().addWidget(self.cron_label)
        self.add_stretch()

    # ---------------------------------------------------------------- 服务
    def _load_services(self):
        self.svc_table.setRowCount(0)
        ok, out, _ = utils.run(
            ["systemctl", "list-units", "--type=service", "--all",
             "--no-pager", "--no-legend"], timeout=15)
        if not ok:
            return
        rows = []
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 4 and parts[0].endswith(".service"):
                unit = parts[0]
                load, active = parts[1], parts[2]
                desc = parts[4] if len(parts) > 4 else ""
                if "not-found" in load:
                    continue
                # 开机启动状态
                state = ""
                rows.append((unit, active, state, desc))
        for unit, active, _state, desc in rows[:60]:
            i = self.svc_table.rowCount()
            self.svc_table.insertRow(i)
            self.svc_table.setItem(i, 0, QTableWidgetItem(unit))
            self.svc_table.setItem(i, 1, QTableWidgetItem(active))
            self.svc_table.setItem(i, 2, QTableWidgetItem("—"))
            self.svc_table.setItem(i, 3, QTableWidgetItem(desc.strip()))

    def _svc_action(self, action: str):
        row = self.svc_table.currentRow()
        if row < 0:
            info_box(self, "提示", "请先在表格中选择一个服务。")
            return
        unit = self.svc_table.item(row, 0).text()
        if not confirm_box(self, action, f"确定对服务 {unit} 执行“{action}”吗？"):
            return
        ok, _o, err = utils.run_root(["systemctl", action, unit])
        if not ok:
            info_box(self, "失败", err)
        self.on_show()

    # ---------------------------------------------------------------- 进程
    def _load_procs(self):
        self.proc_table.setRowCount(0)
        ok, out, _ = utils.run(["ps", "-eo", "pid,user,pcpu,pmem,comm",
                                "--sort=-pcpu"], timeout=10)
        if not ok:
            return
        for line in out.splitlines()[1:31]:
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            i = self.proc_table.rowCount()
            self.proc_table.insertRow(i)
            for j, v in enumerate(parts[:5]):
                self.proc_table.setItem(i, j, QTableWidgetItem(v))

    def _kill_process(self):
        row = self.proc_table.currentRow()
        if row < 0:
            info_box(self, "提示", "请先选择一个进程。")
            return
        pid = self.proc_table.item(row, 0).text()
        cmd = self.proc_table.item(row, 4).text()
        if not confirm_box(self, "结束进程", f"结束进程 {cmd} (PID {pid})？"):
            return
        ok, _o, err = utils.run(["kill", pid], timeout=5)
        if not ok:
            ok, _o, err = utils.run_root(["kill", pid])
        if not ok:
            info_box(self, "失败", err)
        self.on_show()

    # ---------------------------------------------------------------- 刷新
    def on_show(self):
        self._load_services()
        self._load_procs()
        ok, out, _ = utils.run(["journalctl", "-n", "80", "--no-pager"],
                               timeout=10)
        self.log.setPlainText(out if ok else "无法读取 journalctl。")
        ram = utils.ram_info()
        self.cpu_label.setText(
            f"CPU: {utils.cpu_model()} ({utils.cpu_cores()} 核) · "
            f"内存: {ram['used']}/{ram['total']} MB")
        ok, out, _ = utils.run(["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT",
                                "-e", "7"], timeout=5)
        self.disk_label.setPlainText(out if ok else "无法读取 lsblk。")
        ok, out, _ = utils.run(["sh", "-c", "crontab -l 2>/dev/null; "
                                        "echo ---; sudo -n cat /etc/crontab 2>/dev/null || cat /etc/crontab 2>/dev/null"],
                               timeout=5)
        self.cron_label.setPlainText(out if ok else "无法读取 crontab。")
