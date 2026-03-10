"""ResultRowWidget — one row in the scan-results list."""

import os

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from src.gui.palette import PALETTE, label_fg
from src.gui.widgets.badges import ThreatBadge, ProbBar


class ResultRowWidget(QWidget):
    """Displays thumbnail · threat badge · filename · probability for one result."""

    _THUMB_SIZE  = 24
    _BADGE_WIDTH = 82
    _PCT_WIDTH   = 44

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ResultRow")

        label    = result["label"]
        prob     = result["probability"]
        filename = os.path.basename(result["file"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        layout.addWidget(self._make_thumb(result["file"]))
        layout.addWidget(self._make_badge(label))
        layout.addWidget(self._make_name_label(filename), stretch=1)
        layout.addWidget(ProbBar(prob, label))
        layout.addWidget(self._make_pct_label(prob, label))

        self.setStyleSheet(f"""
            QWidget#ResultRow {{
                background:    transparent;
                border-bottom: 1px solid {PALETTE["border"]};
            }}
            QWidget#ResultRow:hover {{
                background: {PALETTE["surface2"]};
            }}
        """)

    # ── Private builders ─────────────────────

    def _make_thumb(self, path: str) -> QLabel:
        thumb = QLabel()
        pix   = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(
                self._THUMB_SIZE, self._THUMB_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
        thumb.setPixmap(pix)
        thumb.setFixedSize(self._THUMB_SIZE + 2, self._THUMB_SIZE + 2)
        return thumb

    def _make_badge(self, label: str) -> ThreatBadge:
        badge = ThreatBadge(label)
        badge.setFixedWidth(self._BADGE_WIDTH)
        return badge

    def _make_name_label(self, filename: str) -> QLabel:
        lbl = QLabel(filename)
        lbl.setStyleSheet(f"""
            color:       {PALETTE["text_bright"]};
            font-family: 'Courier New', monospace;
            font-size:   12px;
        """)
        lbl.setMinimumWidth(0)
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return lbl

    def _make_pct_label(self, prob: float, label: str) -> QLabel:
        lbl = QLabel(f"{prob * 100:5.1f}%")
        lbl.setFixedWidth(self._PCT_WIDTH)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(f"""
            color:       {label_fg(label)};
            font-family: 'Courier New', monospace;
            font-size:   12px;
            font-weight: bold;
        """)
        return lbl