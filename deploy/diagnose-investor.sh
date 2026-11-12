#!/usr/bin/env bash
set -Eeuo pipefail

service=stock-tools.service
if [[ $(id -u) -ne 0 ]]; then printf '请使用 sudo 运行，以检查服务进程。\n' >&2; exit 1; fi
command -v systemctl >/dev/null || { printf '未找到 systemctl。\n' >&2; exit 1; }
if ! systemctl is-active --quiet "$service"; then
  printf '服务未运行：%s\n' "$service" >&2
  exit 1
fi
pid=$(systemctl show "$service" -p MainPID --value)
[[ "$pid" =~ ^[1-9][0-9]*$ && -r "/proc/$pid/cmdline" ]] || { printf '无法读取服务进程。\n' >&2; exit 1; }
IFS= read -r -d '' interpreter < "/proc/$pid/cmdline" || true
printf '服务状态: 运行中\n'
printf '服务进程: %s\n' "$pid"
if [[ "$interpreter" != /* || ! -x "$interpreter" ]]; then
  printf '无法确定绝对 Python 路径；请检查 systemctl cat stock-tools.service。\n' >&2
  exit 1
fi
printf '启动解释器: %s\n' "$interpreter"
"$interpreter" - "$pid" <<'PY'
import importlib.util
import os
import pathlib
import sys
pid = sys.argv[1]
print('Python 版本:', sys.version.split()[0])
print('Python 环境:', '虚拟环境' if sys.prefix != sys.base_prefix else '系统环境')
for name in ('xlrd', 'pypdf'):
    print(f'{name}:', '可导入' if importlib.util.find_spec(name) else '未安装')
try:
    raw = pathlib.Path(f'/proc/{pid}/environ').read_bytes()
    values = [x.split(b'=', 1)[1] for x in raw.split(b'\0') if x.startswith(b'SEC_USER_AGENT=')]
    print('SEC_USER_AGENT 环境变量:', '已设置' if values and b'@' in values[-1] else '未设置或格式无效')
except (OSError, IndexError):
    print('SEC_USER_AGENT 环境变量: 无法检查')
PY
printf '注意：检查使用相同 Python 可执行文件；服务特有的环境变量可能影响模块搜索路径。\n'
