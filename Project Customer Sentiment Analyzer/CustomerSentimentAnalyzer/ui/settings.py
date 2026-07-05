"""
settings.py
------------
Application settings dialog: theme, font size, ML model selection,
chart color scheme, and default export location.
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QFileDialog, QLineEdit, QGroupBox, QDialogButtonBox,
)

from models.ml_model import ALGORITHMS

CHART_COLOR_SCHEMES = ["Default", "Vibrant", "Pastel", "Monochrome"]


class SettingsDialog(QDialog):
    """Modal dialog exposing user-configurable application settings."""

    settings_applied = Signal(dict)

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        self.current_settings = dict(current_settings)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        appearance_box = QGroupBox("Appearance")
        form1 = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.current_settings.get("theme", "Light"))
        form1.addRow("Theme:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(self.current_settings.get("font_size", 10))
        form1.addRow("Font Size:", self.font_size_spin)

        self.chart_colors_combo = QComboBox()
        self.chart_colors_combo.addItems(CHART_COLOR_SCHEMES)
        self.chart_colors_combo.setCurrentText(self.current_settings.get("chart_colors", "Default"))
        form1.addRow("Chart Color Scheme:", self.chart_colors_combo)

        appearance_box.setLayout(form1)
        layout.addWidget(appearance_box)

        model_box = QGroupBox("Model")
        form2 = QFormLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(ALGORITHMS.keys()))
        self.model_combo.setCurrentText(self.current_settings.get("ml_algorithm", "Naive Bayes"))
        form2.addRow("ML Algorithm:", self.model_combo)
        model_box.setLayout(form2)
        layout.addWidget(model_box)

        export_box = QGroupBox("Export")
        form3 = QFormLayout()
        path_layout = QHBoxLayout()
        self.export_path_edit = QLineEdit(self.current_settings.get("export_location", "exports"))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.export_path_edit)
        path_layout.addWidget(browse_btn)
        form3.addRow("Default Export Location:", path_layout)
        export_box.setLayout(form3)
        layout.addWidget(export_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder", self.export_path_edit.text())
        if folder:
            self.export_path_edit.setText(folder)

    def _on_accept(self):
        result = {
            "theme": self.theme_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "chart_colors": self.chart_colors_combo.currentText(),
            "ml_algorithm": self.model_combo.currentText(),
            "export_location": self.export_path_edit.text() or "exports",
        }
        self.settings_applied.emit(result)
        self.accept()

    def get_settings(self) -> dict:
        return {
            "theme": self.theme_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "chart_colors": self.chart_colors_combo.currentText(),
            "ml_algorithm": self.model_combo.currentText(),
            "export_location": self.export_path_edit.text() or "exports",
        }
