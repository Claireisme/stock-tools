"""Summaries of locally collected disclosures, without inferring holdings or returns."""
from collections import defaultdict
import json
import re


def _detail(event):
    try:
        detail = event.get('details') or {}
        if isinstance(detail, str):
            detail = json.loads(detail)
        return detail if isinstance(detail, dict) else {}
    except (TypeError, ValueError):
        return {}


def _side(event):
    source, kind = event.get('source'), str(event.get('event_type', '')).strip()
    if source == 'ark':
        return kind if kind in ('buy', 'sell') else 'other'
    if source == 'congress':
        if kind == 'PTR 披露':
            return None
        return 'buy' if kind == 'P' else 'sell' if re.match(r'^S(?:\b|\s|\()', kind) else 'other'
    if source == 'form4':
        return 'buy' if kind.startswith('P ') else 'sell' if kind.startswith('S ') else 'other'
    if source == '13f':
        return 'buy' if kind in ('新建仓', '增仓') else 'sell' if kind in ('减仓', '退出持仓') else 'other'
    return None


def _day(event, detail):
    # 13F reports quarter-end snapshots, not transaction dates.
    return event.get('transaction_date') or (detail.get('current_period') if event.get('source') == '13f' else (event.get('reported_at') or '')[:10])


def _range(detail):
    def money(value):
        if not isinstance(value, str):
            return None
        match = re.fullmatch(r'\$\s*([\d,]+)', value.strip())
        return int(match.group(1).replace(',', '')) if match else None
    low = money(detail.get('amount_low'))
    high_text = detail.get('amount_high')
    high = money(high_text)
    if low is None or (high is None and not (isinstance(high_text, str) and re.fullmatch(r'Over\s+\$[\d,]+', high_text.strip(), re.I))):
        return None
    if high is not None and high < low:
        return None
    return low, high


def _add_range(target, bounds):
    if bounds is None:
        target['amount_missing'] += 1
        return
    low, high = bounds
    target['amount_count'] += 1
    target['amount_low'] = (target['amount_low'] or 0) + low
    if target['amount_high'] is not None:
        target['amount_high'] = None if high is None else target['amount_high'] + high
    elif target['amount_count'] == 1 and high is not None:
        target['amount_high'] = high


def profile(tracker, investor_id, year=None, side=None, fund=None, offset=0, limit=30, query=None):
    records = tracker.records()
    person = next((r for r in records if r.get('id') == investor_id and r.get('chamber') != 'Senate'), None)
    if person is None:
        raise LookupError('未找到关注对象。')
    if year and (not re.fullmatch(r'\d{4}', year) or not 1900 <= int(year) <= 2100):
        raise ValueError('无效年份。')
    if side and side not in ('buy', 'sell', 'other'):
        raise ValueError('无效交易类型。')
    if fund and not re.fullmatch(r'[A-Z0-9.-]{1,12}', fund):
        raise ValueError('无效基金代码。')
    if query and len(query) > 80:
        raise ValueError('搜索内容过长。')
    if not 0 <= offset <= 1_000_000 or not 1 <= limit <= 100:
        raise ValueError('无效分页参数。')
    with tracker.db() as conn:
        rows = conn.execute('SELECT payload FROM events').fetchall()
    house_ids = tracker.congress_tracker.current_house_filing_ids(tracker.db)
    all_items = []
    for row in rows:
        event = json.loads(row[0])
        if event.get('investor_id') != investor_id or not tracker.visible_event(event, house_ids):
            continue
        detail = _detail(event)
        all_items.append((event, detail, _side(event), _day(event, detail)))
    years = sorted({day[:4] for _, _, _, day in all_items if day and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day)}, reverse=True)
    funds = sorted({d['fund'] for e, d, _, _ in all_items if e.get('source') == 'ark' and isinstance(d.get('fund'), str) and d['fund']})
    items = [(e, d, direction, day) for e, d, direction, day in all_items
             if (not year or (day and day.startswith(year + '-')))
             and (not side or side == direction)
             and (not fund or (e.get('source') == 'ark' and d.get('fund') == fund))
             and (not query or any(query.casefold() in str(value or '').casefold() for value in (e.get('ticker'), d.get('name'), d.get('asset'), d.get('issuer'), d.get('cusip'))))]
    items.sort(key=lambda item: (item[0].get('accepted_at') or item[0].get('reported_at') or item[3] or item[0].get('observed_at') or '', item[0].get('id', '')), reverse=True)
    summary = {'event_count': len(items), 'transaction_count': 0, 'filing_count': 0,
               'buy_count': 0, 'sell_count': 0, 'other_count': 0, 'position_change_count': 0,
               'latest_transaction_date': None, 'latest_reported_at': None,
               'amount_low': None, 'amount_high': None, 'amount_count': 0, 'amount_missing': 0}
    activity, months, filings = {}, defaultdict(lambda: {'buy_count': 0, 'sell_count': 0, 'other_count': 0}), set()
    for event, detail, direction, day in items:
        reported = event.get('reported_at')
        if reported and (not summary['latest_reported_at'] or reported > summary['latest_reported_at']):
            summary['latest_reported_at'] = reported
        url = event.get('source_url')
        if url and event.get('source') != 'ark':
            filings.add((event.get('source'), url))
        if direction is None:
            continue
        if event.get('source') == '13f':
            summary['position_change_count'] += 1
        else:
            summary['transaction_count'] += 1
        summary[direction + '_count'] += 1
        transaction_date = event.get('transaction_date')
        if transaction_date and (not summary['latest_transaction_date'] or transaction_date > summary['latest_transaction_date']):
            summary['latest_transaction_date'] = transaction_date
        if day and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            months[day[:7]][direction + '_count'] += 1
        if event.get('source') == 'congress':
            _add_range(summary, _range(detail))
        ticker = (event.get('ticker') or '').strip()
        name = detail.get('name') or detail.get('asset') or detail.get('issuer') or ticker
        if not ticker and not name:
            continue
        fund_name = detail.get('fund', '') if event.get('source') == 'ark' else ''
        security_id = ticker or detail.get('cusip') or name
        key = (security_id, fund_name)
        if key not in activity:
            activity[key] = {'ticker': ticker, 'name': name, 'fund': fund_name or None,
                             'buy_count': 0, 'sell_count': 0, 'other_count': 0, 'transaction_count': 0,
                             'buy_shares': None, 'sell_shares': None,
                             'amount_low': None, 'amount_high': None, 'amount_count': 0, 'amount_missing': 0}
        entry = activity[key]
        entry[direction + '_count'] += 1
        entry['transaction_count'] += 1
        if event.get('source') == 'congress':
            _add_range(entry, _range(detail))
        if event.get('source') == 'ark' and direction in ('buy', 'sell'):
            try:
                shares = float(event['shares'])
                if 0 <= shares < float('inf'):
                    field = direction + '_shares'
                    entry[field] = (entry[field] or 0) + shares
            except (KeyError, TypeError, ValueError):
                pass
    summary['filing_count'] = len(filings)
    days = [day for _, _, _, day in all_items if day]
    observed = [e['observed_at'] for e, _, _, _ in all_items if e.get('observed_at')]
    return {'record': person, 'summary': summary,
            'activity': sorted(activity.values(), key=lambda x: (-x['transaction_count'], x['ticker'] or x['name'], x['fund'] or '')),
            'timeline': [{'month': month, **counts} for month, counts in sorted(months.items())],
            'events': [event for event, _, _, _ in items[offset:offset + limit]],
            'pagination': {'offset': offset, 'limit': limit, 'total': len(items)},
            'filters': {'years': years, 'funds': funds},
            'coverage': {'first_activity_date': min(days) if days else None, 'last_activity_date': max(days) if days else None,
                         'first_observed_at': min(observed) if observed else None, 'last_observed_at': max(observed) if observed else None}}
