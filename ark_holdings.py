"""Official ARK ETF daily holdings snapshots; differences are not trade records."""
import csv
import io
import json
import math
import re
from datetime import datetime
from urllib.request import Request, urlopen

BASE = 'https://assets.ark-funds.com/fund-documents/funds-etf-csv/'
FILES = {
    'ARKK': 'ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv',
    'ARKF': 'ARK_BLOCKCHAIN_%26_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv',
    'ARKG': 'ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv',
    'ARKQ': 'ARK_AUTONOMOUS_TECH._%26_ROBOTICS_ETF_ARKQ_HOLDINGS.csv',
    'ARKW': 'ARK_NEXT_GENERATION_TECHNOLOGY_ETF_ARKW_HOLDINGS.csv',
    'ARKX': 'ARK_SPACE_%26_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv',
    'ARKB': 'ARK_21SHARES_BITCOIN_ETF_ARKB_HOLDINGS.csv',
    'ARKD': 'ARK_DIET_Q1_BUFFER_ETF_ARKD_HOLDINGS.csv',
    'ARKE': 'ARK_DIET_Q3_BUFFER_ETF_ARKE_HOLDINGS.csv',
    'ARKI': 'ARK_DIET_Q2_BUFFER_ETF_ARKI_HOLDINGS.csv',
    'ARKT': 'ARK_DIET_Q4_BUFFER_ETF_ARKT_HOLDINGS.csv',
    'PRNT': 'THE_3D_PRINTING_ETF_PRNT_HOLDINGS.csv',
    'IZRL': 'ARK_ISRAEL_INNOVATIVE_TECHNOLOGY_ETF_IZRL_HOLDINGS.csv',
}
COLUMNS = ['date', 'fund', 'company', 'ticker', 'cusip', 'shares', 'market value ($)', 'weight (%)']


def _number(text):
    text = str(text).strip().replace(',', '').replace('$', '').replace('%', '')
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError('ARK 持仓数值格式无效') from exc
    if not math.isfinite(number):
        raise ValueError('ARK 持仓数值无效')
    return number


def parse(data, fund):
    if fund not in FILES:
        raise ValueError('未知 ARK 基金')
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig')))
        header = [s.strip().lower() for s in next(reader)]
    except (UnicodeDecodeError, StopIteration) as exc:
        raise ValueError('ARK 持仓文件为空或编码无效') from exc
    if header != COLUMNS:
        raise ValueError('ARK 持仓文件表头发生变化')
    rows, seen, dates = [], set(), set()
    for row in reader:
        if len(row) != len(COLUMNS):
            if len(row) <= 1:
                continue
            raise ValueError('ARK 持仓行列数不正确')
        date, reported_fund, name, ticker, cusip, shares, market, weight = [v.strip() for v in row]
        if reported_fund.upper() != fund or not name or not cusip:
            raise ValueError('ARK 持仓缺少基金或证券标识')
        try:
            as_of = datetime.strptime(date, '%m/%d/%Y').date().isoformat()
        except ValueError as exc:
            raise ValueError('ARK 持仓日期无效') from exc
        security_id = cusip.upper()
        if security_id in seen:
            raise ValueError('ARK 持仓证券标识重复')
        seen.add(security_id)
        dates.add(as_of)
        rows.append({'security_id': security_id, 'ticker': ticker, 'name': name,
                     'cusip': cusip, 'shares': _number(shares), 'market_value': _number(market),
                     'weight': _number(weight)})
    if not rows or len(dates) != 1:
        raise ValueError('ARK 持仓为空或包含多个日期')
    return dates.pop(), rows


def fetch(fund):
    if fund not in FILES:
        raise ValueError('未知 ARK 基金')
    url = BASE + FILES[fund]
    with urlopen(Request(url, headers={'User-Agent': 'Disclosure Watch (holdings monitor)'}), timeout=25) as response:
        payload = response.read(5_000_001)
    if len(payload) > 5_000_000:
        raise ValueError('ARK 持仓文件过大')
    date, positions = parse(payload, fund)
    return {'fund': fund, 'as_of': date, 'source_url': url, 'positions': positions}


def _schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS ark_holdings_snapshots (
        fund TEXT NOT NULL, as_of TEXT NOT NULL, observed_at TEXT NOT NULL,
        source_url TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (fund, as_of))''')


def save(db, result, observed_at):
    with db() as conn:
        _schema(conn)
        conn.execute('''INSERT INTO ark_holdings_snapshots VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(fund, as_of) DO UPDATE SET source_url=excluded.source_url, payload=excluded.payload''',
            (result['fund'], result['as_of'], observed_at, result['source_url'], json.dumps(result['positions'], ensure_ascii=False)))


def refresh(db, now):
    errors, updated = {}, []
    for fund in FILES:
        try:
            result = fetch(fund)
            save(db, result, now())
            updated.append({'fund': fund, 'as_of': result['as_of'], 'count': len(result['positions'])})
        except Exception as exc:
            errors[fund] = str(exc)[:300]
    return {'updated': updated, 'errors': errors}


def snapshot(db, fund='ARKK'):
    if fund not in FILES:
        raise ValueError('未知 ARK 基金')
    with db() as conn:
        _schema(conn)
        available = {row[0]: row[1] for row in conn.execute('SELECT fund, MAX(as_of) FROM ark_holdings_snapshots GROUP BY fund')}
        rows = conn.execute('''SELECT as_of, observed_at, source_url, payload FROM ark_holdings_snapshots
                               WHERE fund = ? ORDER BY as_of DESC LIMIT 2''', (fund,)).fetchall()
    output = {'funds': list(FILES), 'fund': fund, 'as_of': None, 'previous_as_of': None,
              'source_url': BASE + FILES[fund], 'observed_at': None, 'holdings': [], 'closed': [],
              'available_as_of': available}
    if not rows:
        return output
    date, observed, source, raw = rows[0]
    positions = json.loads(raw)
    previous = {entry['security_id']: entry for entry in json.loads(rows[1][3])} if len(rows) > 1 else None
    current_ids = {entry['security_id'] for entry in positions}
    for entry in positions:
        prior = previous.get(entry['security_id']) if previous is not None else None
        delta = round(entry['shares'] - (prior['shares'] if prior else 0), 6) if previous is not None else None
        weight_delta = round(entry['weight'] - (prior['weight'] if prior else 0), 6) if previous is not None else None
        status = None if previous is None else 'new' if prior is None else 'increased' if delta > 0 else 'decreased' if delta < 0 else 'unchanged'
        output['holdings'].append({**entry, 'previous_shares': prior['shares'] if prior else None,
                                   'shares_change': delta, 'weight_change': weight_delta, 'status': status})
    if previous is not None:
        for key, prior in previous.items():
            if key not in current_ids:
                output['closed'].append({**prior, 'shares': 0, 'market_value': 0, 'weight': 0,
                                         'previous_shares': prior['shares'], 'shares_change': -prior['shares'],
                                         'weight_change': -prior['weight'], 'status': 'closed'})
        output['closed'].sort(key=lambda row: (-abs(row['weight_change']), row['security_id']))
    output['holdings'].sort(key=lambda row: (-row['weight'], row['security_id']))
    output.update(as_of=date, previous_as_of=rows[1][0] if len(rows) > 1 else None,
                  observed_at=observed, source_url=source)
    return output
