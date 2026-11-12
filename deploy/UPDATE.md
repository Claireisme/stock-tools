# 更新已安装的数值工具箱

此更新包适用于之前使用本项目安装脚本安装到 `/opt/stock-tools` 的 Ubuntu/Debian 服务器。更新脚本检查原有服务标记、备份旧程序、更新程序并重启服务；不会修改现有 Nginx 配置、域名或 HTTPS 证书。若服务器采用其他部署方式，请先检查实际安装目录和服务，不要运行此脚本。

```sh
sudo bash update.sh
```

为期权行情配置 Alpaca Paper Trading 密钥：

```sh
sudo touch /etc/stock-tools.env
sudo chmod 600 /etc/stock-tools.env
sudo nano /etc/stock-tools.env
```

在编辑器中添加或修改以下三行，替换为自己的密钥并保存。保留文件中的其他配置。

```text
ALPACA_API_KEY=你的APIKey
ALPACA_API_SECRET=你的APISecret
ALPACA_ENV=paper
```

`Ctrl+O`、回车保存，`Ctrl+X` 退出。重启并检查服务：

```sh
sudo systemctl restart stock-tools
sudo systemctl status stock-tools --no-pager
```

访问原网站并刷新页面；进入期权收益计算器，搜索美股并选择合约。若出现问题，查看 `sudo journalctl -u stock-tools -n 50 --no-pager`。行情接口和隐含波动率取决于 Alpaca 数据权限，免费 Indicative 报价为参考值，成交数据延迟约 15 分钟。
