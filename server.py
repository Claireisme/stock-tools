#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ASSETS = {'/zh': ('index.html', 'text/html; charset=utf-8'), '/zh/': ('index.html', 'text/html; charset=utf-8'), '/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/options.css': ('options.css', 'text/css; charset=utf-8'), '/options.js': ('options.js', 'text/javascript; charset=utf-8'), '/options-math.js': ('options-math.js', 'text/javascript; charset=utf-8')}


def quote_symbol(market, code):
    code = code.strip().upper()
    if market == 'cn' and re.fullmatch(r'\d{6}', code):
        prefix = 'sh' if code[0] in '569' else 'sz' if code[0] in '023' else 'bj' if code[0] in '48' else None
        if prefix:
            return prefix + code
    if market == 'hk' and re.fullmatch(r'\d{1,5}', code):
        return 'hk' + code.zfill(5)
    if market == 'us' and re.fullmatch(r'[A-Z]{1,10}(?:[.-][A-Z]{1,4})?', code):
        return 'us' + code
    raise ValueError('股票代码格式不正确，请检查市场和代码。')


def search_stocks(query, market='all', source='sina'):
    query = query.strip()
    if not query or len(query) > 32 or not re.fullmatch(r'[\w.\-\s\u3400-\u9fff]+', query):
        raise ValueError('请输入不超过 32 个字符的股票名称或代码。')
    if market not in ('all', 'cn', 'hk', 'us'):
        raise ValueError('请选择有效的股票市场。')
    if source == 'sina':
        return search_sina(query, market)
    if source == 'yahoo':
        return search_yahoo(query, market)
    if source != 'tencent':
        raise ValueError('请选择有效的数据源。')
    params = urlencode({'v': '2', 't': 'all', 'q': query})
    req = Request('https://smartbox.gtimg.cn/s3/?' + params, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/'})
    with urlopen(req, timeout=8) as response:
        data = response.read(65536).decode('utf-8')
    match = re.fullmatch(r'\s*v_hint=("(?:[^"\\]|\\.)*")\s*;?\s*', data)
    if not match:
        raise ValueError('搜索服务返回了无法识别的数据，请稍后重试。')
    try:
        entries = json.loads(match.group(1)).split('^')
    except json.JSONDecodeError:
        raise ValueError('搜索服务返回了无法识别的数据，请稍后重试。')
    results, seen = [], set()
    for entry in entries:
        fields = entry.split('~')
        if len(fields) < 5:
            continue
        exchange, code, name, _, kind = fields[:5]
        result_market = 'cn' if exchange in ('sh', 'sz', 'bj') and kind == 'GP-A' else exchange if exchange in ('hk', 'us') and kind == 'GP' else None
        if not result_market or (market != 'all' and result_market != market):
            continue
        if result_market == 'us':
            code = re.sub(r'\.(?:oq|n|am|ps|pk)$', '', code, flags=re.IGNORECASE).upper()
        try:
            quote_symbol(result_market, code)
        except ValueError:
            continue
        key = (result_market, code)
        if name and key not in seen:
            seen.add(key)
            results.append({'name': name, 'code': code, 'market': result_market})
    return {'results': results}


def search_sina(query, market):
    params = urlencode({'type': '11,31,41', 'key': query})
    req = Request('https://suggest3.sinajs.cn/suggest/?' + params, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'})
    with urlopen(req, timeout=8) as response:
        data = response.read(65536).decode('gb18030', errors='replace')
    match = re.fullmatch(r'\s*var\s+suggestvalue="([^"\r\n]*)";?\s*', data)
    if not match:
        raise ValueError('新浪搜索服务返回了无法识别的数据，请稍后重试。')
    results, seen = [], set()
    for entry in match.group(1).split(';'):
        fields = entry.split(',')
        if len(fields) < 5:
            continue
        _, kind, code, symbol, name = fields[:5]
        result_market = {'11': 'cn', '31': 'hk', '41': 'us'}.get(kind)
        if not result_market or (market != 'all' and market != result_market):
            continue
        code = code.upper()
        try:
            expected = quote_symbol(result_market, code)
        except ValueError:
            continue
        if result_market == 'cn' and symbol.lower() != expected:
            continue
        key = (result_market, code)
        if name and key not in seen:
            seen.add(key)
            results.append({'name': name, 'code': code, 'market': result_market})
    return {'results': results[:20]}


def yahoo_json(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    with urlopen(req, timeout=8) as response:
        return json.loads(response.read(262144).decode('utf-8'))


class OptionsDataError(Exception):
    def __init__(self, code, message, status=502):
        super().__init__(message)
        self.code, self.status = code, status


def alpaca_setting(name, default=''):
    if name in os.environ:
        return os.environ[name]
    try:
        with (ROOT / '.alpaca-config.json').open(encoding='utf-8') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        raise OptionsDataError('invalid_configuration', 'Alpaca 本地配置无法读取，请重新运行配置程序。', 503) from None
    if not isinstance(config, dict) or not isinstance(config.get(name, default), str):
        raise OptionsDataError('invalid_configuration', 'Alpaca 本地配置格式无效，请重新运行配置程序。', 503)
    return config.get(name, default)


def option_symbol(symbol):
    symbol = symbol.strip().upper()
    if not re.fullmatch(r'[A-Z]{1,10}(?:[.-][A-Z]{1,4})?', symbol):
        raise ValueError('请输入有效的美股或 ETF 代码。')
    return symbol


def option_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date().isoformat() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) else None
    except ValueError:
        return None


def tradier_json(endpoint, params):
    token = os.environ.get('TRADIER_API_TOKEN', '').strip()
    if not token:
        raise OptionsDataError('missing_token', '请在服务端设置 TRADIER_API_TOKEN 后重启服务。', 503)
    request = Request('https://api.tradier.com/v1/markets/options/' + endpoint + '?' + urlencode(params),
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'User-Agent': 'NumberToolkit/1.0'})
    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read(4 * 1024 * 1024).decode('utf-8'))
    except HTTPError as error:
        if error.code in (401, 403):
            raise OptionsDataError('authentication_failed', 'Tradier 认证失败，请检查生产环境令牌和行情权限。') from None
        raise OptionsDataError('provider_unavailable', 'Tradier 行情服务暂不可用或请求次数已达上限。') from None
    except (URLError, OSError, TimeoutError, UnicodeError, ValueError):
        raise OptionsDataError('provider_unavailable', '无法连接 Tradier 行情服务，请稍后重试。') from None
    if not isinstance(data, dict) or 'error' in data or 'errors' in data:
        raise OptionsDataError('provider_response', 'Tradier 返回了无法识别的行情数据。')
    return data


def option_expirations(symbol):
    symbol = option_symbol(symbol)
    data = tradier_json('expirations', {'symbol': symbol})
    container = data.get('expirations')
    if container is None or container == 'null':
        dates = []
    elif isinstance(container, dict):
        dates = container.get('date') or []
    else:
        raise OptionsDataError('provider_response', 'Tradier 返回了无法识别的到期日数据。')
    if isinstance(dates, str):
        dates = [dates]
    if not isinstance(dates, list) or any(not isinstance(d, str) or not option_date(d) for d in dates):
        raise OptionsDataError('provider_response', 'Tradier 返回了无法识别的到期日数据。')
    return {'symbol': symbol, 'expirations': sorted(set(dates)), 'source': 'Tradier'}


def option_number(value, minimum=0, strict=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) and (value > minimum if strict else value >= minimum) else None


def option_count(value):
    number = option_number(value)
    return int(number) if number is not None and number.is_integer() else None


def option_chain(symbol, expiration):
    symbol = option_symbol(symbol)
    if not option_date(expiration):
        raise ValueError('请选择有效的到期日。')
    data = tradier_json('chains', {'symbol': symbol, 'expiration': expiration, 'greeks': 'true'})
    container = data.get('options')
    if container is None or container == 'null':
        contracts = []
    elif isinstance(container, dict):
        contracts = container.get('option') or []
    else:
        raise OptionsDataError('provider_response', 'Tradier 返回了无法识别的期权链数据。')
    if isinstance(contracts, dict):
        contracts = [contracts]
    if not isinstance(contracts, list):
        raise OptionsDataError('provider_response', 'Tradier 返回了无法识别的期权链数据。')
    options = []
    for item in contracts:
        if not isinstance(item, dict):
            continue
        kind, strike = item.get('option_type'), option_number(item.get('strike'), 0, True)
        contract = item.get('symbol')
        if (kind not in ('call', 'put') or strike is None or not isinstance(contract, str)
                or not re.fullmatch(r'[A-Za-z0-9.\-]{1,32}', contract)
                or item.get('contract_size') != 100 or item.get('expiration_date') != expiration):
            continue
        greeks = item.get('greeks') if isinstance(item.get('greeks'), dict) else {}
        options.append({'symbol': contract, 'type': kind, 'strike': strike,
                        'bid': option_number(item.get('bid')), 'ask': option_number(item.get('ask')),
                        'bid_size': option_count(item.get('bidsize')), 'ask_size': option_count(item.get('asksize')),
                        'volume': option_count(item.get('volume')),
                        'last': option_number(item.get('last'), 0, True),
                        'iv': option_number(greeks.get('mid_iv'), 0, True),
                        'bid_time': item.get('bid_date'), 'ask_time': item.get('ask_date'),
                        'trade_time': item.get('trade_date'), 'iv_time': greeks.get('updated_at')})
    options.sort(key=lambda item: (item['strike'], item['type']))
    return {'symbol': symbol, 'expiration': expiration, 'source': 'Tradier', 'options': options}


def alpaca_json(host, path, params):
    key = alpaca_setting('ALPACA_API_KEY').strip()
    secret = alpaca_setting('ALPACA_API_SECRET').strip()
    if not key or not secret:
        raise OptionsDataError('missing_token', '请在服务端设置 ALPACA_API_KEY 和 ALPACA_API_SECRET 后重启服务。', 503)
    request = Request(host + path + '?' + urlencode(params), headers={
        'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret, 'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read(16 * 1024 * 1024).decode('utf-8'))
    except HTTPError as error:
        if error.code in (401, 403):
            raise OptionsDataError('authentication_failed', 'Alpaca 认证失败，请检查密钥、账户环境和行情权限。') from None
        raise OptionsDataError('provider_unavailable', 'Alpaca 行情服务暂不可用或请求次数已达上限。') from None
    except (URLError, OSError, TimeoutError, UnicodeError, ValueError):
        raise OptionsDataError('provider_unavailable', '无法连接 Alpaca 行情服务，请稍后重试。') from None
    if not isinstance(data, dict):
        raise OptionsDataError('provider_response', 'Alpaca 返回了无法识别的数据。')
    return data


def alpaca_pages(host, path, params, field):
    params = dict(params)
    seen = set()
    for _ in range(100):
        data = alpaca_json(host, path, params)
        values = data.get(field)
        expected = dict if field == 'snapshots' else list
        if not isinstance(values, expected):
            raise OptionsDataError('provider_response', 'Alpaca 返回了无法识别的数据。')
        yield values
        token = data.get('next_page_token')
        if not token:
            return
        if not isinstance(token, str) or token in seen or len(token) > 4096:
            raise OptionsDataError('provider_response', 'Alpaca 返回了无效的分页信息。')
        seen.add(token)
        params['page_token'] = token
    raise OptionsDataError('provider_response', '期权数据过多，无法完整获取，请稍后重试。')


def alpaca_contracts(symbol, expiration=None):
    env = alpaca_setting('ALPACA_ENV', 'paper').strip().lower()
    if env not in ('paper', 'live'):
        raise OptionsDataError('invalid_configuration', 'ALPACA_ENV 必须为 paper 或 live。', 503)
    host = 'https://paper-api.alpaca.markets' if env == 'paper' else 'https://api.alpaca.markets'
    params = {'underlying_symbols': symbol, 'show_deliverables': 'true', 'limit': 10000}
    if expiration:
        params['expiration_date'] = expiration
    else:
        today = datetime.now(timezone.utc).date()
        params.update(expiration_date_gte=(today - timedelta(days=1)).isoformat(),
                      expiration_date_lte=(today + timedelta(days=1461)).isoformat())
    contracts = []
    for page in alpaca_pages(host, '/v2/options/contracts', params, 'option_contracts'):
        for item in page:
            if not isinstance(item, dict):
                continue
            deliverables = item.get('deliverables')
            if not isinstance(deliverables, list) or len(deliverables) != 1 or not isinstance(deliverables[0], dict):
                continue
            delivery = deliverables[0]
            if (item.get('underlying_symbol') != symbol or option_number(item.get('size')) != 100
                    or option_number(item.get('multiplier')) != 100
                    or delivery.get('type') != 'equity' or delivery.get('symbol') != symbol
                    or option_number(delivery.get('amount')) != 100 or delivery.get('delayed_settlement') is not False
                    or item.get('type') not in ('call', 'put') or not option_date(str(item.get('expiration_date', '')))
                    or option_number(item.get('strike_price'), 0, True) is None
                    or not isinstance(item.get('symbol'), str)
                    or not re.fullmatch(r'[A-Za-z0-9.\-]{1,32}', item['symbol'])):
                continue
            contracts.append(item)
    return contracts


def alpaca_expirations(symbol):
    symbol = option_symbol(symbol)
    contracts = alpaca_contracts(symbol)
    return {'symbol': symbol, 'expirations': sorted({item['expiration_date'] for item in contracts}), 'source': 'Alpaca indicative'}


def alpaca_chain(symbol, expiration):
    symbol = option_symbol(symbol)
    if not option_date(expiration):
        raise ValueError('请选择有效的到期日。')
    contracts = {item['symbol']: item for item in alpaca_contracts(symbol, expiration)
                 if item['expiration_date'] == expiration}
    options = []
    if contracts:
        params = {'feed': 'indicative', 'expiration_date': expiration, 'limit': 1000}
        for snapshots in alpaca_pages('https://data.alpaca.markets', '/v1beta1/options/snapshots/' + symbol, params, 'snapshots'):
            for contract, snapshot in snapshots.items():
                if contract not in contracts or not isinstance(snapshot, dict):
                    continue
                item = contracts[contract]
                quote = snapshot.get('latestQuote') if isinstance(snapshot.get('latestQuote'), dict) else {}
                trade = snapshot.get('latestTrade') if isinstance(snapshot.get('latestTrade'), dict) else {}
                options.append({'symbol': contract, 'type': item['type'], 'strike': option_number(item['strike_price']),
                                'bid': option_number(quote.get('bp')), 'ask': option_number(quote.get('ap')),
                                'bid_size': option_count(quote.get('bs')), 'ask_size': option_count(quote.get('as')),
                                'volume': None,
                                'last': option_number(trade.get('p'), 0, True),
                                'iv': option_number(snapshot.get('impliedVolatility'), 0, True),
                                'bid_time': quote.get('t'), 'ask_time': quote.get('t'),
                                'trade_time': trade.get('t'), 'iv_time': None})
    options.sort(key=lambda item: (item['strike'], item['type']))
    return {'symbol': symbol, 'expiration': expiration, 'source': 'Alpaca indicative', 'options': options}


def search_yahoo(query, market):
    lookup = query
    if re.fullmatch(r'\d{1,5}', query) and market in ('all', 'hk'):
        lookup = query.lstrip('0').zfill(4) + '.HK'
    params = urlencode({'q': lookup, 'quotesCount': 20, 'newsCount': 0})
    data = yahoo_json('https://query1.finance.yahoo.com/v1/finance/search?' + params)
    if not isinstance(data.get('quotes'), list):
        raise ValueError('Yahoo Finance 搜索服务暂不可用。')
    results, seen = [], set()
    for item in data['quotes']:
        if item.get('quoteType') != 'EQUITY':
            continue
        symbol = str(item.get('symbol', '')).upper()
        exchange = item.get('exchange')
        result_market, code = None, symbol
        if re.fullmatch(r'\d{6}\.(?:SS|SZ)', symbol):
            code = symbol[:6]
            expected = 'sh' if symbol.endswith('.SS') else 'sz'
            try:
                if quote_symbol('cn', code).startswith(expected):
                    result_market = 'cn'
            except ValueError:
                continue
        elif re.fullmatch(r'\d{4,5}\.HK', symbol):
            code, result_market = symbol[:-3].zfill(5), 'hk'
        elif exchange in ('NMS', 'NYQ', 'NGM', 'NCM', 'ASE', 'PCX', 'BTS', 'PNK') and re.fullmatch(r'[A-Z]{1,10}(?:[.-][A-Z]{1,4})?', symbol):
            result_market = 'us'
        if not result_market or (market != 'all' and market != result_market):
            continue
        try:
            quote_symbol(result_market, code)
        except ValueError:
            continue
        name = item.get('shortname') or item.get('longname') or code
        key = (result_market, code)
        if key not in seen:
            seen.add(key)
            results.append({'name': name, 'code': code, 'market': result_market})
    return {'results': results}


def quote_yahoo(market, code, symbol):
    if market == 'cn':
        if symbol.startswith('bj'):
            raise ValueError('Yahoo Finance 暂不支持北交所股票。')
        yahoo_symbol = code + ('.SS' if symbol.startswith('sh') else '.SZ')
    elif market == 'hk':
        yahoo_symbol = code.lstrip('0').zfill(4) + '.HK'
    else:
        yahoo_symbol = code.upper()
    params = urlencode({'interval': '1d', 'range': '5d'})
    data = yahoo_json('https://query1.finance.yahoo.com/v8/finance/chart/' + yahoo_symbol + '?' + params)
    try:
        meta = data['chart']['result'][0]['meta']
        price = float(meta['regularMarketPrice'])
        currency = meta['currency']
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError('Yahoo Finance 暂未提供该股票的有效价格。')
    if not math.isfinite(price) or price <= 0 or currency != {'cn': 'CNY', 'hk': 'HKD', 'us': 'USD'}[market]:
        raise ValueError('Yahoo Finance 暂未提供该股票的有效价格或币种。')
    raw_time = ''
    timestamp, zone = meta.get('regularMarketTime'), meta.get('exchangeTimezoneName')
    if isinstance(timestamp, (int, float)):
        try:
            dt = datetime.fromtimestamp(timestamp, timezone.utc)
            if zone:
                dt = dt.astimezone(ZoneInfo(zone))
            raw_time = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        except (ValueError, OverflowError, OSError, ZoneInfoNotFoundError):
            pass
    return {'name': meta.get('shortName') or meta.get('longName') or code, 'code': code.upper().zfill(5) if market == 'hk' else code.upper(), 'price': price, 'currency': currency, 'time': raw_time, 'source': 'Yahoo Finance'}


def get_quote(market, code, source='sina'):
    symbol = quote_symbol(market, code)
    if source == 'sina':
        return quote_sina(market, code, symbol)
    if source == 'yahoo':
        return quote_yahoo(market, code, symbol)
    if source != 'tencent':
        raise ValueError('请选择有效的数据源。')
    req = Request('https://qt.gtimg.cn/q=' + symbol, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/'})
    with urlopen(req, timeout=8) as response:
        data = response.read(65536).decode('gb18030', errors='replace')
    match = re.search(r'="([^\"]*)"', data)
    fields = match.group(1).split('~') if match else []
    if len(fields) <= 30 or not fields[1]:
        raise ValueError('未找到该股票，请检查代码和市场。')
    try:
        price = float(fields[3])
    except ValueError:
        raise ValueError('行情暂不可用，请稍后重试。')
    if not math.isfinite(price) or price <= 0:
        raise ValueError('该股票暂无有效价格。')
    raw_time = fields[30].strip()
    if re.fullmatch(r'\d{14}', raw_time):
        raw_time = f'{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:8]} {raw_time[8:10]}:{raw_time[10:12]}:{raw_time[12:14]}'
    return {'name': fields[1], 'code': fields[2], 'price': price, 'currency': {'cn': 'CNY', 'hk': 'HKD', 'us': 'USD'}[market], 'time': raw_time, 'source': '腾讯行情'}


def quote_sina(market, code, symbol):
    sina_symbol = 'gb_' + code.lower() if market == 'us' else symbol
    req = Request('https://hq.sinajs.cn/list=' + sina_symbol, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'})
    with urlopen(req, timeout=8) as response:
        data = response.read(65536).decode('gb18030', errors='replace')
    match = re.fullmatch(r'\s*var\s+hq_str_[A-Za-z0-9_.-]+="([^"\r\n]*)";?\s*', data)
    fields = match.group(1).split(',') if match else []
    try:
        if market == 'cn':
            name, price, raw_time = fields[0], float(fields[3]), f'{fields[30]} {fields[31]}'
        elif market == 'hk':
            name, price, raw_time = fields[1], float(fields[6]), f'{fields[17]} {fields[18]}'
        else:
            name, price = fields[0], float(fields[1])
            raw_time = fields[25] if len(fields) > 25 and fields[25] else fields[3]
    except (ValueError, IndexError):
        raise ValueError('新浪行情暂不可用，请检查代码或稍后重试。')
    if not name or not math.isfinite(price) or price <= 0:
        raise ValueError('新浪行情暂未提供该股票的有效价格。')
    return {'name': name, 'code': code.upper().zfill(5) if market == 'hk' else code.upper(), 'price': price, 'currency': {'cn': 'CNY', 'hk': 'HKD', 'us': 'USD'}[market], 'time': raw_time, 'source': '新浪财经'}


SOURCES = ('sina', 'tencent', 'yahoo')
PROVIDER_ERRORS = (URLError, OSError, TimeoutError, UnicodeError, ValueError, KeyError, TypeError)


def with_fallback(operation, source):
    if source not in SOURCES:
        raise ValueError('请选择有效的数据源。')
    try:
        return operation(source), source, None
    except PROVIDER_ERRORS:
        if source != 'sina':
            raise
    try:
        result = operation('tencent')
    except PROVIDER_ERRORS:
        raise ValueError('新浪与腾讯数据源暂时不可用，请稍后重试。')
    return result, 'tencent', {'from': 'sina', 'to': 'tencent', 'reason': '新浪请求失败或未返回有效数据'}


def checked_operation(operation):
    try:
        operation()
        return {'ok': True}
    except PROVIDER_ERRORS:
        return {'ok': False, 'error': '请求失败或未返回有效数据'}


def check_source(source):
    if source not in SOURCES:
        raise ValueError('请选择有效的数据源。')

    def check_search():
        if not search_stocks('AAPL', 'us', source)['results']:
            raise ValueError('搜索未返回预期结果')

    def check_quote():
        get_quote('us', 'AAPL', source)

    with ThreadPoolExecutor(max_workers=2) as executor:
        search = executor.submit(checked_operation, check_search)
        quote = executor.submit(checked_operation, check_quote)
        results = {'source': source, 'search': search.result(), 'quote': quote.result()}
    results['checked_at'] = datetime.now(timezone.utc).isoformat()
    return results


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ('/api/options/expirations', '/api/options/chain'):
            params = parse_qs(url.query)
            try:
                symbol = params.get('symbol', [''])[0]
                source = params.get('source', ['tradier'])[0]
                if source not in ('tradier', 'alpaca'):
                    raise ValueError('请选择有效的期权行情数据源。')
                if url.path.endswith('/expirations'):
                    result = alpaca_expirations(symbol) if source == 'alpaca' else option_expirations(symbol)
                else:
                    expiration = params.get('expiration', [''])[0]
                    result = alpaca_chain(symbol, expiration) if source == 'alpaca' else option_chain(symbol, expiration)
                self.send_json(200, result)
            except ValueError as error:
                self.send_json(400, {'code': 'invalid_request', 'error': str(error)})
            except OptionsDataError as error:
                self.send_json(error.status, {'code': error.code, 'error': str(error)})
            return
        if url.path == '/api/health':
            params = parse_qs(url.query)
            try:
                self.send_json(200, check_source(params.get('source', ['sina'])[0]))
            except ValueError as error:
                self.send_json(400, {'error': str(error)})
            return
        if url.path == '/api/search':
            params = parse_qs(url.query)
            try:
                query = params.get('q', [''])[0].strip()
                market = params.get('market', ['all'])[0]
                source = params.get('source', ['sina'])[0]
                if not query or len(query) > 32 or not re.fullmatch(r'[\w.\-\s\u3400-\u9fff]+', query):
                    raise ValueError('请输入不超过 32 个字符的股票名称或代码。')
                if market not in ('all', 'cn', 'hk', 'us'):
                    raise ValueError('请选择有效的股票市场。')
                result, actual, fallback = with_fallback(lambda name: search_stocks(query, market, name), source)
                result['source'] = actual
                if fallback:
                    result['fallback'] = fallback
                self.send_json(200, result)
            except ValueError as error:
                self.send_json(400, {'error': str(error)})
            except (URLError, OSError, TimeoutError, UnicodeError):
                self.send_json(502, {'error': '搜索服务暂时不可用，请检查网络后重试。'})
            return
        if url.path == '/api/quote':
            params = parse_qs(url.query)
            try:
                market = params.get('market', [''])[0]
                code = params.get('code', [''])[0]
                source = params.get('source', ['sina'])[0]
                quote_symbol(market, code)
                result, actual, fallback = with_fallback(lambda name: get_quote(market, code, name), source)
                result['source_id'] = actual
                if fallback:
                    result['fallback'] = fallback
                self.send_json(200, result)
            except ValueError as error:
                self.send_json(400, {'error': str(error)})
            except (URLError, OSError, TimeoutError):
                self.send_json(502, {'error': '行情服务暂时不可用，请检查网络后重试。'})
            return
        if url.path not in ASSETS:
            self.send_error(404)
            return
        filename, content_type = ASSETS[url.path]
        body = (ROOT / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def server_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('端口必须是 1 到 65535 之间的整数。') from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('端口必须是 1 到 65535 之间的整数。')
    return port


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=server_port, default=os.environ.get('PORT', '8000'), help='监听端口（默认 8000，也可设置 PORT）')
    port = parser.parse_args().port
    print(f'本地调试地址：http://127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
