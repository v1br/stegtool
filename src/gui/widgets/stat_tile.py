from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from src.gui.palette import PALETTE


class StatTile(QFrame):
    """Displays a large numeric value with a small title underneath."""

    def __init__(self, title: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatTile")
        self.setFixedHeight(62)

        self._value_lbl = QLabel(value)
        self._title_lbl = QLabel(title)

        self._value_lbl.setStyleSheet(f"""
            color:       {accent};
            font-family: 'Courier New', monospace;
            font-size:   22px;
            font-weight: bold;
        """)
        self._title_lbl.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      10px;
            letter-spacing: 1.5px;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)
        layout.addWidget(self._value_lbl)
        layout.addWidget(self._title_lbl)

        self.setStyleSheet(f"""
            QFrame#StatTile {{
                background:  {PALETTE["surface"]};
                border:      1px solid {PALETTE["border"]};
                border-top:  2px solid {accent};
                border-radius: 6px;
            }}
        """)

    def set_value(self, value: str) -> None:
        self._value_lbl.setText(value)