#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=/opt/stock-tools-source
fail() { printf '错误：%s\n' "$*" >&2; exit 1; }
[[ $(id -u) -eq 0 ]] || fail '请以 root 运行。'
for command in git flock; do command -v "$command" >/dev/null || fail "缺少 $command。"; done
exec 9>/run/lock/stock-tools-update.lock
flock -n 9 || fail '已有更新正在进行，请稍后重试。'
[[ -d "$SOURCE_DIR/.git" && ! -L "$SOURCE_DIR" ]] || fail "找不到 Git 仓库 $SOURCE_DIR。"
[[ $(git -C "$SOURCE_DIR" symbolic-ref --short HEAD) == main ]] || fail '源码目录不在 main 分支。'
[[ -z $(git -C "$SOURCE_DIR" status --porcelain) ]] || fail '源码目录有未提交的修改，请先检查。'
case "$(git -C "$SOURCE_DIR" remote get-url origin)" in
  https://github.com/Claireisme/stock-tools.git|https://github.com/Claireisme/stock-tools|git@github.com:Claireisme/stock-tools.git) ;;
  *) fail '源码目录 origin 不是预期的 GitHub 仓库。' ;;
esac
GIT_TERMINAL_PROMPT=0 git -C "$SOURCE_DIR" pull --ff-only origin main
bash "$SOURCE_DIR/deploy/apply-git.sh"
