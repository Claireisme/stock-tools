# GitHub 更新网站

本说明仅适用于网站位于 `/www/wwwroot/stock-tools`、以 `stock-tools.service` 运行且监听本机 8001 端口的服务器。源码单独保存在 `/opt/stock-tools-source`，不要在网站目录中直接运行 `git pull`。请先确认服务已配置为开机启动并正在运行。

首次配置：以 root 登录服务器，生成只用于此仓库的密钥。出现确认覆盖时不要覆盖已有密钥，应改用其他文件名。

```bash
ssh-keygen -t ed25519 -f /root/.ssh/stock-tools-deploy -N ''
cat /root/.ssh/stock-tools-deploy.pub
```

在 GitHub 仓库 Settings → Deploy keys 中添加显示的公钥，保持只读；不要上传没有 `.pub` 后缀的私钥。首次连接时确认 GitHub 主机指纹。然后克隆仓库（目录须不存在）：

```bash
GIT_SSH_COMMAND='ssh -i /root/.ssh/stock-tools-deploy -o IdentitiesOnly=yes' git clone --branch main git@github.com:Claireisme/stock-tools.git /opt/stock-tools-source
```

以后每次以 root 登录后执行：

```bash
GIT_SSH_COMMAND='ssh -i /root/.ssh/stock-tools-deploy -o IdentitiesOnly=yes' git -C /opt/stock-tools-source pull --ff-only origin main && bash /opt/stock-tools-source/deploy/apply-git.sh
```

脚本检查服务、备份旧网站文件、复制网站文件并重启服务，然后检查中文页面。检查失败时会尝试恢复备份；备份保存在 `/var/backups/`。不会修改 `.alpaca-config.json`、`.htaccess`、Nginx 或 systemd 配置。若失败，按提示检查服务：

```bash
systemctl status stock-tools --no-pager
journalctl -u stock-tools -n 50 --no-pager
```
