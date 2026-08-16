#!/usr/bin/env bash
# build_deb.sh — 一键打包控制面板为 .deb
# 用法: bash build_deb.sh
# 产物: 项目根目录下的 win11-panel_<version>_all.deb
set -e

# ---------- 路径与版本 ----------
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# 从 packaging/win11-panel/DEBIAN/control 读版本号
CTRL_FILE="packaging/win11-panel/DEBIAN/control"
if [ ! -f "$CTRL_FILE" ]; then
  echo "[ERR] 找不到 $CTRL_FILE" >&2
  exit 1
fi
VERSION=$(grep -m1 '^Version:' "$CTRL_FILE" | awk '{print $2}')
if [ -z "$VERSION" ]; then
  echo "[ERR] 解析版本号失败" >&2
  exit 1
fi
PKG_NAME="win11-panel"
DEB_FILE="${ROOT_DIR}/${PKG_NAME}_${VERSION}_all.deb"
BUILD_DIR="packaging/${PKG_NAME}"

echo "[INFO] 包名: $PKG_NAME  版本: $VERSION"
echo "[INFO] 目标: $DEB_FILE"

# ---------- 工具检查 ----------
for tool in dpkg-deb find rm cp; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[ERR] 缺少必要工具: $tool" >&2
    exit 1
  fi
done

# ---------- 清理旧构建产物 ----------
echo "[STEP] 清理旧打包目录"
# 注意: pkexec 会重置工作目录, 提权删除必须使用绝对路径
if ! rm -rf "${ROOT_DIR}/${BUILD_DIR}/opt" 2>/dev/null; then
  # 目录被 root 占用时才需要提权 (pkexec 弹出图形密码框)
  pkexec rm -rf "${ROOT_DIR}/${BUILD_DIR}/opt"
fi
mkdir -p "${BUILD_DIR}/opt/${PKG_NAME}"

# ---------- 复制源码 ----------
echo "[STEP] 复制源码 -> opt/${PKG_NAME}/"
cp -r src/* "${BUILD_DIR}/opt/${PKG_NAME}/"

# 清理 Python 缓存
find "${BUILD_DIR}" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -name '*.pyc' -delete 2>/dev/null || true

# ---------- 校验关键文件 ----------
if [ ! -f "${BUILD_DIR}/opt/${PKG_NAME}/main.py" ]; then
  echo "[ERR] 复制源码后未找到 main.py" >&2
  exit 1
fi
if [ ! -f "${BUILD_DIR}/opt/${PKG_NAME}/icons/app/win11-panel-256.png" ]; then
  echo "[WARN] 图标 PNG 缺失, 桌面快捷方式可能无图标"
fi
if [ ! -f "${BUILD_DIR}/usr/share/applications/${PKG_NAME}.desktop" ]; then
  echo "[ERR] 缺少 .desktop 文件" >&2
  exit 1
fi

# ---------- 校验可执行脚本 ----------
chmod +x "${BUILD_DIR}/usr/bin/${PKG_NAME}" 2>/dev/null || true

# ---------- 构建 deb ----------
echo "[STEP] 构建 deb 包"
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$DEB_FILE"

# ---------- 输出信息 ----------
echo "============================================"
echo "[OK] 打包完成: $DEB_FILE"
ls -lh "$DEB_FILE"
echo ""
echo "安装命令:   sudo dpkg -i $DEB_FILE"
echo "修复依赖:   sudo apt -f install"
echo "卸载命令:   sudo dpkg -r $PKG_NAME"
echo "============================================"
