# GitHub 更新网站

适用于网站目录 `/www/wwwroot/stock-tools`、源码目录 `/opt/stock-tools-source`、网站监听本机 8001 的服务器。源码目录应是 `Claireisme/stock-tools` 的 main 分支，工作区没有未提交修改。

首次获取包含更新脚本的代码：

```sh
git -C /opt/stock-tools-source pull --ff-only origin main
bash /opt/stock-tools-source/deploy/update-git.sh
```

以后每次更新只需运行：

```sh
bash /opt/stock-tools-source/deploy/update-git.sh
```

脚本先拉取 GitHub main，再备份旧程序到 `/var/backups/` 并更新网站文件。不会覆盖 `.alpaca-config.json`、Nginx 或宝塔配置；更新后检查本机 8001，失败时尝试恢复旧文件。静态页面文件更新不重启服务。

当 `server.py` 有变化时，脚本只会重启一个已运行的独立 `stock-tools.service`，且其工作目录、启动程序和 8001 监听必须与项目一致。否则脚本在修改网站前停止，请先在宝塔中为本项目配置可单独重启的服务；脚本不会重启整个宝塔。已拉取的源码会保留，服务配置好后再次运行更新命令即可。
