# Closed Candle Guard

A small, zero-runtime-dependency Python library and CLI that checks **daily UTC OHLCV** data before a historical research workflow reads it. It guards against inadvertently treating a candle that has not closed (plus a configurable data delay) as available information.

This is an independent, intentionally minimal open-source utility. It contains no private trading logic, credentials, exchange integrations, market data downloads, or backtest results. It makes **no claims about trading performance**.

## What it does

- Rejects invalid OHLC prices, negative volume, non-finite numbers, duplicate candle opens, and invalid timestamps.
- Applies a reproducible eligibility boundary: `known_at = open_time_utc + 1 day + delay_seconds` (default 300s).
- Excludes not-yet-closed candles from eligible data (without treating their presence as a fatal error).
- Warns about gaps in *valid and eligible* daily data and out-of-order rows.
- Returns a deterministic JSON summary; CLI exits `1` on validation errors.

## Quick start

Python 3.10+:

```bash
python -m pip install -e .
closed-candle-guard examples/daily.csv --as-of 2026-10-22T00:05:00Z
```

Or, after installation:

```python
from closed_candle_guard import validate_candles
report = validate_candles(
    [{"open_time_utc": "2026-10-19T00:00:00Z", "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1000"}],
    as_of="2026-10-20T00:05:00Z",
)
print(report.to_dict())
```

## Input contract

CSV headers: `open_time_utc,open,high,low,close,volume`.

- Timestamp must have an explicit offset, and daily UTC opens must be 00:00:00 UTC.
- One candlestick covers `[open, open + 1 day)`. The earliest eligible observation is at `open + 1 day + delay`.
- This tool intentionally supports **1D daily candles only**. It does not infer timezone, market identity, active listings, or exchange-specific lot sizes.
- Gaps are warnings, not evidence of exchange malfunction. They may arise from a market listing late or from incomplete coverage.

## Run tests

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Scope and roadmap

This repository is a small utility foundation, **not an established widely adopted open-source project**. Contributions are welcome for timezone edge cases, better market calendar semantics, and additional safe input formats. Contributions must include tests for the observation-time boundary.

## License

MIT License. See [LICENSE](LICENSE).

---

### Tiếng Việt

Công cụ mã nguồn mở độc lập dùng để kiểm tra dữ liệu nến OHLCV **1D đã đóng** và thời điểm dữ liệu được phép sử dụng trong nghiên cứu/backtest. Không tự giao dịch, không phải chiến lược đầu tư, không tải dữ liệu cá nhân hay bí mật từ dự án khác.
