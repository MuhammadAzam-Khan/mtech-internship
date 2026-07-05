"""
charts.py
----------
Matplotlib chart widgets embedded directly into the PySide6 dashboard via
FigureCanvasQTAgg (generic Qt backend, works with PySide6). Includes pie,
bar, line/trend, histogram, and word cloud rendering helpers.
"""

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd

try:
    from wordcloud import WordCloud
    _WORDCLOUD_AVAILABLE = True
except Exception:
    _WORDCLOUD_AVAILABLE = False

SENTIMENT_COLORS = {"positive": "#2ecc71", "negative": "#e74c3c", "neutral": "#95a5a6"}


class BaseChartCanvas(FigureCanvas):
    """Common base class for all chart widgets, handles theme-aware styling."""

    def __init__(self, width=5, height=4, dpi=100, dark_mode=False):
        self.dark_mode = dark_mode
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self._apply_theme()

    def _apply_theme(self):
        bg = "#1e1e2f" if self.dark_mode else "#ffffff"
        fg = "#e0e0e0" if self.dark_mode else "#2c3e50"
        self.fig.patch.set_facecolor(bg)
        self._bg = bg
        self._fg = fg

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark
        self._apply_theme()


class PieChartCanvas(BaseChartCanvas):
    def plot(self, stats: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)
        labels = ["Positive", "Negative", "Neutral"]
        values = [stats.get("positive", 0), stats.get("negative", 0), stats.get("neutral", 0)]
        colors = [SENTIMENT_COLORS["positive"], SENTIMENT_COLORS["negative"], SENTIMENT_COLORS["neutral"]]
        if sum(values) == 0:
            values = [1, 1, 1]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%", colors=colors, startangle=90,
            textprops={"color": self._fg, "fontsize": 9}
        )
        ax.set_title("Sentiment Distribution", color=self._fg, fontsize=11, fontweight="bold")
        self.draw()


class BarChartCanvas(BaseChartCanvas):
    def plot(self, stats: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)
        labels = ["Positive", "Negative", "Neutral"]
        values = [stats.get("positive", 0), stats.get("negative", 0), stats.get("neutral", 0)]
        colors = [SENTIMENT_COLORS["positive"], SENTIMENT_COLORS["negative"], SENTIMENT_COLORS["neutral"]]
        ax.bar(labels, values, color=colors)
        ax.set_title("Sentiment Counts", color=self._fg, fontsize=11, fontweight="bold")
        ax.tick_params(colors=self._fg)
        for spine in ax.spines.values():
            spine.set_color(self._fg)
        self.fig.tight_layout()
        self.draw()


class LineTrendCanvas(BaseChartCanvas):
    def plot(self, df: pd.DataFrame):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)

        if "date" in df.columns and not df.empty:
            try:
                temp = df.copy()
                temp["date_parsed"] = pd.to_datetime(temp["date"], errors="coerce")
                temp = temp.dropna(subset=["date_parsed"])
                temp["day"] = temp["date_parsed"].dt.date
                pivot = temp.groupby(["day", "sentiment"]).size().unstack(fill_value=0)
                for sentiment in ["positive", "negative", "neutral"]:
                    if sentiment in pivot.columns:
                        ax.plot(pivot.index, pivot[sentiment], marker="o", label=sentiment.capitalize(),
                                color=SENTIMENT_COLORS[sentiment])
                ax.legend(facecolor=self._bg, labelcolor=self._fg, fontsize=8)
                ax.tick_params(axis="x", rotation=30, colors=self._fg)
                ax.tick_params(axis="y", colors=self._fg)
            except Exception:
                ax.text(0.5, 0.5, "Not enough date data for trend", ha="center", color=self._fg)
        else:
            ax.text(0.5, 0.5, "No date data available", ha="center", color=self._fg)

        ax.set_title("Sentiment Trend Over Time", color=self._fg, fontsize=11, fontweight="bold")
        for spine in ax.spines.values():
            spine.set_color(self._fg)
        self.fig.tight_layout()
        self.draw()


class HistogramCanvas(BaseChartCanvas):
    def plot(self, df: pd.DataFrame):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)
        if "score" in df.columns and not df.empty:
            ax.hist(df["score"], bins=20, color="#3498db", edgecolor=self._bg)
        ax.set_title("Sentiment Score Distribution", color=self._fg, fontsize=11, fontweight="bold")
        ax.set_xlabel("Score (-1 to 1)", color=self._fg)
        ax.set_ylabel("Frequency", color=self._fg)
        ax.tick_params(colors=self._fg)
        for spine in ax.spines.values():
            spine.set_color(self._fg)
        self.fig.tight_layout()
        self.draw()


class SourceBarCanvas(BaseChartCanvas):
    def plot(self, df: pd.DataFrame):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)
        if "source" in df.columns and not df.empty:
            counts = df["source"].value_counts()
            ax.bar(counts.index, counts.values, color="#9b59b6")
            ax.tick_params(axis="x", rotation=30, colors=self._fg)
        ax.set_title("Mentions by Source", color=self._fg, fontsize=11, fontweight="bold")
        ax.tick_params(axis="y", colors=self._fg)
        for spine in ax.spines.values():
            spine.set_color(self._fg)
        self.fig.tight_layout()
        self.draw()


class WordCloudCanvas(BaseChartCanvas):
    def plot(self, text: str, colormap: str = "viridis", title: str = "Word Cloud"):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self._bg)
        ax.axis("off")
        if _WORDCLOUD_AVAILABLE and text.strip():
            try:
                wc = WordCloud(width=800, height=400, background_color=self._bg,
                                colormap=colormap, max_words=100).generate(text)
                ax.imshow(wc, interpolation="bilinear")
            except Exception:
                ax.text(0.5, 0.5, "Unable to generate word cloud", ha="center", color=self._fg)
        else:
            ax.text(0.5, 0.5, "No data available", ha="center", color=self._fg)
        ax.set_title(title, color=self._fg, fontsize=11, fontweight="bold")
        self.fig.tight_layout()
        self.draw()
