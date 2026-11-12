import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import congress_tracker
import investor_profiles
import investor_tracker as tracker


def event(key, source, kind, date, ticker='', details=None, url='https://example.org/1'):
    return {'id': key, 'investor_id': 'person', 'source': source, 'event_type': kind,
            'transaction_date': date, 'reported_at': '2026-02-08', 'observed_at': '2026-02-09',
            'source_url': url, 'ticker': ticker, 'shares': 10, 'details': json.dumps(details or {})}


class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = tracker.DB_PATH
        tracker.DB_PATH = Path(self.temp.name) / 'events.sqlite3'
        self.person = {'id': 'person', 'category': 'congress'}
        self.patch = patch.object(tracker, 'records', return_value=[self.person])
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        tracker.DB_PATH = self.previous
        self.temp.cleanup()

    def test_house_ranges_and_filter_and_pagination(self):
        amounts = {'amount_low': '$1,001', 'amount_high': '$15,000', 'asset': 'Acme'}
        summary = event('house:1:filing', 'congress', 'PTR 披露', None, details={'parser_version': congress_tracker.PARSER_VERSION})
        a = event('house:1:trade:0', 'congress', 'P', '2026-01-01', 'ACME', amounts)
        b = event('house:1:trade:1', 'congress', 'S (partial)', '2026-01-02', 'ACME', amounts)
        c = event('house:1:trade:2', 'congress', 'P', '2026-02-01', 'ABC', {'amount_low': '$5,000,001', 'amount_high': 'Over $5,000,000'})
        tracker.save_events([summary, a, b, c])
        result = investor_profiles.profile(tracker, 'person', offset=0, limit=2)
        self.assertEqual(result['summary']['transaction_count'], 3)
        self.assertEqual(result['summary']['filing_count'], 1)
        self.assertEqual(result['summary']['buy_count'], 2)
        self.assertEqual(result['summary']['sell_count'], 1)
        self.assertEqual(result['summary']['amount_low'], 5002003)
        self.assertIsNone(result['summary']['amount_high'])
        self.assertEqual(result['pagination']['total'], 4)
        self.assertEqual(len(result['events']), 2)
        self.assertEqual(investor_profiles.profile(tracker, 'person', side='sell')['summary']['transaction_count'], 1)
        self.assertEqual(investor_profiles.profile(tracker, 'person', year='2025')['events'], [])

    def test_ark_funds_are_separate_and_filing_is_not_a_trade(self):
        a = event('ark-1', 'ark', 'buy', '2026-01-03', 'XYZ', {'fund': 'ARKK', 'name': 'XYZ'})
        b = event('ark-2', 'ark', 'sell', '2026-02-03', 'XYZ', {'fund': 'ARKQ', 'name': 'XYZ'})
        tracker.save_events([a, b])
        result = investor_profiles.profile(tracker, 'person')
        self.assertEqual(result['filters']['funds'], ['ARKK', 'ARKQ'])
        self.assertEqual(len(result['activity']), 2)
        selected = investor_profiles.profile(tracker, 'person', fund='ARKK')
        self.assertEqual(selected['summary']['buy_count'], 1)
        self.assertEqual(selected['summary']['sell_count'], 0)
        self.assertEqual(selected['activity'][0]['buy_shares'], 10)
        self.assertEqual(investor_profiles.profile(tracker, 'person', query='xyz')['summary']['transaction_count'], 2)
        self.assertEqual(investor_profiles.profile(tracker, 'person', query='absent')['summary']['transaction_count'], 0)
        self.assertIsNone(selected['summary']['amount_low'])

    def test_quarter_end_changes_are_not_transactions(self):
        e = event('13f:1', '13f', '增仓', None, details={'issuer': 'XYZ', 'cusip': '123456789', 'current_period': '2026-03-31'})
        tracker.save_events([e])
        result = investor_profiles.profile(tracker, 'person')
        self.assertEqual(result['summary']['transaction_count'], 0)
        self.assertEqual(result['summary']['position_change_count'], 1)
        self.assertEqual(result['timeline'][0]['month'], '2026-03')
        self.assertEqual(result['summary']['buy_count'], 1)
        self.assertEqual(investor_profiles.profile(tracker, 'person', query='123456789')['summary']['position_change_count'], 1)
        self.assertEqual(investor_profiles.profile(tracker, 'person', side='buy')['summary']['position_change_count'], 1)
        self.assertEqual(investor_profiles.profile(tracker, 'person', side='sell')['summary']['position_change_count'], 0)
        self.assertIsNone(result['summary']['latest_transaction_date'])

    def test_invalid_params_and_unknown_investor(self):
        with self.assertRaises(LookupError): investor_profiles.profile(tracker, 'unknown')
        with self.assertRaises(ValueError): investor_profiles.profile(tracker, 'person', year='zzzz')
        with self.assertRaises(ValueError): investor_profiles.profile(tracker, 'person', side='random')
        with self.assertRaises(ValueError): investor_profiles.profile(tracker, 'person', limit=101)


if __name__ == '__main__':
    unittest.main()
