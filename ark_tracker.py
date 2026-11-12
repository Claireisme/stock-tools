"""Retrieve and normalize ARK's latest official ETF trade notification."""

import datetime as dt
import hashlib
import json
import urllib.request

ARK_TRADES_URL = "https://etfs.ark-funds.com/hubfs/idt/trades/ARK_Trades.xls"
_REQUIRED = ("fund", "date", "direction", "ticker", "isin", "name", "shares", "% of etf")


def _date(value, datemode, xlrd):
    if isinstance(value, (int, float)):
        return xlrd.xldate_as_datetime(value, datemode).date().isoformat()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Invalid ARK transaction date: {value!r}")


def parse_ark(data, observed_at=None):
    try:
        import xlrd
    except ImportError as exc:
        raise RuntimeError("ARK 交易文件需要 xlrd：请安装 xlrd>=2.0.1,<3") from exc
    workbook = xlrd.open_workbook(file_contents=data, ignore_workbook_corruption=True)
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat()
    events = []
    found_header = False
    for sheet in workbook.sheets():
        columns = None
        for index in range(sheet.nrows):
            values = sheet.row_values(index)
            if columns is None:
                header = {str(value).strip().lower(): i for i, value in enumerate(values)}
                if all(name in header for name in _REQUIRED):
                    columns = header
                    found_header = True
                continue
            row = {name: values[columns[name]] for name in _REQUIRED}
            if not any(str(value).strip() for value in row.values()):
                continue
            fund = str(row["fund"]).strip().upper()
            ticker = str(row["ticker"]).strip().upper()
            isin = str(row["isin"]).strip().upper()
            direction = str(row["direction"]).strip().lower()
            if not fund or not ticker or not isin or direction not in ("buy", "sell"):
                raise ValueError(f"Invalid ARK trade row {index + 1}")
            date = _date(row["date"], workbook.datemode, xlrd)
            try:
                shares = float(str(row["shares"]).replace(",", ""))
                weight = float(str(row["% of etf"]).replace(",", "").rstrip("%"))
            except ValueError as exc:
                raise ValueError(f"Invalid ARK trade row {index + 1}") from exc
            if shares <= 0 or not (shares < float("inf")) or not (0 <= weight < float("inf")):
                raise ValueError(f"Invalid ARK trade row {index + 1}")
            identity = json.dumps([fund, date, direction, isin], separators=(",", ":"))
            events.append({
                "id": "ark-" + hashlib.sha256(identity.encode()).hexdigest(),
                "investor_id": "cathie-wood", "source": "ark", "event_type": direction,
                "ticker": ticker, "transaction_date": date, "accepted_at": None,
                "reported_at": None, "observed_at": observed_at, "shares": shares,
                "price": None, "plan_10b5_1": None, "source_url": ARK_TRADES_URL,
                "details": json.dumps({"fund": fund, "isin": isin, "name": str(row["name"]).strip(),
                                       "percent_of_etf": weight}, ensure_ascii=False),
            })
    if not found_header:
        raise ValueError("ARK 交易文件缺少预期的表头")
    return events


def fetch_ark():
    request = urllib.request.Request(ARK_TRADES_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; ARK trade monitor)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(10_000_001)
    if len(data) > 10_000_000:
        raise ValueError("ARK 交易文件超过 10 MB")
    return parse_ark(data)
