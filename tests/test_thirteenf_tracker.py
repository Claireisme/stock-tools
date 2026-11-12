import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import thirteenf_tracker as t


def table(*rows):
    items = ''.join(f'<infoTable><nameOfIssuer>{name}</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>{cusip}</cusip><shrsOrPrnAmt><sshPrnamt>{qty}</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>' for name, cusip, qty in rows)
    return ('<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">' + items + '</informationTable>').encode()


class ThirteenFTest(unittest.TestCase):
    def test_holdings_and_deltas(self):
        old = t.parse_information_table(table(('Old','111111111',5),('Down','222222222',20),('Up','333333333',10)))
        new = t.parse_information_table(table(('New','444444444',10),('Down','222222222',10),('Up','333333333',15)))
        filing = {'accepted_at':'2026-05-01','reported_at':'2026-05-01','url':'https://www.sec.gov/file'}
        events = t.compare('fund', '2025-12-31', old, '2026-03-31', new, filing, 'now')
        by_cusip = {json.loads(e['details'])['cusip']: e for e in events}
        self.assertEqual([by_cusip[x]['event_type'] for x in ('111111111','222222222','333333333','444444444')], ['退出持仓','减仓','增仓','新建仓'])
        self.assertEqual(by_cusip['333333333']['shares'], '5')
        self.assertIsNone(by_cusip['333333333']['transaction_date'])
        with self.assertRaises(ValueError):
            t.compare('fund', '2025-09-30', old, '2026-03-31', new, filing, 'now')

    def test_amendments_replace_and_add(self):
        def filing(kind, dt, data):
            return {'amendment':kind,'accepted_at':dt,'reported_at':dt,'accession':dt,'holdings':t.parse_information_table(data)}
        original = filing('INITIAL','1',table(('A','111111111',1)))
        restatement = filing('RESTATEMENT','2',table(('A','111111111',5)))
        addition = filing('NEW HOLDINGS','3',table(('A','111111111',2),('B','222222222',1)))
        merged = t.merge_filings([addition, original, restatement])
        self.assertEqual({v['cusip']: v['amount'] for v in merged.values()}, {'111111111':'7','222222222':'1'})
        with self.assertRaises(ValueError): t.merge_filings([addition])

    def test_refresh_fetches_and_caches_quarterly_filings(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            def db():
                conn = sqlite3.connect(Path(d) / 'a.sqlite')
                conn.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, observed_at TEXT NOT NULL)')
                return conn
            recent = {'form':['13F-HR','13F-HR'], 'reportDate':['2026-03-31','2025-12-31'],
                      'accessionNumber':['0000000001-26-000002','0000000001-26-000001'],
                      'primaryDocument':['primary.xml','primary.xml'], 'filingDate':['2026-05-10','2026-02-10'],
                      'acceptanceDateTime':['2026-05-10T12:00:00Z','2026-02-10T12:00:00Z']}
            calls = []
            def request(url):
                calls.append(url)
                if 'submissions' in url: return json.dumps({'filings':{'recent':recent}}).encode()
                if url.endswith('primary.xml'): return b'<edgarSubmission/>'
                if url.endswith('index.json'): return b'{"directory":{"item":[{"name":"primary.xml"},{"name":"holdings.xml"}]}}'
                return table(('A','111111111',20 if '000000000126000002' in url else 10))
            investor = {'id':'fund','category':'13f','enabled':True,'reporting_person_cik':'1'}
            with patch.object(t.time, 'sleep'):
                result = t.refresh([investor], request, db, lambda:'now')
                before = len(calls)
                result2 = t.refresh([investor], request, db, lambda:'later')
            self.assertEqual(result['updated'], 1)
            self.assertEqual(result2['updated'], 1)
            self.assertEqual(len(calls)-before, 1)
            with db() as conn: rows = conn.execute('SELECT payload FROM events').fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0][0])['event_type'], '增仓')
            self.assertEqual(json.loads(rows[0][0])['observed_at'], 'now')

    def test_revisions_remove_stale_events_but_keep_other_quarters(self):
        with tempfile.TemporaryDirectory() as d:
            def db():
                conn = sqlite3.connect(Path(d)/'a.sqlite')
                conn.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, observed_at TEXT NOT NULL)')
                return conn
            def event(id, period): return {'id':id, 'investor_id':'a','observed_at':'first','details':json.dumps({'current_period':period})}
            t._replace_events(db,'a','2026-03-31',[event('13f:one','2026-03-31')])
            t._replace_events(db,'a','2026-06-30',[event('13f:two','2026-06-30')])
            t._replace_events(db,'a','2026-06-30',[])
            with db() as conn: rows = conn.execute('SELECT id FROM events').fetchall()
            self.assertEqual(rows, [('13f:one',)])

if __name__ == '__main__': unittest.main()
