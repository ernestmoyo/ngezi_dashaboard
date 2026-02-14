"""
Shared utilities for data ingestion: header detection, date normalisation,
column renaming.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def normalise_date(val: Any) -> pd.Timestamp | None:
    """Convert Excel serial number or datetime to pd.Timestamp.

    Excel serial numbers use the 1899-12-30 epoch. Native datetime objects
    are cast directly. Returns None for unparseable values.
    """
    if val is None:
        return None
    if isinstance(val, pd.Timestamp):
        return val
    if isinstance(val, (int, float)):
        try:
            return pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(val))
        except (ValueError, OverflowError):
            logger.warning("Could not convert serial number %s to date", val)
            return None
    try:
        return pd.Timestamp(val)
    except (ValueError, TypeError):
        logger.warning("Could not parse date value: %s", val)
        return None


def to_snake_case(name: str) -> str:
    """Convert a column name to snake_case.

    Handles spaces, parentheses, slashes, and percent signs.
    """
    import re

    s = str(name).strip()
    # Replace common symbols
    s = s.replace("%", "pct").replace("/", "_per_").replace("(", "").replace(")", "")
    s = s.replace("-", "_").replace(".", "_")
    # Collapse whitespace and special chars to underscores
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s)
    # CamelCase to snake_case
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", s)
    s = s.lower().strip("_")
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    return s


def find_header_row(
    sheet,
    signature: set[str],
    max_rows: int = 20,
) -> int | None:
    """Scan an openpyxl sheet for the row containing signature strings.

    Returns the 1-based row index where at least two cells match values
    in `signature`, or None if not found within `max_rows`.
    """
    for row_idx in range(1, max_rows + 1):
        matches = 0
        for cell in sheet[row_idx]:
            if cell.value is not None and str(cell.value).strip() in signature:
                matches += 1
        if matches >= 2:
            return row_idx
    return None


def safe_float(val: Any) -> float | None:
    """Coerce a value to float, returning None for non-numeric values."""
    if val is None:
        return None
    if isinstance(val, str):
        # Skip formula strings and text labels
        val = val.strip()
        if val.startswith("=") or not val:
            return None
        # Handle percentage strings like "78%"
        if val.endswith("%"):
            try:
                return float(val[:-1])
            except ValueError:
                return None
        try:
            return float(val)
        except ValueError:
            return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def normalise_percentage(val: float | None, assume_decimal: bool = False) -> float | None:
    """Normalise percentage to 0-100 range.

    If assume_decimal is True, values < 1.0 are multiplied by 100
    (e.g. 0.78 -> 78.0). Values already in 0-100 range are left as-is.
    """
    if val is None:
        return None
    if assume_decimal and abs(val) < 1.0:
        return val * 100.0
    return val
