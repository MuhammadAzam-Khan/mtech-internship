"""
analytics.py
-------------
Orchestrates the rule-based and ML sentiment engines over a DataFrame of
comments and computes all dashboard statistics: counts, averages,
top keywords, most active source, etc.
"""

from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd

from models.sentiment_model import RuleBasedSentimentEngine
from models.ml_model import MLSentimentEngine
from utils.preprocessing import clean_text
from utils.logger import log_event

_STOP_EXTRA = {"im", "ive", "dont", "didnt", "wasnt", "isnt", "get", "got", "would", "could"}


def analyze_dataframe(
    df: pd.DataFrame,
    ml_algorithm: str = "Naive Bayes",
    progress_callback=None,
) -> pd.DataFrame:
    """
    Run both the rule-based and ML sentiment engines over every comment in
    `df` and return an enriched copy with new columns:

        sentiment, confidence, score,
        ml_sentiment, ml_confidence, model_agreement

    Args:
        df: DataFrame containing at least a 'comment' column.
        ml_algorithm: Which ML algorithm to use for comparison.
        progress_callback: Optional callable(percent:int) invoked periodically
            to report progress (used by the QThread worker to update the UI).
    """
    rule_engine = RuleBasedSentimentEngine()
    ml_engine = MLSentimentEngine(ml_algorithm)
    ml_engine.train()  # loads from cache if available

    result_rows = []
    total = len(df)
    for i, row in enumerate(df.itertuples(index=False)):
        comment = getattr(row, "comment", "")
        rule_result = rule_engine.analyze(comment)
        ml_result = ml_engine.predict(comment)

        result_rows.append({
            "sentiment": rule_result.label,
            "confidence": rule_result.confidence,
            "score": rule_result.score,
            "ml_sentiment": ml_result.label,
            "ml_confidence": ml_result.confidence,
            "model_agreement": rule_result.label == ml_result.label,
        })

        if progress_callback and total > 0 and (i % max(1, total // 100) == 0 or i == total - 1):
            progress_callback(int((i + 1) / total * 100))

    enriched = pd.concat([df.reset_index(drop=True), pd.DataFrame(result_rows)], axis=1)
    log_event("PREDICTION", f"Completed full analysis of {total} comment(s) "
                             f"using rule-based engine + {ml_algorithm}.")
    return enriched


def compute_stats(df: pd.DataFrame) -> Dict:
    """Compute summary statistics used across the dashboard."""
    total = len(df)
    if total == 0:
        return {
            "total": 0, "positive": 0, "negative": 0, "neutral": 0,
            "avg_score": 0.0, "avg_confidence": 0.0, "top_source": "N/A",
            "ml_accuracy_vs_rule": 0.0,
        }

    counts = df["sentiment"].value_counts()
    positive = int(counts.get("positive", 0))
    negative = int(counts.get("negative", 0))
    neutral = int(counts.get("neutral", 0))

    avg_score = float(df["score"].mean()) if "score" in df.columns else 0.0
    avg_confidence = float(df["confidence"].mean()) if "confidence" in df.columns else 0.0

    top_source = "N/A"
    if "source" in df.columns and not df["source"].empty:
        top_source = df["source"].value_counts().idxmax()

    agreement_pct = 0.0
    if "model_agreement" in df.columns and total > 0:
        agreement_pct = float(df["model_agreement"].mean() * 100)

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "avg_score": round(avg_score, 3),
        "avg_confidence": round(avg_confidence, 1),
        "top_source": str(top_source),
        "ml_accuracy_vs_rule": round(agreement_pct, 1),
    }


def extract_top_keywords(df: pd.DataFrame, sentiment: str = None, top_n: int = 10) -> List[Tuple[str, int]]:
    """Return the most frequent meaningful words for a given sentiment
    subset (or the whole dataset if sentiment is None)."""
    subset = df if sentiment is None else df[df["sentiment"] == sentiment]
    if subset.empty:
        return []

    words = []
    for comment in subset["comment"]:
        cleaned = clean_text(comment, keep_stopwords=False)
        for w in cleaned.split():
            if len(w) > 2 and w not in _STOP_EXTRA:
                words.append(w)

    counter = Counter(words)
    return counter.most_common(top_n)


def build_wordcloud_text(df: pd.DataFrame, sentiment: str) -> str:
    subset = df[df["sentiment"] == sentiment]
    cleaned_comments = [clean_text(c, keep_stopwords=False) for c in subset["comment"]]
    return " ".join([c for c in cleaned_comments if c])


def generate_recommendations(stats: Dict, top_negative_keywords: List[Tuple[str, int]]) -> List[str]:
    """Produce simple rule-based recommendations from the aggregate stats."""
    recs = []
    total = stats.get("total", 0)
    if total == 0:
        return ["No data available yet — import or generate comments to see recommendations."]

    negative_ratio = stats.get("negative", 0) / total
    positive_ratio = stats.get("positive", 0) / total

    if negative_ratio > 0.4:
        recs.append("A significant portion of feedback is negative. Prioritize a root-cause "
                     "review of recurring complaints before the next release or campaign.")
    if negative_ratio > 0.15 and top_negative_keywords:
        top_terms = ", ".join([w for w, _ in top_negative_keywords[:5]])
        recs.append(f"Frequent negative terms include: {top_terms}. Consider addressing these "
                     f"specific pain points directly in your response strategy.")
    if positive_ratio > 0.6:
        recs.append("Overall sentiment is strongly positive. Consider highlighting positive "
                     "testimonials in marketing materials.")
    if stats.get("avg_confidence", 0) < 60:
        recs.append("Average model confidence is relatively low, suggesting many comments are "
                     "ambiguous or mixed in tone. Manual review of borderline cases is advised.")
    if stats.get("ml_accuracy_vs_rule", 100) < 70:
        recs.append("The rule-based and ML models disagree on a notable share of comments. "
                     "Consider retraining the ML model with more labeled examples from this domain.")
    if not recs:
        recs.append("Sentiment appears balanced and stable. Continue routine monitoring.")

    return recs
