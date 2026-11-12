"""SEC 13F information-table snapshots and quarter-on-quarter comparisons."""
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation

STATE = {'last_success': None, 'error': None, 'last_attempt_day': None}


def _xml(data):
    root = ET.fromstring(data)
    for node in root.iter():
        node.tag = node.tag.split('}')[-1]
    return root


def _text(root, path):
    node = root.find(path)
    return (node.text or '').strip() if node is not None else ''


def parse_information_table(data):
    root = _xml(data)
    if root.tag.lower() != 'informationtable':
        raise ValueError('不是 13F information table')
    holdings = {}
    for row in root.findall('.//infoTable'):
        cusip = _text(row, 'cusip').upper()
        title = _text(row, 'titleOfClass').upper()
        option = _text(row, 'putCall').upper()
        unit = _text(row, 'shrsOrPrnAmt/sshPrnamtType').upper()
        if not cusip or not title or unit not in ('SH', 'PRN'):
            raise ValueError('13F 持仓缺少证券标识或数量单位')
        key = json.dumps([cusip, title, option, unit], ensure_ascii=False, separators=(',', ':'))
        try:
            amount = Decimal(_text(row, 'shrsOrPrnAmt/sshPrnamt').replace(',', ''))
            if not amount.is_finite() or amount < 0:
                raise ValueError('13F 数量无效')
        except InvalidOperation as exc:
            raise ValueError('13F 数量无效') from exc
        if key not in holdings:
            holdings[key] = {'cusip': cusip, 'title': title, 'put_call': option, 'unit': unit,
                             'issuer': _text(row, 'nameOfIssuer'), 'amount': '0'}
        holdings[key]['amount'] = str(Decimal(holdings[key]['amount']) + amount)
    if not holdings:
        raise ValueError('13F information table 为空')
    return holdings


def merge_filings(filings):
    """Apply restatements and additive amendments chronologically."""
    result = None
    for filing in sorted(filings, key=lambda f: (f['accepted_at'] or f['reported_at'], f['accession'])):
        kind = filing['amendment']
        if kind in ('INITIAL', 'RESTATEMENT'):
            result = {k: dict(v) for k, v in filing['holdings'].items()}
        elif kind == 'NEW HOLDINGS':
            if result is None:
                raise ValueError('13F 新增持仓修订缺少原始申报')
            for key, row in filing['holdings'].items():
                if key in result:
                    result[key]['amount'] = str(Decimal(result[key]['amount']) + Decimal(row['amount']))
                else:
                    result[key] = dict(row)
        else:
            raise ValueError('未知 13F 修订类型')
    return result or {}


def adjacent(older, newer):
    a, b = date.fromisoformat(older), date.fromisoformat(newer)
    return (b.year - a.year) * 12 + b.month - a.month == 3 and a.month in (3, 6, 9, 12) and b.month in (3, 6, 9, 12)


def compare(investor_id, old_period, previous, new_period, current, filing, observed):
    if not adjacent(old_period, new_period):
        raise ValueError('13F 季度不连续，不能推断持仓变化')
    events = []
    for key in sorted(set(previous) | set(current)):
        prior = previous.get(key)
        latest = current.get(key)
        old = Decimal(prior['amount']) if prior else Decimal(0)
        new = Decimal(latest['amount']) if latest else Decimal(0)
        if new == old:
            continue
        label = '新建仓' if old == 0 else '退出持仓' if new == 0 else '增仓' if new > old else '减仓'
        security = latest or prior
        identity = hashlib.sha256(f'{investor_id}:{new_period}:{key}'.encode()).hexdigest()
        detail = {'issuer': security['issuer'], 'cusip': security['cusip'], 'class': security['title'],
                  'put_call': security['put_call'] or None, 'unit': security['unit'], 'previous_period': old_period,
                  'current_period': new_period, 'previous_amount': str(old), 'current_amount': str(new),
                  'change': str(new-old), 'note': '季度末申报持仓对比，不代表交易日期或个人持仓；期权缺少行权价与到期日。'}
        events.append({'id': '13f:' + identity, 'investor_id': investor_id, 'source': '13f', 'event_type': label,
                       'ticker': '', 'transaction_date': None, 'accepted_at': filing['accepted_at'],
                       'reported_at': filing['reported_at'], 'observed_at': observed, 'shares': str(new-old),
                       'price': None, 'plan_10b5_1': None, 'source_url': filing['url'],
                       'details': json.dumps(detail, ensure_ascii=False)})
    return events


def _fetch_filing(request, cik, filing):
    accession = filing['accession']
    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
        raise ValueError('无效 SEC accession')
    primary = filing['primary'].split('/')[-1]
    if not re.fullmatch(r'[\w.-]+', primary):
        raise ValueError('无效 SEC 文件名')
    base = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/'
    cover = _xml(request(base + primary))
    amendment = _text(cover, './/amendmentType').upper() if filing['form'].endswith('/A') else 'INITIAL'
    if amendment not in ('INITIAL', 'RESTATEMENT', 'NEW HOLDINGS'):
        raise ValueError(f'{accession} 修订类型未知')
    items = json.loads(request(base + 'index.json'))['directory']['item']
    names = [item['name'] for item in items if item['name'].lower().endswith('.xml') and item['name'] != primary and re.fullmatch(r'[\w.-]+', item['name'])]
    for name in names:
        raw = request(base + name)
        try:
            root = _xml(raw)
        except ET.ParseError:
            continue
        if root.tag.lower() == 'informationtable':
            return {'amendment': amendment, 'holdings': parse_information_table(raw), 'url': base + name}
    raise ValueError(f'{accession} 未找到 13F 持仓表')


def _cache(db, cik, filing, request):
    with db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS thirteenf_filings (accession TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        cached = conn.execute('SELECT payload FROM thirteenf_filings WHERE accession=?', (filing['accession'],)).fetchone()
    if cached:
        return {**filing, **json.loads(cached[0])}
    fetched = _fetch_filing(request, cik, filing)
    with db() as conn:
        conn.execute('INSERT OR REPLACE INTO thirteenf_filings VALUES (?, ?)', (filing['accession'], json.dumps(fetched, ensure_ascii=False)))
    return {**filing, **fetched}


def _replace_events(db, investor_id, period, events):
    # Replace atomically; amendments can change or eliminate a previously reported delta.
    with db() as conn:
        prior = {r[0]: (json.loads(r[1]), r[2]) for r in conn.execute('SELECT id, payload, observed_at FROM events WHERE id LIKE ?', ('13f:%',)) if json.loads(r[1]).get('investor_id') == investor_id and json.loads(json.loads(r[1]).get('details', '{}')).get('current_period') == period}
        for event in events:
            if event['id'] in prior:
                event['observed_at'] = prior[event['id']][1]
            conn.execute('INSERT INTO events VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                         (event['id'], json.dumps(event, ensure_ascii=False), event['observed_at']))
        for stale in set(prior) - {event['id'] for event in events}:
            conn.execute('DELETE FROM events WHERE id=?', (stale,))


def refresh(records, request, db, now):
    errors, count = [], 0
    original_request = request
    def request(url):
        time.sleep(.15)
        return original_request(url)
    for investor in records:
        cik = investor.get('reporting_person_cik')
        if investor.get('category') != '13f' or not investor.get('enabled') or not cik or not re.fullmatch(r'\d{1,10}', str(cik)):
            continue
        try:
            data = json.loads(request(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json'))
            recent = data['filings']['recent']
            filings = []
            for i, form in enumerate(recent['form']):
                if form not in ('13F-HR', '13F-HR/A'):
                    continue
                period = recent['reportDate'][i]
                try:
                    date.fromisoformat(period)
                except ValueError:
                    continue
                filings.append({'form': form, 'period': period, 'accession': recent['accessionNumber'][i],
                                'primary': recent['primaryDocument'][i], 'reported_at': recent['filingDate'][i],
                                'accepted_at': recent['acceptanceDateTime'][i]})
            periods = sorted({f['period'] for f in filings}, reverse=True)[:2]
            if len(periods) < 2 or not adjacent(periods[1], periods[0]):
                raise ValueError('尚无两个连续季度的 13F 快照')
            grouped = {p: [] for p in periods}
            for filing in filings:
                if filing['period'] in grouped:
                    grouped[filing['period']].append(_cache(db, cik, filing, request))
            previous, current = (merge_filings(grouped[p]) for p in reversed(periods))
            newest = max(grouped[periods[0]], key=lambda f: (f['accepted_at'] or f['reported_at'], f['accession']))
            _replace_events(db, investor['id'], periods[0], compare(investor['id'], periods[1], previous, periods[0], current, newest, now()))
            count += 1
        except Exception as exc:
            errors.append(f'{investor["id"]}: {exc}')
    STATE['error'] = ('部分 13F 抓取失败：' + '; '.join(errors[:3])) if errors else None
    if count:
        STATE['last_success'] = now()
    return {'updated': count, 'errors': errors}
