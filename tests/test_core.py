import unittest
from closed_candle_guard import validate_candles
from closed_candle_guard.cli import main
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory


def bar(time="2026-10-19T00:00:00Z", **kwargs):
    result = {"open_time_utc": time, "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1.5"}
    result.update(kwargs)
    return result


class ValidatorTests(unittest.TestCase):
    def test_exact_as_of_boundary(self):
        rows = [bar()]
        self.assertEqual(validate_candles(rows, as_of="2026-10-20T00:04:59Z").excluded_unclosed, 1)
        self.assertEqual(validate_candles(rows, as_of="2026-10-20T00:05:00Z").eligible, 1)

    def test_invalid_ohlcv(self):
        report = validate_candles([bar(high="99")], as_of="2026-10-22T00:00:00Z")
        self.assertFalse(report.ok)
        self.assertIn("high is below", report.errors[0])

    def test_duplicate_bar(self):
        report = validate_candles([bar(), bar()], as_of="2026-10-22T00:00:00Z")
        self.assertFalse(report.ok)
        self.assertIn("duplicate", report.errors[0])

    def test_detect_missing_day(self):
        report = validate_candles([bar("2026-10-19T00:00:00Z"), bar("2026-10-21T00:00:00Z")], as_of="2026-10-23T00:00:00Z")
        self.assertTrue(report.ok)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("1 missing", report.warnings[0])

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            validate_candles([], as_of="2026-10-22T00:00:00")

    def test_utc_midnight_required(self):
        report = validate_candles([bar("2026-10-19T01:00:00Z")], as_of="2026-10-22T00:00:00Z")
        self.assertFalse(report.ok)

    def test_negative_volume(self):
        report = validate_candles([bar(volume="-1")], as_of="2026-10-22T00:00:00Z")
        self.assertFalse(report.ok)

    def test_nonfinite(self):
        report = validate_candles([bar(close="NaN")], as_of="2026-10-22T00:00:00Z")
        self.assertFalse(report.ok)

    def test_out_of_order_warning(self):
        report = validate_candles([bar("2026-10-20T00:00:00Z"), bar("2026-10-19T00:00:00Z")], as_of="2026-10-23T00:00:00Z")
        self.assertTrue(report.ok)
        self.assertEqual(report.eligible, 2)
        self.assertTrue(any("chronological" in s for s in report.warnings))

    def test_cli(self):
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "bars.csv"
            f.write_text("open_time_utc,open,high,low,close,volume\n2026-10-19T00:00:00Z,100,110,90,105,1000\n", encoding="utf8")
            with redirect_stdout(StringIO()) as output:
                code = main([str(f), "--as-of", "2026-10-20T00:05:00Z"])
            self.assertEqual(code, 0)
            self.assertIn('"eligible": 1', output.getvalue())


if __name__ == "__main__":
    unittest.main()
