"""
sentiment_model.py
--------------------
Rule-based sentiment analysis engine combining VADER and TextBlob.

VADER is tuned for social-media-style text (handles emphasis, negation,
and punctuation well), while TextBlob provides a complementary polarity/
subjectivity score. The engine blends both scores to produce a final
label, a normalized sentiment score in [-1, 1], and a confidence
percentage.
"""

from dataclasses import dataclass
from typing import List

from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.preprocessing import clean_for_sentiment
from utils.logger import get_logger, log_event

logger = get_logger("SentimentModel")


@dataclass
class SentimentResult:
    text: str
    label: str          # "positive" | "negative" | "neutral"
    score: float         # blended compound score in [-1, 1]
    confidence: float    # 0-100 %
    vader_compound: float
    textblob_polarity: float
    textblob_subjectivity: float


class RuleBasedSentimentEngine:
    """Wraps VADER + TextBlob into a single, easy-to-call sentiment engine."""

    POSITIVE_THRESHOLD = 0.05
    NEGATIVE_THRESHOLD = -0.05

    def __init__(self):
        self._vader = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> SentimentResult:
        """Analyze a single piece of text and return a SentimentResult."""
        if not isinstance(text, str) or not text.strip():
            return SentimentResult(text=text, label="neutral", score=0.0, confidence=0.0,
                                    vader_compound=0.0, textblob_polarity=0.0,
                                    textblob_subjectivity=0.0)

        cleaned = clean_for_sentiment(text)

        try:
            vader_scores = self._vader.polarity_scores(cleaned)
            vader_compound = vader_scores["compound"]
        except Exception as exc:
            logger.error(f"VADER failed on text: {exc}")
            vader_compound = 0.0

        try:
            blob = TextBlob(cleaned)
            tb_polarity = blob.sentiment.polarity
            tb_subjectivity = blob.sentiment.subjectivity
        except Exception as exc:
            logger.error(f"TextBlob failed on text: {exc}")
            tb_polarity = 0.0
            tb_subjectivity = 0.0

        # Blend: VADER is weighted slightly higher since it is tuned for
        # informal/social text which matches the target domain.
        blended_score = round((0.6 * vader_compound) + (0.4 * tb_polarity), 4)

        if blended_score >= self.POSITIVE_THRESHOLD:
            label = "positive"
        elif blended_score <= self.NEGATIVE_THRESHOLD:
            label = "negative"
        else:
            label = "neutral"

        confidence = round(min(abs(blended_score) * 100 + 40, 99.0), 1)
        if label == "neutral":
            confidence = round(100 - (abs(blended_score) * 100 + 10), 1)
            confidence = max(confidence, 50.0)

        return SentimentResult(
            text=text,
            label=label,
            score=blended_score,
            confidence=confidence,
            vader_compound=round(vader_compound, 4),
            textblob_polarity=round(tb_polarity, 4),
            textblob_subjectivity=round(tb_subjectivity, 4),
        )

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        results = [self.analyze(t) for t in texts]
        log_event("PREDICTION", f"Rule-based engine analyzed {len(results)} comment(s).")
        return results
