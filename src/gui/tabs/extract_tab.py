"""
ExtractTab — UI for LSB text extraction.

Layout
------
  ┌─ Control bar ─────────────────────────────────────────────────────┐
  │  [SELECT IMAGE]  path/to/image.png                   [EXTRACT]   │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ IMAGE PREVIEW ──────────────┬─ EXTRACTED MESSAGE ───────────────┐
  │                              │                                    │
  │       (preview)              │  extracted text here…              │
  │                              │                                    │
  │                              ├────────────────────────────────────┤
  │                              │ status: N characters extracted     │
  └──────────────────────────────┴────────────────────────────────────┘
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QFrame, QTextEdit,
    QSizePolicy, QSplitter,
)
from PySide6.QtGui  import QPixmap
from PySide6.QtCore import Qt, QThread

from src.gui.palette import PALETTE
from src.gui.worker  import ExtractWorker


class ExtractTab(QWidget):

    def __init__(self, extractor, parent=None):
        super().__init__(parent)
        self._extractor  = extractor
        self._image_path = None
        self._thread     = None
        self._worker     = None
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_controls())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {PALETTE['border']}; }}"
        )
        splitter.addWidget(self._build_image_pane())
        splitter.addWidget(self._build_output_pane())
        splitter.setSizes([420, 420])

        layout.addWidget(splitter, stretch=1)

    # ── Control bar ──────────────────────────────────────────────────

    def _build_controls(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ExtractControls")
        frame.setFixedHeight(54)
        frame.setStyleSheet(f"""
            QFrame#ExtractControls {{
                background:    {PALETTE["surface"]};
                border-bottom: 1px solid {PALETTE["border"]};
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self._select_btn = self._make_action_btn("▶  SELECT IMAGE", self._select_image)

        self._path_label = QLabel("No image selected")
        self._path_label.setStyleSheet(self._dim_label_style(11))
        self._path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._extract_btn = self._make_action_btn(
            "⬡  EXTRACT", self._run_extract, accent=True
        )
        self._extract_btn.setEnabled(False)

        layout.addWidget(self._select_btn)
        layout.addWidget(self._path_label, stretch=1)
        layout.addWidget(self._extract_btn)
        return frame

    # ── Image preview pane ───────────────────────────────────────────

    def _build_image_pane(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ExtractImagePane")
        frame.setStyleSheet(f"QFrame#ExtractImagePane {{ background: {PALETTE['bg']}; }}")
        frame.setMinimumWidth(180)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pane_header("IMAGE PREVIEW"))

        self._image_lbl = QLabel("SELECT AN IMAGE")
        self._image_lbl.setAlignment(Qt.AlignCenter)
        self._image_lbl.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      13px;
            letter-spacing: 3px;
        """)
        layout.addWidget(self._image_lbl, stretch=1)
        return frame

    # ── Output pane ──────────────────────────────────────────────────

    def _build_output_pane(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ExtractOutputPane")
        frame.setStyleSheet(f"QFrame#ExtractOutputPane {{ background: {PALETTE['surface']}; }}")
        frame.setMinimumWidth(180)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pane_header("EXTRACTED MESSAGE"))

        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setPlaceholderText("Extracted text will appear here…")
        self._output_edit.setStyleSheet(f"""
            QTextEdit {{
                background:  {PALETTE["surface"]};
                color:       {PALETTE["text_bright"]};
                border:      none;
                font-family: 'Courier New', monospace;
                font-size:   13px;
                padding:     16px;
            }}
            QScrollBar:vertical {{
                background:    {PALETTE["bg"]};
                width:         6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background:    {PALETTE["border_hi"]};
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        layout.addWidget(self._output_edit, stretch=1)

        # Status strip at bottom of output pane
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setFixedHeight(26)
        self._status_lbl.setObjectName("ExtractStatus")
        self._status_lbl.setStyleSheet(f"""
            QLabel#ExtractStatus {{
                background:     {PALETTE["bg"]};
                color:          {PALETTE["text_dim"]};
                font-family:    'Courier New', monospace;
                font-size:      10px;
                letter-spacing: 1px;
                padding:        0px 16px;
                border-top:     1px solid {PALETTE["border"]};
            }}
        """)
        layout.addWidget(self._status_lbl)
        return frame

    # ── Slot handlers ────────────────────────────────────────────────

    def _select_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Stego Image",
            filter="Images (*.png *.jpg *.jpeg *.bmp *.pgm)",
        )
        if not path:
            return
        self._image_path = path
        self._path_label.setText(os.path.basename(path))
        self._path_label.setStyleSheet(f"""
            color:       {PALETTE["text_bright"]};
            font-family: 'Courier New', monospace;
            font-size:   11px;
        """)
        self._extract_btn.setEnabled(True)
        self._output_edit.clear()
        self._set_status("Ready", PALETTE["text_dim"])
        self._load_preview(path)

    def _run_extract(self) -> None:
        if not self._image_path:
            return

        self._extract_btn.setEnabled(False)
        self._extract_btn.setText("◌  EXTRACTING…")
        self._output_edit.clear()
        self._set_status("Extracting…", PALETTE["text_dim"])

        self._thread = QThread()
        self._worker = ExtractWorker(self._extractor, self._image_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_extract_done)
        self._worker.error.connect(self._on_extract_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_extract_done(self, text: str) -> None:
        self._extract_btn.setEnabled(True)
        self._extract_btn.setText("⬡  EXTRACT")
        if text:
            self._output_edit.setPlainText(text)
            n = len(text)
            self._set_status(
                f"Extracted {n} character{'s' if n != 1 else ''}",
                PALETTE["green"],
            )
        else:
            self._output_edit.setPlaceholderText(
                "No hidden message found in this image."
            )
            self._set_status("No message detected", PALETTE["orange"])

    def _on_extract_error(self, msg: str) -> None:
        self._extract_btn.setEnabled(True)
        self._extract_btn.setText("⬡  EXTRACT")
        self._output_edit.setPlainText(f"Error: {msg}")
        self._set_status("Extraction failed", PALETTE["red"])

    # ── Helpers ──────────────────────────────────────────────────────

    def _load_preview(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._image_lbl.setText("CANNOT LOAD")
            return
        w = max(120, self._image_lbl.width()  - 16)
        h = max(120, self._image_lbl.height() - 16)
        self._image_lbl.setPixmap(
            pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._image_path:
            self._load_preview(self._image_path)

    def _set_status(self, text: str, color: str) -> None:
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(f"""
            QLabel#ExtractStatus {{
                background:     {PALETTE["bg"]};
                color:          {color};
                font-family:    'Courier New', monospace;
                font-size:      10px;
                letter-spacing: 1px;
                padding:        0px 16px;
                border-top:     1px solid {PALETTE["border"]};
            }}
        """)

    # ── Style helpers ────────────────────────────────────────────────

    @staticmethod
    def _pane_header(title: str) -> QWidget:
        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"""
            background:    {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      9px;
            letter-spacing: 2px;
        """)
        layout.addWidget(lbl)
        return header

    @staticmethod
    def _make_action_btn(text: str, callback, accent: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        if accent:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:     transparent;
                    color:          {PALETTE["accent"]};
                    border:         1px solid {PALETTE["accent"]};
                    border-radius:  4px;
                    font-family:    'Courier New', monospace;
                    font-size:      11px;
                    font-weight:    bold;
                    letter-spacing: 2px;
                    padding:        0px 16px;
                }}
                QPushButton:hover    {{ background: {PALETTE["accent_dim"]}; color: #fff; }}
                QPushButton:pressed  {{ background: {PALETTE["accent"]};     color: {PALETTE["bg"]}; }}
                QPushButton:disabled {{ color: {PALETTE["text_dim"]}; border-color: {PALETTE["border"]}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:    transparent;
                    color:         {PALETTE["text"]};
                    border:        1px solid {PALETTE["border_hi"]};
                    border-radius: 4px;
                    font-family:   'Courier New', monospace;
                    font-size:     11px;
                    letter-spacing:1px;
                    padding:       0px 14px;
                }}
                QPushButton:hover {{ background: {PALETTE["surface2"]}; border-color: {PALETTE["text_dim"]}; }}
            """)
        return btn

    @staticmethod
    def _dim_label_style(size: int) -> str:
        return f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   {size}px;
        """