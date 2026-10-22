"""Validate historical OHLCV rows without admitting not-yet-known candles."""
from .core import ValidationReport, validate_candles

__all__ = ["ValidationReport", "validate_candles"]
__version__ = "0.1.0"
