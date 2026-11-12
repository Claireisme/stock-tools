import io
import json
import unittest
import tempfile
from pathlib import Path
import investor_tracker
import zipfile

import congress_tracker as tracker


class HouseTests(unittest.TestCase):
    def test_identity_match_requires_title_name_district_and_term(self):
        rows = ('Prefix\tLast\tFirst\tFilingType\tStateDst\tFilingDate\tDocID\n'
                'Hon.\tPelosi\tNancy\tP\tCA11\t01/17/2025\t123\n'
                'Hon.\tPelosi\tNancy\tP\tCA12\t01/17/2025\t124\n'
                'Mr.\tPelosi\tNancy\tP\tCA11\t01/17/2025\t125\n'
                'Hon.\tPelosi\tNancy\tP\tCA11\t01/17/2027\t126\n')
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('2025FD.txt', rows)
        people = [{'chamber': 'House', 'first': 'Nancy', 'last': 'Pelosi', 'district': 'CA11', 'id': 'n', 'bioguide_id': 'P000197'}]
        result = tracker.parse_index(data.getvalue(), 2025, people)
        self.assertEqual([f['doc_id'] for f in result], ['123'])

    def test_transaction_and_publication_lag(self):
        text = 'SP Alphabet Inc. - Class A Common\nStock (GOOGL) [OP]\nP 01/14/202501/14/2025 $250,001 -\n$500,000\n'
        filing = {'doc_id': '123', 'investor_id': 'n', 'url': 'https://example.test', 'reported_at': '2025-01-17', 'bioguide_id': 'P000197', 'district': 'CA11'}
        events = tracker.parse_text(text, filing, '2025-01-18T00:00:00Z')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['ticker'], 'GOOGL')
        d = json.loads(events[0]['details'])
        self.assertEqual(d['disclosure_delay_days'], 3)
        self.assertEqual((d['amount_low'], d['amount_high'], d['owner']), ('$250,001', '$500,000', 'SP'))

    def test_damaged_pdf_font_does_not_invent_owner_or_skip_first_trade(self):
        text = ('P\x00\x00 T\x00\x00\nClerk of the House of Representatives • Center\n'
                'Name: Hon. Gilbert Cisneros\nStatus: Member\nState/District:CA31\n'
                'ID Owner Asset Transaction\nType\nDate Notification\nDate\nAmount Cap.\nGains >\n$200?\n'
                'Alexandria Real Estate Equities,\nInc. Common Stock (ARE) [ST]\n'
                'P 10/20/202611/09/2026$1,001 - $15,000\n'
                'S\x00\x00 O\x00: 150 Main Street Trust\n'
                'Alliant Energy Corporation (LNT)\n[ST]\n'
                'P 10/20/202611/09/2026$1,001 - $15,000\n')
        f = {'doc_id':'1', 'investor_id':'n', 'url':'https://example.test', 'reported_at':'2026-11-10', 'bioguide_id':'C001123', 'district':'CA31'}
        events = tracker.parse_text(text, f, 'now')
        self.assertEqual([e['ticker'] for e in events], ['ARE', 'LNT'])
        self.assertIsNone(json.loads(events[1]['details'])['owner'])
        self.assertEqual(json.loads(events[0]['details'])['asset'], 'Alexandria Real Estate Equities, Inc. Common Stock (ARE) [ST]')

    def test_damaged_pdf_handles_action_joined_to_asset_line(self):
        text = ('bad\x00font\n'
                'BNP PARIBAS ORD (BNPQF) [ST]S 10/13/202611/09/2026$1,001 - $15,000\n'
                'BridgeBio Pharma, Inc. - Common Stock (BBIO) [ST]\n'
                'P 10/20/202611/09/2026$1,001 - $15,000')
        filing = {'doc_id':'1', 'investor_id':'n', 'url':'https://example.test', 'reported_at':'2026-11-10', 'bioguide_id':'C001123', 'district':'CA31'}
        events = tracker.parse_text(text, filing, 'now')
        self.assertEqual([(event['ticker'], event['event_type']) for event in events], [('BNPQF','S'), ('BBIO','P')])
        self.assertEqual(json.loads(events[1]['details'])['asset'], 'BridgeBio Pharma, Inc. - Common Stock (BBIO) [ST]')

    def test_reparse_atomically_replaces_stale_rows_without_new_alerts(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = investor_tracker.DB_PATH
            investor_tracker.DB_PATH = Path(directory) / 'events.sqlite3'
            try:
                old = [{'id':'house:42:filing', 'observed_at':'first', 'details':'{}'},
                       {'id':'house:42:trade:9', 'observed_at':'first', 'details':'{}'}]
                investor_tracker.save_events(old)
                self.assertEqual(tracker.current_house_filing_ids(investor_tracker.db), set())
                with investor_tracker.db() as conn:
                    before = conn.execute('SELECT MAX(sequence) FROM alert_feed').fetchone()[0]
                new = [{'id':'house:42:filing', 'observed_at':'later', 'details':json.dumps({'parser_version':2})},
                       {'id':'house:42:trade:0', 'observed_at':'later', 'details':'{}'}]
                tracker.save_house_events(investor_tracker.db, new)
                self.assertEqual(tracker.current_house_filing_ids(investor_tracker.db), {'house:42:filing'})
                with investor_tracker.db() as conn:
                    rows = conn.execute('SELECT id, observed_at FROM events ORDER BY id').fetchall()
                    self.assertEqual(rows, [('house:42:filing', 'first'), ('house:42:trade:0', 'first')])
                    self.assertIsNone(conn.execute('SELECT MAX(sequence) FROM alert_feed').fetchone()[0])
            finally:
                investor_tracker.DB_PATH = previous

    def test_unparseable_row_does_not_absorb_following_trade(self):
        text = 'SP Unknown malformed row\nSP Known Corp (ABC) [ST]\nP 01/14/202501/14/2025 $1,001 - $15,000'
        f = {'doc_id':'1', 'investor_id':'n', 'url':'https://example.test', 'reported_at':'2025-01-17', 'bioguide_id':'P000197', 'district':'CA11'}
        events = tracker.parse_text(text, f, 'now')
        self.assertEqual(len(events), 1)
        self.assertEqual(json.loads(events[0]['details'])['asset'], 'Known Corp (ABC) [ST]')


if __name__ == '__main__':
    unittest.main()
