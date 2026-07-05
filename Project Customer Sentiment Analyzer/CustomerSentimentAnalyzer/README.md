# Customer Sentiment Analyzer

An advanced desktop application (PySide6) that monitors customer comments,
reviews, and simulated social media mentions, and automatically classifies
them as **Positive**, **Negative**, or **Neutral** using a combination of
rule-based NLP (VADER + TextBlob) and a trained machine learning classifier
(TF-IDF + Naive Bayes / Logistic Regression / Random Forest / SVM).

Built for the M-Tech AI/ML Internship Program 2026 — Project `Mtech-AI26046`.

---

## Features

- **Modern PySide6 dashboard** — sidebar navigation, top toolbar, status bar,
  KPI cards, light/dark theme toggle.
- **Multiple data import methods** — CSV, Excel, JSON, manual text entry,
  and drag-and-drop file import.
- **Simulated social media monitoring** — mock mentions from Twitter/X,
  Facebook, Instagram, Reddit, and YouTube (architected so a real API
  integration can be dropped in later, see `utils/data_loader.py`).
- **Complete NLP preprocessing pipeline** — HTML/URL/emoji stripping,
  lowercasing, punctuation & number removal, tokenization, stopword
  removal, and lemmatization (NLTK), with graceful offline fallback.
- **Dual sentiment engine** — VADER + TextBlob (rule-based) compared
  side-by-side against a trainable ML classifier (Naive Bayes, Logistic
  Regression, Random Forest, or SVM) on TF-IDF features.
- **Dashboard analytics** — total/positive/negative/neutral counts,
  average sentiment score & confidence, most active source, model
  agreement rate, and an auto-generated text summary with recommendations.
- **Charts** — pie, bar, line/trend, histogram, and per-source bar charts,
  all embedded live in the app (Matplotlib + Qt5Agg).
- **Word clouds** — separate clouds for positive and negative comments,
  plus ranked keyword lists.
- **Sortable, searchable, filterable data table** — filter by sentiment,
  source, or keyword.
- **Export** — CSV, Excel, JSON, and a full multi-page **PDF report**
  (statistics, charts, word clouds, sample table, and recommendations).
- **Settings window** — theme, font size, chart color scheme, ML
  algorithm selection, default export folder.
- **Threaded analysis** — sentiment analysis runs on a background
  `QThread` with a live progress bar, so the UI never freezes.
- **Logging & error handling** — rotating log file (`logs/app.log`)
  capturing imports, predictions, exports, and errors; graceful handling
  of invalid files, empty input, and unsupported formats.

---

## Project Structure

```
CustomerSentimentAnalyzer/
│
├── main.py                     # Entry point + splash screen
├── requirements.txt
├── README.md
│
├── ui/
│   ├── dashboard.py             # Main window (all pages, charts, table)
│   ├── settings.py              # Settings dialog
│   └── charts.py                # Matplotlib chart widgets
│
├── models/
│   ├── sentiment_model.py       # Rule-based engine (VADER + TextBlob)
│   ├── ml_model.py              # ML classifier (TF-IDF + sklearn)
│   └── analytics.py             # Combines both engines + stats/keywords
│
├── utils/
│   ├── preprocessing.py         # NLP cleaning pipeline
│   ├── data_loader.py           # CSV/Excel/JSON import + social simulation
│   ├── exporter.py              # CSV/Excel/JSON export
│   ├── report_generator.py      # PDF report builder
│   └── logger.py                # Rotating file logger
│
├── data/
│   ├── sample_comments.csv      # Sample dataset (150 comments) to try the app
│   └── training_dataset.csv     # Labeled dataset used to train the ML model
│
├── reports/                     # Generated PDF reports land here
├── exports/                     # Exported CSV/Excel/JSON files land here
├── assets/                      # (reserved for icons/images)
└── logs/                        # app.log (rotating log file)
```

---

## Installation

1. **Requirements**: Python 3.11+ recommended (3.9+ should also work).

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate        # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. The first launch will automatically download the required NLTK
   corpora (`punkt`, `stopwords`, `wordnet`). This needs an internet
   connection once; after that everything runs fully offline. If no
   internet is available, the app automatically falls back to a
   built-in lightweight stopword list so it still works.

---

## Running the Application

```bash
python main.py
```

A splash screen appears while the NLP pipeline and ML model are
prepared, then the main dashboard opens.

### Quick start inside the app

1. Go to **Data Import** and click **Load Sample Dataset** (or import
   your own CSV/Excel/JSON file, or drag-and-drop a CSV anywhere onto
   the window).
2. Click **▶ Run Sentiment Analysis** (or press `Ctrl+R`).
3. Explore the **Dashboard**, **Analytics Charts**, **Word Clouds**, and
   **Model Comparison** pages.
4. Use **Reports & Export** to save results as CSV/Excel/JSON or
   generate a full PDF report.

### Keyboard Shortcuts

| Shortcut | Action                       |
|----------|------------------------------|
| Ctrl+O   | Import a file                |
| Ctrl+R   | Run sentiment analysis       |
| Ctrl+F   | Focus the quick search bar   |
| Ctrl+S   | Jump to Reports & Export     |

---

## How It Works

1. **Preprocessing** (`utils/preprocessing.py`) cleans raw text (HTML,
   URLs, emojis, punctuation, numbers), tokenizes it, removes stopwords,
   and lemmatizes the result.
2. **Rule-based sentiment** (`models/sentiment_model.py`) runs VADER and
   TextBlob on lightly-cleaned text (stopwords kept, since they carry
   important context like negation) and blends both scores into a final
   label, numeric score, and confidence percentage.
3. **ML sentiment** (`models/ml_model.py`) runs a TF-IDF + classifier
   pipeline trained on `data/training_dataset.csv`. The trained model is
   cached under `models/cache/` so subsequent runs load instantly. You
   can switch algorithms (Naive Bayes / Logistic Regression / Random
   Forest / SVM) from Settings.
4. **Analytics** (`models/analytics.py`) merges both predictions per
   comment, computes dashboard statistics, extracts top keywords per
   sentiment class, and generates simple rule-based recommendations.

---

## Notes on the ML Model

- The bundled `training_dataset.csv` contains several hundred labeled
  example comments and is intended to demonstrate the full pipeline
  (TF-IDF vectorization, train/test split, accuracy evaluation, model
  caching). Typical held-out accuracy is roughly 90%+ across the
  supported algorithms on this dataset.
- For a real production deployment, you would replace/extend this
  dataset with domain-specific labeled data from your own product
  reviews or support tickets.

---

## Extending With Real Social Media APIs

`utils/data_loader.py` contains `generate_social_mentions()`, which
returns the same standardized DataFrame shape (`id`, `comment`, `source`,
`date`) as the file-import functions. To connect a real API (Twitter/X,
Reddit, etc.), write a new function with the same return shape and call
it from `ui/dashboard.py` in place of `generate_social_mentions()` — no
other code needs to change.

---

## Troubleshooting

- **"NLTK unavailable" warning in the logs**: the app will still work
  using a built-in fallback stopword list; only lemmatization quality is
  slightly reduced.
- **Word cloud shows "No data available"**: make sure you've run
  sentiment analysis first, and that there is at least one comment in
  the relevant sentiment category.
- **Slow first run**: the ML model is trained once and cached under
  `models/cache/`; subsequent runs are much faster.

---

## License

This project uses only free and open-source libraries (PySide6, NLTK,
TextBlob, VADER, scikit-learn, Matplotlib, WordCloud, ReportLab,
openpyxl) and runs entirely locally — no paid APIs required.
