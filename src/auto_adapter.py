"""Automatic CSV adapter for monetary amount-column detection.

This module analyzes a CSV file structure and detects the column that contains
monetary amounts. It is intentionally conservative: it scores candidate columns
using both header names and the actual data patterns in the cells.

Example
-------
>>> from auto_adapter import detect_amount_column_from_csv
>>> detect_amount_column_from_csv("transactions.csv")
3
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union


__all__ = [
    "AutoAdapter",
    "detect_amount_column",
    "detect_amount_column_from_csv",
]

NumberLike = Union[str, int, float]


class AutoAdapter:
    """Compatibility wrapper for automatic financial-column detection.

    This class exposes the simple API expected by the project test harness while
    delegating the actual detection logic to the standalone functions below.
    """

    def detect_financial_column(self, csv_path: Union[str, Path], **kwargs) -> int:
        """Return the zero-based index of the financial amount column.

        Parameters
        ----------
        csv_path:
            Path to the CSV file.
        **kwargs:
            Optional overrides passed through to detect_amount_column_from_csv.
        """
        return detect_amount_column_from_csv(csv_path, **kwargs)

    def detect_amount_column(self, csv_path: Union[str, Path], **kwargs) -> int:
        """Alias kept for convenience and forward compatibility."""
        return self.detect_financial_column(csv_path, **kwargs)


def _normalize_label(value: object) -> str:
    """Normalize a column label for robust matching.

    The function removes accents, converts to lowercase, keeps alphanumerics and
    spaces, and collapses repeated separators. This makes labels such as
    "Amount (€)", "Betrag EUR", and "Iznos" match the same core concepts.
    """
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("&", " and ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_currency_symbols(value: str) -> str:
    """Remove common currency symbols and grouping separators from text."""
    cleaned = value.strip()
    cleaned = cleaned.replace("€", "").replace("$", "").replace("£", "")
    cleaned = cleaned.replace("¥", "").replace("₹", "")
    cleaned = cleaned.replace("¤", "")
    cleaned = cleaned.replace("\u00a0", " ")
    return cleaned.strip()


def _parse_monetary_value(value: object) -> float | None:
    """Return a float for a value that looks like a monetary amount.

    Supported examples include:
      - 1234.56
      - 1,234.56
      - 1.234,56
      - €1,234.56
      - -1234,56
      - 1234
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if isinstance(value, bool):
            return None
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    # Ignore plain dates, percentages, case labels, and identifiers.
    if re.fullmatch(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", text):
        return None
    if re.fullmatch(r"\d+%", text):
        return None
    if re.fullmatch(r"[A-Za-z]+", text):
        return None

    cleaned = _strip_currency_symbols(text)
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace("'", "")

    if cleaned.count(",") and cleaned.count("."):
        # Mixed decimal/group separators. Handle European style and US style.
        if cleaned.rfind(",") > cleaned.rfind("."):
            # e.g. 1.234,56 -> 1234.56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # e.g. 1,234.56 -> 1234.56
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if cleaned.count(",") == 1 and len(cleaned.split(",")[-1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    try:
        result = float(cleaned)
    except ValueError:
        return None

    if abs(result) > 1e12:
        return None
    return result


def _candidate_header_score(header: str) -> int:
    """Return a score based on a header label."""
    label = _normalize_label(header)
    if not label:
        return 0

    aliases = {
        "amount": ["amount", "amount eur", "amount usd", "amount in eur", "amount in usd", "total amount"],
        "betrag": ["betrag", "betrag eur", "betrag usd", "summe", "gesamtbetrag", "wert", "preis"],
        "iznos": ["iznos", "izno", "iznos eur", "iznos usd", "suma", "vrijednost", "novcani iznos"],
        "value": ["value", "amount value", "money", "cash", "monetary amount"],
    }

    for key, values in aliases.items():
        if label == key or label in values:
            return 80
        if any(part in label for part in values):
            return 70
        if key in label:
            return 60

    # Additional generic hints.
    if "amount" in label or "betrag" in label or "iznos" in label or "izno" in label:
        return 75
    if "total" in label or "sum" in label:
        return 35
    return 0


def _column_data_quality(values: Sequence[object], max_samples: int = 50) -> Tuple[float, int]:
    """Assess whether a column contains monetary values.

    Returns a tuple of (score, valid_count).
    """
    sample_values = []
    for value in values[:max_samples]:
        if value is None:
            continue
        sample_values.append(value)

    valid_count = 0
    for value in sample_values:
        if _parse_monetary_value(value) is not None:
            valid_count += 1

    total = len(sample_values)
    if total == 0:
        return 0.0, 0

    ratio = valid_count / total
    score = ratio * 100.0
    if valid_count >= 3:
        score += min(valid_count * 2.0, 20.0)
    return score, valid_count


def _read_csv_rows(path: Union[str, Path], encoding: str = "utf-8-sig") -> List[List[str]]:
    """Read a CSV file as rows with delimiter auto-detection."""
    csv_path = Path(path)
    with csv_path.open("r", encoding=encoding, newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            reader = csv.reader(handle, dialect)
        except csv.Error:
            reader = csv.reader(handle)
        rows = [row for row in reader if row]
    return rows


def detect_amount_column(rows: Iterable[Sequence[object]]) -> int:
    """Detect the column index containing monetary values in a CSV-like dataset.

    Parameters
    ----------
    rows:
        Iterable of rows. The first row is assumed to be a header.

    Returns
    -------
    int
        Zero-based index of the detected monetary amount column.

    Raises
    ------
    ValueError
        If no reliable amount column can be detected.
    """
    row_list = [list(row) for row in rows if row]
    if not row_list:
        raise ValueError("CSV content is empty.")

    header = row_list[0]
    data_rows = row_list[1:]
    if not header:
        raise ValueError("Header row is empty.")

    max_columns = max(len(r) for r in row_list)
    padded_header = header + ["" for _ in range(max_columns - len(header))]

    candidates: List[Tuple[int, float]] = []

    for index in range(max_columns):
        column_values = [row[index] if index < len(row) else "" for row in data_rows]
        header_name = padded_header[index] if index < len(padded_header) else ""
        header_score = _candidate_header_score(header_name)
        data_score, valid_count = _column_data_quality(column_values)

        total_score = header_score + data_score
        if header_score > 0 or valid_count >= 2:
            candidates.append((index, total_score))

    if not candidates:
        raise ValueError("Could not detect a monetary amount column in the CSV.")

    candidates.sort(key=lambda item: item[1], reverse=True)
    best_index, best_score = candidates[0]

    if best_score < 60:
        raise ValueError(
            f"No reliable monetary amount column detected. Highest score was {best_score:.2f}."
        )

    return best_index


def detect_amount_column_from_csv(
    csv_path: Union[str, Path],
    *,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
) -> int:
    """Open a CSV file and return the zero-based index of the amount column.

    Parameters
    ----------
    csv_path:
        Path to a CSV file.
    encoding:
        Text encoding used to read the file.
    delimiter:
        Optional CSV delimiter override. If omitted, the function auto-detects it.

    Returns
    -------
    int
        Zero-based column index of the detected amount column.
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    if delimiter is not None:
        with csv_file.open("r", encoding=encoding, newline="") as handle:
            rows = [row for row in csv.reader(handle, delimiter=delimiter) if row]
    else:
        rows = _read_csv_rows(csv_file, encoding=encoding)

    return detect_amount_column(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detect the monetary amount column in a CSV file.")
    parser.add_argument("csv_path", type=str, help="Path to the CSV file to inspect.")
    args = parser.parse_args()

    index = detect_amount_column_from_csv(args.csv_path)
    print(index)
