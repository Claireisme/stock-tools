import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class OptionsApiTests(unittest.TestCase):
    @patch('server.tradier_json')
    def test_expirations_handles_single_and_empty(self, request):
        request.return_value = {'expirations': {'date': '2027-01-15'}}
        self.assertEqual(server.option_expirations('aapl')['expirations'], ['2027-01-15'])
        request.return_value = {'expirations': None}
        self.assertEqual(server.option_expirations('AAPL')['expirations'], [])

    @patch('server.tradier_json')
    def test_contract_fields_and_missing_iv(self, request):
        item = {'symbol': 'AAPL270115C00100000', 'option_type': 'call', 'strike': 100,
                'expiration_date': '2027-01-15', 'contract_size': 100,
                'bid': 2.5, 'ask': 3, 'bidsize': 0, 'asksize': 12, 'volume': 50, 'last': None, 'greeks': {'mid_iv': .25}}
        request.return_value = {'options': {'option': item}}
        contract = server.option_chain('AAPL', '2027-01-15')['options'][0]
        self.assertEqual((contract['strike'], contract['bid'], contract['ask'], contract['iv']), (100, 2.5, 3, .25))
        self.assertEqual((contract['bid_size'], contract['ask_size'], contract['volume']), (0, 12, 50))
        self.assertIsNone(contract['last'])
        item['greeks'] = None
        self.assertIsNone(server.option_chain('AAPL', '2027-01-15')['options'][0]['iv'])
        item['contract_size'] = 10
        self.assertEqual(server.option_chain('AAPL', '2027-01-15')['options'], [])

    def test_validation_and_missing_token(self):
        with self.assertRaises(ValueError):
            server.option_expirations('AAPL&bad=1')
        with self.assertRaises(ValueError):
            server.option_chain('AAPL', '2027-02-30')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(server.OptionsDataError) as error:
                server.option_expirations('AAPL')
            self.assertEqual(error.exception.code, 'missing_token')

class AlpacaTests(unittest.TestCase):
    def contract(self):
        return {'symbol': 'AAPL270115C00100000', 'underlying_symbol': 'AAPL',
                'expiration_date': '2027-01-15', 'type': 'call', 'strike_price': '100',
                'size': '100', 'multiplier': '100',
                'deliverables': [{'type': 'equity', 'symbol': 'AAPL', 'amount': '100', 'delayed_settlement': False}]}

    @patch('server.alpaca_json')
    def test_pagination_and_filter_adjusted_contracts(self, request):
        adjusted = self.contract()
        adjusted['deliverables'] += [{'type': 'cash', 'symbol': 'USD', 'amount': '100'}]
        request.side_effect = [
            {'option_contracts': [self.contract()], 'next_page_token': 'next'},
            {'option_contracts': [adjusted], 'next_page_token': None}]
        result = server.alpaca_contracts('AAPL')
        self.assertEqual(len(result), 1)
        self.assertEqual(request.call_args_list[1].args[2]['page_token'], 'next')
        self.assertIn('expiration_date_lte', request.call_args_list[0].args[2])

    @patch('server.alpaca_json')
    def test_chain_snapshots_and_pagination(self, request):
        request.side_effect = [
            {'option_contracts': [self.contract()], 'next_page_token': None},
            {'snapshots': {}, 'next_page_token': 'next'},
            {'snapshots': {'AAPL270115C00100000': {'latestQuote': {'bp': 2, 'ap': 4, 'bs': 2, 'as': 3, 't': '2026-11-11T12:00:00Z'}, 'latestTrade': {'p': 3, 's': 9}, 'impliedVolatility': .27}}, 'next_page_token': None},
        ]
        result = server.alpaca_chain('AAPL', '2027-01-15')
        item = result['options'][0]
        self.assertEqual((item['bid'], item['ask'], item['last'], item['iv']), (2, 4, 3, .27))
        self.assertEqual((item['bid_size'], item['ask_size'], item['volume']), (2, 3, None))
        self.assertEqual(item['bid_time'], '2026-11-11T12:00:00Z')
        self.assertEqual(request.call_args_list[1].args[2]['feed'], 'indicative')
        self.assertEqual(request.call_args_list[2].args[2]['page_token'], 'next')

    @patch('server.alpaca_json')
    def test_repeated_page_token_fails(self, request):
        request.return_value = {'snapshots': {}, 'next_page_token': 'loop'}
        with self.assertRaises(server.OptionsDataError):
            list(server.alpaca_pages('https://data.alpaca.markets', '/x', {}, 'snapshots'))

    def test_count_validation(self):
        self.assertEqual(server.option_count(0), 0)
        for value in (None, False, -1, 1.2, 'bad', float('inf')):
            self.assertIsNone(server.option_count(value))

    def test_missing_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(server, 'ROOT', Path(folder)), patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(server.OptionsDataError) as error:
                server.alpaca_expirations('AAPL')
            self.assertEqual(error.exception.code, 'missing_token')


if __name__ == '__main__':
    unittest.main()
