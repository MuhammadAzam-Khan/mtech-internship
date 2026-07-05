"""
main.py
--------
Entry point for the Customer Sentiment Analyzer desktop application.

Launches a splash screen while heavy imports (NLTK corpora, ML model
training/loading) settle, then opens the main dashboard window.

Run with:
    python main.py
"""

import os
import sys
import traceback

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger, log_event

logger = get_logger("Main")


def build_splash_pixmap() -> QPixmap:
    """Programmatically render a splash screen image (no external asset
    file required)."""
    width, height = 560, 320
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#1abc9c"))
    gradient.setColorAt(1.0, QColor("#2c3e50"))
    painter.setBrush(gradient)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, width, height, 18, 18)

    painter.setPen(QColor("#ffffff"))
    title_font = QFont("Segoe UI", 26, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(0, 100, width, 60, Qt.AlignCenter, "Customer Sentiment Analyzer")

    subtitle_font = QFont("Segoe UI", 11)
    painter.setFont(subtitle_font)
    painter.drawText(0, 160, width, 30, Qt.AlignCenter, "AI-Powered NLP & Machine Learning Dashboard")

    small_font = QFont("Segoe UI", 9)
    painter.setFont(small_font)
    painter.drawText(0, height - 50, width, 30, Qt.AlignCenter, "Loading modules, please wait...")

    painter.end()
    return pixmap


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Customer Sentiment Analyzer")

    splash_pixmap = build_splash_pixmap()
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.FramelessWindowHint)
    splash.show()
    app.processEvents()

    log_event("SYSTEM", "Splash screen displayed, loading application modules.")

    try:
        splash.showMessage("Loading NLP pipeline...", Qt.AlignBottom | Qt.AlignHCenter, QColor("white"))
        app.processEvents()
        from utils import preprocessing  # noqa: F401  (triggers NLTK setup)

        splash.showMessage("Preparing sentiment engines...", Qt.AlignBottom | Qt.AlignHCenter, QColor("white"))
        app.processEvents()
        from models.sentiment_model import RuleBasedSentimentEngine  # noqa: F401
        from models.ml_model import MLSentimentEngine

        # Warm up / cache the default ML model in the background of splash.
        try:
            MLSentimentEngine("Naive Bayes").train()
        except Exception as exc:
            logger.warning(f"Could not pre-train default ML model: {exc}")

        splash.showMessage("Building dashboard...", Qt.AlignBottom | Qt.AlignHCenter, QColor("white"))
        app.processEvents()
        from ui.dashboard import MainWindow

        window = MainWindow()
    except Exception as exc:
        logger.error(f"Fatal startup error: {exc}\n{traceback.format_exc()}")
        splash.close()
        QMessageBox.critical(None, "Startup Error",
                              f"The application failed to start:\n\n{exc}\n\n"
                              f"See logs/app.log for details.")
        sys.exit(1)

    def show_main():
        window.show()
        splash.finish(window)
        log_event("SYSTEM", "Main window displayed.")

    QTimer.singleShot(600, show_main)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
