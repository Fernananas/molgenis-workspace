from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data/input" / "EBpatients.xlsx"
OUTPUT_DIR = BASE_DIR / "data/output"
DATATYPE_OUT = OUTPUT_DIR / "datatype.csv"
CATEGORICAL_OUT = OUTPUT_DIR / "categorical_values.csv"


BOOL_TRUE = {"waar", "true", "1", "yes", "ja"}
BOOL_FALSE = {"onwaar", "false", "0", "no", "nee"}


def normalize_value(value: object) -> str:
    """Convert a raw cell to a normalized string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def split_terms(cell_text: str) -> List[str]:
    """Split comma-separated terms and trim whitespace."""
    return [part.strip() for part in cell_text.split(",") if part.strip()]


def is_bool_column(values: List[str]) -> bool:
    if not values:
        return False
    lowered = {v.lower() for v in values}
    return lowered.issubset(BOOL_TRUE | BOOL_FALSE)


def is_date_column(series: pd.Series, values: List[str]) -> bool:
    if not values:
        return False

    # Try parsing all non-empty values as dates (day-first for Dutch style dates).
    parsed = pd.to_datetime(series.replace("", pd.NA), errors="coerce", dayfirst=True)
    non_empty_count = sum(1 for v in values if v != "")
    parsed_count = parsed.notna().sum()
    return parsed_count == non_empty_count and non_empty_count > 0


def detect_categorical(values: List[str]) -> Tuple[str | None, List[str]]:
    """
    Detect categorical type:
    - ref: all values are single-term (no comma splitting needed)
    - ref_array: at least one row has multiple comma-separated terms
    Returns datatype and sorted unique terms.
    """
    if not values:
        return None, []

    contains_comma = any("," in v for v in values)
    all_terms: Set[str] = set()

    for v in values:
        terms = split_terms(v)
        if not terms:
            continue
        for term in terms:
            all_terms.add(term)

    if not all_terms:
        return None, []

    datatype = "ref_array" if contains_comma else "ref"
    return datatype, sorted(all_terms)


def infer_column_type(series: pd.Series) -> Tuple[str, List[str]]:
    """
    Inference order:
    1) text if any value length > 255
    2) bool if values are only bool terms
    3) date if all non-empty parse as dates
    4) ref/ref_array for categorical terms
    5) string default
    """
    normalized = [normalize_value(v) for v in series.tolist()]
    non_empty = [v for v in normalized if v != ""]

    if not non_empty:
        return "string", []

    if any(len(v) > 255 for v in non_empty):
        return "text", []

    if is_bool_column(non_empty):
        return "bool", []

    # Build a temporary series from normalized values for consistent date parsing.
    normalized_series = pd.Series(non_empty)
    if is_date_column(normalized_series, non_empty):
        return "date", []

    categorical_type, unique_terms = detect_categorical(non_empty)
    if categorical_type is not None:
        return categorical_type, unique_terms

    return "string", []


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(INPUT_FILE, dtype=str)

    datatype_rows: List[Dict[str, str]] = []
    categorical_rows: List[Dict[str, str]] = []

    for col in df.columns:
        dtype, unique_terms = infer_column_type(df[col])

        datatype_rows.append(
            {
                "column_name": str(col),
                "datatype": dtype,
            }
        )

        if dtype in {"ref", "ref_array"}:
            for term in unique_terms:
                categorical_rows.append(
                    {
                        "column_name": str(col),
                        "value": term,
                    }
                )

    pd.DataFrame(datatype_rows).to_csv(DATATYPE_OUT, index=False)
    pd.DataFrame(categorical_rows).to_csv(CATEGORICAL_OUT, index=False)

    print(f"Saved datatype overview: {DATATYPE_OUT}")
    print(f"Saved categorical values: {CATEGORICAL_OUT}")


if __name__ == "__main__":
    main()