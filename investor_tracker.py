"""Public disclosure monitoring; events are observations, not investment advice."""
import json
import os
import re
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
import thirteenf_tracker
import congress_tracker
import ark_holdings

ROOT = Path(__file__).resolve().parent
WATCHLIST = ROOT / 'investor_watchlist.json'
DB_PATH = Path(os.environ.get('INVESTOR_DB_PATH', str(ROOT / 'investor_events.sqlite3')))
LOCK = threading.Lock()
SEC_REQUEST_LOCK = threading.Lock()
SEC_LAST_REQUEST = 0.0
STATE = {'running': False, 'last_attempt': None, 'last_success': None, 'error': None, 'ark_last_success': None, 'ark_error': None, 'ark_last_attempt_day': None, 'holdings_last_attempt_day': None, 'holdings_last_success': None, 'holdings_error': None, 'congress_last_success': None, 'congress_error': None, 'congress_last_attempt_day': None}


def now():
    return datetime.now(timezone.utc).isoformat()


def records():
    return json.loads(WATCHLIST.read_text(encoding='utf-8'))['records']


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.executescript('''CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, observed_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS alert_feed (sequence INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sec_empty_filings (accession TEXT NOT NULL, investor_id TEXT NOT NULL, owner_cik TEXT NOT NULL, issuer_cik TEXT NOT NULL, PRIMARY KEY (accession, investor_id, owner_cik, issuer_cik));
    CREATE TRIGGER IF NOT EXISTS event_alert_insert AFTER INSERT ON events BEGIN
      INSERT INTO alert_feed(payload) VALUES (NEW.payload);
    END;
    CREATE TRIGGER IF NOT EXISTS event_alert_update AFTER UPDATE OF payload ON events
    WHEN OLD.payload <> NEW.payload BEGIN
      INSERT INTO alert_feed(payload) VALUES (NEW.payload);
    END;''')
    return conn


def save_events(events):
    with db() as conn:
        for event in events:
            existing = conn.execute('SELECT observed_at FROM events WHERE id = ?', (event['id'],)).fetchone()
            if existing:
                event['observed_at'] = existing[0]
            conn.execute('INSERT INTO events VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                         (event['id'], json.dumps(event, ensure_ascii=False), event['observed_at']))


def request(url):
    global SEC_LAST_REQUEST
    ua = os.environ.get('SEC_USER_AGENT', '').strip()
    if not ua:
        try:
            ua = str(json.loads((ROOT / '.sec-config.json').read_text(encoding='utf-8')).get('user_agent', '')).strip()
        except (OSError, ValueError, TypeError, AttributeError):
            ua = ''
    if not ua or '@' not in ua:
        raise ValueError('请设置包含联系邮箱的 SEC_USER_AGENT 环境变量。')
    with SEC_REQUEST_LOCK:
        delay = 0.15 - (time.monotonic() - SEC_LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        SEC_LAST_REQUEST = time.monotonic()
        with urlopen(Request(url, headers={'User-Agent': ua, 'Accept-Encoding': 'identity'}), timeout=15) as response:
            data = response.read(50 * 1024 * 1024 + 1)
        if len(data) > 50 * 1024 * 1024:
            raise ValueError('SEC 文件超过 50 MB 限制')
        return data


def value(element, path):
    node = element.find(path)
    return (node.text or '').strip() if node is not None else ''


def parse_form4(data, investor, filing, source_url, observed_at):
    root = ET.fromstring(data)
    for node in root.iter():
        node.tag = node.tag.split('}')[-1]
    owners = [value(owner, 'reportingOwnerId/rptOwnerCik').lstrip('0') for owner in root.findall('reportingOwner')]
    if investor['reporting_person_cik'].lstrip('0') not in owners:
        return []
    issuer_cik = value(root, 'issuer/issuerCik').lstrip('0')
    if not investor.get('issuer_cik') or issuer_cik != str(investor['issuer_cik']).lstrip('0'):
        return []
    issuer = value(root, 'issuer/issuerTradingSymbol')
    plan_text = value(root, 'aff10b5One').lower()
    plan = True if plan_text in ('1', 'true') else False if plan_text in ('0', 'false') else None
    events = []
    for table in ('nonDerivativeTable', 'derivativeTable'):
        transaction_tag = 'nonDerivativeTransaction' if table == 'nonDerivativeTable' else 'derivativeTransaction'
        for index, transaction in enumerate(root.findall(f'{table}/{transaction_tag}')):
            code = value(transaction, 'transactionCoding/transactionCode')
            kind = {'P': 'P 买入（公开市场或私下）', 'S': 'S 卖出（公开市场或私下）', 'M': '期权行权或转换', 'F': '税款或行权价扣缴', 'G': '赠与'}.get(code, '其他交易')
            events.append({'id': f"sec:{filing['accession']}:{table}:{index}:{investor['id']}", 'investor_id': investor['id'], 'source': 'form4', 'event_type': kind, 'ticker': issuer,
                'transaction_date': value(transaction, 'transactionDate/value') or None, 'accepted_at': filing['accepted_at'], 'reported_at': filing['reported_at'], 'observed_at': observed_at,
                'shares': value(transaction, 'transactionAmounts/transactionShares/value') or None, 'price': value(transaction, 'transactionAmounts/transactionPricePerShare/value') or None,
                'plan_10b5_1': plan, 'source_url': source_url, 'details': f"代码 {code or '未知'}；{'衍生证券' if table == 'derivativeTable' else '非衍生证券'}；10b5-1 标记适用于整份申报。"})
    return events


def refresh_sec():
    errors = []
    for investor in records():
        cik = investor.get('reporting_person_cik')
        if not investor.get('enabled') or not cik or not re.fullmatch(r'\d{1,10}', str(cik)):
            continue
        try:
            data = json.loads(request(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json'))
        except Exception as exc:
            errors.append(f'{investor["id"]}: {exc}')
            continue
        recent = data['filings']['recent']
        for i, form in enumerate(recent['form']):
            if form not in ('4', '4/A', 'SC 13D', 'SC 13D/A', 'SCHEDULE 13D', 'SCHEDULE 13D/A'):
                continue
            try:
                filing_date = datetime.fromisoformat(recent['filingDate'][i]).date()
            except (ValueError, TypeError):
                continue
            if filing_date < (datetime.now(timezone.utc) - timedelta(days=180)).date():
                continue
            if form in ('4', '4/A') and (investor.get('category') != 'form4' or not investor.get('issuer_cik')):
                continue
            accession = recent['accessionNumber'][i]
            primary = recent['primaryDocument'][i].split('/')[-1]
            if not re.fullmatch(r'[\w.-]+', primary) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
                continue
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{primary}"
            filing = {'accession': accession, 'accepted_at': recent.get('acceptanceDateTime', [None] * len(recent['form']))[i], 'reported_at': recent['filingDate'][i]}
            with db() as conn:
                rows = conn.execute('SELECT payload FROM events WHERE id LIKE ?', (f'sec:{accession}:%',)).fetchall()
                empty = conn.execute('SELECT 1 FROM sec_empty_filings WHERE accession = ? AND investor_id = ? AND owner_cik = ? AND issuer_cik = ?', (accession, investor['id'], str(cik), str(investor.get('issuer_cik') or ''))).fetchone()
                exists = empty or any(json.loads(row[0]).get('investor_id') == investor['id'] for row in rows)
            if exists:
                continue
            observed = now()
            try:
                if form in ('4', '4/A'):
                    events = parse_form4(request(url), investor, filing, url, observed)
                else:
                    events = [{'id': f'sec:{accession}:filing:{investor["id"]}', 'investor_id': investor['id'], 'source': '13d', 'event_type': form, 'ticker': '', 'transaction_date': None, 'accepted_at': filing['accepted_at'], 'reported_at': filing['reported_at'], 'observed_at': observed, 'shares': None, 'price': None, 'plan_10b5_1': None, 'source_url': url, 'details': '主动持股申报或修订；具体持股比例和变动须查阅原文件。'}]
                save_events(events)
                if not events:
                    with db() as conn:
                        conn.execute('INSERT OR IGNORE INTO sec_empty_filings VALUES (?, ?, ?, ?)', (accession, investor['id'], str(cik), str(investor.get('issuer_cik') or '')))
            except Exception as exc:
                errors.append(f'{accession}: {exc}')
            time.sleep(0.15)
    if errors:
        raise ValueError('部分 SEC 文件抓取失败：' + '; '.join(errors[:3]))


def refresh(force_ark=False):
    with LOCK:
        STATE.update(running=True, last_attempt=now(), error=None)
    try:
        try:
            refresh_sec()
            STATE['last_success'] = now()
        except Exception as exc:
            STATE['error'] = str(exc)[:300]
        eastern = datetime.now(ZoneInfo('America/New_York'))
        today = eastern.date().isoformat()
        if force_ark or thirteenf_tracker.STATE['last_attempt_day'] != today:
            thirteenf_tracker.STATE['last_attempt_day'] = today
            try:
                thirteenf_tracker.refresh(records(), request, db, now)
            except Exception as exc:
                thirteenf_tracker.STATE['error'] = str(exc)[:300]
        if force_ark or STATE['congress_last_attempt_day'] != today:
            STATE['congress_last_attempt_day'] = today
            try:
                existing = congress_tracker.current_house_filing_ids(db)
                events, errors = congress_tracker.fetch_house_ptr(existing)
                congress_tracker.save_house_events(db, events)
                STATE['congress_error'] = '; '.join(errors[:3]) if errors else None
                if not errors:
                    STATE['congress_last_success'] = now()
            except Exception as exc:
                STATE['congress_error'] = str(exc)[:300]
        holdings_due = STATE['holdings_last_attempt_day'] != today and eastern.weekday() < 5 and (eastern.hour, eastern.minute) >= (16, 30)
        if force_ark or holdings_due:
            STATE['holdings_last_attempt_day'] = today
            try:
                result = ark_holdings.refresh(db, now)
                STATE['holdings_error'] = '部分基金更新失败：' + '; '.join(f'{k}: {v}' for k,v in result['errors'].items()) if result['errors'] else None
                if result['updated']:
                    STATE['holdings_last_success'] = now()
            except Exception as exc:
                STATE['holdings_error'] = str(exc)[:300]
        ark_day = eastern.date().isoformat()
        ark_due = eastern.weekday() < 5 and (eastern.hour, eastern.minute) >= (16, 30) and STATE['ark_last_attempt_day'] != ark_day
        if force_ark or ark_due:
            STATE['ark_last_attempt_day'] = ark_day
            STATE['ark_error'] = None
            try:
                from ark_tracker import fetch_ark
                save_events(fetch_ark())
                STATE['ark_last_success'] = now()
            except Exception as exc:
                STATE['ark_error'] = str(exc)[:300]
    finally:
        with LOCK:
            STATE['running'] = False


def start_refresh(force_ark=True):
    with LOCK:
        if STATE['running']:
            return False
        STATE['running'] = True
    threading.Thread(target=refresh, args=(force_ark,), daemon=True).start()
    return True


def start_scheduler():
    def run():
        while True:
            start_refresh(force_ark=False)
            time.sleep(900)
    threading.Thread(target=run, daemon=True).start()


def visible_event(event, current_house):
    event_id = event.get('id', '')
    if event_id.startswith('senate:'):
        return False
    if event_id.startswith('house:'):
        parts = event_id.split(':')
        return len(parts) >= 3 and f'house:{parts[1]}:filing' in current_house
    return True


def snapshot(source=None, query=None):
    with db() as conn:
        rows = conn.execute('SELECT payload FROM events').fetchall()
    current_house = congress_tracker.current_house_filing_ids(db)
    events = [event for row in rows if visible_event(event := json.loads(row[0]), current_house)]
    if source:
        events = [event for event in events if event.get('source') == source]
    if query:
        by_id = {r['id']: r for r in records()}
        key = query.casefold()
        events = [event for event in events if key in json.dumps([event, by_id.get(event.get('investor_id'), {})], ensure_ascii=False).casefold()]
    events.sort(key=lambda e: e.get('accepted_at') or e.get('reported_at') or e.get('transaction_date') or e.get('observed_at') or '', reverse=True)
    return {'records': [record for record in records() if record.get('chamber') != 'Senate'], 'events': events[:500], 'sources': [
        {'id': 'form4', 'name': 'SEC Form 4', 'status': 'error' if STATE['error'] else ('active' if STATE['last_success'] else 'pending'), 'message': STATE['error'] or '每 15 分钟检查已核实 CIK；10b5-1 标记为申报级。', 'last_success': STATE['last_success']},
        {'id': 'ark', 'name': 'ARK 每日交易', 'status': 'error' if STATE['ark_error'] else ('active' if STATE['ark_last_success'] else 'pending'), 'message': STATE['ark_error'] or 'ARK 基金交易，并非个人交易。', 'last_success': STATE['ark_last_success']},
        {'id': 'ark_holdings', 'name': 'ARK 每日持仓', 'status': 'error' if STATE['holdings_error'] else ('active' if STATE['holdings_last_success'] else 'pending'), 'message': STATE['holdings_error'] or '盘后更新基金持仓快照。', 'last_success': STATE['holdings_last_success']},
        {'id': 'congress', 'name': '众议院 PTR', 'status': 'error' if STATE['congress_error'] else ('active' if STATE['congress_last_success'] else 'pending'), 'message': (STATE['congress_error'] or '每日检查众议院官方披露。'), 'last_success': STATE['congress_last_success']},
        {'id': '13f', 'name': 'SEC Form 13F', 'status': 'error' if thirteenf_tracker.STATE['error'] else ('active' if thirteenf_tracker.STATE['last_success'] else 'pending'), 'message': thirteenf_tracker.STATE['error'] or '每日检查已核实的机构；季度快照不等同于逐笔交易。', 'last_success': thirteenf_tracker.STATE['last_success']},
        {'id': '13d', 'name': 'SEC Schedule 13D', 'status': 'error' if STATE['error'] else ('active' if STATE['last_success'] else 'pending'), 'message': STATE['error'] or '检查已核实 CIK 的申报及修订；具体内容请查看原文。', 'last_success': STATE['last_success']}], 'running': STATE['running'], 'last_attempt': STATE['last_attempt']}
