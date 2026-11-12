#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/stock-tools
SERVICE=/etc/systemd/system/stock-tools.service
DROPIN_DIR=/etc/systemd/system/stock-tools.service.d
DROPIN="$DROPIN_DIR/market-data.conf"
MARK='# Managed by stock-tools updater'
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
files=(index.html style.css app.js options.css options.js options-math.js investors.css investors.js investor-profile.js ark-holdings.js ark-position-chart.js investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json server.py)
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || fail '请使用 sudo bash update.sh 运行。'
command -v systemctl >/dev/null || fail '仅支持使用 systemd 的 Linux 服务器。'
[[ -d /run/systemd/system ]] || fail '当前系统未运行 systemd。'
[[ -d "$APP_DIR" && ! -L "$APP_DIR" && -f "$APP_DIR/.stock-tools-managed" ]] || fail '未找到由原安装脚本管理的 /opt/stock-tools；请先检查旧站点的安装方式。'
[[ -f "$SERVICE" && ! -L "$SERVICE" ]] && head -n 1 "$SERVICE" | grep -Fxq '# Managed by stock-tools installer' || fail '未找到原安装脚本管理的 systemd 服务，未修改。'
[[ ! -L "$DROPIN_DIR" && ! -L "$DROPIN" ]] || fail '服务配置目录或文件是符号链接，请先检查。'
if [[ -e "$DROPIN" ]] && ! head -n 1 "$DROPIN" | grep -Fxq "$MARK"; then fail '现有 market-data.conf 不是本脚本管理的文件，未覆盖。'; fi
for file in "${files[@]}"; do [[ -f "$SCRIPT_DIR/$file" ]] || fail "更新包中缺少 $file。"; done

backup_dir=$(mktemp -d /opt/stock-tools-backup.XXXXXXXX)
chmod 0700 "$backup_dir"
for file in "${files[@]}"; do
  if [[ -f "$APP_DIR/$file" ]]; then cp -p "$APP_DIR/$file" "$backup_dir/$file"; fi
done
for file in "${files[@]}"; do install -m 0644 "$SCRIPT_DIR/$file" "$APP_DIR/$file"; done
install -d -m 0755 "$DROPIN_DIR"
cat > "$DROPIN" <<'EOF'
# Managed by stock-tools updater
[Service]
StateDirectory=stock-tools
Environment=INVESTOR_DB_PATH=/var/lib/stock-tools/investor_events.sqlite3
EnvironmentFile=-/etc/stock-tools.env
EOF
chmod 0644 "$DROPIN"
systemctl daemon-reload
systemctl restart stock-tools.service
systemctl is-active --quiet stock-tools.service || fail "服务未启动；旧程序备份在 $backup_dir，请查看 journalctl -u stock-tools -n 50。"
printf '更新完成。旧程序备份：%s\n' "$backup_dir"
printf 'Alpaca 密钥配置在 /etc/stock-tools.env，设置后执行 sudo systemctl restart stock-tools。\n'
