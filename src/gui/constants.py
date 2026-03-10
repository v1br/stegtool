"""
Prediction label constants.

Using an Enum eliminates the ~20 scattered magic strings ("STEGO", "COVER", …)
and makes exhaustiveness checking and refactoring safe.
"""

from enum import StrEnum


class Label(StrEnum):
    STEGO      = "STEGO"
    SUSPICIOUS = "SUSPICIOUS"
    CLEAN      = "CLEAN"
    COVER      = "COVER"   # detector alias for CLEAN — normalised on ingestion

    @classmethod
    def normalise(cls, raw: str) -> "Label":
        """Map COVER → CLEAN; leave everything else unchanged."""
        if raw == cls.COVER:
            return cls.CLEAN
        return cls(raw)