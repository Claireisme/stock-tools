import json
import unittest
from unittest.mock import patch
import senate_tracker as s


class SenateTrackerTest(unittest.TestCase):
    def setUp(self):
        self.members = json.loads(s.IDENTITIES.read_text())['members']
        self.row = ['Richard', 'Blumenthal', 'Senator', '<a href="/search/view/ptr/1234-abcd/">Periodic Transaction Report</a>', '10/01/2026']
        self.filing = s.candidate(self.row, self.members)

    def test_matching_requires_senator_term_and_official_link(self):
        self.assertEqual(self.filing['member']['bioguide_id'], 'B001277')
        self.assertIsNone(s.candidate(['Richard', 'Blumenthal', 'Staff', self.row[3], self.row[4]], self.members))
        self.assertIsNone(s.candidate(['Richard', 'Blumenthal', 'Senator', '<a href="https://evil.example/search/view/ptr/1/">PTR</a>', self.row[4]], self.members))
        self.assertIsNone(s.candidate(['Richard', 'Blumenthal', 'Senator', self.row[3], '01/01/2024'], self.members))

    def test_state_verified_and_amount_range_delay(self):
        raw = b'''<p>Office of Senator from Connecticut</p><table><tr><th>#</th><th>Transaction Date</th><th>Owner</th><th>Ticker</th><th>Asset Name</th><th>Asset Type</th><th>Type</th><th>Amount</th><th>Comment</th></tr><tr><td>1</td><td>09/01/2026</td><td>Spouse</td><td>XYZ</td><td>Example Corp</td><td>Stock</td><td>Purchase</td><td>$1,001 - $15,000</td><td>--</td></tr></table>'''
        summary, trade = s.parse_filing(raw, self.filing, '2026-10-02T00:00:00Z')
        self.assertEqual(trade['investor_id'], 'richard-blumenthal')
        self.assertEqual(trade['transaction_date'], '2026-09-01')
        detail = json.loads(trade['details'])
        self.assertEqual(detail['disclosure_delay_days'], 30)
        self.assertEqual(detail['amount_range'], '$1,001 - $15,000')
        self.assertEqual(detail['owner'], 'Spouse')
        self.assertTrue(json.loads(summary['details'])['identity_verified'])

    def test_unverified_identity_and_scanned_file_are_retained_without_attribution(self):
        summary = s.parse_filing(b'%PDF-1.5 scan', self.filing, '2026-10-02')[0]
        self.assertIsNone(summary['investor_id'])
        self.assertFalse(json.loads(summary['details'])['identity_verified'])
        self.assertEqual(json.loads(summary['details'])['parsed_trade_count'], 0)

    def test_consent_required_before_network(self):
        with patch.object(s.Session, 'consent', side_effect=AssertionError('network')):
            with self.assertRaises(ValueError):
                s.fetch_senate_ptr(consent=False)

    def test_search_and_report_pipeline_without_live_network(self):
        row = self.row
        class FakeSession:
            def consent(self):
                return 'csrf'
            def fetch(self, url, values=None, referer=None):
                if url == s.DATA:
                    return json.dumps({'data': [row]}).encode()
                return b'<title>Periodic Transaction Report</title><p>Senator from Connecticut</p><table><tr><th>Transaction Date</th><th>Owner</th><th>Ticker</th><th>Asset Name</th><th>Type</th><th>Amount</th></tr><tr><td>09/01/2026</td><td>Self</td><td>XYZ</td><td>Example</td><td>Sale</td><td>$1,001 - $15,000</td></tr></table>'
        events, errors = s.fetch_senate_ptr(consent=True, session=FakeSession())
        self.assertFalse(errors)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]['investor_id'], 'richard-blumenthal')
        events, errors = s.fetch_senate_ptr([events[0]['id']], consent=True, session=FakeSession())
        self.assertEqual(events, [])

    def test_changed_search_shape_is_an_error_not_empty_results(self):
        class FakeSession:
            def consent(self):
                return 'csrf'
            def fetch(self, url, values=None, referer=None):
                return json.dumps({'data': [{'unexpected': 'format'}]}).encode()
        with self.assertRaisesRegex(ValueError, '记录格式变化'):
            s.fetch_senate_ptr(consent=True, session=FakeSession())

    def test_cross_domain_redirect_rejected(self):
        from urllib.request import Request
        handler = s.OfficialRedirect()
        request = Request(s.HOME)
        with self.assertRaises(ValueError):
            handler.redirect_request(request, None, 302, 'Found', {}, 'https://attacker.example/steal')

    def test_official_403_safe_reference(self):
        from urllib.error import HTTPError
        session = s.Session()
        with patch.object(session.opener, 'open', side_effect=HTTPError(s.HOME, 403, 'Forbidden', {'X-Reference-Error': '18.abcdef.12345'}, None)):
            with self.assertRaisesRegex(RuntimeError, r'参考编号：18\.abcdef\.12345'):
                session.consent()
        with patch.object(session.opener, 'open', side_effect=HTTPError(s.HOME, 403, 'Forbidden', {'X-Reference-Error': '<script>'}, None)):
            with self.assertRaises(RuntimeError) as raised:
                session.consent()
            self.assertNotIn('<script>', str(raised.exception))

    def test_official_403_is_visible(self):
        from urllib.error import HTTPError
        session = s.Session()
        with patch.object(session.opener, 'open', side_effect=HTTPError(s.HOME, 403, 'Forbidden', {}, None)):
            with self.assertRaisesRegex(RuntimeError, '403'):
                session.consent()


if __name__ == '__main__':
    unittest.main()
