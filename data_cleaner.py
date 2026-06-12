import pandas as pd
import io
from typing import Dict, Optional


def clean_sales_csv(file_bytes: bytes, mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Load a CSV and normalize column names.

    mapping: optional dict mapping standard field names (e.g. 'sale_date') -> original header name
    This allows the frontend to let users map arbitrary CSV headers to the expected fields.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    # normalize dataframe column names to a comparable form
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # default renames for common header variants
    rename_map = {
        "date": "sale_date",
        "order_date": "sale_date",
        "sales": "revenue",
        "total": "revenue",
        "item": "product",
        "product_name": "product",
        "qty": "quantity",
        "units": "quantity",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # apply user-provided mapping (standard_field -> original_header_name)
    if mapping:
        normalized_mapping = {}
        for standard_field, header_name in mapping.items():
            if not header_name:
                continue
            norm_hdr = header_name.strip().lower().replace(" ", "_")
            normalized_mapping[norm_hdr] = standard_field
        if normalized_mapping:
            df.rename(columns=normalized_mapping, inplace=True)

    # required fields for downstream processing
    required = ["sale_date", "product", "revenue"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)} — please map them in the upload UI.")

    df.dropna(subset=["sale_date", "product", "revenue"], inplace=True)
    df.drop_duplicates(inplace=True)
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")
    df.dropna(subset=["sale_date"], inplace=True)
    df["sale_date"] = df["sale_date"].dt.date

    for col in ["revenue", "profit", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["quantity"] = df.get("quantity", pd.Series(dtype=float)).fillna(1).astype(int)
    df["profit"] = df.get("profit", pd.Series(dtype=float)).fillna(0.0)
    df["category"] = df.get("category", pd.Series(dtype=str)).fillna("Unknown")
    df["region"] = df.get("region", pd.Series(dtype=str)).fillna("Unknown")

    return df
