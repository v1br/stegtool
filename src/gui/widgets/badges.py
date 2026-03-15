from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

from src.gui.palette import PALETTE, label_fg, label_bg


class ThreatBadge(QLabel):
    """Compact coloured badge used in the result list and detail panel."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        fg = label_fg(label)
        bg = label_bg(label)
        self.setText(label)
        self.setFixedHeight(20)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                background:    {bg};
                color:         {fg};
                border:        1px solid {fg};
                border-radius: 3px;
                font-family:   'Courier New', monospace;
                font-size:     8px;
                font-weight:   bold;
                padding:       1px 7px;
                letter-spacing:1.5px;
            }}
        """)


class ProbBar(QWidget):
    """Mini horizontal bar filled proportionally to a probability value."""

    _HEIGHT = 8
    _RADIUS = 4

    def __init__(self, prob: float, label: str, parent=None):
        super().__init__(parent)
        self._prob  = max(0.0, min(1.0, prob))
        self._label = label
        self.setFixedSize(80, self._HEIGHT)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PALETTE["border"]))
        p.drawRoundedRect(0, 0, w, h, self._RADIUS, self._RADIUS)

        # Fill
        fill_w = int(self._prob * w)
        if fill_w > 0:
            p.setBrush(QColor(label_fg(self._label)))
            p.drawRoundedRect(0, 0, fill_w, h, self._RADIUS, self._RADIUS)