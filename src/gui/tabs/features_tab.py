import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QFrame, QSizePolicy,
    QScrollArea,
)
from PySide6.QtGui  import QPainter, QColor, QLinearGradient, QBrush
from PySide6.QtCore import Qt, QThread, QRectF

from src.gui.palette import PALETTE, label_fg
from src.gui.worker  import AnalysisWorker


# ── Tiny custom bar chart widget ─────────────────────────────────────────────

class GroupedBarChart(QWidget):
    """
    Draws a grouped bar chart for N named metrics, up to 2 series (cover/stego).
    Each value is normalised to [0, 1] within its metric for display height,
    but the raw value is shown as a label above the bar.
    """

    BAR_W     = 38
    GROUP_GAP = 18
    BAR_GAP   = 4
    LABEL_H   = 36    # space above bars for value text
    AXIS_H    = 22    # space below bars for metric name

    COVER_COLOR = PALETTE["accent"]       # cyan
    STEGO_COLOR = PALETTE["orange"]       # orange

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title   = title
        self._names:  list[str]  = []
        self._cover:  list[float] = []
        self._stego:  list[float] = []
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(
        self,
        names:  list[str],
        cover:  list[float],
        stego:  list[float] | None = None,
    ) -> None:
        self._names = names
        self._cover = cover
        self._stego = stego or []
        n = len(names)
        bars_per_group = 2 if stego else 1
        total_w = n * (bars_per_group * self.BAR_W + (bars_per_group - 1) * self.BAR_GAP + self.GROUP_GAP)
        self.setFixedWidth(max(300, total_w + 60))
        self.update()

    def paintEvent(self, _event) -> None:
        if not self._names:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        chart_h = h - self.LABEL_H - self.AXIS_H
        has_stego = bool(self._stego)
        bars_per_group = 2 if has_stego else 1
        n = len(self._names)

        group_w = bars_per_group * self.BAR_W + (bars_per_group - 1) * self.BAR_GAP
        total_w = n * group_w + (n - 1) * self.GROUP_GAP
        x_start = (w - total_w) // 2

        for i, name in enumerate(self._names):
            gx = x_start + i * (group_w + self.GROUP_GAP)

            # Normalise per-group so each metric fills its own height range.
            # This makes small cover-vs-stego differences visible.
            group_vals = [self._cover[i]]
            if has_stego and i < len(self._stego):
                group_vals.append(self._stego[i])
            group_max = max(abs(v) for v in group_vals) or 1.0

            for j, (val, color) in enumerate(
                [(self._cover[i], self.COVER_COLOR)]
                + ([(self._stego[i], self.STEGO_COLOR)] if has_stego else [])
            ):
                bx = gx + j * (self.BAR_W + self.BAR_GAP)
                bar_h = max(2, int(abs(val) / group_max * chart_h))
                by    = self.LABEL_H + chart_h - bar_h

                # Bar fill with gradient
                grad = QLinearGradient(bx, by, bx, by + bar_h)
                c = QColor(color)
                c_dim = QColor(color)
                c_dim.setAlpha(120)
                grad.setColorAt(0.0, c)
                grad.setColorAt(1.0, c_dim)
                p.setBrush(QBrush(grad))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(bx, by, self.BAR_W, bar_h, 3, 3)

                # Value label above bar
                p.setPen(QColor(color))
                p.setFont(self._small_font(8))
                label = self._fmt(val)
                p.drawText(
                    bx, self.LABEL_H - 18, self.BAR_W, 16,
                    Qt.AlignHCenter | Qt.AlignBottom,
                    label,
                )

            # Metric name below group
            p.setPen(QColor(PALETTE["text_dim"]))
            p.setFont(self._small_font(9))
            p.drawText(
                gx, h - self.AXIS_H, group_w, self.AXIS_H,
                Qt.AlignHCenter | Qt.AlignVCenter,
                name,
            )

    @staticmethod
    def _fmt(v: float) -> str:
        if abs(v) >= 100:
            return f"{v:.0f}"
        if abs(v) >= 1:
            return f"{v:.3f}"
        return f"{v:.4f}"

    @staticmethod
    def _small_font(size: int):
        from PySide6.QtGui import QFont
        f = QFont("Courier New")
        f.setPointSize(size)
        return f


# ── Section frame helper ──────────────────────────────────────────────────────

def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("FeatureSection")
    frame.setStyleSheet(f"""
        QFrame#FeatureSection {{
            background:    {PALETTE["surface"]};
            border:        1px solid {PALETTE["border"]};
            border-radius: 6px;
        }}
    """)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 16)
    layout.setSpacing(10)

    hdr = QLabel(title)
    hdr.setStyleSheet(f"""
        color:          {PALETTE["accent"]};
        font-family:    'Courier New', monospace;
        font-size:      10px;
        font-weight:    bold;
        letter-spacing: 2px;
    """)
    layout.addWidget(hdr)
    return frame, layout


# ── Main tab ──────────────────────────────────────────────────────────────────

class FeaturesTab(QWidget):

    def __init__(self, detector, parent=None):
        super().__init__(parent)
        self._detector    = detector
        self._cover_path  = None
        self._stego_path  = None
        self._thread      = None
        self._worker      = None
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_controls())

        # Legend strip
        layout.addWidget(self._build_legend())

        # Scrollable chart area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {PALETTE["bg"]}; border: none; }}
            QScrollBar:vertical {{
                background: {PALETTE["bg"]}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {PALETTE["border_hi"]}; border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar:horizontal {{
                background: {PALETTE["bg"]}; height: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:horizontal {{
                background: {PALETTE["border_hi"]}; border-radius: 3px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        """)

        self._charts_container = QWidget()
        self._charts_container.setStyleSheet(f"background: {PALETTE['bg']};")
        self._charts_layout = QVBoxLayout(self._charts_container)
        self._charts_layout.setContentsMargins(16, 16, 16, 16)
        self._charts_layout.setSpacing(14)

        self._placeholder = QLabel(
            "Select a cover image  ·  optionally a stego image  ·  then press  ⬡ ANALYSE"
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      12px;
            letter-spacing: 2px;
        """)
        self._charts_layout.addWidget(self._placeholder, stretch=1)
        self._charts_layout.addStretch()

        self._scroll.setWidget(self._charts_container)
        layout.addWidget(self._scroll, stretch=1)

    # ── Control bar ──────────────────────────────────────────────────

    def _build_controls(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("FeaturesControls")
        frame.setFixedHeight(54)
        frame.setStyleSheet(f"""
            QFrame#FeaturesControls {{
                background:    {PALETTE["surface"]};
                border-bottom: 1px solid {PALETTE["border"]};
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        # Cover image
        cover_lbl = QLabel("COVER")
        cover_lbl.setFixedWidth(46)
        cover_lbl.setStyleSheet(self._field_label_style())

        self._cover_btn = self._make_btn("▶  SELECT", lambda: self._pick("cover"))

        self._cover_path_lbl = QLabel("No image selected")
        self._cover_path_lbl.setStyleSheet(self._dim_style(11))
        self._cover_path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Stego image (optional)
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet(f"background: {PALETTE['border']}; max-width:1px; border:none;")

        stego_lbl = QLabel("STEGO")
        stego_lbl.setFixedWidth(46)
        stego_lbl.setStyleSheet(self._field_label_style())

        self._stego_btn = self._make_btn("▶  SELECT", lambda: self._pick("stego"))

        self._stego_path_lbl = QLabel("Optional — compare with cover")
        self._stego_path_lbl.setStyleSheet(self._dim_style(11))
        self._stego_path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Analyse button
        self._analyse_btn = self._make_btn("⬡  ANALYSE", self._run_analysis, accent=True)
        self._analyse_btn.setEnabled(False)

        layout.addWidget(cover_lbl)
        layout.addWidget(self._cover_btn)
        layout.addWidget(self._cover_path_lbl, stretch=1)
        layout.addWidget(div)
        layout.addWidget(stego_lbl)
        layout.addWidget(self._stego_btn)
        layout.addWidget(self._stego_path_lbl, stretch=1)
        layout.addWidget(self._analyse_btn)
        return frame

    def _build_legend(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(28)
        bar.setStyleSheet(f"""
            background:    {PALETTE["surface2"]};
            border-bottom: 1px solid {PALETTE["border"]};
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(18)
        layout.addStretch()

        for color, text in [
            (GroupedBarChart.COVER_COLOR, "COVER IMAGE"),
            (GroupedBarChart.STEGO_COLOR, "STEGO IMAGE"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px;")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                color:          {color};
                font-family:    'Courier New', monospace;
                font-size:      9px;
                letter-spacing: 1.5px;
            """)
            layout.addWidget(dot)
            layout.addWidget(lbl)

        layout.addStretch()
        return bar

    # ── Slot handlers ────────────────────────────────────────────────

    def _pick(self, role: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {role.title()} Image",
            filter="Images (*.png *.jpg *.jpeg *.bmp *.pgm)",
        )
        if not path:
            return
        import os
        name = os.path.basename(path)
        if role == "cover":
            self._cover_path = path
            self._cover_path_lbl.setText(name)
            self._cover_path_lbl.setStyleSheet(f"""
                color: {PALETTE["text_bright"]}; font-family: 'Courier New', monospace; font-size: 11px;
            """)
        else:
            self._stego_path = path
            self._stego_path_lbl.setText(name)
            self._stego_path_lbl.setStyleSheet(f"""
                color: {PALETTE["orange"]}; font-family: 'Courier New', monospace; font-size: 11px;
            """)
        self._analyse_btn.setEnabled(bool(self._cover_path))

    def _run_analysis(self) -> None:
        if not self._cover_path:
            return
        self._analyse_btn.setEnabled(False)
        self._analyse_btn.setText("◌  ANALYSING…")
        self._clear_charts()

        self._thread = QThread()
        self._worker = AnalysisWorker(
            self._detector, self._cover_path, self._stego_path
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_analysis_done(self, cover: dict, stego) -> None:
        self._analyse_btn.setEnabled(True)
        self._analyse_btn.setText("⬡  ANALYSE")
        if cover:
            self._render_charts(cover, stego)

    def _on_analysis_error(self, msg: str) -> None:
        self._analyse_btn.setEnabled(True)
        self._analyse_btn.setText("⬡  ANALYSE")
        self._placeholder.setText(f"Error: {msg}")
        self._clear_charts()   # ensures placeholder is back in layout

    # ── Chart rendering ──────────────────────────────────────────────

    def _render_charts(self, cover: dict, stego) -> None:
        # Remove placeholder and any stretch left from _clear_charts
        while self._charts_layout.count():
            item = self._charts_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._placeholder:
                w.deleteLater()
        self._placeholder.hide()

        has_stego = stego is not None

        # ── GLCM ──────────────────────────────────────────────────────
        glcm_names  = ["Contrast", "Correlation", "Energy", "Homogeneity"]
        cover_glcm  = list(cover["glcm"])
        stego_glcm  = list(stego["glcm"]) if has_stego else None

        sec, sec_layout = _section("GLCM FEATURES  —  Gray-Level Co-occurrence Matrix")
        chart = GroupedBarChart("GLCM")
        chart.set_data(glcm_names, cover_glcm, stego_glcm)
        sec_layout.addWidget(chart, alignment=Qt.AlignLeft)
        self._charts_layout.addWidget(sec)

        # ── LSB Entropy ───────────────────────────────────────────────
        ent_sec, ent_layout = _section("LSB ENTROPY  —  Bit-plane randomness (0 = ordered, 1 = random)")
        ent_chart = GroupedBarChart("Entropy")
        ent_chart.set_data(
            ["LSB Entropy"],
            [cover["entropy"]],
            [stego["entropy"]] if has_stego else None,
        )
        ent_chart.setFixedWidth(160)
        ent_layout.addWidget(ent_chart, alignment=Qt.AlignLeft)
        self._charts_layout.addWidget(ent_sec)

        # ── SPAM entropy + std dev ────────────────────────────────────
        # The 196 SPAM values are 4 sub-matrices of 49 transition probabilities.
        # mean() is always ≈1/49 (constant) — use entropy and std dev instead,
        # both of which change measurably with LSB embedding.

        def _spam_entropy(chunk: np.ndarray) -> float:
            """Shannon entropy of a transition probability sub-matrix."""
            p = chunk + 1e-12
            p = p / p.sum()
            return float(-np.sum(p * np.log2(p)))

        def _spam_std(chunk: np.ndarray) -> float:
            """Standard deviation — how peaked vs flat the distribution is."""
            return float(chunk.std())

        direction_labels = ["Horizontal", "Vertical", "Diagonal↘", "Diagonal↗"]

        cover_spam   = np.array(cover["spam"])
        cover_chunks = np.array_split(cover_spam, 4)
        cover_ent    = [_spam_entropy(c) for c in cover_chunks]
        cover_std    = [_spam_std(c)     for c in cover_chunks]

        stego_ent = stego_std = None
        if has_stego:
            stego_spam   = np.array(stego["spam"])
            stego_chunks = np.array_split(stego_spam, 4)
            stego_ent    = [_spam_entropy(c) for c in stego_chunks]
            stego_std    = [_spam_std(c)     for c in stego_chunks]

        spam_sec, spam_layout = _section(
            "SPAM FEATURES  —  Sub-pixel Adjacency Matrix per direction"
        )

        # Entropy sub-chart
        ent_hdr = QLabel("TRANSITION ENTROPY  (bits)  —  higher = flatter distribution = more randomness")
        ent_hdr.setStyleSheet(f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   10px;
            font-weight: bold;
        """)
        spam_layout.addWidget(ent_hdr)

        spam_ent_chart = GroupedBarChart("SPAM-Entropy")
        spam_ent_chart.set_data(direction_labels, cover_ent, stego_ent)
        spam_layout.addWidget(spam_ent_chart, alignment=Qt.AlignLeft)

        # Std dev sub-chart
        std_hdr = QLabel("TRANSITION STD DEV  —  lower = flatter = less inter-pixel correlation")
        std_hdr.setStyleSheet(f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   10px;
            font-weight: bold;
            margin-top:  6px;
        """)
        spam_layout.addWidget(std_hdr)

        spam_std_chart = GroupedBarChart("SPAM-Std")
        spam_std_chart.set_data(direction_labels, cover_std, stego_std)
        spam_layout.addWidget(spam_std_chart, alignment=Qt.AlignLeft)

        note = QLabel(
            "LSB embedding randomises pixel differences, flattening the transition "
            "distribution — entropy rises toward the maximum (5.61 bits for 49 bins) "
            "and std dev falls toward zero.  Cover images have peaked distributions "
            "(low entropy, high std dev); 0.5 bpp stego images approach uniformity."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"""
            color:       {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size:   10px;
        """)
        spam_layout.addWidget(note)
        self._charts_layout.addWidget(spam_sec)

        # ── Detection scores ──────────────────────────────────────────
        det_sec, det_layout = _section("DETECTION SCORES  —  Per-payload-size model probability")
        det_layout.addWidget(self._build_score_rows(cover, stego))
        self._charts_layout.addWidget(det_sec)

        self._charts_layout.addStretch()

    def _build_score_rows(self, cover: dict, stego) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        bpps = sorted(cover.get("model_probabilities", {}).keys())

        # Header row
        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(0, 0, 0, 4)
        hdr_layout.setSpacing(0)
        for text, width in [("MODEL", 70), ("COVER", 160), ("", 50), ("STEGO", 160), ("", 50)]:
            l = QLabel(text)
            l.setFixedWidth(width)
            l.setStyleSheet(f"""
                color:          {PALETTE["text_dim"]};
                font-family:    'Courier New', monospace;
                font-size:      9px;
                letter-spacing: 1.5px;
            """)
            hdr_layout.addWidget(l)
        hdr_layout.addStretch()
        layout.addWidget(hdr)

        for bpp in bpps:
            c_prob = cover["model_probabilities"].get(bpp, 0.0)
            s_prob = stego["model_probabilities"].get(bpp, 0.0) if stego else None
            layout.addWidget(self._score_row(bpp, c_prob, s_prob))

        # Final aggregated score
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            f"background: {PALETTE['border']}; max-height: 1px; border: none;"
        )
        layout.addWidget(line)
        layout.addWidget(self._score_row(
            "FINAL",
            cover["probability"],
            stego["probability"] if stego else None,
            bold=True,
        ))
        return container

    def _score_row(
        self, label: str, c_prob: float, s_prob: float | None, bold: bool = False
    ) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        def _lbl(text, width, color=PALETTE["text_dim"], size=10):
            l = QLabel(text)
            l.setFixedWidth(width)
            l.setStyleSheet(f"""
                color:       {color};
                font-family: 'Courier New', monospace;
                font-size:   {size}px;
                {'font-weight: bold;' if bold else ''}
            """)
            return l

        layout.addWidget(_lbl(label, 70, PALETTE["text"]))
        layout.addWidget(self._mini_bar(c_prob, GroupedBarChart.COVER_COLOR, 140))
        layout.addWidget(_lbl(f"  {c_prob:.3f}", 50, GroupedBarChart.COVER_COLOR))

        if s_prob is not None:
            layout.addWidget(self._mini_bar(s_prob, GroupedBarChart.STEGO_COLOR, 140))
            layout.addWidget(_lbl(f"  {s_prob:.3f}", 50, GroupedBarChart.STEGO_COLOR))

        layout.addStretch()
        return row

    @staticmethod
    def _mini_bar(prob: float, color: str, width: int = 140) -> QWidget:

        class _Bar(QWidget):
            def __init__(self, p, c, w):
                super().__init__()
                self._prob  = p
                self._color = c
                self.setFixedSize(w, 10)

            def paintEvent(self, _):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(PALETTE["border"]))
                painter.drawRoundedRect(0, 2, self.width(), 6, 3, 3)
                fw = int(self._prob * self.width())
                if fw > 0:
                    painter.setBrush(QColor(self._color))
                    painter.drawRoundedRect(0, 2, fw, 6, 3, 3)

        return _Bar(prob, color, width)

    # ── Helpers ──────────────────────────────────────────────────────

    def _clear_charts(self) -> None:
        """Remove all chart sections, leaving the placeholder in place."""
        while self._charts_layout.count():
            item = self._charts_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._placeholder:
                w.deleteLater()
        # Placeholder back on top, visible, no stretch yet
        self._charts_layout.addWidget(self._placeholder)
        self._placeholder.show()

    @staticmethod
    def _make_btn(text: str, callback, accent: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        if accent:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {PALETTE["accent"]};
                    border: 1px solid {PALETTE["accent"]}; border-radius: 4px;
                    font-family: 'Courier New', monospace; font-size: 11px;
                    font-weight: bold; letter-spacing: 2px; padding: 0px 16px;
                }}
                QPushButton:hover   {{ background: {PALETTE["accent_dim"]}; color: #fff; }}
                QPushButton:pressed {{ background: {PALETTE["accent"]}; color: {PALETTE["bg"]}; }}
                QPushButton:disabled {{ color: {PALETTE["text_dim"]}; border-color: {PALETTE["border"]}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {PALETTE["text"]};
                    border: 1px solid {PALETTE["border_hi"]}; border-radius: 4px;
                    font-family: 'Courier New', monospace; font-size: 11px;
                    letter-spacing: 1px; padding: 0px 14px;
                }}
                QPushButton:hover {{ background: {PALETTE["surface2"]}; border-color: {PALETTE["text_dim"]}; }}
            """)
        return btn

    @staticmethod
    def _field_label_style() -> str:
        return f"""
            color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
            font-size: 10px; letter-spacing: 1.5px;
        """

    @staticmethod
    def _dim_style(size: int) -> str:
        return f"""
            color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
            font-size: {size}px;
        """