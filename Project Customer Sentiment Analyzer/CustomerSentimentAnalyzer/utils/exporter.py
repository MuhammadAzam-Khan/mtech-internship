"""
exporter.py
------------
Handles exporting analyzed results to CSV, Excel, and JSON formats.
PDF report export is handled separately in `utils/report_generator.py`
since it involves charts and layout rather than tabular dumping.
"""

import json
import os

import pandas as pd

from utils.logger import log_event


class ExportError(Exception):
    pass


def export_csv(df: pd.DataFrame, path: str) -> str:
    try:
        df.to_csv(path, index=False, encoding="utf-8")
    except Exception as exc:
        raise ExportError(f"Failed to export CSV: {exc}")
    log_event("EXPORT", f"Exported {len(df)} rows to CSV: {os.path.basename(path)}")
    return path


def export_excel(df: pd.DataFrame, path: str) -> str:
    try:
        df.to_excel(path, index=False, engine="openpyxl")
    except Exception as exc:
        raise ExportError(f"Failed to export Excel file: {exc}")
    log_event("EXPORT", f"Exported {len(df)} rows to Excel: {os.path.basename(path)}")
    return path


def export_json(df: pd.DataFrame, path: str) -> str:
    try:
        records = df.to_dict(orient="records")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False, default=str)
    except Exception as exc:
        raise ExportError(f"Failed to export JSON: {exc}")
    log_event("EXPORT", f"Exported {len(df)} rows to JSON: {os.path.basename(path)}")
    return path


def export_dataframe(df: pd.DataFrame, path: str) -> str:
    """Dispatch export based on file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return export_csv(df, path)
    elif ext == ".xlsx":
        return export_excel(df, path)
    elif ext == ".json":
        return export_json(df, path)
    else:
        raise ExportError(f"Unsupported export format: {ext}")
