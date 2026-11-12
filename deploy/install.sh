#!/usr/bin/env bash
set -Eeuo pipefail

MARK='# Managed by stock-tools installer'
APP_DIR=/opt/stock-tools
SERVICE=/etc/systemd/system/stock-tools.service
SITE=/etc/nginx/sites-available/stock-tools
ENABLED=/etc/nginx/sites-enabled/stock-tools
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

fail() { printf '\n错误：%s\n' "$*" >&2; exit 1; }
owned() { [[ -f "$1" ]] && head -n 1 "$1" | grep -Fxq "$MARK"; }

[[ $(id -u) -eq 0 ]] || fail '请使用 sudo bash install.sh 运行。'
[[ -t 0 ]] || fail '安装脚本需要交互终端。'
command -v apt-get >/dev/null && command -v systemctl >/dev/null || fail '仅支持使用 systemd 的 Ubuntu 或 Debian。'
[[ -d /run/systemd/system ]] || fail '当前系统未运行 systemd。'
for file in index.html style.css app.js options.css options.js options-math.js investors.css investors.js investor-profile.js ark-holdings.js ark-position-chart.js investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json server.py; do
  [[ -f "$SCRIPT_DIR/$file" ]] || fail "安装包中缺少 $file。"
done

printf '此脚本将安装 Python 和 Nginx，配置 stock-tools 服务并开放网站。\n'
read -r -p '请输入已指向本服务器的域名（例如 tools.example.com）：' domain
# A domain is used as data in Nginx and Certbot, never as arbitrary configuration.
[[ ${#domain} -le 253 && "$domain" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ && "$domain" == *.* && ! "$domain" =~ ^[0-9.]+$ ]] || fail '请输入有效的英文域名，不能使用 IP 地址或通配符。'
IFS='.' read -r -a labels <<< "$domain"
for label in "${labels[@]}"; do
  [[ ${#label} -le 63 && "$label" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$ ]] || fail '域名格式无效。'
done
domain=${domain,,}
read -r -p '是否申请 HTTPS 证书？请先将域名解析到本机并开放 80、443 端口 [Y/n]：' https_answer
case "$https_answer" in ''|[Yy]|[Yy][Ee][Ss]) use_https=1 ;; [Nn]|[Nn][Oo]) use_https=0 ;; *) fail '请输入 y 或 n。' ;; esac

[[ ! -L "$APP_DIR" && ! -L "$SERVICE" && ! -L "$SITE" ]] || fail '目标目录或配置文件是符号链接，请先检查。'
if [[ -e "$APP_DIR" && ! -f "$APP_DIR/.stock-tools-managed" ]]; then fail "$APP_DIR 已存在且不是本脚本管理的目录，请检查后再操作。"; fi
if [[ -e "$SERVICE" ]] && ! owned "$SERVICE"; then fail "$SERVICE 已存在且不属于本脚本，未覆盖。"; fi
if [[ -e "$SITE" ]] && ! owned "$SITE"; then fail "$SITE 已存在且不属于本脚本，未覆盖。"; fi
if [[ -L "$ENABLED" ]]; then
  [[ $(readlink "$ENABLED") == "$SITE" ]] || fail "$ENABLED 指向其他配置，未覆盖。"
elif [[ -e "$ENABLED" ]]; then fail "$ENABLED 已存在且不是本脚本的链接，未覆盖。"; fi
if id stock-tools >/dev/null 2>&1 && [[ ! -f "$APP_DIR/.stock-tools-managed" ]]; then fail 'stock-tools 用户已存在，但不是本脚本创建的安装，未继续。'; fi
if [[ -f "$SITE" ]] && ! awk -v domain="$domain" '$1 == "server_name" { for (i=2; i<=NF; i++) { gsub(/;/, "", $i); if (tolower($i) == domain) found=1 } } END { exit !found }' "$SITE"; then
  fail '现有 stock-tools 站点的域名与输入不一致，请先手动处理旧配置。'
fi
command -v ss >/dev/null || fail '缺少 ss 命令，无法检查 8000 端口。请先安装 iproute2。'
if ss -ltnH '( sport = :8000 )' | grep -q .; then
  systemctl is-active --quiet stock-tools.service || fail '8000 端口已被占用，请先检查占用进程。'
fi
if [[ -d /etc/nginx/sites-enabled ]]; then
  while IFS= read -r -d '' config; do
    [[ "$config" == "$ENABLED" ]] && continue
    if grep -Ehi '^[[:space:]]*server_name[[:space:]]+' "$config" 2>/dev/null | tr ' ;\t' '\n\n\n' | grep -Fxiq "$domain"; then
      fail "其他启用的 Nginx 站点已使用 $domain：$config"
    fi
  done < <(find /etc/nginx/sites-enabled -maxdepth 1 \( -type f -o -type l \) -print0)
fi

printf '\n即将安装到 %s，绑定域名 %s。不会更改防火墙规则。\n' "$APP_DIR" "$domain"
read -r -p '确认继续？[y/N]：' confirm
case "$confirm" in [Yy]|[Yy][Ee][Ss]) ;; *) printf '已取消。\n'; exit 0 ;; esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
packages=(python3 nginx)
if (( use_https )); then packages+=(certbot python3-certbot-nginx); fi
apt-get install -y "${packages[@]}"

if ! id stock-tools >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin stock-tools
fi
install -d -m 0755 "$APP_DIR"
touch "$APP_DIR/.stock-tools-managed"
chmod 0644 "$APP_DIR/.stock-tools-managed"
for file in index.html style.css app.js options.css options.js options-math.js investors.css investors.js investor-profile.js ark-holdings.js ark-position-chart.js investor_tracker.py investor_profiles.py ark_tracker.py ark_holdings.py ark_history.py thirteenf_tracker.py congress_tracker.py senate_tracker.py congress_identities.json investor_watchlist.json server.py; do
  install -m 0644 "$SCRIPT_DIR/$file" "$APP_DIR/$file"
done
chown -R root:root "$APP_DIR"

cat > "$SERVICE" <<'EOF'
# Managed by stock-tools installer
[Unit]
Description=Stock Tools
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=stock-tools
Group=stock-tools
WorkingDirectory=/opt/stock-tools
StateDirectory=stock-tools
Environment=INVESTOR_DB_PATH=/var/lib/stock-tools/investor_events.sqlite3
EnvironmentFile=-/etc/stock-tools.env
ExecStart=/usr/bin/python3 /opt/stock-tools/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now stock-tools.service
systemctl restart stock-tools.service
systemctl is-active --quiet stock-tools.service || fail '应用未成功启动，请运行 journalctl -u stock-tools -n 50 检查。'

# Preserve an existing installer-managed Nginx file: Certbot may have added TLS settings.
created_site=0
if [[ ! -f "$SITE" ]]; then
  cat > "$SITE" <<EOF
# Managed by stock-tools installer
server {
    listen 80;
    server_name $domain;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
    }
}
EOF
  created_site=1
fi
created_link=0
if [[ ! -L "$ENABLED" ]]; then ln -s "$SITE" "$ENABLED"; created_link=1; fi
if ! nginx -t; then
  (( created_link )) && rm -f "$ENABLED"
  (( created_site )) && rm -f "$SITE"
  fail 'Nginx 配置检查失败；新建的站点配置已撤回，请检查现有配置。'
fi
systemctl enable --now nginx
systemctl reload nginx

if (( use_https )); then
  printf '\n开始申请证书，Certbot 可能会要求填写邮箱并确认其服务条款。\n'
  unset DEBIAN_FRONTEND
  if certbot --nginx -d "$domain"; then
    printf '\n完成：HTTPS 网站应可通过 https://%s 访问。\n' "$domain"
  else
    printf '\nHTTPS 证书申请未成功，请检查域名解析、80/443 端口和 Certbot 输出，并确认 Nginx 配置后重试：\n  sudo certbot --nginx -d %s\n' "$domain" >&2
    exit 1
  fi
else
  printf '\n完成：HTTP 网站应可通过 http://%s 访问。\n' "$domain"
fi
printf '日志：sudo journalctl -u stock-tools -f\n'
printf '请从网站分别测试各行情源；接口的可用性取决于服务器网络和数据源。\n'
