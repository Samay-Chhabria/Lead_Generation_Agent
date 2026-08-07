"""Design tokens shared by both themes (fonts, spacing, radii)."""

FONT_FAMILY = "Segoe UI"
MONO_FONT = "Cascadia Mono"

WINDOW_MIN_WIDTH = 1080
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_WIDTH = 1280
WINDOW_DEFAULT_HEIGHT = 860

CARD_RADIUS = 14
CONTROL_RADIUS = 10
CARD_BODY_RADIUS = 10
BORDER_WIDTH = 1

LAYOUT_MARGIN = 16
PANEL_SPACING = 12
CONTROL_SPACING = 8

#: Per-panel scroll areas keep each card independent inside the columns.
PANEL_SCROLL_OBJECT = "panelScroll"
PANEL_SCROLL_CONTENT = "scrollContent"

STEP_CURRENT_PROPERTY = "state"
STEP_CURRENT_VALUE = "current"
STEP_DONE_VALUE = "done"
STEP_FAILED_VALUE = "failed"
STEP_PENDING_VALUE = "pending"
