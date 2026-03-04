from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QSplitter,
    QFrame,
    QScrollArea,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QStatusBar,
)
from PySide6.QtGui import (
    QColor,
    QPixmap,
    QFont,
    QPainter,
    QPen,
    QLinearGradient,
    QBrush,
    QPalette,
    QIcon,
)
from PySide6.QtCore import (
    QObject,
    Signal,
    QThread,
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QSize,
)

import sys
import os
import math

from src.detector import SteganalysisTool


# ─────────────────────────────────────────────
#  Color palette
# ─────────────────────────────────────────────

PALETTE = {
    "bg":          "#0d0f14",
    "surface":     "#141720",
    "surface2":    "#1c2030",
    "border":      "#252a3a",
    "border_hi":   "#2e3550",
    "text":        "#c8d0e8",
    "text_dim":    "#5a6280",
    "text_bright": "#edf0ff",
    "accent":      "#00d4ff",
    "accent_dim":  "#005566",
    "green":       "#00e5a0",
    "green_dim":   "#003d2b",
    "orange":      "#ff9500",
    "orange_dim":  "#3d2400",
    "red":         "#ff3b5c",
    "red_dim":     "#3d0013",
}


# ─────────────────────────────────────────────
#  Animated scan line widget (decorative)
# ─────────────────────────────────────────────

class ScanLineWidget(QWidget):
    """Animated horizontal scan line shown while processing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self._pos = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._active = True
        self._pos = 0.0
        self._timer.start(16)
        self.show()

    def stop(self):
        self._active = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._pos = (self._pos + 0.012) % 1.0
        self.update()

    def paintEvent(self, event):
        if not self._active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        center = int(self._pos * w)
        grad = QLinearGradient(max(0, center - 120), 0, min(w, center + 120), 0)
        grad.setColorAt(0.0,   QColor(0, 212, 255, 0))
        grad.setColorAt(0.4,   QColor(0, 212, 255, 180))
        grad.setColorAt(0.5,   QColor(200, 240, 255, 255))
        grad.setColorAt(0.6,   QColor(0, 212, 255, 180))
        grad.setColorAt(1.0,   QColor(0, 212, 255, 0))
        p.fillRect(0, 0, w, 2, QBrush(grad))


# ─────────────────────────────────────────────
#  Threat badge
# ─────────────────────────────────────────────

class ThreatBadge(QLabel):
    COLORS = {
        "STEGO":      (PALETTE["red"],    PALETTE["red_dim"],    "STEGO"),
        "SUSPICIOUS": (PALETTE["orange"], PALETTE["orange_dim"], "SUSPICIOUS"),
        "CLEAN":      (PALETTE["green"],  PALETTE["green_dim"],  "CLEAN"),
    }

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        fg, bg, text = self.COLORS.get(label, (PALETTE["text_dim"], PALETTE["surface"], label))
        self.setText(text)
        self.setFixedHeight(20)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border: 1px solid {fg};
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 8px;
                font-weight: bold;
                padding: 1px 7px;
                letter-spacing: 1.5px;
            }}
        """)


# ─────────────────────────────────────────────
#  Probability bar (mini inline bar)
# ─────────────────────────────────────────────

class ProbBar(QWidget):
    def __init__(self, prob: float, label: str, parent=None):
        super().__init__(parent)
        self._prob = prob
        self._label = label
        self.setFixedSize(80, 8)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PALETTE["border"]))
        p.drawRoundedRect(0, 0, w, h, 4, 4)

        # Fill
        fill_w = int(self._prob * w)
        if fill_w > 0:
            if self._label == "STEGO":
                color = QColor(PALETTE["red"])
            elif self._label == "SUSPICIOUS":
                color = QColor(PALETTE["orange"])
            else:
                color = QColor(PALETTE["green"])
            p.setBrush(color)
            p.drawRoundedRect(0, 0, fill_w, h, 4, 4)


# ─────────────────────────────────────────────
#  Result row widget (used inside QListWidget)
# ─────────────────────────────────────────────

class ResultRowWidget(QWidget):
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ResultRow")

        label    = result["label"]
        prob     = result["probability"]
        filename = os.path.basename(result["file"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Thumbnail
        thumb = QLabel()
        pix = QPixmap(result["file"])

        if not pix.isNull():
            pix = pix.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        thumb.setPixmap(pix)
        thumb.setFixedSize(26,26)

        layout.addWidget(thumb)

        # Threat badge
        badge = ThreatBadge(label)
        badge.setFixedWidth(82)
        layout.addWidget(badge)

        # Filename
        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet(f"""
            color: {PALETTE["text_bright"]};
            font-family: 'Courier New', monospace;
            font-size: 12px;
        """)
        name_lbl.setMinimumWidth(0)
        name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        name_lbl.setElideMode = lambda: None  # handled by label width
        layout.addWidget(name_lbl, stretch=1)

        # Prob bar + text
        bar = ProbBar(prob, label)
        layout.addWidget(bar)

        pct_lbl = QLabel(f"{prob * 100:5.1f}%")
        pct_lbl.setFixedWidth(44)
        pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if label == "STEGO":
            pct_color = PALETTE["red"]
        elif label == "SUSPICIOUS":
            pct_color = PALETTE["orange"]
        else:
            pct_color = PALETTE["green"]

        pct_lbl.setStyleSheet(f"""
            color: {pct_color};
            font-family: 'Courier New', monospace;
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(pct_lbl)

        self.setStyleSheet(f"""
            QWidget#ResultRow {{
                background: transparent;
                border-bottom: 1px solid {PALETTE["border"]};
            }}
            QWidget#ResultRow:hover {{
                background: {PALETTE["surface2"]};
            }}
        """)


# ─────────────────────────────────────────────
#  Stat tile (summary cards)
# ─────────────────────────────────────────────

class StatTile(QFrame):
    def __init__(self, title: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatTile")
        self.setFixedHeight(62)

        self._accent = accent
        self._value_lbl = QLabel(value)
        self._title_lbl = QLabel(title)

        self._value_lbl.setStyleSheet(f"""
            color: {accent};
            font-family: 'Courier New', monospace;
            font-size: 22px;
            font-weight: bold;
        """)
        self._title_lbl.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 10px;
            letter-spacing: 1.5px;
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 8, 14, 8)
        v.setSpacing(2)
        v.addWidget(self._value_lbl)
        v.addWidget(self._title_lbl)

        self.setStyleSheet(f"""
            QFrame#StatTile {{
                background: {PALETTE["surface"]};
                border: 1px solid {PALETTE["border"]};
                border-top: 2px solid {accent};
                border-radius: 6px;
            }}
        """)

    def set_value(self, v: str):
        self._value_lbl.setText(v)


# ─────────────────────────────────────────────
#  Detail panel widget
# ─────────────────────────────────────────────

class DetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Vertical splitter: image on top, details below ──
        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setHandleWidth(4)
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {PALETTE["border"]};
            }}
            QSplitter::handle:hover {{
                background: {PALETTE["accent"]};
            }}
        """)

        # ── Image preview pane ──
        self.image_frame = QFrame()
        self.image_frame.setObjectName("ImageFrame")
        self.image_frame.setMinimumHeight(80)
        self.image_frame.setStyleSheet(f"""
            QFrame#ImageFrame {{
                background: {PALETTE["bg"]};
            }}
        """)
        img_layout = QVBoxLayout(self.image_frame)
        img_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel("SELECT AN IMAGE")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 13px;
            letter-spacing: 3px;
        """)
        img_layout.addWidget(self.image_label)
        self._splitter.addWidget(self.image_frame)

        # ── Scroll area for details ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(60)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {PALETTE["surface"]}; border: none; }}
            QScrollBar:vertical {{
                background: {PALETTE["bg"]};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {PALETTE["border_hi"]};
                border-radius: 3px;
            }}
        """)

        self.details_widget = QWidget()
        self.details_widget.setStyleSheet(f"background: {PALETTE['surface']};")
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setContentsMargins(20, 18, 20, 18)
        self.details_layout.setSpacing(12)
        self.details_layout.addStretch()

        scroll.setWidget(self.details_widget)
        self._splitter.addWidget(scroll)

        # Start with a 55/45 split
        self._splitter.setSizes([300, 260])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        layout.addWidget(self._splitter)

    def _section(self, label: str, value: str, value_color: str = None):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        lbl = QLabel(label.upper())
        lbl.setFixedWidth(140)
        lbl.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 10px;
            letter-spacing: 1.5px;
        """)

        val = QLabel(value)
        vc = value_color or PALETTE["text_bright"]
        val.setStyleSheet(f"""
            color: {vc};
            font-family: 'Courier New', monospace;
            font-size: 13px;
            font-weight: bold;
        """)
        val.setWordWrap(True)

        h.addWidget(lbl)
        h.addWidget(val, stretch=1)
        return row

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: {PALETTE['border']}; max-height: 1px; border: none;")
        return line

    def show_result(self, result: dict):
        # Clear old widgets
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        label = result["label"]
        prob  = result["probability"]

        # Label color
        if label == "STEGO":
            lc = PALETTE["red"]
        elif label == "SUSPICIOUS":
            lc = PALETTE["orange"]
        else:
            lc = PALETTE["green"]

        self.details_layout.addWidget(self._section("Prediction",   label,            lc))
        self.details_layout.addWidget(self._section("Probability",  f"{prob:.4f}",     lc))
        self.details_layout.addWidget(self._section("Filename",     os.path.basename(result["file"]), PALETTE["text"]))
        self.details_layout.addWidget(self._divider())

        if "estimated_payload" in result:
            self.details_layout.addWidget(
                self._section("Est. Payload", f"{result['estimated_payload']} bpp")
            )

        if "consensus" in result:
            self.details_layout.addWidget(
                self._section("Model Consensus", str(result["consensus"]))
            )

        if "model_probabilities" in result:
            self.details_layout.addWidget(self._divider())
            hdr = QLabel("MODEL RESPONSES")
            hdr.setStyleSheet(f"""
                color: {PALETTE["accent"]};
                font-family: 'Courier New', monospace;
                font-size: 10px;
                letter-spacing: 2px;
                font-weight: bold;
            """)
            self.details_layout.addWidget(hdr)

            for bpp, p in sorted(result["model_probabilities"].items()):
                row = QWidget()
                row.setStyleSheet("background: transparent;")
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 2, 0, 2)
                h.setSpacing(12)

                bpp_lbl = QLabel(f"{bpp} bpp")
                bpp_lbl.setFixedWidth(60)
                bpp_lbl.setStyleSheet(f"""
                    color: {PALETTE["text_dim"]};
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                """)

                bar = ProbBar(p, label)
                bar.setFixedSize(120, 6)

                p_lbl = QLabel(f"{p:.3f}")
                p_lbl.setStyleSheet(f"""
                    color: {PALETTE["text"]};
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                """)

                h.addWidget(bpp_lbl)
                h.addWidget(bar)
                h.addWidget(p_lbl)
                h.addStretch()
                self.details_layout.addWidget(row)

        self.details_layout.addStretch()

    def show_image(self, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            h = max(80, self.image_frame.height() - 16)
            w = max(80, self.image_frame.width() - 16)
            scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("CANNOT LOAD IMAGE")

    def clear(self):
        self.image_label.setText("SELECT AN IMAGE")
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.details_layout.addStretch()


# ─────────────────────────────────────────────
#  Worker
# ─────────────────────────────────────────────

class ScanWorker(QObject):
    finished = Signal(list)
    progress = Signal(int, int)

    def __init__(self, detector, folder):
        super().__init__()
        self.detector = detector
        self.folder   = folder

    def run(self):
        files  = sorted(os.listdir(self.folder))
        images = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".pgm"))]
        results, total = [], len(images)

        for i, file in enumerate(images, start=1):
            path   = os.path.join(self.folder, file)
            result = self.detector.analyze_image(path)
            if result:
                results.append(result)
            self.progress.emit(i, total)

        results.sort(key=lambda x: x["probability"], reverse=True)
        self.finished.emit(results)


# ─────────────────────────────────────────────
#  Main window
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("STEGANALYSIS  ·  FORENSIC SCANNER")
        self.results = []
        self.detector = SteganalysisTool()
        self._build_ui()
        self._apply_global_styles()

    # ── UI construction ──────────────────────

    def _build_ui(self):

        root = QWidget()
        root.setObjectName("Root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header bar ──
        header = self._make_header()
        root_layout.addWidget(header)

        # ── Scan line (decorative) ──
        self.scan_line = ScanLineWidget()
        self.scan_line.hide()
        root_layout.addWidget(self.scan_line)

        # ── Stats row ──
        stats_bar = self._make_stats_bar()
        root_layout.addWidget(stats_bar)

        # ── Main content area ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {PALETTE["border"]}; }}
        """)

        splitter.addWidget(self._make_left_panel())
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([480, 520])

        root_layout.addWidget(splitter, stretch=1)

        # ── Status bar ──
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {PALETTE["surface"]};
                color: {PALETTE["text_dim"]};
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border-top: 1px solid {PALETTE["border"]};
                padding: 2px 8px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — select a folder to begin analysis")

        self.setCentralWidget(root)

    def _make_header(self):
        header = QWidget()
        header.setFixedHeight(56)
        header.setObjectName("Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(14)

        # Logo / title
        title = QLabel("⬡  STEGANALYSIS")
        title.setStyleSheet(f"""
            color: {PALETTE["accent"]};
            font-family: 'Courier New', monospace;
            font-size: 15px;
            font-weight: bold;
            letter-spacing: 4px;
        """)
        h.addWidget(title)

        subtitle = QLabel("FORENSIC IMAGE SCANNER")
        subtitle.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 10px;
            letter-spacing: 3px;
        """)
        h.addWidget(subtitle)
        h.addStretch()

        # Scan button
        self.scan_button = QPushButton("▶  SCAN FOLDER")
        self.scan_button.setFixedSize(160, 34)
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.clicked.connect(self.select_and_scan)
        self.scan_button.setObjectName("ScanButton")
        h.addWidget(self.scan_button)

        return header

    def _make_stats_bar(self):
        bar = QWidget()
        bar.setFixedHeight(82)
        bar.setObjectName("StatsBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(10)

        self.stat_total      = StatTile("TOTAL SCANNED",  "—", PALETTE["accent"])
        self.stat_stego      = StatTile("STEGO DETECTED", "—", PALETTE["red"])
        self.stat_suspicious = StatTile("SUSPICIOUS",     "—", PALETTE["orange"])
        self.stat_clean      = StatTile("CLEAN",          "—", PALETTE["green"])

        for tile in (self.stat_total, self.stat_stego, self.stat_suspicious, self.stat_clean):
            h.addWidget(tile)

        return bar

    def _make_left_panel(self):
        panel = QWidget()
        panel.setObjectName("LeftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Column header
        col_header = QWidget()
        col_header.setFixedHeight(32)
        col_header.setObjectName("ColHeader")
        ch = QHBoxLayout(col_header)
        ch.setContentsMargins(12, 0, 12, 0)
        ch.setSpacing(10)

        def col_lbl(text, width=None):
            l = QLabel(text)
            l.setStyleSheet(f"""
                color: {PALETTE["text_dim"]};
                font-family: 'Courier New', monospace;
                font-size: 9px;
                letter-spacing: 1.5px;
            """)
            if width:
                l.setFixedWidth(width)
            return l

        ch.addWidget(col_lbl("THREAT",  82))
        ch.addWidget(col_lbl("FILENAME"), )
        ch.addStretch()
        ch.addWidget(col_lbl("SCORE"))
        layout.addWidget(col_header)

        # Progress bar (slim, accent-colored, hidden until scanning)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setObjectName("SlimProgress")
        layout.addWidget(self.progress)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setObjectName("ResultsList")
        self.results_list.setSpacing(0)
        self.results_list.setFrameShape(QFrame.NoFrame)
        self.results_list.itemClicked.connect(self.display_result)
        self.results_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.results_list, stretch=1)

        # Empty-state placeholder
        self.empty_label = QLabel("No images analyzed yet.\nClick  ▶  SCAN FOLDER  to begin.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.8;
            letter-spacing: 1px;
        """)
        layout.addWidget(self.empty_label)

        return panel

    def _make_right_panel(self):
        panel = QWidget()
        panel.setObjectName("RightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Panel header
        ph = QWidget()
        ph.setFixedHeight(32)
        ph.setObjectName("PanelHeader")
        ph_layout = QHBoxLayout(ph)
        ph_layout.setContentsMargins(16, 0, 16, 0)
        phl = QLabel("IMAGE ANALYSIS")
        phl.setStyleSheet(f"""
            color: {PALETTE["text_dim"]};
            font-family: 'Courier New', monospace;
            font-size: 9px;
            letter-spacing: 1.5px;
        """)
        ph_layout.addWidget(phl)
        layout.addWidget(ph)

        self.detail_panel = DetailPanel()
        layout.addWidget(self.detail_panel, stretch=1)
        return panel

    # ── Global styles ────────────────────────

    def _apply_global_styles(self):
        self.setStyleSheet(f"""

        QMainWindow, QWidget#Root {{
            background-color: {PALETTE["bg"]};
        }}

        QWidget#Header {{
            background: {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}

        QWidget#StatsBar {{
            background: {PALETTE["bg"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}

        QWidget#ColHeader {{
            background: {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}

        QWidget#PanelHeader {{
            background: {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}

        QWidget#LeftPanel {{
            background: {PALETTE["bg"]};
            border-right: 1px solid {PALETTE["border"]};
        }}

        QWidget#RightPanel {{
            background: {PALETTE["surface"]};
        }}

        QListWidget#ResultsList {{
            background: {PALETTE["bg"]};
            border: none;
            outline: none;
        }}

        QListWidget#ResultsList::item {{
            background: transparent;
            padding: 0px;
            border: none;
        }}

        QListWidget#ResultsList::item:selected {{
            background: {PALETTE["surface2"]};
            border-left: 2px solid {PALETTE["accent"]};
        }}

        QListWidget#ResultsList::item:hover {{
            background: {PALETTE["surface"]};
        }}

        QProgressBar#SlimProgress {{
            background: {PALETTE["surface"]};
            border: none;
        }}

        QProgressBar#SlimProgress::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PALETTE["accent_dim"]}, stop:1 {PALETTE["accent"]});
        }}

        QPushButton#ScanButton {{
            background: transparent;
            color: {PALETTE["accent"]};
            border: 1px solid {PALETTE["accent"]};
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 0px 14px;
        }}

        QPushButton#ScanButton:hover {{
            background: {PALETTE["accent_dim"]};
            color: #fff;
        }}

        QPushButton#ScanButton:pressed {{
            background: {PALETTE["accent"]};
            color: {PALETTE["bg"]};
        }}

        QPushButton#ScanButton:disabled {{
            color: {PALETTE["text_dim"]};
            border-color: {PALETTE["border"]};
        }}

        QScrollBar:vertical {{
            background: {PALETTE["bg"]};
            width: 6px;
            border-radius: 3px;
        }}

        QScrollBar::handle:vertical {{
            background: {PALETTE["border_hi"]};
            border-radius: 3px;
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        """)

    # ── Scan flow ────────────────────────────

    def select_and_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if not folder:
            return

        self.results_list.clear()
        self.empty_label.hide()
        self.detail_panel.clear()
        self.scan_button.setEnabled(False)
        self.scan_button.setText("◌  SCANNING…")
        self.progress.setValue(0)
        self.scan_line.start()
        self.status_bar.showMessage(f"Scanning  {folder}")

        self._reset_stats()

        self.thread = QThread()
        self.worker = ScanWorker(self.detector, folder)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.scan_complete)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def update_progress(self, current, total):
        pct = int((current / total) * 100) if total else 0
        self.progress.setValue(pct)
        self.status_bar.showMessage(f"Analyzing images…  {current} / {total}  ({pct}%)")

    def scan_complete(self, results):
        self.results = results
        self.results_list.clear()
        self.scan_line.stop()

        stego_count      = sum(1 for r in results if r["label"] == "STEGO")
        suspicious_count = sum(1 for r in results if r["label"] == "SUSPICIOUS")
        clean_count      = sum(1 for r in results if r["label"] == ("CLEAN", "COVER"))

        self.stat_total.set_value(str(len(results)))
        self.stat_stego.set_value(str(stego_count))
        self.stat_suspicious.set_value(str(suspicious_count))
        self.stat_clean.set_value(str(clean_count))

        for r in results:
            if r["label"] == "COVER":
                r["label"] = "CLEAN"
            item   = QListWidgetItem(self.results_list)
            widget = ResultRowWidget(r)
            item.setSizeHint(QSize(0, 44))
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

        if not results:
            self.empty_label.setText("No images found in selected folder.")
            self.empty_label.show()

        self.progress.setValue(100)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("▶  SCAN FOLDER")

        threat_msg = f"  ·  {stego_count} STEGO  {suspicious_count} SUSPICIOUS  {clean_count} CLEAN" if results else ""
        self.status_bar.showMessage(f"Scan complete — {len(results)} images analyzed{threat_msg}")

        if results:
            self.results_list.setCurrentRow(0)
            self.display_result(self.results_list.item(0))

    def display_result(self, item):
        index  = self.results_list.row(item)
        result = self.results[index]
        self.detail_panel.show_image(result["file"])
        self.detail_panel.show_result(result)

    def _reset_stats(self):
        for tile in (self.stat_total, self.stat_stego, self.stat_suspicious, self.stat_clean):
            tile.set_value("—")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def start_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark base palette so Qt native elements (scrollbars, dialogs) match
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
    app.setPalette(pal)

    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    sys.exit(app.exec())