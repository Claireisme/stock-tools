import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import ark_history
import ark_holdings
import investor_tracker as tracker


class ArkHistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = tracker.DB_PATH
        tracker.DB_PATH = Path(self.tmp.name) / 'test.db'
        self.item = {'security_id':'88160R101', 'ticker':'TSLA', 'name':'Tesla', 'shares':20, 'weight':2, 'market_value':100}
        for day, positions in [('2026-11-10', [self.item]), ('2026-11-11', []), ('2026-11-12', [{**self.item,'shares':30}])]:
            ark_holdings.save(tracker.db, {'fund':'ARKK','as_of':day,'source_url':'https://example.com','positions':positions}, 'observed')
        self.now = datetime(2026,11,13,17,0,tzinfo=ZoneInfo('America/New_York'))

    def tearDown(self):
        tracker.DB_PATH = self.old
        self.tmp.cleanup()

    def test_history_and_prices_with_verified_cusip(self):
        def api(host,path,params):
            if path.startswith('/v2/assets/'):
                self.assertTrue(path.endswith('88160R101'))
                return {'symbol':'TSLA','class':'us_equity'}
            self.assertEqual(params['feed'],'iex')
            self.assertEqual(params['adjustment'],'raw')
            return {'bars':[{'t':'2026-11-10T05:00:00Z','c':250.0}, {'t':'2026-11-11T05:00:00Z','c':None}]}
        data=ark_history.history(tracker.db,'ARKK','88160R101',api,today=self.now)
        self.assertEqual([p['shares'] for p in data['holdings']],[20,None,30])
        self.assertEqual(data['price']['points'],[{'date':'2026-11-10','close':250.0}])
        self.assertIsNone(data['price']['error'])

    def test_mismatch_cannot_produce_price(self):
        def api(host,path,params):
            self.assertTrue(path.startswith('/v2/assets/'))
            return {'symbol':'OTHER','class':'us_equity'}
        data=ark_history.history(tracker.db,'ARKK','88160R101',api,today=self.now)
        self.assertEqual(data['price']['points'],[])
        self.assertIn('未能匹配',data['price']['error'])

    def test_missing_ticker_and_missing_price_keep_positions(self):
        pos={**self.item,'security_id':'PRIVATE', 'ticker':''}
        ark_holdings.save(tracker.db, {'fund':'ARKK','as_of':'2026-11-13','source_url':'https://example.com','positions':[pos]}, 'observed')
        with patch('ark_history.quote',side_effect=AssertionError('no network')):
            data=ark_history.history(tracker.db,'ARKK','PRIVATE',None,today=self.now)
        self.assertEqual(data['holdings'][-1]['shares'],20)
        self.assertTrue(data['price']['error'])

    def test_no_invented_holdings_and_invalid_fund(self):
        with self.assertRaises(LookupError):
            ark_history.history(tracker.db,'ARKK','123456789',None,today=self.now)
        with self.assertRaises(ValueError):
            ark_history.history(tracker.db,'../x','88160R101',None,today=self.now)


if __name__ == '__main__':
    unittest.main()
