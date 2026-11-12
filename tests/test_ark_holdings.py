import sqlite3
import tempfile
import unittest
from pathlib import Path

import ark_holdings as h

HEADER = 'date,fund,company,ticker,cusip,shares,market value ($),weight (%)\n'


def csv_bytes(rows):
    return (HEADER + rows + '"Fund disclosure"\n').encode()


class ARKHoldingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'holdings.sqlite'
    def tearDown(self):
        self.tmp.cleanup()
    def db(self):
        return sqlite3.connect(self.path)
    def save(self, date, positions, observed):
        h.save(self.db, {'fund': 'ARKK', 'as_of': date, 'source_url': 'https://assets.ark-funds.com/test.csv', 'positions': positions}, observed)
    def test_official_csv_handles_blank_ticker_and_cash_without_merging(self):
        date, rows = h.parse(csv_bytes('11/10/2026,ARKK,Private Co,,PPOPENAIC,"123,456","$5,234.10",2.50%\n11/10/2026,ARKK,Cash Fund,,X9USDGSFT,9,"$9.00",0.10%\n'), 'ARKK')
        self.assertEqual(date, '2026-11-10')
        self.assertEqual(len(rows), 2)
        self.assertEqual([x['security_id'] for x in rows], ['PPOPENAIC', 'X9USDGSFT'])
        self.assertEqual(rows[0]['shares'], 123456)
        self.assertEqual(rows[0]['weight'], 2.5)
    def test_reject_incomplete_and_mixed_dates(self):
        with self.assertRaises(ValueError):
            h.parse(csv_bytes('11/10/2026,ARKK,Test,TST,CUSIP,10,$11,2%\n11/11/2026,ARKK,Test2,T2,CUSIP2,11,$12,3%\n'), 'ARKK')
        with self.assertRaises(ValueError):
            h.parse(csv_bytes('11/10/2026,ARKK,Test,TST,CUSIP,10,$11,2%\n11/10/2026,ARKK,Bad,B,CUSIP\n'), 'ARKK')
    def test_snapshots_compare_and_do_not_assume_a_trade(self):
        _, before = h.parse(csv_bytes('11/10/2026,ARKK,First,ONE,111,100,$100,5%\n11/10/2026,ARKK,Second,,222,20,$20,1%\n'), 'ARKK')
        self.save('2026-11-10', before, 'first')
        single = h.snapshot(self.db, 'ARKK')
        self.assertIsNone(single['previous_as_of'])
        self.assertTrue(all(item['status'] is None and item['shares_change'] is None for item in single['holdings']))
        _, after = h.parse(csv_bytes('11/11/2026,ARKK,First,ONE,111,120,$130,6%\n11/11/2026,ARKK,Third,,333,30,$30,2%\n'), 'ARKK')
        self.save('2026-11-11', after, 'second')
        result = h.snapshot(self.db, 'ARKK')
        self.assertEqual(result['previous_as_of'], '2026-11-10')
        self.assertEqual([(x['security_id'], x['status'], x['shares_change']) for x in result['holdings']], [('111','increased',20), ('333','new',30)])
        self.assertEqual((result['closed'][0]['security_id'], result['closed'][0]['shares_change']), ('222', -20))
        self.save('2026-11-11', after, 'reloaded')
        self.assertEqual(h.snapshot(self.db, 'ARKK')['observed_at'], 'second')
    def test_bad_fund_does_not_form_url(self):
        with self.assertRaises(ValueError): h.snapshot(self.db, '../evil')


if __name__ == '__main__': unittest.main()
