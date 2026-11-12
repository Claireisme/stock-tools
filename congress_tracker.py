"""House Clerk PTR index and text-based PDF extraction."""
import csv
import io
import json
import re
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

IDENTITIES = Path(__file__).with_name('congress_identities.json')
BASE = 'https://disclosures-clerk.house.gov'
PARSER_VERSION = 2


def fetch(url, limit=20_000_000):
    with urlopen(Request(url, headers={'User-Agent': 'Disclosure Watch (public filing research)'}), timeout=30) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError('House 文件超过大小限制')
    return payload


def filing_date(s):
    return datetime.strptime(s.strip(), '%m/%d/%Y').date().isoformat()


def parse_index(payload, year, identities):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = f'{year}FD.txt'
        info = archive.getinfo(name)
        if info.file_size > 50_000_000:
            raise ValueError('House 索引超过大小限制')
        text = archive.read(info).decode('utf-8-sig')
    matches = []
    by_key = {(m['first'].casefold(), m['last'].casefold(), m['district'].upper()): m
              for m in identities if m['chamber'] == 'House'}
    for row in csv.DictReader(io.StringIO(text), delimiter='\t'):
        if row.get('FilingType') != 'P' or row.get('Prefix', '').strip() != 'Hon.':
            continue
        key = (row.get('First', '').strip().casefold(), row.get('Last', '').strip().casefold(), row.get('StateDst', '').strip().upper())
        m = by_key.get(key)
        if not m or not re.fullmatch(r'\d+', row.get('DocID', '')):
            continue
        try:
            reported = filing_date(row['FilingDate'])
        except (ValueError, KeyError):
            continue
        if not ('2025-01-03' <= reported < '2027-01-03'):
            continue
        matches.append({'investor_id': m['id'], 'bioguide_id': m['bioguide_id'], 'doc_id': row['DocID'], 'year': year,
                        'reported_at': reported, 'district': m['district'],
                        'url': f'{BASE}/public_disc/ptr-pdfs/{year}/{row["DocID"]}.pdf'})
    return matches


TRANSACTION = re.compile(r'(?m)^\s*(?P<owner>SP|JT|DC|--|S)\s+(?P<asset>(?:(?!\n\s*(?:SP|JT|DC|--)\s+).){1,500}?)\s+(?P<action>P|S(?:\s*\(partial\)|\s*\(full\))?|E)\s+(?P<date>\d{2}/\d{2}/\d{4})\s*(?P<notice>\d{2}/\d{2}/\d{4})\s*(?P<low>\$[\d,]+)\s*-\s*(?P<high>\$[\d,]+|Over\s+\$[\d,]+)', re.S | re.M)


def parse_text(text, filing, observed_at):
    if '\x00' in text:
        return parse_damaged_text(text, filing, observed_at)
    text = text.replace('\x00', '')
    events = []
    for index, match in enumerate(TRANSACTION.finditer(text)):
        item = match.groupdict()
        try:
            trade_date = filing_date(item['date'])
            delay = (date.fromisoformat(filing['reported_at']) - date.fromisoformat(trade_date)).days
        except ValueError:
            continue
        asset = ' '.join(item['asset'].split())
        ticker = re.search(r'\(([A-Z][A-Z0-9.\-]{0,9})\)', asset)
        details = {'asset': asset, 'owner': item['owner'], 'amount_low': item['low'], 'amount_high': item['high'],
                   'notification_date': filing_date(item['notice']), 'disclosure_delay_days': delay,
                   'bioguide_id': filing['bioguide_id'], 'district': filing['district'],
                   'note': '金额为区间；申报人、配偶或受抚养人可能为交易人。交易分类及金额请核对原件。'}
        events.append({'id': f'house:{filing["doc_id"]}:trade:{index}', 'investor_id': filing['investor_id'], 'source': 'congress',
                       'event_type': item['action'], 'ticker': ticker.group(1) if ticker else '', 'transaction_date': trade_date,
                       'accepted_at': None, 'reported_at': filing['reported_at'], 'observed_at': observed_at, 'shares': None,
                       'price': None, 'plan_10b5_1': None, 'source_url': filing['url'], 'details': json.dumps(details, ensure_ascii=False)})
    return events



DAMAGED_TRADE = re.compile(r'(?<![A-Za-z])(?P<action>P|S(?:\s*\(partial\)|\s*\(full\))?|E)\s+(?P<date>\d{2}/\d{2}/\d{4})\s*(?P<notice>\d{2}/\d{2}/\d{4})\s*(?P<low>\$[\d,]+)\s*-\s*(?P<high>\$[\d,]+|Over\s+\$[\d,]+)')


def parse_damaged_text(text, filing, observed_at):
    # Do not interpret partially decoded font labels as owners or asset names.
    cleaned = '\n'.join(line for line in text.splitlines() if '\x00' not in line)
    cleaned = re.sub(r'ID Owner Asset Transaction.*?\$200\?', '', cleaned, flags=re.S)
    cleaned = re.sub(r'(?m)^(?:Filing ID #\d+|Clerk of the House of Representatives.*|Name:.*|Status:.*|State/District:.*)\s*$', '', cleaned)
    events = []
    previous = 0
    for match in DAMAGED_TRADE.finditer(cleaned):
        item = match.groupdict()
        segment = cleaned[previous:match.start()].strip()
        previous = match.end()
        if not re.search(r'\[[A-Z]{2,4}\]\s*$', segment) or len(re.findall(r'\[[A-Z]{2,4}\]', segment)) != 1:
            continue
        owner_match = re.match(r'^(SP|JT|DC|--)\s+', segment)
        owner = owner_match.group(1) if owner_match else None
        if owner_match:
            segment = segment[owner_match.end():]
        asset = ' '.join(segment.split())
        try:
            trade_date = filing_date(item['date'])
            notice_date = filing_date(item['notice'])
            delay = (date.fromisoformat(filing['reported_at']) - date.fromisoformat(trade_date)).days
        except ValueError:
            continue
        ticker = re.search(r'\(([A-Z][A-Z0-9.\-]{0,9})\)', asset)
        details = {'asset': asset, 'owner': owner, 'amount_low': item['low'], 'amount_high': item['high'],
                   'notification_date': notice_date, 'disclosure_delay_days': delay,
                   'bioguide_id': filing['bioguide_id'], 'district': filing['district'],
                   'note': '金额为区间；字体损坏时交易人可能无法识别，请核对原件。'}
        events.append({'id': f'house:{filing["doc_id"]}:trade:{len(events)}', 'investor_id': filing['investor_id'],
                       'source': 'congress', 'event_type': item['action'], 'ticker': ticker.group(1) if ticker else '',
                       'transaction_date': trade_date, 'accepted_at': None, 'reported_at': filing['reported_at'],
                       'observed_at': observed_at, 'shares': None, 'price': None, 'plan_10b5_1': None,
                       'source_url': filing['url'], 'details': json.dumps(details, ensure_ascii=False)})
    return events

def parse_pdf(data, filing, observed_at):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('众院 PTR 文件需要 pypdf，请安装 pypdf') from exc
    reader = PdfReader(io.BytesIO(data))
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    events = parse_text(text, filing, observed_at)
    # Always retain discovery, including image-only and unrecognized forms.
    details = {'bioguide_id': filing['bioguide_id'], 'district': filing['district'], 'parsed_trade_count': len(events), 'parser_version': PARSER_VERSION,
               'note': 'PTR 申报；未解析的扫描件或版式须查阅原件。'}
    summary = {'id': f'house:{filing["doc_id"]}:filing', 'investor_id': filing['investor_id'], 'source': 'congress',
               'event_type': 'PTR 披露', 'ticker': '', 'transaction_date': None, 'accepted_at': None,
               'reported_at': filing['reported_at'], 'observed_at': observed_at, 'shares': None, 'price': None,
               'plan_10b5_1': None, 'source_url': filing['url'], 'details': json.dumps(details, ensure_ascii=False)}
    return [summary, *events]



def current_house_filing_ids(db):
    with db() as conn:
        result = set()
        for event_id, payload in conn.execute("SELECT id, payload FROM events WHERE id LIKE 'house:%:filing'"):
            try:
                details = json.loads(json.loads(payload).get('details', '{}'))
            except (ValueError, TypeError, AttributeError):
                continue
            if details.get('parser_version') == PARSER_VERSION:
                result.add(event_id)
        return result


def save_house_events(db, events):
    groups = {}
    for event in events:
        match = re.fullmatch(r'house:(\d+):(?:filing|trade:\d+)', event.get('id', ''))
        if not match:
            raise ValueError('无效的众议院事件编号')
        groups.setdefault(match.group(1), []).append(event)
    for doc_id, group in groups.items():
        if not any(event['id'] == f'house:{doc_id}:filing' for event in group):
            raise ValueError('众议院申报缺少索引记录')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT observed_at FROM events WHERE id = ?', (f'house:{doc_id}:filing',)).fetchone()
            checkpoint = conn.execute('SELECT COALESCE(MAX(sequence), 0) FROM alert_feed').fetchone()[0]
            if old:
                conn.execute('DELETE FROM events WHERE id LIKE ?', (f'house:{doc_id}:%',))
            for event in group:
                event = dict(event)
                if old:
                    event['observed_at'] = old[0]
                conn.execute('INSERT INTO events VALUES (?, ?, ?)',
                             (event['id'], json.dumps(event, ensure_ascii=False), event['observed_at']))
            if old:
                conn.execute('DELETE FROM alert_feed WHERE sequence > ?', (checkpoint,))
                outdated = []
                for sequence, payload in conn.execute('SELECT sequence, payload FROM alert_feed'):
                    try:
                        event_id = json.loads(payload).get('id', '')
                    except (ValueError, TypeError, AttributeError):
                        continue
                    if event_id.startswith(f'house:{doc_id}:'):
                        outdated.append((sequence,))
                conn.executemany('DELETE FROM alert_feed WHERE sequence = ?', outdated)

def fetch_house_ptr(existing_ids=(), years=None):
    identities = json.loads(IDENTITIES.read_text())['members']
    year = datetime.now(timezone.utc).year
    if years is None and year not in (2025, 2026):
        raise ValueError('议席任期资料已过期，需要重新核验身份。')
    years = years or (year, year - 1)
    existing_ids = set(existing_ids)
    events, failures = [], []
    for year in years:
        if year not in (2025, 2026):
            continue
        try:
            filings = parse_index(fetch(f'{BASE}/public_disc/financial-pdfs/{year}FD.zip'), year, identities)
        except Exception as exc:
            failures.append(f'{year}: {exc}')
            continue
        filings.sort(key=lambda item: (item['reported_at'], item['doc_id']), reverse=True)
        for filing in filings:
            if f'house:{filing["doc_id"]}:filing' in existing_ids:
                continue
            try:
                events.extend(parse_pdf(fetch(filing['url']), filing, datetime.now(timezone.utc).isoformat()))
            except Exception as exc:
                failures.append(f'{filing["doc_id"]}: {exc}')
            time.sleep(0.15)
            if len([event for event in events if event['event_type'] == 'PTR 披露']) >= 40:
                return events, failures
    return events, failures
