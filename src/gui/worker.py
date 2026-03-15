import os

from PySide6.QtCore import QObject, Signal

from src.gui.constants import Label

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".pgm")


# ── Scan ─────────────────────────────────────────────────────────────────────

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


# ── Embed ─────────────────────────────────────────────────────────────────────

class EmbedWorker(QObject):
    """
    Embeds a text payload into an image, saves to output_path,
    then runs the detector on the stego result.

    Signals
    -------
    finished(stego_path, result | None)
    error(message)
    """

    finished = Signal(str, object)   # (stego_path, detection_result | None)
    error    = Signal(str)

    def __init__(
        self,
        embedder,
        detector,
        image_path:   str,
        text:         str,
        payload_bpp:  float,
        output_path:  str,
    ):
        super().__init__()
        self._embedder    = embedder
        self._detector    = detector
        self._image_path  = image_path
        self._text        = text
        self._payload_bpp = payload_bpp
        self._output_path = output_path

    def run(self) -> None:
        try:
            self._embedder.embed(
                self._image_path,
                self._output_path,
                self._text,
                self._payload_bpp,
            )
            result = self._detector.analyze_image(self._output_path)
            if result:
                result["label"] = str(Label.normalise(result["label"]))
            self.finished.emit(self._output_path, result)
        except Exception as exc:
            self.error.emit(str(exc))


# ── Extract ───────────────────────────────────────────────────────────────────

class ExtractWorker(QObject):
    """
    Extracts a hidden LSB text payload from a single image.

    Signals
    -------
    finished(text)   — empty string if no message found
    error(message)
    """

    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, extractor, image_path: str):
        super().__init__()
        self._extractor  = extractor
        self._image_path = image_path

    def run(self) -> None:
        try:
            text = self._extractor.extract(self._image_path)
            self.finished.emit(text or "")
        except Exception as exc:
            self.error.emit(str(exc))


# ── Analysis ──────────────────────────────────────────────────────────────────

class AnalysisWorker(QObject):
    """
    Runs full feature extraction on one or two images so the
    FeaturesTab can compare cover vs stego feature vectors.

    Emits finished(cover_data, stego_data) where each data dict has keys:
        spam, glcm, entropy, features, label, probability, model_probabilities
    stego_data is None when only one image path is provided.

    Signals
    -------
    finished(cover_data, stego_data | None)
    error(message)
    """

    finished = Signal(object, object)
    error    = Signal(str)

    def __init__(self, detector, cover_path: str, stego_path: str = None):
        super().__init__()
        self._detector   = detector
        self._cover_path = cover_path
        self._stego_path = stego_path

    def run(self) -> None:
        try:
            cover = self._detector.analyze_image(self._cover_path)
            if cover:
                cover["label"] = str(Label.normalise(cover["label"]))

            stego = None
            if self._stego_path:
                stego = self._detector.analyze_image(self._stego_path)
                if stego:
                    stego["label"] = str(Label.normalise(stego["label"]))

            self.finished.emit(cover, stego)
        except Exception as exc:
            self.error.emit(str(exc))