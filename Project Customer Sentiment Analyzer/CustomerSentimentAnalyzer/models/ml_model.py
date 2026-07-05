"""
ml_model.py
------------
Machine-learning-based sentiment classifier, used to compare against the
rule-based (VADER + TextBlob) engine.

Pipeline: TF-IDF vectorization -> Multinomial Naive Bayes / Logistic
Regression / SVM / Random Forest (selectable). The model is trained on
`data/training_dataset.csv` the first time it is needed and cached to
`models/trained_model.joblib` for fast reloading on subsequent runs.
"""

import os
from dataclasses import dataclass
from typing import List

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from utils.preprocessing import clean_text
from utils.logger import get_logger, log_event

logger = get_logger("MLModel")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINING_DATA_PATH = os.path.join(BASE_DIR, "data", "training_dataset.csv")
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "models", "cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

ALGORITHMS = {
    "Naive Bayes": lambda: MultinomialNB(),
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=200, random_state=42),
    "SVM": lambda: CalibratedClassifierCV(LinearSVC(), cv=3),
}


@dataclass
class MLResult:
    text: str
    label: str
    confidence: float


class MLSentimentEngine:
    """
    Trains (or loads a cached) ML classifier for 3-class sentiment
    prediction (positive / negative / neutral).
    """

    def __init__(self, algorithm: str = "Naive Bayes"):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from {list(ALGORITHMS)}")
        self.algorithm = algorithm
        self.pipeline: Pipeline = None
        self.accuracy: float = None
        self._cache_path = os.path.join(MODEL_CACHE_DIR, f"{algorithm.replace(' ', '_').lower()}.joblib")

    def _build_pipeline(self) -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000)),
            ("clf", ALGORITHMS[self.algorithm]()),
        ])

    def train(self, force: bool = False) -> float:
        """Train the model on the bundled training dataset, or load a
        cached version if available and `force` is False."""
        if not force and os.path.exists(self._cache_path):
            try:
                cached = joblib.load(self._cache_path)
                self.pipeline = cached["pipeline"]
                self.accuracy = cached["accuracy"]
                logger.info(f"Loaded cached '{self.algorithm}' model (accuracy={self.accuracy:.2f}).")
                return self.accuracy
            except Exception as exc:
                logger.warning(f"Failed to load cached model, retraining: {exc}")

        if not os.path.exists(TRAINING_DATA_PATH):
            raise FileNotFoundError(f"Training dataset not found at {TRAINING_DATA_PATH}")

        df = pd.read_csv(TRAINING_DATA_PATH)
        df["clean"] = df["comment"].apply(lambda t: clean_text(t, keep_stopwords=False))
        df = df[df["clean"].str.strip() != ""]

        X_train, X_test, y_train, y_test = train_test_split(
            df["clean"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
        )

        pipeline = self._build_pipeline()
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, preds)

        self.pipeline = pipeline
        self.accuracy = accuracy

        try:
            joblib.dump({"pipeline": pipeline, "accuracy": accuracy}, self._cache_path)
        except Exception as exc:
            logger.warning(f"Could not cache trained model: {exc}")

        log_event("SYSTEM", f"Trained '{self.algorithm}' ML model. Test accuracy: {accuracy:.2%}")
        return accuracy

    def predict(self, text: str) -> MLResult:
        if self.pipeline is None:
            self.train()
        cleaned = clean_text(text, keep_stopwords=False)
        if not cleaned:
            return MLResult(text=text, label="neutral", confidence=0.0)

        label = self.pipeline.predict([cleaned])[0]
        try:
            proba = self.pipeline.predict_proba([cleaned])[0]
            confidence = round(max(proba) * 100, 1)
        except Exception:
            confidence = 75.0  # fallback when predict_proba is unavailable

        return MLResult(text=text, label=label, confidence=confidence)

    def predict_batch(self, texts: List[str]) -> List[MLResult]:
        if self.pipeline is None:
            self.train()
        results = [self.predict(t) for t in texts]
        log_event("PREDICTION", f"ML engine ({self.algorithm}) analyzed {len(results)} comment(s).")
        return results
