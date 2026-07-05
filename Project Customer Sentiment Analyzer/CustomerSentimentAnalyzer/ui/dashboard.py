"""
dashboard.py
-------------
Main application window for the Customer Sentiment Analyzer.

Implements the full dashboard experience: sidebar navigation, top toolbar,
status bar, KPI cards, sortable/searchable data table, embedded charts,
word clouds, settings integration, threaded analysis with progress
reporting, drag-and-drop CSV import, and export/report generation.
"""

import os
import traceback
from datetime import datetime

import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QFont, QKeySequence, QAction, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QFrame, QToolBar, QFileDialog,
    QMessageBox, QProgressBar, QTextEdit, QSplitter, QGridLayout, QSpinBox,
    QApplication, QAbstractItemView, QSizePolicy, QScrollArea,
)

from models.analytics import (
    analyze_dataframe, compute_stats, extract_top_keywords,
    build_wordcloud_text, generate_recommendations,
)
from utils.data_loader import load_file, load_manual_entries, generate_social_mentions, DataLoadError
from utils.exporter import export_dataframe, ExportError
from utils.report_generator import generate_pdf_report, ReportError
from utils.logger import get_logger, log_event
from ui.charts import (
    PieChartCanvas, BarChartCanvas, LineTrendCanvas, HistogramCanvas,
    SourceBarCanvas, WordCloudCanvas,
)
from ui.settings import SettingsDialog

logger = get_logger("Dashboard")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")

LIGHT_STYLESHEET = """
QMainWindow, QWidget { background-color: #f4f6fa; color: #2c3e50; font-family: 'Segoe UI', Arial; }
QFrame#sidebar { background-color: #2c3e50; }
QFrame#card { background-color: #ffffff; border-radius: 10px; border: 1px solid #e1e5ea; }
QLabel#cardValue { font-size: 22px; font-weight: bold; }
QLabel#cardTitle { font-size: 11px; color: #7f8c8d; }
QPushButton#navBtn { color: #ecf0f1; background-color: transparent; text-align: left;
                      padding: 12px 18px; border: none; font-size: 13px; }
QPushButton#navBtn:hover { background-color: #34495e; }
QPushButton#navBtnActive { color: #ffffff; background-color: #1abc9c; text-align: left;
                            padding: 12px 18px; border: none; font-size: 13px; font-weight: bold; }
QTableWidget { background-color: #ffffff; gridline-color: #e1e5ea; border-radius: 6px; }
QHeaderView::section { background-color: #34495e; color: white; padding: 6px; border: none; }
QPushButton#primaryBtn { background-color: #1abc9c; color: white; padding: 8px 16px;
                          border-radius: 6px; font-weight: bold; }
QPushButton#primaryBtn:hover { background-color: #16a085; }
QLineEdit, QComboBox, QSpinBox { padding: 6px; border: 1px solid #d0d7de; border-radius: 5px;
                                  background-color: #ffffff; }
QProgressBar { border-radius: 5px; text-align: center; background-color: #e1e5ea; }
QProgressBar::chunk { background-color: #1abc9c; border-radius: 5px; }
"""

DARK_STYLESHEET = """
QMainWindow, QWidget { background-color: #1e1e2f; color: #e0e0e0; font-family: 'Segoe UI', Arial; }
QFrame#sidebar { background-color: #15151f; }
QFrame#card { background-color: #262639; border-radius: 10px; border: 1px solid #33334a; }
QLabel#cardValue { font-size: 22px; font-weight: bold; color: #ffffff; }
QLabel#cardTitle { font-size: 11px; color: #9a9ab0; }
QPushButton#navBtn { color: #cfd2e0; background-color: transparent; text-align: left;
                      padding: 12px 18px; border: none; font-size: 13px; }
QPushButton#navBtn:hover { background-color: #2a2a40; }
QPushButton#navBtnActive { color: #ffffff; background-color: #6c5ce7; text-align: left;
                            padding: 12px 18px; border: none; font-size: 13px; font-weight: bold; }
QTableWidget { background-color: #262639; gridline-color: #33334a; color: #e0e0e0; border-radius: 6px; }
QHeaderView::section { background-color: #33334a; color: white; padding: 6px; border: none; }
QPushButton#primaryBtn { background-color: #6c5ce7; color: white; padding: 8px 16px;
                          border-radius: 6px; font-weight: bold; }
QPushButton#primaryBtn:hover { background-color: #5a4bd1; }
QLineEdit, QComboBox, QSpinBox { padding: 6px; border: 1px solid #33334a; border-radius: 5px;
                                  background-color: #262639; color: #e0e0e0; }
QProgressBar { border-radius: 5px; text-align: center; background-color: #33334a; color: white; }
QProgressBar::chunk { background-color: #6c5ce7; border-radius: 5px; }
"""


# ---------------------------------------------------------------------------
# Background worker thread (keeps the UI responsive during analysis)
# ---------------------------------------------------------------------------
class AnalysisWorker(QThread):
    progress_updated = Signal(int)
    finished_ok = Signal(pd.DataFrame)
    failed = Signal(str)

    def __init__(self, df: pd.DataFrame, ml_algorithm: str):
        super().__init__()
        self.df = df
        self.ml_algorithm = ml_algorithm

    def run(self):
        try:
            result = analyze_dataframe(
                self.df, ml_algorithm=self.ml_algorithm,
                progress_callback=lambda p: self.progress_updated.emit(p),
            )
            self.finished_ok.emit(result)
        except Exception as exc:
            logger.error(f"Analysis failed: {exc}\n{traceback.format_exc()}")
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Reusable KPI Card widget
# ---------------------------------------------------------------------------
class KPICard(QFrame):
    def __init__(self, title: str, value: str = "0", accent: str = "#1abc9c"):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(90)
        self.setFrameShape(QFrame.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        self.value_label.setStyleSheet(f"color: {accent};")

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("cardTitle")

        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Customer Sentiment Analyzer — M-Tech AI/ML Internship Project")
        self.resize(1360, 860)
        self.setAcceptDrops(True)

        self.raw_df = pd.DataFrame(columns=["id", "comment", "source", "date"])
        self.analyzed_df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.recent_files = []

        self.settings = {
            "theme": "Light",
            "font_size": 10,
            "chart_colors": "Default",
            "ml_algorithm": "Naive Bayes",
            "export_location": EXPORTS_DIR,
        }

        os.makedirs(EXPORTS_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)

        self._build_ui()
        self.apply_theme()
        self.statusBar().showMessage("Ready. Import data or generate simulated social mentions to begin.")
        log_event("SYSTEM", "Application started.")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        self._build_toolbar()
        self._build_shortcuts()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(4)

        logo = QLabel("  📊  SentimentAI")
        logo.setStyleSheet("color: white; font-size: 16px; font-weight: bold; padding: 10px 18px 20px 18px;")
        sidebar_layout.addWidget(logo)

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard"),
            ("import", "📁  Data Import"),
            ("social", "📱  Social Monitor"),
            ("table", "📋  Comments Table"),
            ("charts", "📈  Analytics Charts"),
            ("wordcloud", "☁️  Word Clouds"),
            ("compare", "🤖  Model Comparison"),
            ("report", "🧾  Reports & Export"),
            ("settings", "⚙️  Settings"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sidebar_layout.addStretch()
        self.theme_toggle_btn = QPushButton("🌙  Toggle Theme")
        self.theme_toggle_btn.setObjectName("navBtn")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_toggle_btn)

        root_layout.addWidget(self.sidebar)

        # --- Main content area ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 16, 20, 16)

        self.pages = QStackedWidget()
        self.page_dashboard = self._build_dashboard_page()
        self.page_import = self._build_import_page()
        self.page_social = self._build_social_page()
        self.page_table = self._build_table_page()
        self.page_charts = self._build_charts_page()
        self.page_wordcloud = self._build_wordcloud_page()
        self.page_compare = self._build_compare_page()
        self.page_report = self._build_report_page()
        self.page_settings_placeholder = self._build_settings_page()

        self.pages.addWidget(self.page_dashboard)   # 0
        self.pages.addWidget(self.page_import)       # 1
        self.pages.addWidget(self.page_social)        # 2
        self.pages.addWidget(self.page_table)          # 3
        self.pages.addWidget(self.page_charts)          # 4
        self.pages.addWidget(self.page_wordcloud)        # 5
        self.pages.addWidget(self.page_compare)           # 6
        self.pages.addWidget(self.page_report)             # 7
        self.pages.addWidget(self.page_settings_placeholder) # 8

        self.page_index = {
            "dashboard": 0, "import": 1, "social": 2, "table": 3, "charts": 4,
            "wordcloud": 5, "compare": 6, "report": 7, "settings": 8,
        }

        content_layout.addWidget(self.pages)
        root_layout.addWidget(content_container, stretch=1)

        self.switch_page("dashboard")

        # Progress bar (used during analysis) shown in status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(220)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        import_action = QAction("📁 Import", self)
        import_action.triggered.connect(self.import_file_dialog)
        toolbar.addAction(import_action)

        analyze_action = QAction("▶ Analyze", self)
        analyze_action.triggered.connect(self.run_analysis)
        toolbar.addAction(analyze_action)

        export_action = QAction("⬇ Export", self)
        export_action.triggered.connect(lambda: self.switch_page("report"))
        toolbar.addAction(export_action)

        settings_action = QAction("⚙ Settings", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()
        self.toolbar_search = QLineEdit()
        self.toolbar_search.setPlaceholderText("Quick search comments... (Ctrl+F)")
        self.toolbar_search.setFixedWidth(280)
        self.toolbar_search.textChanged.connect(self.apply_filters)
        toolbar.addWidget(self.toolbar_search)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.import_file_dialog)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.run_analysis)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.toolbar_search.setFocus())
        QShortcut(QKeySequence("Ctrl+S"), self, activated=lambda: self.switch_page("report"))

    # ------------------------------------------------------------------
    # Page: Dashboard (KPI overview)
    # ------------------------------------------------------------------
    def _build_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Dashboard Overview")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        subtitle = QLabel("Real-time summary of customer sentiment across all imported and monitored channels.")
        subtitle.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.card_total = KPICard("Total Comments", "0", "#3498db")
        self.card_positive = KPICard("Positive", "0", "#2ecc71")
        self.card_negative = KPICard("Negative", "0", "#e74c3c")
        self.card_neutral = KPICard("Neutral", "0", "#95a5a6")
        self.card_avg_score = KPICard("Avg Sentiment Score", "0.00", "#9b59b6")
        self.card_avg_conf = KPICard("Avg Confidence", "0%", "#f39c12")
        self.card_top_source = KPICard("Most Active Source", "N/A", "#1abc9c")
        self.card_agreement = KPICard("Model Agreement", "0%", "#16a085")

        for i, card in enumerate([self.card_total, self.card_positive, self.card_negative,
                                   self.card_neutral, self.card_avg_score, self.card_avg_conf,
                                   self.card_top_source, self.card_agreement]):
            grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(grid)

        # Mini charts row
        mini_row = QHBoxLayout()
        self.dash_pie = PieChartCanvas(width=4, height=3.2)
        self.dash_bar = BarChartCanvas(width=4, height=3.2)
        mini_row.addWidget(self.dash_pie)
        mini_row.addWidget(self.dash_bar)
        layout.addLayout(mini_row)

        # AI summary box
        summary_label = QLabel("AI-Generated Summary & Recommendations")
        summary_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(summary_label)
        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setMaximumHeight(140)
        self.summary_box.setPlaceholderText("Run an analysis to generate an automatic summary and recommendations...")
        layout.addWidget(self.summary_box)

        return page

    # ------------------------------------------------------------------
    # Page: Data Import
    # ------------------------------------------------------------------
    def _build_import_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Data Import")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        info = QLabel("Import CSV, Excel, or JSON files containing customer comments, or drag & drop "
                       "a CSV file anywhere onto this window. You can also load the bundled sample dataset.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("📁  Browse File (CSV / Excel / JSON)")
        browse_btn.setObjectName("primaryBtn")
        browse_btn.clicked.connect(self.import_file_dialog)
        btn_row.addWidget(browse_btn)

        sample_btn = QPushButton("📊  Load Sample Dataset")
        sample_btn.clicked.connect(self.load_sample_dataset)
        btn_row.addWidget(sample_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        manual_label = QLabel("Or type / paste comments manually (one comment per line):")
        manual_label.setStyleSheet("margin-top: 14px; font-weight: bold;")
        layout.addWidget(manual_label)

        self.manual_text_edit = QTextEdit()
        self.manual_text_edit.setPlaceholderText(
            "I love this product!\nThe delivery was late and the box was damaged.\nIt works fine overall."
        )
        layout.addWidget(self.manual_text_edit)

        manual_btn_row = QHBoxLayout()
        load_manual_btn = QPushButton("➕  Add Manual Comments")
        load_manual_btn.setObjectName("primaryBtn")
        load_manual_btn.clicked.connect(self.load_manual_comments)
        manual_btn_row.addWidget(load_manual_btn)
        manual_btn_row.addStretch()
        layout.addLayout(manual_btn_row)

        self.import_status_label = QLabel("No data loaded yet.")
        self.import_status_label.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        layout.addWidget(self.import_status_label)

        self.recent_files_label = QLabel("Recent files: none")
        self.recent_files_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(self.recent_files_label)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Page: Social Monitor (simulation)
    # ------------------------------------------------------------------
    def _build_social_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Social Media Monitoring (Simulated)")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        info = QLabel("Generates simulated mentions from Twitter/X, Facebook, Instagram, Reddit, and "
                       "YouTube. The architecture is designed so real API integrations can be plugged "
                       "in later (see utils/data_loader.py) without changing the rest of the application.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info)

        form_row = QHBoxLayout()
        form_row.addWidget(QLabel("Brand / keyword to monitor:"))
        self.brand_input = QLineEdit("the brand")
        form_row.addWidget(self.brand_input)
        form_row.addWidget(QLabel("Number of mentions:"))
        self.mention_count_spin = QSpinBox()
        self.mention_count_spin.setRange(5, 500)
        self.mention_count_spin.setValue(30)
        form_row.addWidget(self.mention_count_spin)
        layout.addLayout(form_row)

        generate_btn = QPushButton("📡  Fetch Simulated Mentions")
        generate_btn.setObjectName("primaryBtn")
        generate_btn.clicked.connect(self.generate_social_data)
        layout.addWidget(generate_btn)

        self.social_status_label = QLabel("No mentions fetched yet.")
        self.social_status_label.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        layout.addWidget(self.social_status_label)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Page: Comments Table
    # ------------------------------------------------------------------
    def _build_table_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header_row = QHBoxLayout()
        header = QLabel("Comments Table")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(header)
        header_row.addStretch()

        analyze_btn = QPushButton("▶  Run Sentiment Analysis")
        analyze_btn.setObjectName("primaryBtn")
        analyze_btn.clicked.connect(self.run_analysis)
        header_row.addWidget(analyze_btn)
        layout.addLayout(header_row)

        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by keyword...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_row.addWidget(self.search_input)

        self.sentiment_filter = QComboBox()
        self.sentiment_filter.addItems(["All Sentiments", "Positive", "Negative", "Neutral"])
        self.sentiment_filter.currentIndexChanged.connect(self.apply_filters)
        filter_row.addWidget(self.sentiment_filter)

        self.source_filter = QComboBox()
        self.source_filter.addItems(["All Sources"])
        self.source_filter.currentIndexChanged.connect(self.apply_filters)
        filter_row.addWidget(self.source_filter)

        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Comment", "Source", "Date", "Sentiment", "Confidence", "ML Sentiment", "Length"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.table_count_label = QLabel("0 rows")
        self.table_count_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.table_count_label)

        return page

    # ------------------------------------------------------------------
    # Page: Analytics Charts
    # ------------------------------------------------------------------
    def _build_charts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Analytics Charts")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(16)

        self.chart_pie = PieChartCanvas(width=5, height=4)
        self.chart_bar = BarChartCanvas(width=5, height=4)
        self.chart_line = LineTrendCanvas(width=5, height=4)
        self.chart_hist = HistogramCanvas(width=5, height=4)
        self.chart_source = SourceBarCanvas(width=5, height=4)

        grid.addWidget(self.chart_pie, 0, 0)
        grid.addWidget(self.chart_bar, 0, 1)
        grid.addWidget(self.chart_line, 1, 0)
        grid.addWidget(self.chart_hist, 1, 1)
        grid.addWidget(self.chart_source, 2, 0, 1, 2)

        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return page

    # ------------------------------------------------------------------
    # Page: Word Clouds
    # ------------------------------------------------------------------
    def _build_wordcloud_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Word Clouds")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        row = QHBoxLayout()
        self.wc_positive = WordCloudCanvas(width=6, height=4.5)
        self.wc_negative = WordCloudCanvas(width=6, height=4.5)
        row.addWidget(self.wc_positive)
        row.addWidget(self.wc_negative)
        layout.addLayout(row)

        keywords_row = QHBoxLayout()
        self.top_pos_keywords_label = QTextEdit()
        self.top_pos_keywords_label.setReadOnly(True)
        self.top_pos_keywords_label.setPlaceholderText("Top positive keywords will appear here...")
        self.top_neg_keywords_label = QTextEdit()
        self.top_neg_keywords_label.setReadOnly(True)
        self.top_neg_keywords_label.setPlaceholderText("Top negative keywords will appear here...")
        keywords_row.addWidget(self.top_pos_keywords_label)
        keywords_row.addWidget(self.top_neg_keywords_label)
        layout.addLayout(keywords_row)

        return page

    # ------------------------------------------------------------------
    # Page: Model Comparison
    # ------------------------------------------------------------------
    def _build_compare_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Rule-Based vs Machine Learning Model Comparison")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        info = QLabel("Compares predictions from the rule-based engine (VADER + TextBlob) against "
                       "the trained machine learning classifier (TF-IDF + selectable algorithm).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info)

        self.compare_summary_label = QLabel("Run an analysis to see model comparison statistics.")
        self.compare_summary_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(self.compare_summary_label)

        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(5)
        self.compare_table.setHorizontalHeaderLabels(
            ["Comment", "Rule-Based", "Rule Confidence", "ML Model", "ML Confidence"]
        )
        self.compare_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.compare_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.compare_table)

        return page

    # ------------------------------------------------------------------
    # Page: Reports & Export
    # ------------------------------------------------------------------
    def _build_report_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Reports & Export")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        info = QLabel("Export your analyzed results, or generate a complete PDF report including "
                       "statistics, charts, and word clouds.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info)

        export_row = QHBoxLayout()
        for label, ext in [("Export CSV", ".csv"), ("Export Excel", ".xlsx"), ("Export JSON", ".json")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, e=ext: self.export_results(e))
            export_row.addWidget(btn)
        layout.addLayout(export_row)

        report_btn = QPushButton("🧾  Generate Full PDF Report")
        report_btn.setObjectName("primaryBtn")
        report_btn.clicked.connect(self.generate_report)
        layout.addWidget(report_btn)

        self.report_status_label = QLabel("")
        self.report_status_label.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        self.report_status_label.setWordWrap(True)
        layout.addWidget(self.report_status_label)

        layout.addStretch()
        return page

    def _build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)
        info = QLabel("Click below to open the full settings dialog (theme, font size, model "
                       "selection, chart colors, export location).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info)
        open_btn = QPushButton("⚙  Open Settings Dialog")
        open_btn.setObjectName("primaryBtn")
        open_btn.clicked.connect(self.open_settings_dialog)
        layout.addWidget(open_btn)
        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def switch_page(self, key: str):
        for k, btn in self.nav_buttons.items():
            btn.setObjectName("navBtnActive" if k == key else "navBtn")
            btn.setStyle(btn.style())  # force stylesheet re-evaluation
        if key == "settings":
            self.open_settings_dialog()
            key = "dashboard"
            self.nav_buttons["dashboard"].setObjectName("navBtnActive")
        self.pages.setCurrentIndex(self.page_index[key])

    # ------------------------------------------------------------------
    # Data import handlers
    # ------------------------------------------------------------------
    def import_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Comments File", "", "Data Files (*.csv *.xlsx *.xls *.json)"
        )
        if path:
            self._load_path(path)

    def _load_path(self, path: str):
        try:
            df = load_file(path)
            self._set_raw_data(df, replace=True)
            self.recent_files.insert(0, path)
            self.recent_files = self.recent_files[:5]
            self.recent_files_label.setText("Recent files: " + ", ".join(os.path.basename(p) for p in self.recent_files))
            self.import_status_label.setText(f"✅ Loaded {len(df)} comment(s) from {os.path.basename(path)}")
            self.statusBar().showMessage(f"Imported {len(df)} comments from {os.path.basename(path)}", 5000)
        except DataLoadError as exc:
            self._show_error("Import Error", str(exc))
        except Exception as exc:
            logger.error(f"Unexpected import error: {exc}\n{traceback.format_exc()}")
            self._show_error("Unexpected Error", f"Could not import file: {exc}")

    def load_sample_dataset(self):
        sample_path = os.path.join(DATA_DIR, "sample_comments.csv")
        if os.path.exists(sample_path):
            self._load_path(sample_path)
        else:
            self._show_error("File Not Found", "Sample dataset could not be located.")

    def load_manual_comments(self):
        text = self.manual_text_edit.toPlainText()
        try:
            df = load_manual_entries(text)
            self._set_raw_data(df, replace=False)
            self.import_status_label.setText(f"✅ Added {len(df)} manual comment(s). "
                                              f"Total: {len(self.raw_df)}")
            self.manual_text_edit.clear()
        except DataLoadError as exc:
            self._show_error("Input Error", str(exc))

    def generate_social_data(self):
        brand = self.brand_input.text().strip() or "the brand"
        count = self.mention_count_spin.value()
        try:
            df = generate_social_mentions(count=count, brand_name=brand)
            self._set_raw_data(df, replace=False)
            self.social_status_label.setText(f"✅ Fetched {len(df)} simulated mentions. "
                                              f"Total dataset size: {len(self.raw_df)}")
            self.statusBar().showMessage(f"Generated {len(df)} simulated social mentions.", 5000)
        except Exception as exc:
            self._show_error("Simulation Error", str(exc))

    def _set_raw_data(self, df: pd.DataFrame, replace: bool):
        if replace or self.raw_df.empty:
            self.raw_df = df
        else:
            combined = pd.concat([self.raw_df, df], ignore_index=True)
            combined["id"] = range(1, len(combined) + 1)
            self.raw_df = combined
        self.analyzed_df = pd.DataFrame()  # invalidate previous analysis
        self._refresh_table(self.raw_df)

    # ------------------------------------------------------------------
    # Drag & drop support
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".csv", ".xlsx", ".xls", ".json")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".csv", ".xlsx", ".xls", ".json")):
                self._load_path(path)
                self.switch_page("import")
                break

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def run_analysis(self):
        if self.raw_df.empty:
            self._show_error("No Data", "Please import data, add manual comments, or fetch social "
                                         "mentions before running analysis.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Running sentiment analysis, please wait...")

        self.worker = AnalysisWorker(self.raw_df, self.settings.get("ml_algorithm", "Naive Bayes"))
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.finished_ok.connect(self._on_analysis_finished)
        self.worker.failed.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_analysis_finished(self, result_df: pd.DataFrame):
        self.analyzed_df = result_df
        self.filtered_df = result_df
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage(f"Analysis complete: {len(result_df)} comments processed.", 6000)

        self._populate_source_filter()
        self._refresh_table(result_df)
        self._refresh_dashboard()
        self._refresh_charts()
        self._refresh_wordclouds()
        self._refresh_comparison()
        log_event("SYSTEM", f"Analysis pipeline completed for {len(result_df)} comments.")

    def _on_analysis_failed(self, message: str):
        self.progress_bar.setVisible(False)
        self._show_error("Analysis Failed", message)

    # ------------------------------------------------------------------
    # Table / filtering
    # ------------------------------------------------------------------
    def _populate_source_filter(self):
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem("All Sources")
        if "source" in self.analyzed_df.columns:
            for s in sorted(self.analyzed_df["source"].unique()):
                self.source_filter.addItem(str(s))
        self.source_filter.blockSignals(False)

    def apply_filters(self):
        df = self.analyzed_df if not self.analyzed_df.empty else self.raw_df
        if df.empty:
            return

        keyword = (self.search_input.text() if hasattr(self, "search_input") else "").strip().lower()
        toolbar_keyword = self.toolbar_search.text().strip().lower() if hasattr(self, "toolbar_search") else ""
        keyword = keyword or toolbar_keyword

        sentiment = self.sentiment_filter.currentText() if hasattr(self, "sentiment_filter") else "All Sentiments"
        source = self.source_filter.currentText() if hasattr(self, "source_filter") else "All Sources"

        filtered = df.copy()
        if keyword:
            filtered = filtered[filtered["comment"].str.lower().str.contains(keyword, na=False)]
        if sentiment != "All Sentiments" and "sentiment" in filtered.columns:
            filtered = filtered[filtered["sentiment"] == sentiment.lower()]
        if source != "All Sources" and "source" in filtered.columns:
            filtered = filtered[filtered["source"] == source]

        self.filtered_df = filtered
        self._refresh_table(filtered)

    def _refresh_table(self, df: pd.DataFrame):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        has_sentiment = "sentiment" in df.columns

        for _, row in df.iterrows():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(row.get("id", ""))))
            self.table.setItem(r, 1, QTableWidgetItem(str(row.get("comment", ""))))
            self.table.setItem(r, 2, QTableWidgetItem(str(row.get("source", ""))))
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get("date", ""))))

            if has_sentiment:
                sentiment_item = QTableWidgetItem(str(row.get("sentiment", "")).capitalize())
                color_map = {"Positive": QColor("#d4f8e8"), "Negative": QColor("#fbdcdc"), "Neutral": QColor("#eceff1")}
                sentiment_item.setBackground(color_map.get(sentiment_item.text(), QColor("#ffffff")))
                self.table.setItem(r, 4, sentiment_item)
                self.table.setItem(r, 5, QTableWidgetItem(f"{row.get('confidence', 0):.1f}%"))
                self.table.setItem(r, 6, QTableWidgetItem(str(row.get("ml_sentiment", "")).capitalize()))
            else:
                self.table.setItem(r, 4, QTableWidgetItem("—"))
                self.table.setItem(r, 5, QTableWidgetItem("—"))
                self.table.setItem(r, 6, QTableWidgetItem("—"))

            self.table.setItem(r, 7, QTableWidgetItem(str(len(str(row.get("comment", ""))))))

        self.table.setSortingEnabled(True)
        self.table_count_label.setText(f"{len(df)} row(s)")

    # ------------------------------------------------------------------
    # Dashboard / charts / wordcloud / comparison refresh
    # ------------------------------------------------------------------
    def _refresh_dashboard(self):
        if self.analyzed_df.empty:
            return
        stats = compute_stats(self.analyzed_df)
        self.card_total.set_value(str(stats["total"]))
        self.card_positive.set_value(str(stats["positive"]))
        self.card_negative.set_value(str(stats["negative"]))
        self.card_neutral.set_value(str(stats["neutral"]))
        self.card_avg_score.set_value(f"{stats['avg_score']:.2f}")
        self.card_avg_conf.set_value(f"{stats['avg_confidence']:.1f}%")
        self.card_top_source.set_value(stats["top_source"])
        self.card_agreement.set_value(f"{stats['ml_accuracy_vs_rule']:.1f}%")

        self.dash_pie.plot(stats)
        self.dash_bar.plot(stats)

        top_neg_keywords = extract_top_keywords(self.analyzed_df, "negative", top_n=8)
        recommendations = generate_recommendations(stats, top_neg_keywords)
        summary_html = f"<b>Overall Summary:</b> Out of {stats['total']} comments analyzed, " \
                        f"{stats['positive']} ({stats['positive']/max(stats['total'],1)*100:.1f}%) were positive, " \
                        f"{stats['negative']} ({stats['negative']/max(stats['total'],1)*100:.1f}%) were negative, " \
                        f"and {stats['neutral']} were neutral.<br><br><b>Recommendations:</b><ul>"
        for rec in recommendations:
            summary_html += f"<li>{rec}</li>"
        summary_html += "</ul>"
        self.summary_box.setHtml(summary_html)

    def _refresh_charts(self):
        if self.analyzed_df.empty:
            return
        stats = compute_stats(self.analyzed_df)
        self.chart_pie.plot(stats)
        self.chart_bar.plot(stats)
        self.chart_line.plot(self.analyzed_df)
        self.chart_hist.plot(self.analyzed_df)
        self.chart_source.plot(self.analyzed_df)

    def _refresh_wordclouds(self):
        if self.analyzed_df.empty:
            return
        pos_text = build_wordcloud_text(self.analyzed_df, "positive")
        neg_text = build_wordcloud_text(self.analyzed_df, "negative")
        self.wc_positive.plot(pos_text, colormap="Greens", title="Positive Comments")
        self.wc_negative.plot(neg_text, colormap="Reds", title="Negative Comments")

        pos_keywords = extract_top_keywords(self.analyzed_df, "positive", top_n=15)
        neg_keywords = extract_top_keywords(self.analyzed_df, "negative", top_n=15)
        self.top_pos_keywords_label.setHtml(
            "<b>Top Positive Keywords:</b><br>" + "<br>".join(f"{w} — {c}" for w, c in pos_keywords)
        )
        self.top_neg_keywords_label.setHtml(
            "<b>Top Negative Keywords:</b><br>" + "<br>".join(f"{w} — {c}" for w, c in neg_keywords)
        )

    def _refresh_comparison(self):
        if self.analyzed_df.empty:
            return
        stats = compute_stats(self.analyzed_df)
        algo = self.settings.get("ml_algorithm", "Naive Bayes")
        self.compare_summary_label.setText(
            f"Rule-based (VADER + TextBlob) vs {algo}: {stats['ml_accuracy_vs_rule']:.1f}% agreement "
            f"across {stats['total']} comments."
        )
        self.compare_table.setRowCount(0)
        sample = self.analyzed_df.head(200)
        for _, row in sample.iterrows():
            r = self.compare_table.rowCount()
            self.compare_table.insertRow(r)
            self.compare_table.setItem(r, 0, QTableWidgetItem(str(row.get("comment", ""))))
            self.compare_table.setItem(r, 1, QTableWidgetItem(str(row.get("sentiment", "")).capitalize()))
            self.compare_table.setItem(r, 2, QTableWidgetItem(f"{row.get('confidence', 0):.1f}%"))
            self.compare_table.setItem(r, 3, QTableWidgetItem(str(row.get("ml_sentiment", "")).capitalize()))
            self.compare_table.setItem(r, 4, QTableWidgetItem(f"{row.get('ml_confidence', 0):.1f}%"))

    # ------------------------------------------------------------------
    # Export / Report
    # ------------------------------------------------------------------
    def export_results(self, ext: str):
        df = self.filtered_df if not self.filtered_df.empty else self.analyzed_df
        if df.empty:
            df = self.raw_df
        if df.empty:
            self._show_error("No Data", "There is no data to export yet.")
            return

        default_dir = self.settings.get("export_location", EXPORTS_DIR)
        os.makedirs(default_dir, exist_ok=True)
        default_name = os.path.join(default_dir, f"sentiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        filters = {".csv": "CSV Files (*.csv)", ".xlsx": "Excel Files (*.xlsx)", ".json": "JSON Files (*.json)"}
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", default_name, filters[ext])
        if not path:
            return
        try:
            export_dataframe(df, path)
            self.report_status_label.setText(f"✅ Exported {len(df)} rows to {path}")
            self.statusBar().showMessage(f"Exported results to {os.path.basename(path)}", 5000)
        except ExportError as exc:
            self._show_error("Export Error", str(exc))

    def generate_report(self):
        if self.analyzed_df.empty:
            self._show_error("No Analysis Yet", "Please run sentiment analysis before generating a report.")
            return

        default_dir = self.settings.get("export_location", REPORTS_DIR)
        os.makedirs(default_dir, exist_ok=True)
        default_path = os.path.join(REPORTS_DIR, f"sentiment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", default_path, "PDF Files (*.pdf)")
        if not path:
            return

        try:
            stats = compute_stats(self.analyzed_df)
            pos_text = build_wordcloud_text(self.analyzed_df, "positive")
            neg_text = build_wordcloud_text(self.analyzed_df, "negative")
            top_neg_keywords = extract_top_keywords(self.analyzed_df, "negative", top_n=8)
            recommendations = generate_recommendations(stats, top_neg_keywords)

            generate_pdf_report(
                self.analyzed_df, stats, path,
                project_title="Customer Sentiment Analyzer",
                positive_text=pos_text, negative_text=neg_text,
                recommendations=recommendations,
            )
            self.report_status_label.setText(f"✅ PDF report generated: {path}")
            self.statusBar().showMessage("PDF report generated successfully.", 5000)
        except ReportError as exc:
            self._show_error("Report Generation Failed", str(exc))
        except Exception as exc:
            logger.error(f"Unexpected report error: {exc}\n{traceback.format_exc()}")
            self._show_error("Unexpected Error", f"Could not generate report: {exc}")

    # ------------------------------------------------------------------
    # Settings / Theme
    # ------------------------------------------------------------------
    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.settings.update(dialog.get_settings())
            self.apply_theme()
            self.statusBar().showMessage("Settings updated.", 3000)

    def apply_theme(self):
        is_dark = self.settings.get("theme", "Light") == "Dark"
        QApplication.instance().setStyleSheet(DARK_STYLESHEET if is_dark else LIGHT_STYLESHEET)
        font = QFont("Segoe UI", self.settings.get("font_size", 10))
        QApplication.instance().setFont(font)

        for canvas_attr in ["dash_pie", "dash_bar", "chart_pie", "chart_bar", "chart_line",
                             "chart_hist", "chart_source", "wc_positive", "wc_negative"]:
            canvas = getattr(self, canvas_attr, None)
            if canvas is not None:
                canvas.set_dark_mode(is_dark)
        if not self.analyzed_df.empty:
            self._refresh_charts()
            self._refresh_dashboard()
            self._refresh_wordclouds()

    def toggle_theme(self):
        self.settings["theme"] = "Dark" if self.settings.get("theme") == "Light" else "Light"
        self.apply_theme()

    # ------------------------------------------------------------------
    # Error handling helper
    # ------------------------------------------------------------------
    def _show_error(self, title: str, message: str):
        log_event("ERROR", f"{title}: {message}", level="error")
        QMessageBox.critical(self, title, message)
