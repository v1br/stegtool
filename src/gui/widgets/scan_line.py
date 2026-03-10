"""Animated horizontal scan line shown while a scan is in progress."""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QLinearGradient, QBrush, QColor
from PySide6.QtCore import QTimer, Qt

from src.gui.palette import PALETTE


class ScanLineWidget(QWidget):
    """A thin, animated glow that sweeps across the top of the results panel."""

    _SPEED   = 0.012   # fraction of width advanced per tick
    _TICK_MS = 16      # ~60 fps

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self._pos    = 0.0
        self._active = False
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ── Public API ───────────────────────────

    def start(self) -> None:
        self._active = True
        self._pos    = 0.0
        self._timer.start(self._TICK_MS)
        self.show()

    def stop(self) -> None:
        self._active = False
        self._timer.stop()
        self.hide()

    # ── Internals ────────────────────────────

    def _tick(self) -> None:
        self._pos = (self._pos + self._SPEED) % 1.0
        self.update()

    def paintEvent(self, _event) -> None:
        if not self._active:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w      = self.width()
        center = int(self._pos * w)

        grad = QLinearGradient(max(0, center - 120), 0, min(w, center + 120), 0)
        grad.setColorAt(0.0, QColor(0, 212, 255,   0))
        grad.setColorAt(0.4, QColor(0, 212, 255, 180))
        grad.setColorAt(0.5, QColor(200, 240, 255, 255))
        grad.setColorAt(0.6, QColor(0, 212, 255, 180))
        grad.setColorAt(1.0, QColor(0, 212, 255,   0))

        p.fillRect(0, 0, w, 2, QBrush(grad))