#!/bin/sh
# 源码直接运行（开发调试用）
exec python3 "$(dirname "$0")/src/main.py" "$@"
