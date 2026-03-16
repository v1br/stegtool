from __future__ import annotations

PALETTE: dict[str, str] = {
    "bg":          "#0d0f14",
    "surface":     "#141720",
    "surface2":    "#1c2030",
    "border":      "#252a3a",
    "border_hi":   "#2e3550",
    "text":        "#e2e8f8",
    "text_dim":    "#99aac4",
    "text_bright": "#ffffff",
    "accent":      "#00d4ff",
    "accent_dim":  "#005566",
    "green":       "#00e5a0",
    "green_dim":   "#003d2b",
    "orange":      "#ff9500",
    "orange_dim":  "#3d2400",
    "red":         "#ff3b5c",
    "red_dim":     "#3d0013",
}


def label_fg(label: str) -> str:
    """Return the foreground hex color for a given prediction label."""
    return {
        "STEGO":      PALETTE["red"],
        "SUSPICIOUS": PALETTE["orange"],
        "CLEAN":      PALETTE["green"],
    }.get(label, PALETTE["text_dim"])


def label_bg(label: str) -> str:
    """Return the background hex color for a given prediction label."""
    return {
        "STEGO":      PALETTE["red_dim"],
        "SUSPICIOUS": PALETTE["orange_dim"],
        "CLEAN":      PALETTE["green_dim"],
    }.get(label, PALETTE["surface"])