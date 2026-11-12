import json
import sys
import types
import unittest
from unittest.mock import patch

import ark_tracker


class Sheet:
    def __init__(self, rows):
        self.rows = rows
        self.nrows = len(rows)

    def row_values(self, index):
        return self.rows[index]


def workbook(rows):
    return types.SimpleNamespace(sheets=lambda: [Sheet(rows)], datemode=0)


HEADER = ["FUND", "Date", "Direction", "Ticker", "ISIN", "Name", "Shares", "% of ETF"]
TRADE = ["ARKK", "2026/11/10", "Buy", "TSLA", "US88160R1014", "Tesla", 123.0, 0.123]


class ArkTests(unittest.TestCase):
    def parse(self, rows):
        fake = types.SimpleNamespace(open_workbook=lambda **kwargs: workbook(rows))
        with patch.dict(sys.modules, {"xlrd": fake}):
            return ark_tracker.parse_ark(b"test", "2026-11-11T00:00:00+00:00")

    def test_fund_trades_and_stable_identity(self):
        first = self.parse([["Disclaimer"], HEADER, TRADE])[0]
        revised = self.parse([HEADER, TRADE[:6] + [150, 0.2]])[0]
        self.assertEqual(first["id"], revised["id"])
        self.assertEqual(first["transaction_date"], "2026-11-10")
        self.assertEqual(first["event_type"], "buy")
        self.assertEqual(json.loads(first["details"])["fund"], "ARKK")
        self.assertIsNone(first["reported_at"])

    def test_schema_change_and_invalid_row_fail(self):
        with self.assertRaises(ValueError):
            self.parse([["unexpected header"]])
        with self.assertRaises(ValueError):
            self.parse([HEADER, TRADE[:2] + ["unknown"] + TRADE[3:]])

    def test_same_security_in_different_funds_is_distinct(self):
        events = self.parse([HEADER, TRADE, ["ARKQ"] + TRADE[1:]])
        self.assertNotEqual(events[0]["id"], events[1]["id"])


if __name__ == "__main__":
    unittest.main()
