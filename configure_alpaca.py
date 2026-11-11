#!/usr/bin/env python3
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / '.alpaca-config.json'


def save_config(key, secret, environment='paper'):
    if not key or not secret or environment not in ('paper', 'live'):
        raise ValueError('密钥不能为空，账户环境必须是 paper 或 live。')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=ROOT, prefix='.alpaca-config-', delete=False) as file:
            temporary = file.name
            os.fchmod(file.fileno(), 0o600)
            json.dump({'ALPACA_API_KEY': key, 'ALPACA_API_SECRET': secret, 'ALPACA_ENV': environment}, file)
            file.write('\n')
        os.replace(temporary, CONFIG_PATH)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def main():
    if not sys.stdin.isatty():
        raise ValueError('请在终端中交互运行此程序。')
    print('请输入 Alpaca Paper Trading 的 API Key 和 Secret（输入时不会显示）。')
    key = getpass.getpass('API Key: ').strip()
    secret = getpass.getpass('API Secret: ').strip()
    save_config(key, secret)
    print('配置已保存。重启项目服务后生效。')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'配置失败：{error}', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\n已取消，原配置未更改。', file=sys.stderr)
        sys.exit(1)
