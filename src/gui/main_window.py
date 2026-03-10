"""
MainWindow — application shell.

Responsibilities
----------------
* Lay out the top-level UI (header, stats bar, list panel, detail panel).
* Orchestrate the scan flow (open dialog → spin up worker → handle results).
* Update summary tiles and status bar.

Widget implementation details live in src/gui/widgets/.
Threading lives in src/gui/worker.py.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QListWidget,
    QListWidgetItem, QProgressBar, QSplitter, QFrame,
    QStatusBar, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, QSize

from src.gui.palette    import PALETTE
from src.gui.constants  import Label
from src.gui.worker     import ScanWorker
from src.gui    import (
    ScanLineWidget, ResultRowWidget, StatTile, DetailPanel,
)


class MainWindow(QMainWindow):

    def __init__(self, detector):
        super().__init__()
        self.setWindowTitle("STEGANALYSIS  ·  FORENSIC SCANNER")
        self._detector = detector
        self._results: list[dict] = []
        self._build_ui()
        self._apply_global_styles()

    # ── UI construction ──────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self._scan_line = ScanLineWidget()
        self._scan_line.hide()
        layout.addWidget(self._scan_line)

        layout.addWidget(self._build_stats_bar())
        layout.addWidget(self._build_content_splitter(), stretch=1)

        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(f"""
            QStatusBar {{
                background:  {PALETTE["surface"]};
                color:       {PALETTE["text_dim"]};
                font-family: 'Courier New', monospace;
                font-size:   11px;
                border-top:  1px solid {PALETTE["border"]};
                padding:     2px 8px;
            }}
        """)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready — select a folder to begin analysis")

        self.setCentralWidget(root)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        header.setObjectName("Header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        title = QLabel("⬡  STEGANALYSIS")
        title.setStyleSheet(f"""
            color:          {PALETTE["accent"]};
            font-family:    'Courier New', monospace;
            font-size:      15px;
            font-weight:    bold;
            letter-spacing: 4px;
        """)
        subtitle = QLabel("FORENSIC IMAGE SCANNER")
        subtitle.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      10px;
            letter-spacing: 3px;
        """)

        self._scan_button = QPushButton("▶  SCAN FOLDER")
        self._scan_button.setFixedSize(160, 34)
        self._scan_button.setCursor(Qt.PointingHandCursor)
        self._scan_button.setObjectName("ScanButton")
        self._scan_button.clicked.connect(self._select_and_scan)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self._scan_button)
        return header

    def _build_stats_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(82)
        bar.setObjectName("StatsBar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self._tile_total      = StatTile("TOTAL SCANNED",  "—", PALETTE["accent"])
        self._tile_stego      = StatTile("STEGO DETECTED", "—", PALETTE["red"])
        self._tile_suspicious = StatTile("SUSPICIOUS",     "—", PALETTE["orange"])
        self._tile_clean      = StatTile("CLEAN",          "—", PALETTE["green"])

        for tile in self._all_tiles():
            layout.addWidget(tile)
        return bar

    def _build_content_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {PALETTE['border']}; }}"
        )
        splitter.addWidget(self._build_list_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([480, 520])
        return splitter

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("LeftPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_column_header())

        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("SlimProgress")
        layout.addWidget(self._progress)

        self._results_list = QListWidget()
        self._results_list.setObjectName("ResultsList")
        self._results_list.setSpacing(0)
        self._results_list.setFrameShape(QFrame.NoFrame)
        self._results_list.setSelectionMode(QListWidget.SingleSelection)
        self._results_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list, stretch=1)

        self._empty_label = QLabel(
            "No images analyzed yet.\nClick  ▶  SCAN FOLDER  to begin."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      12px;
            line-height:    1.8;
            letter-spacing: 1px;
        """)
        layout.addWidget(self._empty_label)
        return panel

    def _build_column_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(32)
        header.setObjectName("ColHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        def _col(text: str, width: int = 0) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                color:          {PALETTE["text_dim"]};
                font-family:    'Courier New', monospace;
                font-size:      9px;
                letter-spacing: 1.5px;
            """)
            if width:
                lbl.setFixedWidth(width)
            return lbl

        layout.addWidget(_col("THREAT", 82))
        layout.addWidget(_col("FILENAME"))
        layout.addStretch()
        layout.addWidget(_col("SCORE"))
        return header

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("RightPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        ph = QWidget()
        ph.setFixedHeight(32)
        ph.setObjectName("PanelHeader")
        ph_layout = QHBoxLayout(ph)
        ph_layout.setContentsMargins(16, 0, 16, 0)
        phl = QLabel("IMAGE ANALYSIS")
        phl.setStyleSheet(f"""
            color:          {PALETTE["text_dim"]};
            font-family:    'Courier New', monospace;
            font-size:      9px;
            letter-spacing: 1.5px;
        """)
        ph_layout.addWidget(phl)
        layout.addWidget(ph)

        self._detail_panel = DetailPanel()
        layout.addWidget(self._detail_panel, stretch=1)
        return panel

    # ── Scan orchestration ───────────────────

    def _select_and_scan(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if not folder:
            return

        self._results_list.clear()
        self._empty_label.hide()
        self._detail_panel.clear()
        self._set_scanning_state(True)
        self._reset_stats()
        self._progress.setValue(0)
        self._status_bar.showMessage(f"Scanning  {folder}")

        self._thread = QThread()
        self._worker = ScanWorker(self._detector, folder)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_scan_complete)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_progress(self, current: int, total: int) -> None:
        pct = int((current / total) * 100) if total else 0
        self._progress.setValue(pct)
        self._status_bar.showMessage(
            f"Analyzing images…  {current} / {total}  ({pct}%)"
        )

    def _on_scan_complete(self, results: list[dict]) -> None:
        self._results = results
        self._results_list.clear()
        self._scan_line.stop()
        self._set_scanning_state(False)
        self._progress.setValue(100)

        # Count by label (labels are already normalised by the worker)
        counts = {label: 0 for label in (Label.STEGO, Label.SUSPICIOUS, Label.CLEAN)}
        for r in results:
            if r["label"] in counts:
                counts[r["label"]] += 1

        self._tile_total.set_value(str(len(results)))
        self._tile_stego.set_value(str(counts[Label.STEGO]))
        self._tile_suspicious.set_value(str(counts[Label.SUSPICIOUS]))
        self._tile_clean.set_value(str(counts[Label.CLEAN]))

        for result in results:
            item = QListWidgetItem(self._results_list)
            item.setSizeHint(QSize(0, 44))
            self._results_list.addItem(item)
            self._results_list.setItemWidget(item, ResultRowWidget(result))

        if not results:
            self._empty_label.setText("No images found in selected folder.")
            self._empty_label.show()
        else:
            self._results_list.setCurrentRow(0)
            self._display_result(0)

        n = len(results)
        threat = (
            f"  ·  {counts[Label.STEGO]} STEGO  "
            f"{counts[Label.SUSPICIOUS]} SUSPICIOUS  "
            f"{counts[Label.CLEAN]} CLEAN"
            if results else ""
        )
        self._status_bar.showMessage(f"Scan complete — {n} image{'s' if n != 1 else ''} analyzed{threat}")

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        self._display_result(self._results_list.row(item))

    def _display_result(self, index: int) -> None:
        result = self._results[index]
        self._detail_panel.show_image(result["file"])
        self._detail_panel.show_result(result)

    # ── Helpers ──────────────────────────────

    def _set_scanning_state(self, scanning: bool) -> None:
        self._scan_button.setEnabled(not scanning)
        self._scan_button.setText("◌  SCANNING…" if scanning else "▶  SCAN FOLDER")
        if scanning:
            self._scan_line.start()

    def _reset_stats(self) -> None:
        for tile in self._all_tiles():
            tile.set_value("—")

    def _all_tiles(self):
        return (self._tile_total, self._tile_stego, self._tile_suspicious, self._tile_clean)

    # ── Global stylesheet ────────────────────

    def _apply_global_styles(self) -> None:
        self.setStyleSheet(f"""
        QMainWindow, QWidget#Root {{
            background-color: {PALETTE["bg"]};
        }}
        QWidget#Header {{
            background:   {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}
        QWidget#StatsBar {{
            background:    {PALETTE["bg"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}
        QWidget#ColHeader {{
            background:    {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}
        QWidget#PanelHeader {{
            background:    {PALETTE["surface"]};
            border-bottom: 1px solid {PALETTE["border"]};
        }}
        QWidget#LeftPanel {{
            background:   {PALETTE["bg"]};
            border-right:  1px solid {PALETTE["border"]};
        }}
        QWidget#RightPanel {{
            background: {PALETTE["surface"]};
        }}
        QListWidget#ResultsList {{
            background: {PALETTE["bg"]};
            border:     none;
            outline:    none;
        }}
        QListWidget#ResultsList::item {{
            background: transparent;
            padding:    0px;
            border:     none;
        }}
        QListWidget#ResultsList::item:selected {{
            background:  {PALETTE["surface2"]};
            border-left: 2px solid {PALETTE["accent"]};
        }}
        QListWidget#ResultsList::item:hover {{
            background: {PALETTE["surface"]};
        }}
        QProgressBar#SlimProgress {{
            background: {PALETTE["surface"]};
            border:     none;
        }}
        QProgressBar#SlimProgress::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {PALETTE["accent_dim"]}, stop:1 {PALETTE["accent"]}
            );
        }}
        QPushButton#ScanButton {{
            background:     transparent;
            color:          {PALETTE["accent"]};
            border:         1px solid {PALETTE["accent"]};
            border-radius:  4px;
            font-family:    'Courier New', monospace;
            font-size:      11px;
            font-weight:    bold;
            letter-spacing: 2px;
            padding:        0px 14px;
        }}
        QPushButton#ScanButton:hover {{
            background: {PALETTE["accent_dim"]};
            color:      #fff;
        }}
        QPushButton#ScanButton:pressed {{
            background: {PALETTE["accent"]};
            color:      {PALETTE["bg"]};
        }}
        QPushButton#ScanButton:disabled {{
            color:        {PALETTE["text_dim"]};
            border-color: {PALETTE["border"]};
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
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """)