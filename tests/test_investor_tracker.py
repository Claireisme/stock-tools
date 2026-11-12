import json
import tempfile
import unittest
from pathlib import Path
import investor_tracker as tracker


class InvestorTrackerTest(unittest.TestCase):
    def test_form4_identity_codes_and_plan(self):
        xml = b'''<ownershipDocument><issuer><issuerCik>0001326380</issuerCik><issuerTradingSymbol>GME</issuerTradingSymbol></issuer>
        <reportingOwner><reportingOwnerId><rptOwnerCik>0001767470</rptOwnerCik></reportingOwnerId></reportingOwner>
        <aff10b5One>1</aff10b5One><nonDerivativeTable>
        <nonDerivativeTransaction><transactionDate><value>2026-10-13</value></transactionDate><transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>10</value></transactionShares></transactionAmounts></nonDerivativeTransaction>
        <nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode></transactionCoding></nonDerivativeTransaction>
        <nonDerivativeTransaction><transactionCoding><transactionCode>F</transactionCode></transactionCoding></nonDerivativeTransaction>
        </nonDerivativeTable><derivativeTable><derivativeTransaction><transactionCoding><transactionCode>M</transactionCode></transactionCoding></derivativeTransaction></derivativeTable></ownershipDocument>'''
        filing = {'accession': '1', 'accepted_at': '2026-10-13T20:00:00Z', 'reported_at': '2026-10-13'}
        event = tracker.parse_form4(xml, {'id': 'cohen', 'reporting_person_cik': '0001767470', 'issuer_cik': '0001326380'}, filing, 'https://example.com', '2026-10-14')
        self.assertEqual([e['event_type'] for e in event], ['P 买入（公开市场或私下）', 'S 卖出（公开市场或私下）', '税款或行权价扣缴', '期权行权或转换'])
        self.assertTrue(all(e['plan_10b5_1'] is True for e in event))
        self.assertTrue(all('整份申报' in e['details'] for e in event))
        self.assertEqual(event[0]['shares'], '10')
        self.assertEqual(tracker.parse_form4(xml, {'id': 'cohen', 'reporting_person_cik': '0001767470', 'issuer_cik': '0000000001'}, filing, '', ''), [])
        self.assertEqual(tracker.parse_form4(xml, {'id': 'other', 'reporting_person_cik': '123'}, filing, '', ''), [])

    def test_joint_filing_tracks_each_reporting_person_once(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as path:
            original = tracker.DB_PATH
            tracker.DB_PATH = Path(path) / 'events.sqlite3'
            today = datetime.now(timezone.utc).date().isoformat()
            people = [{'id': 'a', 'category': 'form4', 'enabled': True, 'reporting_person_cik': '1', 'issuer_cik': '3'},
                      {'id': 'b', 'category': 'form4', 'enabled': True, 'reporting_person_cik': '2', 'issuer_cik': '3'}]
            recent = {'form': ['4'], 'accessionNumber': ['0000000001-26-000001'], 'primaryDocument': ['filing.xml'], 'filingDate': [today], 'acceptanceDateTime': [today]}
            xml = b'<ownershipDocument><issuer><issuerCik>3</issuerCik><issuerTradingSymbol>ABC</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerCik>1</rptOwnerCik></reportingOwnerId></reportingOwner><reportingOwner><reportingOwnerId><rptOwnerCik>2</rptOwnerCik></reportingOwnerId></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionCoding><transactionCode>P</transactionCode></transactionCoding></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'
            def request(url):
                return json.dumps({'filings': {'recent': recent}}).encode() if 'submissions' in url else xml
            try:
                tracker.save_events([{'id': 'sec:0000000001-26-000001:nonDerivativeTable:0', 'investor_id': 'a', 'observed_at': 'earlier'}])
                with patch.object(tracker, 'records', return_value=people), patch.object(tracker, 'request', side_effect=request), patch.object(tracker.time, 'sleep'):
                    tracker.refresh_sec()
                    tracker.refresh_sec()
                with tracker.db() as conn:
                    events = [json.loads(row[0]) for row in conn.execute('SELECT payload FROM events')]
                self.assertEqual(sorted(e['investor_id'] for e in events), ['a', 'b'])
            finally:
                tracker.DB_PATH = original

    def test_unmatched_filing_is_cached_by_verified_identity(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as path:
            original = tracker.DB_PATH
            tracker.DB_PATH = Path(path) / 'events.sqlite3'
            today = datetime.now(timezone.utc).date().isoformat()
            person = {'id': 'a', 'category': 'form4', 'enabled': True, 'reporting_person_cik': '1', 'issuer_cik': '3'}
            recent = {'form': ['4'], 'accessionNumber': ['0000000001-26-000001'], 'primaryDocument': ['filing.xml'], 'filingDate': [today], 'acceptanceDateTime': [today]}
            xml = b'<ownershipDocument><issuer><issuerCik>4</issuerCik></issuer><reportingOwner><reportingOwnerId><rptOwnerCik>1</rptOwnerCik></reportingOwnerId></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionCoding><transactionCode>P</transactionCode></transactionCoding></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'
            fetched = []
            def request(url):
                if 'submissions' in url:
                    return json.dumps({'filings': {'recent': recent}}).encode()
                fetched.append(url)
                return xml
            try:
                with patch.object(tracker, 'records', return_value=[person]), patch.object(tracker, 'request', side_effect=request), patch.object(tracker.time, 'sleep'):
                    tracker.refresh_sec()
                    tracker.refresh_sec()
                    self.assertEqual(len(fetched), 1)
                    person['issuer_cik'] = '4'
                    tracker.refresh_sec()
                    self.assertEqual(len(fetched), 2)
                with tracker.db() as conn:
                    self.assertEqual(conn.execute('SELECT count(*) FROM events').fetchone()[0], 1)
            finally:
                tracker.DB_PATH = original

    def test_search_runs_before_result_limit(self):
        with tempfile.TemporaryDirectory() as path:
            original = tracker.DB_PATH
            tracker.DB_PATH = Path(path) / 'events.sqlite3'
            try:
                events = [{'id': f'13f:{i}', 'investor_id': 'none', 'source': '13f',
                           'observed_at': f'{i:04d}', 'details': 'Rare Corp' if i == 0 else 'Other'}
                          for i in range(510)]
                tracker.save_events(events)
                self.assertEqual(len(tracker.snapshot('13f')['events']), 500)
                result = tracker.snapshot('13f', 'Rare Corp')['events']
                self.assertEqual([event['id'] for event in result], ['13f:0'])
            finally:
                tracker.DB_PATH = original

    def test_revised_event_retains_first_observed_time(self):
        with tempfile.TemporaryDirectory() as path:
            original = tracker.DB_PATH
            tracker.DB_PATH = Path(path) / 'events.sqlite3'
            try:
                tracker.save_events([{'id': 'ark:test', 'observed_at': 'first', 'shares': '10'}])
                tracker.save_events([{'id': 'ark:test', 'observed_at': 'later', 'shares': '20'}])
                with tracker.db() as conn:
                    rows = conn.execute('SELECT payload FROM events').fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(json.loads(rows[0][0]), {'id': 'ark:test', 'observed_at': 'first', 'shares': '20'})
            finally:
                tracker.DB_PATH = original

if __name__ == '__main__':
    unittest.main()
