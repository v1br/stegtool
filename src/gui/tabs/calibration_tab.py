"""
CalibrationTab — confidence calibration visualisation across payload sizes.

Shows how the model's probability score distributes across all scanned images
for each payload-size model (0.1 – 0.5 bpp).  Populated automatically from
the most recent DETECT scan results; no extra user input required.

Layout
──────
  ┌─ Info bar ─────────────────────────────────────────────────────────────────┐
  │  "Showing calibration data for N images from last scan"     [REFRESH]      │
  └────────────────────────────────────────────────────────────────────────────┘
  ┌─ Per-model strip (one row per bpp) ────────────────────────────────────────┐
  │  0.1 bpp  [distribution bar]  mean: 0.xx  stego: N  cover: N              │
  │  0.2 bpp  …                                                                │
  │  …                                                                          │
  └────────────────────────────────────────────────────────────────────────────┘
  ┌─ Final score distribution ─────────────────────────────────────────────────┐
  │  Histogram (20 bins) of aggregate probabilities colour-coded by label      │
  └────────────────────────────────────────────────────────────────────────────┘
  ┌─ Score vs payload heatmap ─────────────────────────────────────────────────┐
  │  Each row = one bpp model, each column = a probability bucket              │
  └────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import math
from collections import defaultdict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QScrollArea, QSizePolicy,
)
from PySide6.QtGui  import QPainter, QColor, QLinearGradient, QBrush, QFont
from PySide6.QtCore import Qt

from src.gui.palette   import PALETTE, label_fg
from src.gui.constants import Label


# ── Tiny painters ─────────────────────────────────────────────────────────────

class _DistBar(QWidget):
    """
    Horizontal segmented bar showing the distribution of scores for one model.
    Scores are bucketed into CLEAN / SUSPICIOUS / STEGO bands using the same
    thresholds as the detector (0.45 / 0.65).
    """
    _H = 18

    def __init__(self, probs: list[float], parent=None):
        super().__init__(parent)
        self._probs = probs
        self.setFixedHeight(self._H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        if not self._probs:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self._probs)

        clean      = sum(1 for v in self._probs if v <  0.45) / n
        suspicious = sum(1 for v in self._probs if 0.45 <= v < 0.65) / n
        stego      = sum(1 for v in self._probs if v >= 0.65) / n

        x = 0
        for frac, color in [
            (clean,      PALETTE["green"]),
            (suspicious, PALETTE["orange"]),
            (stego,      PALETTE["red"]),
        ]:
            bw = int(frac * w)
            if bw > 0:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(color))
                p.drawRect(x, 0, bw, h)
                x += bw

        # Threshold markers
        for threshold in (0.45, 0.65):
            tx = int(threshold * w)
            p.setPen(QColor(PALETTE["bg"]))
            p.drawLine(tx, 0, tx, h)


class _Histogram(QWidget):
    """
    20-bin histogram of final aggregate probability scores.
    Bars coloured by which detection band the bin centre falls in.
    """
    BINS    = 20
    LABEL_H = 16
    AXIS_H  = 18

    def __init__(self, probs: list[float], parent=None):
        super().__init__(parent)
        self._probs = probs
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        if not self._probs:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w   = self.width()
        h   = self.height()
        ch  = h - self.LABEL_H - self.AXIS_H   # chart height

        # Build bins
        counts = [0] * self.BINS
        for v in self._probs:
            idx = min(int(v * self.BINS), self.BINS - 1)
            counts[idx] += 1
        max_count = max(counts) or 1

        bar_w = w / self.BINS

        for i, count in enumerate(counts):
            bx    = int(i * bar_w)
            bw    = max(1, int(bar_w) - 1)
            bh    = int(count / max_count * ch)
            by    = self.LABEL_H + ch - bh
            mid   = (i + 0.5) / self.BINS   # bin centre

            if mid >= 0.65:
                color = PALETTE["red"]
            elif mid >= 0.45:
                color = PALETTE["orange"]
            else:
                color = PALETTE["green"]

            grad = QLinearGradient(bx, by, bx, by + bh)
            c    = QColor(color)
            cd   = QColor(color); cd.setAlpha(140)
            grad.setColorAt(0.0, c)
            grad.setColorAt(1.0, cd)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(bx, by, bw, bh, 2, 2)

            # Count label above bar
            if count > 0:
                p.setPen(QColor(color))
                f = QFont("Courier New"); f.setPointSize(7)
                p.setFont(f)
                p.drawText(bx, self.LABEL_H - 2, bw, 14,
                           Qt.AlignHCenter | Qt.AlignBottom, str(count))

        # X-axis tick labels
        p.setPen(QColor(PALETTE["text_dim"]))
        f = QFont("Courier New"); f.setPointSize(7)
        p.setFont(f)
        for tick in (0.0, 0.25, 0.45, 0.65, 0.75, 1.0):
            tx = int(tick * w)
            p.drawText(tx - 12, h - self.AXIS_H, 24, self.AXIS_H,
                       Qt.AlignHCenter | Qt.AlignVCenter, f"{tick:.2f}")

        # Threshold lines
        p.setPen(QColor(PALETTE["border_hi"]))
        for thr in (0.45, 0.65):
            tx = int(thr * w)
            p.drawLine(tx, self.LABEL_H, tx, self.LABEL_H + ch)


class _Heatmap(QWidget):
    """
    Rows = bpp models (0.1 – 0.5), Columns = 10 probability buckets.
    Cell colour intensity = mean count / row max.
    """
    BINS    = 10
    ROW_H   = 32
    LABEL_W = 52
    AXIS_H  = 18

    def __init__(self, results: list[dict], bpps: list[str], parent=None):
        super().__init__(parent)
        self._results = results
        self._bpps    = bpps
        n_rows = len(bpps)
        self.setFixedHeight(n_rows * self.ROW_H + self.AXIS_H + 8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        if not self._results or not self._bpps:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w  = self.width()
        cw = w - self.LABEL_W   # chart area width

        f = QFont("Courier New"); f.setPointSize(8)
        p.setFont(f)

        for row_i, bpp in enumerate(self._bpps):
            counts = [0] * self.BINS
            for r in self._results:
                prob = r.get("model_probabilities", {}).get(bpp, 0.0)
                idx  = min(int(prob * self.BINS), self.BINS - 1)
                counts[idx] += 1
            row_max = max(counts) or 1

            by = row_i * self.ROW_H

            # Row label
            p.setPen(QColor(PALETTE["text_dim"]))
            p.drawText(0, by, self.LABEL_W, self.ROW_H,
                       Qt.AlignVCenter | Qt.AlignRight, f"{bpp} bpp  ")

            cell_w = cw / self.BINS
            for col_i, count in enumerate(counts):
                cx    = self.LABEL_W + int(col_i * cell_w)
                cw_px = max(1, int(cell_w) - 1)
                alpha = int(255 * count / row_max)
                mid   = (col_i + 0.5) / self.BINS
                if mid >= 0.65:
                    base = QColor(PALETTE["red"])
                elif mid >= 0.45:
                    base = QColor(PALETTE["orange"])
                else:
                    base = QColor(PALETTE["green"])
                base.setAlpha(max(20, alpha))
                p.setPen(Qt.NoPen)
                p.setBrush(base)
                p.drawRoundedRect(cx, by + 4, cw_px, self.ROW_H - 8, 3, 3)

                # Count text
                if count > 0:
                    p.setPen(QColor(PALETTE["text_bright"]))
                    p.drawText(cx, by, cw_px, self.ROW_H,
                               Qt.AlignCenter, str(count))

        # X-axis labels
        y_axis = len(self._bpps) * self.ROW_H
        p.setPen(QColor(PALETTE["text_dim"]))
        cell_w = cw / self.BINS
        for i in range(self.BINS + 1):
            tx = self.LABEL_W + int(i * cell_w)
            p.drawText(tx - 12, y_axis, 24, self.AXIS_H,
                       Qt.AlignHCenter | Qt.AlignVCenter,
                       f"{i/self.BINS:.1f}")


# ── Section helper ────────────────────────────────────────────────────────────

def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("CalibSection")
    frame.setStyleSheet(f"""
        QFrame#CalibSection {{
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
        color: {PALETTE["accent"]}; font-family: 'Courier New', monospace;
        font-size: 10px; font-weight: bold; letter-spacing: 2px;
    """)
    layout.addWidget(hdr)
    return frame, layout


# ── Main widget ───────────────────────────────────────────────────────────────

class CalibrationTab(QWidget):
    """
    Reads results from the MainWindow's scan result list and renders
    calibration charts.  Call refresh(results) whenever the scan finishes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[dict] = []
        self._build_ui()

    # ── Public API ───────────────────────────────────────────────────

    def refresh(self, results: list[dict]) -> None:
        """Called by MainWindow after every completed scan."""
        self._results = results
        self._render()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_info_bar())

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
        """)

        self._container = QWidget()
        self._container.setStyleSheet(f"background: {PALETTE['bg']};")
        self._content   = QVBoxLayout(self._container)
        self._content.setContentsMargins(16, 16, 16, 16)
        self._content.setSpacing(14)

        self._placeholder = QLabel(
            "Run a scan on the  DETECT  tab first  —  charts will appear here automatically."
        )
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(f"""
            color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
            font-size: 12px; letter-spacing: 2px;
        """)
        self._content.addWidget(self._placeholder)
        self._content.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, stretch=1)

    def _build_info_bar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(46)
        bar.setObjectName("CalibBar")
        bar.setStyleSheet(f"""
            QFrame#CalibBar {{
                background: {PALETTE["surface"]};
                border-bottom: 1px solid {PALETTE["border"]};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self._info_lbl = QLabel("No scan data yet")
        self._info_lbl.setStyleSheet(f"""
            color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
            font-size: 10px; letter-spacing: 1px;
        """)

        # Legend dots
        legend = QWidget()
        legend.setStyleSheet("background: transparent;")
        leg_layout = QHBoxLayout(legend)
        leg_layout.setContentsMargins(0, 0, 0, 0)
        leg_layout.setSpacing(14)
        for color, text in [
            (PALETTE["green"],  "CLEAN  < 0.45"),
            (PALETTE["orange"], "SUSPICIOUS  0.45–0.65"),
            (PALETTE["red"],    "STEGO  ≥ 0.65"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                color: {color}; font-family: 'Courier New', monospace;
                font-size: 9px; letter-spacing: 1px; background: transparent;
            """)
            leg_layout.addWidget(dot)
            leg_layout.addWidget(lbl)

        layout.addWidget(self._info_lbl)
        layout.addStretch()
        layout.addWidget(legend)
        return bar

    # ── Rendering ────────────────────────────────────────────────────

    def _render(self) -> None:
        # Clear previous content
        while self._content.count():
            item = self._content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        results = self._results
        n = len(results)

        if not results:
            self._info_lbl.setText("No scan data yet")
            self._content.addWidget(self._placeholder)
            self._content.addStretch()
            return

        counts = {Label.STEGO: 0, Label.SUSPICIOUS: 0, Label.CLEAN: 0}
        for r in results:
            lbl = r.get("label", "")
            if lbl in counts:
                counts[lbl] += 1

        self._info_lbl.setText(
            f"{n} image{'s' if n != 1 else ''}  ·  "
            f"{counts[Label.STEGO]} stego  "
            f"{counts[Label.SUSPICIOUS]} suspicious  "
            f"{counts[Label.CLEAN]} clean"
        )

        bpps = sorted({
            bpp
            for r in results
            for bpp in r.get("model_probabilities", {})
        })

        # ── 1. Per-model distribution bars ────────────────────────────
        dist_sec, dist_layout = _section(
            "PER-MODEL SCORE DISTRIBUTION  —  proportion of images in each confidence band"
        )
        dist_layout.addWidget(self._build_legend_row())

        for bpp in bpps:
            probs = [
                r["model_probabilities"][bpp]
                for r in results
                if bpp in r.get("model_probabilities", {})
            ]
            if not probs:
                continue
            mean_p = sum(probs) / len(probs)
            n_stego = sum(1 for v in probs if v >= 0.65)
            n_clean = sum(1 for v in probs if v < 0.45)
            dist_layout.addWidget(
                self._dist_row(bpp, probs, mean_p, n_stego, n_clean, n)
            )

        self._content.addWidget(dist_sec)

        # ── 2. Final score histogram ───────────────────────────────────
        hist_sec, hist_layout = _section(
            "FINAL SCORE HISTOGRAM  —  distribution of aggregate detection probabilities"
        )
        final_probs = [r["probability"] for r in results]
        hist = _Histogram(final_probs)
        hist.setFixedHeight(160)
        hist_layout.addWidget(hist)
        self._content.addWidget(hist_sec)

        # ── 3. Score vs payload heatmap ───────────────────────────────
        heat_sec, heat_layout = _section(
            "SCORE vs PAYLOAD HEATMAP  —  image count per (model × probability bucket)"
        )
        heat = _Heatmap(results, bpps)
        heat_layout.addWidget(heat)
        note = QLabel(
            "Each cell shows how many images landed in that probability bucket for that "
            "payload-size model.  Ideally cover images cluster left; stego images cluster right."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"""
            color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
            font-size: 10px;
        """)
        heat_layout.addWidget(note)
        self._content.addWidget(heat_sec)

        self._content.addStretch()

    def _build_legend_row(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(0)

        for text, width in [("MODEL", 70), ("DISTRIBUTION", 200), ("MEAN", 70),
                             ("STEGO", 60), ("CLEAN", 60)]:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(f"""
                color: {PALETTE["text_dim"]}; font-family: 'Courier New', monospace;
                font-size: 9px; letter-spacing: 1.5px;
            """)
            layout.addWidget(lbl)
        layout.addStretch()
        return row

    def _dist_row(
        self, bpp: str, probs: list[float],
        mean_p: float, n_stego: int, n_clean: int, n_total: int,
    ) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)

        def _lbl(text, width, color=PALETTE["text_dim"], size=10):
            l = QLabel(text)
            l.setFixedWidth(width)
            l.setStyleSheet(f"""
                color: {color}; font-family: 'Courier New', monospace; font-size: {size}px;
            """)
            return l

        mean_color = (
            PALETTE["red"]    if mean_p >= 0.65 else
            PALETTE["orange"] if mean_p >= 0.45 else
            PALETTE["green"]
        )

        bar = _DistBar(probs)
        bar.setFixedWidth(200)

        layout.addWidget(_lbl(f"{bpp} bpp", 70, PALETTE["text"]))
        layout.addWidget(bar)
        layout.addWidget(_lbl(f"  {mean_p:.3f}", 70, mean_color))
        layout.addWidget(_lbl(f"  {n_stego}", 60, PALETTE["red"]))
        layout.addWidget(_lbl(f"  {n_clean}", 60, PALETTE["green"]))
        layout.addStretch()
        return row