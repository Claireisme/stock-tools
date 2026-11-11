#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=/opt/stock-tools-source
APP_DIR=/www/wwwroot/stock-tools
SERVICE=stock-tools.service
files=(index.html style.css app.js options.css options.js options-math.js server.py configure_alpaca.py)
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail '请以 root 运行。'
for command in git python3 curl systemctl cmp; do command -v "$command" >/dev/null || fail "缺少 $command。"; done
[[ -d "$APP_DIR" && ! -L "$APP_DIR" ]] || fail "找不到网站目录 $APP_DIR。"
[[ -d "$SOURCE_DIR/.git" && ! -L "$SOURCE_DIR" ]] || fail "找不到 Git 仓库 $SOURCE_DIR。"
[[ -z $(git -C "$SOURCE_DIR" status --porcelain) ]] || fail '源码目录有未提交的修改，请先检查。'
for file in "${files[@]}"; do
  [[ -f "$SOURCE_DIR/$file" && ! -L "$SOURCE_DIR/$file" ]] || fail "源码缺少文件或文件是符号链接：$file"
  [[ -f "$APP_DIR/$file" && ! -L "$APP_DIR/$file" ]] || fail "网站文件不存在或是符号链接：$file"
done

backend_changed=0
cmp -s "$SOURCE_DIR/server.py" "$APP_DIR/server.py" || backend_changed=1
if (( backend_changed )); then
  # Only restart an independently managed service that owns the current listener.
  systemctl is-active --quiet "$SERVICE" || fail '服务端代码有更新，但没有运行中的独立 stock-tools.service；请先在宝塔中配置可单独重启的项目服务。未修改网站。'
  [[ $(systemctl show "$SERVICE" -p WorkingDirectory --value) == "$APP_DIR" ]] || fail '服务端代码有更新，但 stock-tools.service 的工作目录不匹配。未修改网站。'
  pid=$(systemctl show "$SERVICE" -p MainPID --value)
  [[ "$pid" =~ ^[1-9][0-9]*$ && -r "/proc/$pid/cmdline" ]] || fail '无法确认 stock-tools 服务进程。未修改网站。'
  tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq "$APP_DIR/server.py" || fail 'stock-tools.service 启动的不是项目服务。未修改网站。'
  command -v ss >/dev/null || fail '缺少 ss，无法确认 8001 端口的服务进程。未修改网站。'
  ss -ltnp '( sport = :8001 )' | grep -Eq "pid=${pid}([,)]|$)" || fail 'stock-tools.service 没有监听 8001；为避免重启其他服务，未修改网站。'
fi

work=$(mktemp -d /tmp/stock-tools-check.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
PYTHONPYCACHEPREFIX="$work" python3 -m py_compile "$SOURCE_DIR/server.py" "$SOURCE_DIR/configure_alpaca.py"
backup=$(mktemp -d /var/backups/stock-tools.XXXXXXXX)
chmod 700 "$backup"
for file in "${files[@]}"; do cp -p -- "$APP_DIR/$file" "$backup/$file"; done
restore() {
  trap - ERR
  printf '更新未通过检查，正在恢复旧文件。\n' >&2
  for file in "${files[@]}"; do cp -p -- "$backup/$file" "$APP_DIR/$file" || printf '恢复失败：%s\n' "$file" >&2; done
  if (( backend_changed )); then systemctl restart "$SERVICE" || printf '旧服务未能启动，请检查 systemctl status stock-tools。\n' >&2; fi
  printf '备份位置：%s\n' "$backup" >&2
  exit 1
}
trap restore ERR
for file in "${files[@]}"; do
  install -m "$(stat -c '%a' "$APP_DIR/$file")" -o "$(stat -c '%u' "$APP_DIR/$file")" -g "$(stat -c '%g' "$APP_DIR/$file")" "$SOURCE_DIR/$file" "$APP_DIR/$file"
done
if (( backend_changed )); then
  systemctl restart "$SERVICE"
  systemctl is-active --quiet "$SERVICE"
fi
curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 1 --max-time 5 http://127.0.0.1:8001/zh/ -o /dev/null
for file in index.html options.js options.css; do
  curl --fail --silent --show-error --max-time 5 "http://127.0.0.1:8001/$file" -o "$work/$file"
  if ! cmp -s "$SOURCE_DIR/$file" "$work/$file"; then
    printf '错误：8001 端口返回的 %s 与更新文件不一致。\n' "$file" >&2
    false
  fi
done
trap - ERR
printf '更新完成：%s\n旧文件备份：%s\n' "$(git -C "$SOURCE_DIR" rev-parse --short HEAD)" "$backup"
