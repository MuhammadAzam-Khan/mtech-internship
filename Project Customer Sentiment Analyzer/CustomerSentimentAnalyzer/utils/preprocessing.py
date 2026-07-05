"""
preprocessing.py
-----------------
Complete NLP preprocessing pipeline used before sentiment prediction.

Steps applied (in order):
    1. HTML tag removal
    2. URL removal
    3. Emoji removal
    4. Lowercasing
    5. Punctuation / special character removal
    6. Number removal
    7. Tokenization
    8. Stopword removal
    9. Lemmatization

The pipeline degrades gracefully: if NLTK corpora are not available locally,
it attempts to download them once, and falls back to a lightweight built-in
stopword list / simple whitespace tokenizer if downloading is not possible
(e.g. no internet access).
"""

import re
import string
from typing import List

from utils.logger import get_logger

logger = get_logger("Preprocessing")

# ---------------------------------------------------------------------------
# Optional NLTK setup (with graceful fallback)
# ---------------------------------------------------------------------------
_NLTK_READY = False
try:
    import nltk
    from nltk.corpus import stopwords as nltk_stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize

    def _ensure_nltk_data():
        packages = {
            "tokenizers/punkt": "punkt",
            "tokenizers/punkt_tab": "punkt_tab",
            "corpora/stopwords": "stopwords",
            "corpora/wordnet": "wordnet",
            "corpora/omw-1.4": "omw-1.4",
        }
        for path, pkg in packages.items():
            try:
                nltk.data.find(path)
            except LookupError:
                try:
                    nltk.download(pkg, quiet=True)
                except Exception as exc:  # pragma: no cover - network dependent
                    logger.warning(f"Could not download NLTK package '{pkg}': {exc}")

    _ensure_nltk_data()
    _lemmatizer = WordNetLemmatizer()
    _STOPWORDS = set(nltk_stopwords.words("english"))
    _NLTK_READY = True
except Exception as exc:  # pragma: no cover
    logger.warning(f"NLTK unavailable, falling back to built-in tools: {exc}")
    _NLTK_READY = False

# Lightweight fallback stopword list (used only if NLTK data is unavailable).
_FALLBACK_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "you", "your", "yours", "yourself",
    "yourselves",
}

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)

HTML_TAG_PATTERN = re.compile(r"<.*?>")
URL_PATTERN = re.compile(r"http\S+|www\.\S+")
NUMBER_PATTERN = re.compile(r"\d+")


def remove_html(text: str) -> str:
    return HTML_TAG_PATTERN.sub(" ", text)


def remove_urls(text: str) -> str:
    return URL_PATTERN.sub(" ", text)


def remove_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub(" ", text)


def remove_numbers(text: str) -> str:
    return NUMBER_PATTERN.sub(" ", text)


def remove_punctuation(text: str) -> str:
    return text.translate(str.maketrans("", "", string.punctuation))


def tokenize(text: str) -> List[str]:
    if _NLTK_READY:
        try:
            return word_tokenize(text)
        except Exception:
            pass
    return text.split()


def remove_stopwords(tokens: List[str]) -> List[str]:
    stop_set = _STOPWORDS if _NLTK_READY else _FALLBACK_STOPWORDS
    return [t for t in tokens if t not in stop_set]


def lemmatize(tokens: List[str]) -> List[str]:
    if _NLTK_READY:
        try:
            return [_lemmatizer.lemmatize(t) for t in tokens]
        except Exception:
            pass
    return tokens


def clean_text(text: str, keep_stopwords: bool = False) -> str:
    """
    Run the full preprocessing pipeline on a single piece of text and
    return a cleaned string (space-joined tokens).

    Args:
        text: Raw input text (comment, tweet, review, etc.).
        keep_stopwords: If True, stopwords are preserved. Sentiment tools
            like VADER/TextBlob perform better with stopwords kept, while
            the ML/keyword-extraction pipeline benefits from removing them.

    Returns:
        Cleaned text string.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    text = remove_html(text)
    text = remove_urls(text)
    text = remove_emojis(text)
    text = text.lower()
    text = remove_numbers(text)
    text = remove_punctuation(text)

    tokens = tokenize(text)
    if not keep_stopwords:
        tokens = remove_stopwords(tokens)
    tokens = lemmatize(tokens)
    tokens = [t.strip() for t in tokens if t.strip()]

    return " ".join(tokens)


def clean_for_sentiment(text: str) -> str:
    """Lighter cleaning pass (keeps stopwords/negations) tailored for
    rule-based sentiment engines such as VADER and TextBlob, which rely on
    contextual words like 'not', 'very', 'but' to gauge polarity."""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = remove_html(text)
    text = remove_urls(text)
    text = remove_emojis(text)
    return text.strip()
