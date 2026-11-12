"""Official Senate eFD PTR adapter; access requires explicit non-commercial consent."""
import http.cookiejar
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

BASE = 'https://efdsearch.senate.gov'
HOME = BASE + '/search/home/'
SEARCH = BASE + '/search/'
DATA = BASE + '/search/report/data/'
IDENTITIES = Path(__file__).with_name('congress_identities.json')


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.token = None
        self.links, self.tables, self.before_tables = [], [], []
        self._table = self._row = self._cell = None
        self._anchor = False
        self._table_seen = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name') == 'csrfmiddlewaretoken':
            self.token = attrs.get('value')
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'table' and self._table is None:
            self._table, self._table_seen = [], True
        elif tag == 'tr' and self._table is not None:
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []
        elif tag == 'br' and self._cell is not None:
            self._cell.append(' ')

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif not self._table_seen:
            self.before_tables.append(data)

    def handle_endtag(self, tag):
        if tag in ('th', 'td') and self._cell is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == 'table' and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def document(value):
    parser = Document()
    parser.feed(value)
    return parser


def official_url(link):
    url = urljoin(BASE, link)
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'efdsearch.senate.gov' or parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('参议院文件链接不是官方来源')
    if not re.fullmatch(r'/search/view/(?:ptr|paper)/[a-zA-Z0-9-]+/?', parsed.path):
        raise ValueError('参议院文件链接格式未知')
    return url


def normalize(s):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', str(s).casefold()).split())


def date_iso(value):
    for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError('参议院披露日期格式未知')


def candidate(row, identities):
    if not isinstance(row, list) or len(row) < 5:
        return None
    first, last, office, link, filed = row[:5]
    if not all(isinstance(x, str) for x in (first, last, office, link, filed)):
        return None
    # Matching names alone is insufficient; require elected-office and state evidence later.
    aliases = {'tommy-tuberville': (('tommy', 'tuberville'), ('thomas', 'tuberville')),
               'richard-blumenthal': (('richard', 'blumenthal'),)}
    if 'senator' not in normalize(office).split():
        return None
    for member in identities:
        if member.get('chamber') != 'Senate' or (normalize(first), normalize(last)) not in aliases.get(member['id'], ()):
            continue
        link_parser = document(link)
        if len(link_parser.links) != 1:
            continue
        try:
            url = official_url(link_parser.links[0])
            reported = date_iso(filed)
        except ValueError:
            continue
        if not ('2025-01-03' <= reported < '2027-01-03'):
            continue
        return {'member': member, 'office': office, 'url': url, 'reported_at': reported,
                'doc_id': urlsplit(url).path.strip('/').split('/')[-1]}
    return None


def identity_verified(filing, parsed):
    state = filing['member']['state'].upper()
    state_name = {'AL': 'Alabama', 'CT': 'Connecticut'}.get(state, '')
    # Only accept explicit state/office labels outside tables; ticker/asset text cannot identify a filer.
    text = ' '.join([filing['office'], *parsed.before_tables])
    state_pattern = '|'.join(re.escape(x) for x in (state, state_name) if x)
    return bool(re.search(r'\b(?:state|senator\s+(?:for|from))\s*[:\-]?\s*(?:' + state_pattern + r')\b', text, re.I))


def parse_filing(raw, filing, observed):
    is_pdf = raw.startswith(b'%PDF')
    html = '' if is_pdf else raw.decode('utf-8', errors='replace')
    parsed = document(html)
    verified = identity_verified(filing, parsed)
    investor_id = filing['member']['id'] if verified else None
    url = filing['url']
    common = {'investor_id': investor_id, 'source': 'congress', 'ticker': '', 'transaction_date': None,
              'accepted_at': None, 'reported_at': filing['reported_at'], 'observed_at': observed,
              'shares': None, 'price': None, 'plan_10b5_1': None, 'source_url': url}
    prefix = 'senate:' + filing['doc_id']
    trades = []
    required = ('transaction date', 'owner', 'ticker', 'asset name', 'type', 'amount')
    for table in parsed.tables:
        if not table:
            continue
        header = [normalize(x) for x in table[0]]
        if not all(h in header for h in required):
            continue
        for number, row in enumerate(table[1:], 1):
            if len(row) != len(header):
                continue
            fields = dict(zip(header, row))
            try:
                transaction = date_iso(fields['transaction date'])
                delay = (date.fromisoformat(filing['reported_at']) - date.fromisoformat(transaction)).days
            except ValueError:
                continue
            ticker = fields['ticker'] if re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,9}', fields['ticker']) else ''
            detail = {'asset': fields['asset name'], 'owner': fields['owner'], 'amount_range': fields['amount'],
                      'asset_type': fields.get('asset type'), 'comment': fields.get('comment'),
                      'disclosure_delay_days': delay, 'identity_verified': verified,
                      'bioguide_id': filing['member']['bioguide_id'] if verified else None,
                      'note': '金额为区间；交易人可能是本人、配偶或受抚养人。'}
            trades.append({**common, 'id': f'{prefix}:trade:{number}', 'event_type': fields['type'],
                           'ticker': ticker, 'transaction_date': transaction,
                           'details': json.dumps(detail, ensure_ascii=False)})
        break
    note = '身份待核验：索引及文件未同时提供明确的议席州信息。' if not verified else 'PTR 原文；扫描件或未识别版式需人工查阅。'
    detail = {'identity_verified': verified, 'candidate_name': filing['member']['id'],
              'bioguide_id': filing['member']['bioguide_id'] if verified else None,
              'parsed_trade_count': len(trades), 'note': note}
    summary = {**common, 'id': prefix + ':filing', 'event_type': '参议院 PTR 披露',
               'details': json.dumps(detail, ensure_ascii=False)}
    return [summary, *trades]


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname != 'efdsearch.senate.gov' or parsed.port or parsed.username or parsed.password:
            raise ValueError('参议院网站重定向至非官方域名')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Session:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(OfficialRedirect(), HTTPCookieProcessor(self.cookies))

    def fetch(self, url, values=None, referer=None):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != 'efdsearch.senate.gov':
            raise ValueError('只允许访问官方参议院网站')
        headers = {'User-Agent': 'Disclosure Watch (non-commercial public filing research)'}
        if referer:
            headers['Referer'] = referer
        payload = urlencode(values).encode() if values is not None else None
        req = Request(url, data=payload, headers=headers)
        try:
            with self.opener.open(req, timeout=25) as response:
                if urlsplit(response.geturl()).hostname != 'efdsearch.senate.gov':
                    raise ValueError('参议院网站重定向至非官方域名')
                data = response.read(20_000_001)
        except HTTPError as exc:
            if exc.code == 403:
                reference = (exc.headers.get('X-Reference-Error') or '').strip() if exc.headers else ''
                suffix = f' 参考编号：{reference}' if re.fullmatch(r'[A-Za-z0-9._-]{1,100}', reference) else ''
                raise RuntimeError('参议院网站拒绝访问（HTTP 403），请检查网络或稍后重试。' + suffix) from exc
            raise
        if len(data) > 20_000_000:
            raise ValueError('参议院文件超过大小限制')
        return data

    def consent(self):
        token = document(self.fetch(HOME).decode('utf-8', 'replace')).token
        if not token:
            raise ValueError('参议院同意页面缺少 CSRF 令牌')
        self.fetch(HOME, {'csrfmiddlewaretoken': token, 'prohibition_agreement': '1'}, HOME)
        search = document(self.fetch(SEARCH).decode('utf-8', 'replace'))
        return next((c.value for c in self.cookies if c.name in ('csrftoken', 'csrf')), search.token or token)


def fetch_senate_ptr(existing_ids=(), *, consent=False, session=None):
    if not consent:
        raise ValueError('未确认参议院披露使用限制和非商业用途')
    if not ('2025-01-03' <= date.today().isoformat() < '2027-01-03'):
        raise ValueError('参议院议席任期资料已过期，需要重新核验身份。')
    members = json.loads(IDENTITIES.read_text(encoding='utf-8'))['members']
    session = session or Session()
    token = session.consent()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime('%m/%d/%Y 00:00:00')
    existing = set(existing_ids)
    events, errors = [], []
    for offset in range(0, 5000, 100):
        payload = {'start': str(offset), 'length': '100', 'report_types': '[11]',
                   'submitted_start_date': cutoff, 'csrfmiddlewaretoken': token}
        data = json.loads(session.fetch(DATA, payload, SEARCH))
        rows = data.get('data')
        if not isinstance(rows, list):
            raise ValueError('参议院搜索返回格式未知')
        if any(not isinstance(row, list) or len(row) < 5 or not all(isinstance(x, str) for x in row[:5]) for row in rows):
            raise ValueError('参议院搜索记录格式变化，无法可靠检查披露')
        for row in rows:
            filing = candidate(row, members)
            if not filing or f'senate:{filing["doc_id"]}:filing' in existing:
                continue
            try:
                raw = session.fetch(filing['url'])
                # Unexpected login or access pages must not be reported as successful filings.
                if b'csrfmiddlewaretoken' in raw and b'prohibition_agreement' in raw:
                    raise ValueError('参议院同意会话已失效')
                if not raw.startswith(b'%PDF') and b'periodic transaction' not in raw.lower():
                    raise ValueError('参议院报告页面格式未知')
                events.extend(parse_filing(raw, filing, datetime.now(timezone.utc).isoformat()))
            except Exception as exc:
                errors.append(f'{filing["doc_id"]}: {exc}')
            time.sleep(.15)
            if sum(e['event_type'] == '参议院 PTR 披露' for e in events) >= 40:
                return events, errors
        if len(rows) < 100:
            return events, errors
    errors.append('参议院检索结果超过分页上限，部分结果未检查')
    return events, errors
