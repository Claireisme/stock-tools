#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=/opt/stock-tools-source
APP_DIR=/www/wwwroot/stock-tools
SERVICE=stock-tools.service
DROPIN_DIR=/etc/systemd/system/stock-tools.service.d
DROPIN="$DROPIN_DIR/investor-tracker.conf"
MARK='# Managed by stock-tools investor tracker'
files=(index.html style.css app.js options.css options.js options-math.js investors.css investors.js investor-profile.js ark-holdings.js ark-position-chart.js investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json server.py configure_alpaca.py)
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail '请以 root 运行。'
for command in git python3 curl systemctl cmp; do command -v "$command" >/dev/null || fail "缺少 $command。"; done
[[ -d "$APP_DIR" && ! -L "$APP_DIR" ]] || fail "找不到网站目录 $APP_DIR。"
[[ -d "$SOURCE_DIR/.git" && ! -L "$SOURCE_DIR" ]] || fail "找不到 Git 仓库 $SOURCE_DIR。"
[[ -z $(git -C "$SOURCE_DIR" status --porcelain) ]] || fail '源码目录有未提交的修改，请先检查。'
for file in "${files[@]}"; do
  [[ -f "$SOURCE_DIR/$file" && ! -L "$SOURCE_DIR/$file" ]] || fail "源码缺少文件或文件是符号链接：$file"
  [[ ! -L "$APP_DIR/$file" ]] || fail "网站文件是符号链接：$file"
done

backend_changed=0
for file in server.py investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json; do
  cmp -s "$SOURCE_DIR/$file" "$APP_DIR/$file" || backend_changed=1
done
if true; then
  # Only restart an independently managed service that owns the current listener.
  systemctl is-active --quiet "$SERVICE" || fail '服务端代码有更新，但没有运行中的独立 stock-tools.service；请先在宝塔中配置可单独重启的项目服务。未修改网站。'
  [[ $(systemctl show "$SERVICE" -p WorkingDirectory --value) == "$APP_DIR" ]] || fail '服务端代码有更新，但 stock-tools.service 的工作目录不匹配。未修改网站。'
  pid=$(systemctl show "$SERVICE" -p MainPID --value)
  [[ "$pid" =~ ^[1-9][0-9]*$ && -r "/proc/$pid/cmdline" ]] || fail '无法确认 stock-tools 服务进程。未修改网站。'
  tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq "$APP_DIR/server.py" || fail 'stock-tools.service 启动的不是项目服务。未修改网站。'
  command -v ss >/dev/null || fail '缺少 ss，无法确认 8001 端口的服务进程。未修改网站。'
  ss -ltnp '( sport = :8001 )' | grep -Eq "pid=${pid}([,)]|$)" || fail 'stock-tools.service 没有监听 8001；为避免重启其他服务，未修改网站。'
fi

[[ ! -L "$DROPIN_DIR" && ! -L "$DROPIN" ]] || fail '服务配置目录或文件是符号链接。'
if [[ -e "$DROPIN" ]] && ! head -n 1 "$DROPIN" | grep -Fxq "$MARK"; then fail '现有 investor-tracker.conf 不属于本程序，未覆盖。'; fi
work=$(mktemp -d /tmp/stock-tools-check.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
PYTHONPYCACHEPREFIX="$work" python3 -m py_compile "$SOURCE_DIR/server.py" "$SOURCE_DIR/configure_alpaca.py" "$SOURCE_DIR/investor_tracker.py" "$SOURCE_DIR/investor_profiles.py" "$SOURCE_DIR/ark_tracker.py" "$SOURCE_DIR/ark_holdings.py" "$SOURCE_DIR/ark_history.py" "$SOURCE_DIR/thirteenf_tracker.py" "$SOURCE_DIR/congress_tracker.py" "$SOURCE_DIR/senate_tracker.py"
backup=$(mktemp -d /var/backups/stock-tools.XXXXXXXX)
chmod 700 "$backup"
if [[ -f "$DROPIN" ]]; then cp -p "$DROPIN" "$backup/service.conf"; fi
for file in "${files[@]}"; do if [[ -f "$APP_DIR/$file" ]]; then cp -p -- "$APP_DIR/$file" "$backup/$file"; fi; done
restore() {
  trap - ERR
  printf '更新未通过检查，正在恢复旧文件。\n' >&2
  if [[ -f "$backup/service.conf" ]]; then
    install -d -m 0755 "$DROPIN_DIR"
    cp -p "$backup/service.conf" "$DROPIN"
  else
    rm -f -- "$DROPIN"
  fi
  systemctl daemon-reload || true
  for file in "${files[@]}"; do if [[ -f "$backup/$file" ]]; then cp -p -- "$backup/$file" "$APP_DIR/$file" || printf '恢复失败：%s\n' "$file" >&2; else rm -f -- "$APP_DIR/$file"; fi; done
  systemctl restart "$SERVICE" || printf '旧服务未能启动，请检查 systemctl status stock-tools。\n' >&2
  printf '备份位置：%s\n' "$backup" >&2
  exit 1
}
trap restore ERR
for file in "${files[@]}"; do
  if [[ -f "$APP_DIR/$file" ]]; then
    install -m "$(stat -c '%a' "$APP_DIR/$file")" -o "$(stat -c '%u' "$APP_DIR/$file")" -g "$(stat -c '%g' "$APP_DIR/$file")" "$SOURCE_DIR/$file" "$APP_DIR/$file"
  else
    install -m 0644 "$SOURCE_DIR/$file" "$APP_DIR/$file"
  fi
done
install -d -m 0755 "$DROPIN_DIR"
cat > "$DROPIN" <<'EOF'
# Managed by stock-tools investor tracker
[Service]
StateDirectory=stock-tools
Environment=INVESTOR_DB_PATH=/var/lib/stock-tools/investor_events.sqlite3
EnvironmentFile=-/etc/stock-tools.env
EOF
chmod 0644 "$DROPIN"
systemctl daemon-reload
systemctl restart "$SERVICE"
systemctl is-active --quiet "$SERVICE"
curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 1 --max-time 5 http://127.0.0.1:8001/zh/ -o /dev/null
for file in index.html options.js options.css investors.js investors.css; do
  curl --fail --silent --show-error --max-time 5 "http://127.0.0.1:8001/$file" -o "$work/$file"
  if ! cmp -s "$SOURCE_DIR/$file" "$work/$file"; then
    printf '错误：8001 端口返回的 %s 与更新文件不一致。\n' "$file" >&2
    false
  fi
done
trap - ERR
printf '更新完成：%s\n旧文件备份：%s\n' "$(git -C "$SOURCE_DIR" rev-parse --short HEAD)" "$backup"
