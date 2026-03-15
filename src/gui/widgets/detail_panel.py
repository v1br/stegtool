import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSplitter, QScrollArea,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from src.gui.palette import PALETTE, label_fg
from src.gui.widgets.badges import ProbBar


class DetailPanel(QWidget):
    """Vertically split: image preview on top, scrollable analysis below."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = self._build_splitter()
        layout.addWidget(self._splitter)

    # ── Public API ───────────────────────────

    def show_image(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._image_label.setText("CANNOT LOAD IMAGE")
            return
        h = max(80, self._image_frame.height() - 16)
        w = max(80, self._image_frame.width()  - 16)
        self._image_label.setPixmap(
            pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def show_result(self, result: dict) -> None:
        self._clear_details()
        label = result["label"]
        prob  = result["probability"]
        color = label_fg(label)

        self._add_row("Prediction",  label,                               color)
        self._add_row("Probability", f"{prob:.4f}",                       color)
        self._add_row("Filename",    os.path.basename(result["file"]),    PALETTE["text"])
        self._add_divider()

        if "estimated_payload" in result:
            self._add_row("Est. Payload", f"{result['estimated_payload']} bpp")

        if "consensus" in result:
            self._add_row("Model Consensus", str(result["consensus"]))

        if "model_probabilities" in result:
            self._add_divider()
            self._add_section_header("MODEL RESPONSES")
            for bpp, p in sorted(result["model_probabilities"].items()):
                self._details_layout.addWidget(
                    self._model_prob_row(bpp, p, label)
                )

        self._details_layout.addStretch()

    def clear(self) -> None:
        self._image_label.setText("SELECT AN IMAGE")
        self._clear_details()

    # ── Builder helpers ──────────────────────

    def _build_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter::handle       {{ background: {PALETTE["border"]}; }}
            QSplitter::handle:hover {{ background: {PALETTE["accent"]}; }}
        """)

        self._image_frame, self._image_label = self._build_image_pane()
        splitter.addWidget(self._image_frame)
        splitter.addWidget(self._build_details_pane())

        splitter.setSizes([300, 260])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        return splitter

    def _build_image_pane(self) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("ImageFrame")
        frame.setMinimumHeight(80)
        frame.setStyleSheet(f"QFrame#ImageFrame {{ background: {PALETTE['bg']}; }}")

        label = QLabel("SELECT AN IMAGE")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      13px;
            letter-spacing: 3px;
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        return frame, label

    def _build_details_pane(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(60)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {PALETTE["surface"]}; border: none; }}
            QScrollBar:vertical {{
                background:    {PALETTE["bg"]};
                width:         6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background:    {PALETTE["border_hi"]};
                border-radius: 3px;
            }}
        """)

        container = QWidget()
        container.setStyleSheet(f"background: {PALETTE['surface']};")
        self._details_layout = QVBoxLayout(container)
        self._details_layout.setContentsMargins(20, 18, 20, 18)
        self._details_layout.setSpacing(12)
        self._details_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    # ── Detail-row factories ─────────────────

    def _add_row(self, label: str, value: str, value_color: str = None) -> None:
        self._details_layout.addWidget(
            self._make_row(label, value, value_color or PALETTE["text_bright"])
        )

    def _add_divider(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            f"background: {PALETTE['border']}; max-height: 1px; border: none;"
        )
        self._details_layout.addWidget(line)

    def _add_section_header(self, text: str) -> None:
        hdr = QLabel(text)
        hdr.setStyleSheet(f"""
            color:          {PALETTE["accent"]};
            font-family:    'Courier New', monospace;
            font-size:      10px;
            letter-spacing: 2px;
            font-weight:    bold;
        """)
        self._details_layout.addWidget(hdr)

    def _clear_details(self) -> None:
        while self._details_layout.count():
            item = self._details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._details_layout.addStretch()

    @staticmethod
    def _make_row(label: str, value: str, value_color: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        lbl = QLabel(label.upper())
        lbl.setFixedWidth(140)
        lbl.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      10px;
            letter-spacing: 1.5px;
        """)

        val = QLabel(value)
        val.setStyleSheet(f"""
            color:       {value_color};
            font-family: 'Courier New', monospace;
            font-size:   13px;
            font-weight: bold;
        """)
        val.setWordWrap(True)

        h.addWidget(lbl)
        h.addWidget(val, stretch=1)
        return row

    @staticmethod
    def _model_prob_row(bpp: str, prob: float, label: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(12)

        bpp_lbl = QLabel(f"{bpp} bpp")
        bpp_lbl.setFixedWidth(60)
        bpp_lbl.setStyleSheet(f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   11px;
        """)

        bar = ProbBar(prob, label)
        bar.setFixedSize(120, 6)

        p_lbl = QLabel(f"{prob:.3f}")
        p_lbl.setStyleSheet(f"""
            color:       {PALETTE["text"]};
            font-family: 'Courier New', monospace;
            font-size:   11px;
        """)

        h.addWidget(bpp_lbl)
        h.addWidget(bar)
        h.addWidget(p_lbl)
        h.addStretch()
        return row