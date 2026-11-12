#!/usr/bin/env bash
set -Eeuo pipefail

service=stock-tools.service
app=/www/wwwroot/stock-tools
revision=${1:-}
files=(investors.js investor-profile.js investors.css index.html)
baseline=(d271388a314e5804c26b37d5dc0a0d5b18ab037001ef80273b2a872a0487688f 148e15b80ddf901e28d7675c0016114bca929bfe18f56d5454145c5755b53bb8 b4171a685b8eb68f9918fcb6cbe8fbf9e0f860750250197bc2e891feb6939734 911ba4aa99dcb15b7685c76aa7fec6e2f2bdc9ae8ed65835a829269345140405)
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail '请使用 root 运行。'
[[ $revision =~ ^[0-9a-f]{40}$ ]] || fail '请提供完整的目标版本号。'
for command in systemctl curl sha256sum ss flock; do command -v "$command" >/dev/null || fail "缺少 $command。"; done
exec 9>/run/lock/stock-tools-update.lock
flock -n 9 || fail '已有更新正在进行，请稍后重试。'
[[ -d $app && ! -L $app ]] || fail '网站目录不匹配。'
systemctl is-active --quiet "$service" || fail '服务未运行。'
[[ $(systemctl show "$service" -p WorkingDirectory --value) == "$app" ]] || fail '服务工作目录不匹配。'
pid=$(systemctl show "$service" -p MainPID --value)
[[ $pid =~ ^[1-9][0-9]*$ && -r /proc/$pid/cmdline ]] || fail '无法检查服务进程。'
tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq "$app/server.py" || fail '服务未运行预期的网站程序。'
ss -ltnp '( sport = :8001 )' | grep -Eq "pid=${pid}([,)]|$)" || fail '服务进程未监听预期端口。'
work=$(mktemp -d /tmp/stock-tools-timezone.XXXXXXXX)
staged=''
trap 'rm -rf -- "$work"; if [[ -n $staged ]]; then rm -f -- "$staged"; fi' EXIT
for i in "${!files[@]}"; do
  file=${files[$i]}
  [[ -f $app/$file && ! -L $app/$file ]] || fail "网站文件缺失或是符号链接：$file"
  curl -fsSL "https://raw.githubusercontent.com/Claireisme/stock-tools/$revision/$file" -o "$work/$file"
  [[ -s $work/$file ]] || fail "下载的文件为空：$file"
  old=$(sha256sum "$app/$file" | cut -d' ' -f1)
  new=$(sha256sum "$work/$file" | cut -d' ' -f1)
  [[ $old == "${baseline[$i]}" || $old == "$new" ]] || fail "网站文件已被修改：$file；未覆盖。"
done
backup=$(mktemp -d /var/backups/stock-tools-timezone.XXXXXXXX)
chmod 700 "$backup"
for file in "${files[@]}"; do cp -p -- "$app/$file" "$backup/$file"; done
restore() {
  trap - ERR
  printf '更新未通过检查，正在恢复原文件。\n' >&2
  for file in "${files[@]}"; do cp -p -- "$backup/$file" "$app/$file" || printf '恢复失败：%s\n' "$file" >&2; done
  printf '备份位置：%s\n' "$backup" >&2
  exit 1
}
trap restore ERR
for file in "${files[@]}"; do
  staged=$(mktemp "$app/.timezone.XXXXXXXX")
  install -m "$(stat -c '%a' "$app/$file")" -o "$(stat -c '%u' "$app/$file")" -g "$(stat -c '%g' "$app/$file")" "$work/$file" "$staged"
  mv -f -- "$staged" "$app/$file"
  staged=''
done
for file in "${files[@]}"; do
  curl -fsS --max-time 5 "http://127.0.0.1:8001/$file" -o "$work/check-$file"
  cmp -s "$work/$file" "$work/check-$file" || false
done
trap - ERR
printf '页面更新完成，旧文件备份：%s\n' "$backup"
