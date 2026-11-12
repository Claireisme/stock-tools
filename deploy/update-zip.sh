#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/www/wwwroot/stock-tools
SERVICE=stock-tools.service
DROPIN_DIR=/etc/systemd/system/stock-tools.service.d
DROPIN="$DROPIN_DIR/investor-tracker.conf"
MARK='# Managed by stock-tools investor tracker'
files=(index.html style.css app.js options.css options.js options-math.js investors.css investors.js investor-profile.js ark-holdings.js ark-position-chart.js investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json server.py configure_alpaca.py)
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail '请以 root 运行。'
[[ $# -eq 1 && -f "$1" ]] || fail '用法：bash update-zip.sh 网站压缩包.zip'
command -v systemctl >/dev/null && command -v python3 >/dev/null && command -v curl >/dev/null || fail '需要 systemctl、python3 和 curl。'
[[ -d "$APP_DIR" && ! -L "$APP_DIR" ]] || fail "找不到网站目录 $APP_DIR。"
[[ $(systemctl show "$SERVICE" -p WorkingDirectory --value) == "$APP_DIR" ]] || fail 'stock-tools 服务未配置为使用预期的网站目录。请先配置并启动该服务。'
systemctl is-active --quiet "$SERVICE" || fail 'stock-tools 服务未运行，请先检查服务状态。'
[[ ! -L "$DROPIN_DIR" && ! -L "$DROPIN" ]] || fail '服务配置目录或文件是符号链接。'
if [[ -e "$DROPIN" ]] && ! head -n 1 "$DROPIN" | grep -Fxq "$MARK"; then fail '现有 investor-tracker.conf 不属于本程序，未覆盖。'; fi
work=$(mktemp -d /tmp/stock-tools-update.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
python3 - "$1" "$work" "${files[@]}" <<'PY'
import pathlib, sys, zipfile
archive, work, *names = sys.argv[1:]
with zipfile.ZipFile(archive) as z:
    for name in names:
        matches = [i for i in z.infolist() if i.filename == name and not i.is_dir()]
        if len(matches) != 1 or matches[0].file_size > 5_000_000:
            raise SystemExit(f'无效的更新包：{name}')
        (pathlib.Path(work) / name).write_bytes(z.read(matches[0]))
PY
python3 -m py_compile "$work/server.py" "$work/configure_alpaca.py" "$work/investor_tracker.py" "$work/investor_profiles.py" "$work/ark_tracker.py" "$work/ark_holdings.py" "$work/ark_history.py" "$work/thirteenf_tracker.py" "$work/congress_tracker.py" "$work/senate_tracker.py"
for file in "${files[@]}"; do [[ ! -L "$APP_DIR/$file" ]] || fail "现有文件是符号链接：$file"; done
backup=$(mktemp -d /var/backups/stock-tools.XXXXXXXX)
chmod 700 "$backup"
if [[ -f "$DROPIN" ]]; then cp -p "$DROPIN" "$backup/service.conf"; fi
for file in "${files[@]}"; do if [[ -f "$APP_DIR/$file" ]]; then cp -p -- "$APP_DIR/$file" "$backup/$file"; fi; done
restore() {
  printf '更新未通过检查，正在恢复旧文件。\n' >&2
  if [[ -f "$backup/service.conf" ]]; then
    install -d -m 0755 "$DROPIN_DIR"
    cp -p "$backup/service.conf" "$DROPIN"
  else
    rm -f -- "$DROPIN"
  fi
  systemctl daemon-reload || true
  for file in "${files[@]}"; do if [[ -f "$backup/$file" ]]; then cp -p -- "$backup/$file" "$APP_DIR/$file"; else rm -f -- "$APP_DIR/$file"; fi; done
  systemctl restart "$SERVICE" || printf '旧服务未能启动，请检查 systemctl status stock-tools。\n' >&2
  printf '备份位置：%s\n' "$backup" >&2
  exit 1
}
trap restore ERR
for file in "${files[@]}"; do
  if [[ -f "$APP_DIR/$file" ]]; then
    install -m "$(stat -c '%a' "$APP_DIR/$file")" -o "$(stat -c '%u' "$APP_DIR/$file")" -g "$(stat -c '%g' "$APP_DIR/$file")" "$work/$file" "$APP_DIR/$file"
  else
    install -m 0644 "$work/$file" "$APP_DIR/$file"
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
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8001/zh/ -o /dev/null
trap - ERR
printf '更新完成。旧文件备份：%s\n' "$backup"
