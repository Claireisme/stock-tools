#!/usr/bin/env bash
set -Eeuo pipefail

service=stock-tools.service
app=/www/wwwroot/stock-tools
fix_dir=/etc/systemd/system/stock-tools.service.d
fix_conf=$fix_dir/zzzz-investor-repair.conf
fix_env=/etc/stock-tools-investor-repair.env
venv=/opt/stock-tools-investor-python
source_url=https://raw.githubusercontent.com/Claireisme/stock-tools/5c4d613/server.py
source_hash=905a9dbc3887ecc17072fcb63656af677e5c552be8fb63a8f0663bfde9477033
baseline_hash=3d9e7e3f2b59565d595c7e1e5face2c7a2ccc1b77861ca582aa62d987119f6e0
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) == 0 ]] || fail '请使用 root 运行。'
for command in systemctl curl sha256sum python3 ss; do command -v "$command" >/dev/null || fail "缺少 $command。"; done
systemctl is-active --quiet "$service" || fail '服务未运行。'
[[ $(systemctl show "$service" -p WorkingDirectory --value) == "$app" ]] || fail '服务工作目录不匹配。'
pid=$(systemctl show "$service" -p MainPID --value)
[[ "$pid" =~ ^[1-9][0-9]*$ && -r /proc/$pid/cmdline && -r /proc/$pid/environ ]] || fail '无法检查服务进程。'
mapfile -d '' -t args < "/proc/$pid/cmdline"
[[ ${args[0]:-} == /usr/bin/python3 ]] || fail '启动解释器不是 /usr/bin/python3。'
printf '%s\n' "${args[@]}" | grep -Fxq "$app/server.py" || fail '服务未运行预期的网站程序。'
ss -ltnp '( sport = :8001 )' | grep -Eq "pid=${pid}([,)]|$)" || fail '服务进程未监听预期端口。'
[[ ! -L $app/server.py && -f $app/server.py && ! -L $fix_dir && ! -e $fix_conf && ! -L $fix_conf && ! -e $fix_env && ! -L $fix_env && ! -e $venv && ! -L $venv ]] || fail '目标文件已存在或含符号链接，请先检查。'
current_hash=$(sha256sum "$app/server.py" | cut -d' ' -f1)
[[ $current_hash == "$baseline_hash" || $current_hash == "$source_hash" ]] || fail '当前程序版本与已验证版本不一致，未进行修改。'
if tr '\0' '\n' < "/proc/$pid/environ" | grep -q '^PYTHONPATH=.'; then fail '服务已配置 PYTHONPATH，需要先检查现有配置。'; fi
# Preserve the existing database setting; do not write INVESTOR_DB_PATH or touch the database.
db_path=$(/usr/bin/python3 - "$pid" "$app" <<'PY'
import os, pathlib, sys
raw = pathlib.Path('/proc', sys.argv[1], 'environ').read_bytes()
env = dict(x.split(b'=', 1) for x in raw.split(b'\0') if b'=' in x)
print(os.fsdecode(env.get(b'INVESTOR_DB_PATH', os.fsencode(sys.argv[2] + '/investor_events.sqlite3'))))
PY
)
[[ -f "$db_path" ]] || fail "当前数据库不存在：$db_path；请先检查。"
work=$(mktemp -d /tmp/stock-tools-investor-repair.XXXXXXXX)
trap 'result=$?; rm -rf -- "$work"; if (( result != 0 )); then rm -rf -- "$venv"; fi' EXIT
curl -fsSL "$source_url" -o "$work/server.py"
printf '%s  %s\n' "$source_hash" "$work/server.py" | sha256sum -c --status || fail '程序文件校验失败。'
PYTHONPYCACHEPREFIX="$work/pycache" /usr/bin/python3 -m py_compile "$work/server.py"
if ! /usr/bin/python3 -m venv "$venv"; then
  rm -rf -- "$venv"
  fail '无法创建 Python 虚拟环境；请先安装 python3.12-venv，然后重新运行。'
fi
if ! "$venv/bin/python" -m pip install 'xlrd>=2.0.1,<3' 'pypdf>=4,<7'; then
  rm -rf -- "$venv"
  fail '安装采集组件失败，请检查服务器网络。'
fi
site=$($venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$site" /usr/bin/python3 -c 'import xlrd,pypdf; print("采集组件已安装：", xlrd.__version__, pypdf.__version__)' || fail '采集组件检查失败。'
backup=$(mktemp -d /var/backups/stock-tools-investor-repair.XXXXXXXX)
chmod 700 "$backup"
cp -p "$app/server.py" "$backup/server.py"
restore() {
  trap - ERR
  printf '修复未通过检查，正在恢复原程序和服务配置。\n' >&2
  cp -p "$backup/server.py" "$app/server.py" || true
  rm -f "$fix_conf" "$fix_env"
  systemctl daemon-reload || true
  systemctl restart "$service" || printf '恢复后服务未能启动，请检查服务状态。\n' >&2
  printf '原程序备份：%s\n' "$backup" >&2
  exit 1
}
trap restore ERR
install -d -m 0755 "$fix_dir"
install -m "$(stat -c '%a' "$app/server.py")" -o "$(stat -c '%u' "$app/server.py")" -g "$(stat -c '%g' "$app/server.py")" "$work/server.py" "$app/server.py"
umask 077
cat > "$fix_env" <<ENV
SEC_USER_AGENT="Stock Tools test@test.com"
PUBLIC_ORIGIN="https://tool.respecllc.com"
PYTHONPATH="$site"
ENV
chmod 0600 "$fix_env"
cat > "$fix_conf" <<ENV
[Service]
EnvironmentFile=$fix_env
ENV
chmod 0644 "$fix_conf"
systemctl daemon-reload
systemctl restart "$service"
systemctl is-active --quiet "$service"
curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 1 --max-time 5 http://127.0.0.1:8001/zh/ -o /dev/null
new_pid=$(systemctl show "$service" -p MainPID --value)
/usr/bin/python3 - "$new_pid" "$db_path" "$site" <<'PY'
import os, pathlib, sys
raw = pathlib.Path('/proc', sys.argv[1], 'environ').read_bytes()
env = dict(x.split(b'=', 1) for x in raw.split(b'\0') if b'=' in x)
assert env.get(b'SEC_USER_AGENT') == b'Stock Tools test@test.com', 'SEC 访问标识未生效'
assert env.get(b'PUBLIC_ORIGIN') == b'https://tool.respecllc.com', '公开网站地址未生效'
assert os.fsdecode(env.get(b'PYTHONPATH', b'')) == sys.argv[3], 'Python 组件路径未生效'
assert os.fsdecode(env.get(b'INVESTOR_DB_PATH', b'/www/wwwroot/stock-tools/investor_events.sqlite3')) == sys.argv[2], '数据库路径发生变化'
PY
trap - ERR
printf '修复完成；数据库路径未变：%s\n原程序备份：%s\n' "$db_path" "$backup"
printf '请在网站点击“检查更新”，等待采集结束后查看各项状态。\n'
printf 'SEC 要求使用可联系邮箱；如 test@test.com 不可接收邮件，请更换为实际联系邮箱。\n'
