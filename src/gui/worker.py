"""
ScanWorker — runs the detector over a folder in a background QThread.

Responsibilities
----------------
* Enumerate image files in a directory.
* Call detector.analyze_image() for each file.
* Emit progress updates and a final sorted result list.
* Normalise raw detector labels (COVER → CLEAN) before emitting results,
  so the rest of the UI never has to deal with COVER.
"""

import os

from PySide6.QtCore import QObject, Signal

from src.gui.constants import Label

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".pgm")


class ScanWorker(QObject):
    """Runs in a QThread; communicates back via Qt signals."""

    progress = Signal(int, int)   # (current, total)
    finished = Signal(list)       # list[dict] — normalised, sorted by probability desc

    def __init__(self, detector, folder: str):
        super().__init__()
        self._detector = detector
        self._folder   = folder

    def run(self) -> None:
        images  = self._collect_images()
        total   = len(images)
        results = []

        for i, path in enumerate(images, start=1):
            result = self._detector.analyze_image(path)
            if result:
                result["label"] = str(Label.normalise(result["label"]))
                results.append(result)
            self.progress.emit(i, total)

        results.sort(key=lambda r: r["probability"], reverse=True)
        self.finished.emit(results)

    # ── Helpers ──────────────────────────────

    def _collect_images(self) -> list[str]:
        try:
            entries = sorted(os.listdir(self._folder))
        except OSError:
            return []
        return [
            os.path.join(self._folder, f)
            for f in entries
            if f.lower().endswith(_IMAGE_EXTENSIONS)
        ]