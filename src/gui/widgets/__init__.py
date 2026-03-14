"""
src/gui package — public widget exports.

Import from here rather than from the individual widget modules so that
internal module reorganisation never breaks callers.
"""

from src.gui.widgets.scan_line    import ScanLineWidget
from src.gui.widgets.result_row   import ResultRowWidget
from src.gui.widgets.stat_tile    import StatTile
from src.gui.widgets.detail_panel import DetailPanel
from src.gui.widgets.embed_tab    import EmbedTab
from src.gui.widgets.extract_tab  import ExtractTab

__all__ = [
    "ScanLineWidget",
    "ResultRowWidget",
    "StatTile",
    "DetailPanel",
    "EmbedTab",
    "ExtractTab",
]