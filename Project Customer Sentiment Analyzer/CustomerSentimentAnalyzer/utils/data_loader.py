"""
data_loader.py
---------------
Handles all data ingestion for the Customer Sentiment Analyzer:

- CSV / Excel / JSON file import
- Manual / live text entry
- Simulated social media monitoring (Twitter/X, Facebook, Instagram,
  Reddit, YouTube) — architected so a real API client could be dropped
  in later without changing the calling code.
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import List

import pandas as pd

from utils.logger import get_logger, log_event

logger = get_logger("DataLoader")

REQUIRED_COLUMN_CANDIDATES = ["comment", "text", "review", "message", "content"]


class DataLoadError(Exception):
    """Raised when an input file cannot be parsed into usable comment data."""


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the resulting DataFrame has the standard columns used
    throughout the application: id, comment, source, date."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    comment_col = None
    for candidate in REQUIRED_COLUMN_CANDIDATES:
        if candidate in df.columns:
            comment_col = candidate
            break
    if comment_col is None:
        # Fall back to the first column if nothing matches.
        if len(df.columns) == 0:
            raise DataLoadError("The file does not contain any columns.")
        comment_col = df.columns[0]
        logger.warning(f"No standard comment column found, using '{comment_col}' instead.")

    if comment_col != "comment":
        df = df.rename(columns={comment_col: "comment"})

    if "source" not in df.columns:
        df["source"] = "Imported File"
    if "date" not in df.columns:
        df["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "id" not in df.columns:
        df.insert(0, "id", range(1, len(df) + 1))

    df["comment"] = df["comment"].astype(str)
    df = df[df["comment"].str.strip() != ""]
    df = df[df["comment"].str.lower() != "nan"]
    df = df.reset_index(drop=True)
    df["id"] = range(1, len(df) + 1)

    return df[["id", "comment", "source", "date"]]


def load_csv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")
    except Exception as exc:
        raise DataLoadError(f"Failed to read CSV file: {exc}")
    result = _normalize_dataframe(df)
    log_event("IMPORT", f"Loaded {len(result)} rows from CSV file: {os.path.basename(path)}")
    return result


def load_excel(path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path)
    except Exception as exc:
        raise DataLoadError(f"Failed to read Excel file: {exc}")
    result = _normalize_dataframe(df)
    log_event("IMPORT", f"Loaded {len(result)} rows from Excel file: {os.path.basename(path)}")
    return result


def load_json(path: str) -> pd.DataFrame:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # Try common wrapper keys, otherwise treat dict as a single record.
            for key in ("comments", "data", "records", "items"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]
        df = pd.DataFrame(data)
    except Exception as exc:
        raise DataLoadError(f"Failed to read JSON file: {exc}")
    result = _normalize_dataframe(df)
    log_event("IMPORT", f"Loaded {len(result)} rows from JSON file: {os.path.basename(path)}")
    return result


def load_file(path: str) -> pd.DataFrame:
    """Dispatch to the correct loader based on file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return load_csv(path)
    elif ext in (".xlsx", ".xls"):
        return load_excel(path)
    elif ext == ".json":
        return load_json(path)
    else:
        raise DataLoadError(f"Unsupported file format: {ext}")


def load_manual_entries(text_block: str, source: str = "Manual Entry") -> pd.DataFrame:
    """Convert a block of manually typed text (one comment per line) into
    a standard comments DataFrame."""
    lines = [line.strip() for line in text_block.splitlines() if line.strip()]
    if not lines:
        raise DataLoadError("No text was entered.")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    df = pd.DataFrame({
        "id": range(1, len(lines) + 1),
        "comment": lines,
        "source": [source] * len(lines),
        "date": [now] * len(lines),
    })
    log_event("IMPORT", f"Loaded {len(df)} manually entered comment(s).")
    return df


# ---------------------------------------------------------------------------
# Simulated social media monitoring
# ---------------------------------------------------------------------------

_SOCIAL_TEMPLATES = {
    "Twitter/X": [
        "Just tried {brand} and honestly it's {opinion}. #customerexperience",
        "@{brand}support your product is {opinion}, {detail}",
        "Can we talk about how {opinion} {brand}'s new update is? {detail}",
        "{brand} delivery took forever this time, {detail}",
    ],
    "Facebook": [
        "I posted a review for {brand} — overall it was {opinion}. {detail}",
        "Anyone else think {brand}'s customer service is {opinion}? {detail}",
        "Sharing my experience with {brand}: {opinion}, {detail}",
    ],
    "Instagram": [
        "Unboxing my {brand} order today, it's {opinion}! {detail}",
        "New {brand} haul, honestly {opinion}. {detail}",
        "Story update: {brand} purchase was {opinion}. {detail}",
    ],
    "Reddit": [
        "[Review] {brand} — my honest take: {opinion}. {detail}",
        "Has anyone had a {opinion} experience with {brand}? {detail}",
        "PSA: {brand}'s support team was {opinion} when I reached out. {detail}",
    ],
    "YouTube": [
        "Great video, but my own experience with {brand} was {opinion}. {detail}",
        "Comment: {brand} product review — {opinion}, {detail}",
        "Subscribed! Also tried {brand} myself, {opinion}. {detail}",
    ],
}

_OPINIONS_POS = ["fantastic", "amazing", "really impressive", "excellent", "great"]
_OPINIONS_NEG = ["disappointing", "frustrating", "pretty bad", "terrible", "not good"]
_OPINIONS_NEU = ["okay", "average", "fine", "decent", "as expected"]

_DETAILS_POS = [
    "highly recommend it to everyone.",
    "will definitely be a repeat customer.",
    "exceeded my expectations honestly.",
    "the support team was super quick too.",
]
_DETAILS_NEG = [
    "still waiting on a refund.",
    "won't be buying again.",
    "customer support has ignored my messages.",
    "arrived damaged and no one helped.",
]
_DETAILS_NEU = [
    "might try it again to see if it improves.",
    "nothing to complain about but nothing amazing either.",
    "works fine for now.",
    "will update this if anything changes.",
]

_BRANDS = ["the brand", "this company", "the store", "the shop", "them"]


def generate_social_mentions(count: int = 25, brand_name: str = "the brand") -> pd.DataFrame:
    """
    Generate simulated social media mentions across multiple platforms.

    This function stands in for a real social listening API integration.
    The architecture (returning the same standardized DataFrame shape as
    load_file) means a future developer could swap this out for a live
    Twitter/Reddit/etc. API client with no changes required elsewhere in
    the application.
    """
    rows = []
    now = datetime.now()
    platforms = list(_SOCIAL_TEMPLATES.keys())

    for i in range(count):
        platform = random.choice(platforms)
        template = random.choice(_SOCIAL_TEMPLATES[platform])
        bucket = random.choice(["pos", "neg", "neu"])
        if bucket == "pos":
            opinion = random.choice(_OPINIONS_POS)
            detail = random.choice(_DETAILS_POS)
        elif bucket == "neg":
            opinion = random.choice(_OPINIONS_NEG)
            detail = random.choice(_DETAILS_NEG)
        else:
            opinion = random.choice(_OPINIONS_NEU)
            detail = random.choice(_DETAILS_NEU)

        text = template.format(brand=brand_name, opinion=opinion, detail=detail)
        timestamp = now - timedelta(minutes=random.randint(0, 60 * 24 * 3))
        rows.append({
            "id": i + 1,
            "comment": text,
            "source": platform,
            "date": timestamp.strftime("%Y-%m-%d %H:%M"),
        })

    df = pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)
    df["id"] = range(1, len(df) + 1)
    log_event("IMPORT", f"Simulated {len(df)} social media mentions.")
    return df
