# 持仓追踪服务排查

以下步骤针对独立的 `stock-tools.service`；先确认服务和 Python 环境，再修改服务器配置。诊断脚本不输出邮箱、密钥或环境变量的值，也不会修改数据库：

```sh
sudo bash /opt/stock-tools-source/deploy/diagnose-investor.sh
```

如果脚本尚未部署，可先更新源码，或将诊断脚本复制到服务器后运行。检查结果里的“启动解释器”是实际进程启动时使用的 Python 路径；若服务配置了特殊的 `PYTHONPATH`，仅运行该解释器的检测结果可能与服务进程不同。

如果检测结果显示 Python 使用虚拟环境，将下面的路径替换为诊断输出的解释器路径，再安装依赖：

```sh
service_python=/请替换为诊断结果中的绝对路径
sudo "$service_python" -m pip install 'xlrd>=2.0.1,<3' 'pypdf>=4,<7'
```

如果显示系统环境、无法确定解释器或没有 pip，请先确认服务器系统及服务设置；不要直接对未知的系统 Python 使用 `--break-system-packages`。不同 Linux 发行版提供的系统包版本不同，也不一定被当前服务使用的 Python 识别。

SEC 要求 User-Agent 包含真实可联系邮箱。以管理员方式编辑 `/etc/stock-tools.env`，在保留已有 Alpaca 密钥和其他内容的前提下添加或修改一行；将示例邮箱替换为实际地址：

```text
SEC_USER_AGENT="Stock Tools your-real-email@example.com"
```

这个地址会作为请求标识发送给 SEC，不应提交到 GitHub。检查环境文件权限应限制对敏感配置的访问。若反向代理改写 Host，导致“检查更新”显示跨站错误，还需要添加网站的公开来源（不含路径或末尾斜杠），例如：

```text
PUBLIC_ORIGIN="https://tool.respecllc.com"
```

依赖和配置完成后：

```sh
sudo systemctl restart stock-tools.service
sudo systemctl status stock-tools.service --no-pager
```

然后在网站点击“检查更新”，等待各来源检查完成；如仍有错误，在不公开密钥的前提下检查服务日志。不要为了修复依赖而覆盖 `/var/lib/stock-tools/investor_events.sqlite3`。
