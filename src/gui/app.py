"""
app.py — application entry point.

Responsibilities
----------------
* Create the QApplication.
* Apply the dark Fusion palette to native Qt elements (dialogs, scrollbars, etc.).
* Instantiate the detector and main window.
* Start the event loop.
"""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from src.gui.palette     import PALETTE
from src.gui.main_window import MainWindow
from src.detector        import SteganalysisTool


def start_gui() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_build_dark_palette())

    window = MainWindow(detector=SteganalysisTool())
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())


def _build_dark_palette() -> QPalette:
    """Native Qt widgets (file dialogs, scrollbars) inherit this palette."""
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(PALETTE["bg"]))
    pal.setColor(QPalette.WindowText,      QColor(PALETTE["text"]))
    pal.setColor(QPalette.Base,            QColor(PALETTE["surface"]))
    pal.setColor(QPalette.AlternateBase,   QColor(PALETTE["surface2"]))
    pal.setColor(QPalette.Text,            QColor(PALETTE["text"]))
    pal.setColor(QPalette.Button,          QColor(PALETTE["surface"]))
    pal.setColor(QPalette.ButtonText,      QColor(PALETTE["text"]))
    pal.setColor(QPalette.Highlight,       QColor(PALETTE["accent_dim"]))
    pal.setColor(QPalette.HighlightedText, QColor(PALETTE["accent"]))
    return pal