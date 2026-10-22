"""Zero-dependency, deterministic, daily-candle validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping, Iterable

UTC = timezone.utc


def _aware_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must have a UTC offset")
    return parsed.astimezone(UTC)


@dataclass
class ValidationReport:
    checked: int = 0
    eligible: int = 0
    excluded_unclosed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    first_eligible_open_utc: str | None = None
    last_eligible_open_utc: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "eligible": self.eligible,
            "excluded_unclosed": self.excluded_unclosed,
            "errors": self.errors,
            "warnings": self.warnings,
            "first_eligible_open_utc": self.first_eligible_open_utc,
            "last_eligible_open_utc": self.last_eligible_open_utc,
        }


def validate_candles(
    records: Iterable[Mapping[str, str]],
    *,
    as_of: str | datetime,
    delay_seconds: int = 300,
) -> ValidationReport:
    """Validate 1D UTC OHLCV rows.

    A candle is eligible only if as_of >= its UTC open + 1 day + delay.
    This is a data validation helper, not a trading signal or strategy.
    CSV row numbers start from 2 (header is row 1).
    """
    if not isinstance(delay_seconds, int) or isinstance(delay_seconds, bool) or delay_seconds < 0:
        raise ValueError("delay_seconds must be a nonnegative integer")
    cutoff = _aware_utc(as_of)
    result = ValidationReport()
    seen: set[datetime] = set()
    eligible_opens: list[datetime] = []
    previous: datetime | None = None

    for row_num, record in enumerate(records, start=2):
        result.checked += 1
        label = f"row {row_num}"
        try:
            opened = _aware_utc(record["open_time_utc"])
            if opened.hour or opened.minute or opened.second or opened.microsecond:
                raise ValueError("1D candles must open at 00:00:00 UTC")
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            result.errors.append(f"{label}: invalid open_time_utc ({exc})")
            continue
        if opened in seen:
            result.errors.append(f"{label}: duplicate open_time_utc {opened.isoformat()}")
            continue
        seen.add(opened)
        if previous is not None and opened < previous:
            result.warnings.append(f"{label}: rows are out of chronological order")
        previous = opened

        try:
            nums = {name: Decimal(str(record[name])) for name in ("open", "high", "low", "close", "volume")}
            if any(not value.is_finite() for value in nums.values()):
                raise ValueError("non-finite numeric value")
            if nums["open"] <= 0 or nums["close"] <= 0 or nums["low"] <= 0 or nums["high"] <= 0:
                raise ValueError("OHLC prices must be positive")
            if nums["volume"] < 0:
                raise ValueError("volume must be nonnegative")
            if nums["high"] < max(nums["open"], nums["close"], nums["low"]):
                raise ValueError("high is below an OHLC value")
            if nums["low"] > min(nums["open"], nums["close"], nums["high"]):
                raise ValueError("low is above an OHLC value")
        except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
            result.errors.append(f"{label}: invalid OHLCV ({exc})")
            continue

        known_at = opened + timedelta(days=1, seconds=delay_seconds)
        if cutoff < known_at:
            result.excluded_unclosed += 1
        else:
            result.eligible += 1
            eligible_opens.append(opened)

    sorted_opens = sorted(eligible_opens)
    if sorted_opens:
        result.first_eligible_open_utc = sorted_opens[0].isoformat()
        result.last_eligible_open_utc = sorted_opens[-1].isoformat()
        for left, right in zip(sorted_opens, sorted_opens[1:]):
            missing = (right - left).days - 1
            if missing > 0:
                result.warnings.append(
                    f"gap: {missing} missing daily candle(s) between {left.date()} and {right.date()}"
                )
    return result
