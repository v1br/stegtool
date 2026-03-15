import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QFileDialog,
    QFrame, QSizePolicy,
)
from PySide6.QtGui  import QPixmap
from PySide6.QtCore import Qt, QThread

from src.gui.palette        import PALETTE, label_fg
from src.gui.worker         import EmbedWorker
from src.gui.widgets.badges import ProbBar


class EmbedTab(QWidget):

    def __init__(self, embedder, detector, parent=None):
        super().__init__(parent)
        self._embedder    = embedder
        self._detector    = detector
        self._image_path  = None
        self._stego_path  = None
        self._thread      = None
        self._worker      = None
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setObjectName("EmbedTabLayout")

        layout.addWidget(self._build_controls())

        # Comparison row — hidden until first embed
        self._comparison = self._build_comparison()
        self._comparison.hide()
        layout.addWidget(self._comparison, stretch=1)

        # Verdict strip — hidden until first embed
        self._verdict_frame = self._build_verdict_strip()
        self._verdict_frame.hide()
        layout.addWidget(self._verdict_frame)

        # Placeholder — visible until an image is selected
        self._placeholder = QLabel(
            "Select an image and enter a message  ·  then press  ⬡ EMBED"
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      12px;
            letter-spacing: 2px;
        """)
        layout.addWidget(self._placeholder, stretch=1)

    # ── Control bar ──────────────────────────────────────────────────

    def _build_controls(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("EmbedControls")
        frame.setStyleSheet(f"""
            QFrame#EmbedControls {{
                background:    {PALETTE["surface"]};
                border-bottom: 1px solid {PALETTE["border"]};
            }}
        """)

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(8)

        # ── Row 1: image path + payload selector + embed button ──
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self._select_btn = self._make_action_btn("▶  SELECT IMAGE", self._select_image)

        self._path_label = QLabel("No image selected")
        self._path_label.setStyleSheet(self._dim_label_style(11))
        self._path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._path_label.setMinimumWidth(0)

        payload_lbl = QLabel("PAYLOAD")
        payload_lbl.setStyleSheet(self._field_label_style())

        self._payload_combo = QComboBox()
        for v in ["0.1", "0.2", "0.3", "0.4", "0.5"]:
            self._payload_combo.addItem(f"{v} bpp", v)
        self._payload_combo.setCurrentIndex(2)          # default 0.3
        self._payload_combo.setFixedWidth(96)
        self._payload_combo.setStyleSheet(self._combo_style())

        self._embed_btn = self._make_action_btn("⬡  EMBED", self._run_embed, accent=True)
        self._embed_btn.setEnabled(False)

        row1.addWidget(self._select_btn)
        row1.addWidget(self._path_label, stretch=1)
        row1.addWidget(payload_lbl)
        row1.addWidget(self._payload_combo)
        row1.addWidget(self._embed_btn)

        # ── Row 2: text message input ──
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        msg_lbl = QLabel("MESSAGE")
        msg_lbl.setFixedWidth(72)
        msg_lbl.setStyleSheet(self._field_label_style())

        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Enter the text to embed…")
        self._text_input.setStyleSheet(self._input_style())
        self._text_input.textChanged.connect(self._update_embed_ready)

        row2.addWidget(msg_lbl)
        row2.addWidget(self._text_input, stretch=1)

        outer.addLayout(row1)
        outer.addLayout(row2)
        return frame

    # ── Side-by-side comparison ──────────────────────────────────────

    def _build_comparison(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("ComparisonWidget")
        widget.setStyleSheet(f"background: {PALETTE['bg']};")

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        orig_panel, self._orig_lbl  = self._make_image_panel("ORIGINAL")
        stego_panel, self._stego_lbl = self._make_image_panel("STEGO")

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet(
            f"background: {PALETTE['border']}; max-width: 1px; border: none;"
        )

        layout.addWidget(orig_panel,  stretch=1)
        layout.addWidget(divider)
        layout.addWidget(stego_panel, stretch=1)
        return widget

    def _make_image_panel(self, title: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setStyleSheet(f"background: {PALETTE['bg']};")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pane_header(title))

        img = QLabel("—")
        img.setAlignment(Qt.AlignCenter)
        img.setMinimumHeight(180)
        img.setStyleSheet(self._dim_label_style(12))
        layout.addWidget(img, stretch=1)

        return frame, img

    # ── Verdict strip ────────────────────────────────────────────────

    def _build_verdict_strip(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("VerdictStrip")
        frame.setFixedHeight(80)
        frame.setStyleSheet(f"""
            QFrame#VerdictStrip {{
                background: {PALETTE["surface"]};
                border-top: 1px solid {PALETTE["border"]};
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(24)

        # "MODEL VERDICT" label
        section_lbl = QLabel("MODEL VERDICT")
        section_lbl.setFixedWidth(100)
        section_lbl.setStyleSheet(self._field_label_style())

        # Main label + probability
        self._verdict_lbl = QLabel("—")
        self._verdict_lbl.setStyleSheet(f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   20px;
            font-weight: bold;
        """)
        self._verdict_prob_lbl = QLabel("")
        self._verdict_prob_lbl.setStyleSheet(self._dim_label_style(12))

        summary = QWidget()
        summary.setStyleSheet("background: transparent;")
        summary.setFixedWidth(180)
        s_layout = QHBoxLayout(summary)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(10)
        s_layout.addWidget(self._verdict_lbl)
        s_layout.addWidget(self._verdict_prob_lbl)
        s_layout.addStretch()

        # Per-model mini bars
        self._bars_widget = QWidget()
        self._bars_widget.setStyleSheet("background: transparent;")
        self._bars_layout = QHBoxLayout(self._bars_widget)
        self._bars_layout.setContentsMargins(0, 0, 0, 0)
        self._bars_layout.setSpacing(20)

        # Save button — hidden until a successful embed
        self._save_btn = self._make_action_btn("↓  SAVE IMAGE", self._save_image)
        self._save_btn.hide()

        layout.addWidget(section_lbl)
        layout.addWidget(summary)
        layout.addWidget(self._bars_widget, stretch=1)
        layout.addWidget(self._save_btn)
        return frame

    # ── Slot handlers ────────────────────────────────────────────────

    def _select_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image",
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
        self._update_embed_ready()
        # Show original image immediately
        self._comparison.show()
        self._placeholder.hide()
        self._load_into_label(path, self._orig_lbl)
        self._stego_lbl.setText("—")

    def _update_embed_ready(self) -> None:
        ready = bool(self._image_path and self._text_input.text().strip())
        self._embed_btn.setEnabled(ready)

    def _run_embed(self) -> None:
        text = self._text_input.text().strip()
        if not self._image_path or not text:
            return

        bpp = float(self._payload_combo.currentData())
        base, ext = os.path.splitext(self._image_path)
        self._stego_path = f"{base}_stego_{int(bpp * 10)}{ext or '.png'}"

        self._embed_btn.setEnabled(False)
        self._embed_btn.setText("◌  EMBEDDING…")
        self._verdict_frame.hide()
        self._save_btn.hide()

        self._thread = QThread()
        self._worker = EmbedWorker(
            self._embedder, self._detector,
            self._image_path, text, bpp, self._stego_path,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_embed_done)
        self._worker.error.connect(self._on_embed_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_embed_done(self, stego_path: str, result: object) -> None:
        self._embed_btn.setEnabled(True)
        self._embed_btn.setText("⬡  EMBED")
        self._load_into_label(stego_path, self._stego_lbl)
        if result:
            self._populate_verdict(result)
            self._save_btn.show()
            self._verdict_frame.show()

    def _on_embed_error(self, msg: str) -> None:
        self._embed_btn.setEnabled(True)
        self._embed_btn.setText("⬡  EMBED")
        self._save_btn.hide()
        self._verdict_lbl.setText("ERROR")
        self._verdict_lbl.setStyleSheet(f"""
            color:       {PALETTE["red"]};
            font-family: 'Courier New', monospace;
            font-size:   20px;
            font-weight: bold;
        """)
        self._verdict_prob_lbl.setText(msg)
        self._verdict_frame.show()

    def _save_image(self) -> None:
        if not self._stego_path or not os.path.exists(self._stego_path):
            return

        # Suggest the auto-generated stego filename as the default
        suggested = os.path.basename(self._stego_path)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Stego Image",
            suggested,
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp);;All Files (*)",
        )
        if not dest:
            return

        import shutil
        try:
            shutil.copy2(self._stego_path, dest)
        except Exception as exc:
            # Surface the error in the verdict prob label rather than a dialog
            self._verdict_prob_lbl.setText(f"Save failed: {exc}")

    # ── Verdict population ───────────────────────────────────────────

    def _populate_verdict(self, result: dict) -> None:
        label = result["label"]
        prob  = result["probability"]
        color = label_fg(label)

        self._verdict_lbl.setText(label)
        self._verdict_lbl.setStyleSheet(f"""
            color:       {color};
            font-family: 'Courier New', monospace;
            font-size:   20px;
            font-weight: bold;
        """)
        self._verdict_prob_lbl.setText(f"{prob:.4f}")

        # Rebuild per-model bars
        while self._bars_layout.count():
            item = self._bars_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for bpp, p in sorted(result.get("model_probabilities", {}).items()):
            col = QWidget()
            col.setStyleSheet("background: transparent;")
            col_layout = QVBoxLayout(col)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(3)

            bpp_lbl = QLabel(bpp)
            bpp_lbl.setAlignment(Qt.AlignCenter)
            bpp_lbl.setStyleSheet(self._dim_label_style(9))

            bar = ProbBar(p, label)
            bar.setFixedSize(52, 6)

            p_lbl = QLabel(f"{p:.2f}")
            p_lbl.setAlignment(Qt.AlignCenter)
            p_lbl.setStyleSheet(f"""
                color:       {PALETTE["text"]};
                font-family: 'Courier New', monospace;
                font-size:   9px;
            """)

            col_layout.addWidget(bpp_lbl)
            col_layout.addWidget(bar, alignment=Qt.AlignCenter)
            col_layout.addWidget(p_lbl)
            self._bars_layout.addWidget(col)

        self._bars_layout.addStretch()

    # ── Image helpers ────────────────────────────────────────────────

    @staticmethod
    def _load_into_label(path: str, label: QLabel) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            label.setText("CANNOT LOAD")
            return
        w = max(120, label.width()  - 16)
        h = max(120, label.height() - 16)
        label.setPixmap(
            pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def resizeEvent(self, event) -> None:
        """Re-scale cached images when the panel is resized."""
        super().resizeEvent(event)
        if self._image_path:
            self._load_into_label(self._image_path, self._orig_lbl)
        if self._stego_path and os.path.exists(self._stego_path):
            self._load_into_label(self._stego_path, self._stego_lbl)

    # ── Shared style builders ────────────────────────────────────────

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
    def _field_label_style() -> str:
        return f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      10px;
            letter-spacing: 1.5px;
        """

    @staticmethod
    def _dim_label_style(size: int) -> str:
        return f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   {size}px;
        """

    @staticmethod
    def _input_style() -> str:
        return f"""
            QLineEdit {{
                background:  {PALETTE["surface2"]};
                color:       {PALETTE["text_bright"]};
                border:      1px solid {PALETTE["border_hi"]};
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size:   12px;
                padding:     4px 10px;
            }}
            QLineEdit:focus {{ border-color: {PALETTE["accent"]}; }}
        """

    @staticmethod
    def _combo_style() -> str:
        return f"""
            QComboBox {{
                background:    {PALETTE["surface2"]};
                color:         {PALETTE["text"]};
                border:        1px solid {PALETTE["border_hi"]};
                border-radius: 4px;
                font-family:   'Courier New', monospace;
                font-size:     11px;
                padding:       2px 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background:              {PALETTE["surface2"]};
                color:                   {PALETTE["text"]};
                selection-background-color: {PALETTE["accent_dim"]};
                border: 1px solid {PALETTE["border"]};
            }}
        """