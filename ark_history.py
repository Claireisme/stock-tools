"""History of ARK end-of-day positions and separately sourced stock prices."""
import json
import math
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
import ark_holdings


def history(db, fund, security_id, request, *, today=None, asset_host='https://paper-api.alpaca.markets'):
    if fund not in ark_holdings.FILES:
        raise ValueError('未知 ARK 基金。')
    if not isinstance(security_id, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}', security_id):
        raise ValueError('无效的证券标识。')
    with db() as conn:
        ark_holdings._schema(conn)
        rows = conn.execute('SELECT as_of, payload, source_url FROM ark_holdings_snapshots WHERE fund=? ORDER BY as_of', (fund,)).fetchall()
    history, reference, tickers = [], None, set()
    for date, raw, source in rows:
        entry = next((item for item in json.loads(raw) if item.get('security_id') == security_id), None)
        if entry:
            reference = entry
            if entry.get('ticker'):
                tickers.add(entry['ticker'].upper().strip())
        history.append({'date': date, 'shares': entry.get('shares') if entry else None,
                        'weight': entry.get('weight') if entry else None,
                        'market_value': entry.get('market_value') if entry else None,
                        'reported': entry is not None, 'source_url': source})
    if reference is None:
        raise LookupError('没有找到该证券的持仓记录。')
    ticker = str(reference.get('ticker') or '').strip().upper()
    price = {'symbol': ticker or None, 'source': 'Alpaca IEX', 'currency': 'USD', 'adjustment': 'raw', 'points': [], 'error': None}
    result = {'fund': fund, 'security': {'security_id': security_id, 'ticker': ticker, 'name': reference.get('name')}, 'holdings': history, 'price': price}
    if not re.fullmatch(r'[A-Z0-9]{9}', security_id) or not re.fullmatch(r'[A-Z]{1,10}(?:[.-][A-Z]{1,4})?', ticker) or len(tickers) != 1:
        price['error'] = '该资产缺少可核验的美股代码，无法显示股价。'
        return result
    try:
        # Query by the official snapshot CUSIP, then require an exact symbol match.
        asset = request(asset_host, '/v2/assets/' + quote(security_id, safe=''), {})
        if asset.get('class') != 'us_equity' or str(asset.get('symbol', '')).upper() != ticker:
            price['error'] = '股票代码与持仓证券标识未能匹配，无法显示股价。'
            return result
        now = today or datetime.now(ZoneInfo('America/New_York'))
        last = now.date() if (now.hour, now.minute) >= (16, 30) else (now - timedelta(days=1)).date()
        start = min(last - timedelta(days=90), datetime.fromisoformat(history[0]['date']).date())
        start = max(start, last - timedelta(days=730))
        bars = request('https://data.alpaca.markets', '/v2/stocks/' + quote(ticker, safe='') + '/bars', {'timeframe':'1Day','start':start.isoformat(),'end':last.isoformat(),'feed':'iex','adjustment':'raw','limit':1000})
        if bars.get('next_page_token'):
            raise ValueError('股价历史超过单次查询上限。')
        if not isinstance(bars.get('bars'), list):
            raise ValueError('股价数据格式无效。')
        for bar in bars['bars']:
            close = bar.get('c')
            ts = str(bar.get('t',''))[:10]
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', ts) and isinstance(close,(float,int)) and not isinstance(close,bool) and math.isfinite(close) and close > 0:
                price['points'].append({'date':ts,'close':close})
        if not price['points']:
            price['error'] = '该证券暂无可用的 IEX 历史收盘价。'
    except Exception:
        price['error'] = '无法获取或核验股价，请检查 Alpaca 配置及行情权限。'
    return result
