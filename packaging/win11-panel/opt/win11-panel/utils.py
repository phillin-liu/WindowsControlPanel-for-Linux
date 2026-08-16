"""utils.py — 系统命令封装与系统信息读取
所有页面通过此模块与底层 Linux 工具 (nmcli/bluetoothctl/pactl/xrandr/timedatectl/apt...) 交互。
"""
import os
import re
import shutil
import subprocess

from PyQt5.QtCore import QObject, pyqtSignal, QProcess


# ---------------------------------------------------------------- 命令执行
def have(cmd: str) -> bool:
    """检查命令是否存在"""
    return shutil.which(cmd) is not None


def run(cmd, timeout=10):
    """执行命令。cmd 可为 list 或 str。返回 (ok: bool, stdout: str, stderr: str)"""
    try:
        if isinstance(cmd, str):
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "操作超时，请重试"
    except Exception as e:  # noqa
        return False, "", str(e)


def run_root(cmd):
    """以 root 权限执行命令 (通过 pkexec)。返回 (ok, stdout, stderr)
    用户在认证框点取消时返回 ok=False 且 err 提示已取消。"""
    if not have("pkexec"):
        return False, "", "未安装授权组件，无法执行需要管理员权限的操作"
    if isinstance(cmd, str):
        argv = ["pkexec", "sh", "-c", cmd]
    else:
        argv = ["pkexec"] + list(cmd)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except Exception as e:  # noqa
        return False, "", str(e)
    if p.returncode == 0:
        return True, p.stdout.strip(), p.stderr.strip()
    if not p.stderr.strip():
        # pkexec 被用户取消：退出码 126/127 且无 stderr
        return False, p.stdout.strip(), "已取消管理员授权，未执行任何更改"
    return False, p.stdout.strip(), p.stderr.strip()


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def read_first_line(path: str) -> str:
    for line in read_text(path).splitlines():
        if line.strip():
            return line.strip()
    return ""


# ---------------------------------------------------------------- gsettings (GNOME)
def gget(schema, key, default=""):
    if not have("gsettings"):
        return default
    ok, out, _ = run(["gsettings", "get", schema, key])
    if ok:
        return out.strip().strip("'")
    return default


def gset(schema, key, value) -> bool:
    if not have("gsettings"):
        return False
    ok, _, _ = run(["gsettings", "set", schema, key, value])
    return ok


# ---------------------------------------------------------------- 系统信息
def os_release() -> dict:
    info = {}
    for line in read_text("/etc/os-release").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip().strip('"')
    return info


def desktop_env() -> str:
    return os.environ.get("XDG_CURRENT_DESKTOP", "未知")


def session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "未知")


def kernel_version() -> str:
    ok, out, _ = run(["uname", "-r"])
    return out if ok else "未知"


def hostname() -> str:
    ok, out, _ = run(["hostname"])
    return out if ok else os.uname().nodename


def cpu_model() -> str:
    for line in read_text("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "未知"


def cpu_cores() -> int:
    return os.cpu_count() or 1


def ram_info() -> dict:
    """返回 {total, used, avail} (MB)"""
    info = {"total": 0, "used": 0, "avail": 0}
    for line in read_text("/proc/meminfo").splitlines():
        if line.startswith(("MemTotal", "MemAvailable")):
            k, v = line.split(":", 1)
            mb = int(v.strip().split()[0]) // 1024
            if k == "MemTotal":
                info["total"] = mb
            else:
                info["avail"] = mb
    info["used"] = info["total"] - info["avail"]
    return info


def gpu_info() -> str:
    ok, out, _ = run(["lspci"], timeout=5)
    if not ok:
        return "未知"
    for line in out.splitlines():
        if re.search(r"VGA|3D controller|Display controller", line, re.I):
            return line.split(":", 2)[-1].strip()
    return "未知"


def current_user() -> dict:
    """当前用户信息 {name, uid, gid, gecos(全名), home, shell, groups}"""
    ok, out, _ = run(["getent", "passwd", os.environ.get("USER", "") or os.environ.get("LOGNAME", "")])
    if ok and ":" in out:
        parts = out.split(":")
        info = {"name": parts[0], "uid": parts[2], "gid": parts[3],
                "gecos": parts[4], "home": parts[5], "shell": parts[6], "groups": ""}
        ok2, groups, _ = run(["id", "-nG", info["name"]])
        if ok2:
            info["groups"] = groups
        return info
    name = os.environ.get("USER", "user")
    return {"name": name, "uid": "?", "gid": "?", "gecos": "", "home": os.path.expanduser("~"),
            "shell": "", "groups": ""}


def human_size(n_bytes) -> str:
    n = float(n_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def dir_size(path: str) -> int:
    ok, out, _ = run(["du", "-sb", path], timeout=30)
    if ok and out:
        try:
            return int(out.split()[0])
        except ValueError:
            return 0
    return 0


# ---------------------------------------------------------------- .desktop 解析
def parse_desktop_file(path: str) -> dict:
    """解析 .desktop 文件，优先取中文 Name/Comment"""
    entry = {"path": path, "appid": os.path.basename(path).removesuffix(".desktop"),
             "name": "", "name_zh": "", "comment": "", "comment_zh": "", "icon": "",
             "exec": "", "nodisplay": False, "terminal": False}
    section = ""
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line
            continue
        if section != "[Desktop Entry]" or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if k == "Name":
            entry["name"] = v
        elif k == "Name[zh_CN]" or k == "Name[zh_CN.UTF-8]":
            entry["name_zh"] = v
        elif k == "Comment":
            entry["comment"] = v
        elif k.startswith("Comment[zh"):
            entry["comment_zh"] = v
        elif k == "Icon":
            entry["icon"] = v
        elif k == "Exec":
            entry["exec"] = v
        elif k == "NoDisplay":
            entry["nodisplay"] = v.lower() == "true"
        elif k == "Terminal":
            entry["terminal"] = v.lower() == "true"
    entry["title"] = entry["name_zh"] or entry["name"] or entry["appid"]
    entry["desc"] = entry["comment_zh"] or entry["comment"]
    return entry


def desktop_apps_dirs() -> list:
    dirs = ["/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/usr/local/share/applications"]
    return [d for d in dirs if os.path.isdir(d)]


def list_desktop_apps() -> list:
    apps = []
    seen = set()
    for d in desktop_apps_dirs():
        try:
            for f in sorted(os.listdir(d)):
                if f.endswith(".desktop") and f not in seen:
                    seen.add(f)
                    apps.append(parse_desktop_file(os.path.join(d, f)))
        except OSError:
            pass
    return [a for a in apps if a["name"] and not a["nodisplay"]]


def launch_app(entry: dict) -> bool:
    if have("gtk-launch"):
        ok, _, _ = run(["gtk-launch", entry["appid"]])
        if ok:
            return True
    if entry["exec"]:
        cmd = re.sub(r"%[fFuUdDnNickvm]", "", entry["exec"]).strip()
        subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False


# ---------------------------------------------------------------- 后台命令 (流式输出)
class AsyncCommand(QObject):
    """QProcess 封装：用于 apt 更新等长任务的实时输出"""
    output = pyqtSignal(str)
    finished = pyqtSignal(bool, int)  # (成功, 退出码)
    failed = pyqtSignal(str)

    def start(self, cmd, as_root=False):
        argv = (["pkexec"] + cmd) if as_root else cmd
        self._proc = QProcess(self)
        self._proc.readyReadStandardOutput.connect(self._on_out)
        self._proc.readyReadStandardError.connect(self._on_err)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)
        self.output.emit(f"$ {' '.join(argv)}\n")
        self._proc.start(argv[0], argv[1:])

    def _on_out(self):
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.output.emit(data)

    def _on_err(self):
        data = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace")
        self.output.emit(data)

    def _on_finished(self, code, _status):
        self.output.emit("\n[完成]\n")
        self.finished.emit(code == 0, code)

    def _on_error(self, err):
        self.failed.emit(f"进程启动失败: {err}")
