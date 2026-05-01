"""
WebSpec DSL - Native Element Type Mapping

When running against Appium, driver.page_source returns the accessibility
tree as XML instead of HTML.  This module maps WebSpec's English element
names (button, input, checkbox, ...) to the platform-specific types that
appear in that XML.

The existing BS4 resolver can parse the XML unchanged — we just need to
translate the element type that the resolver searches for.
"""

from typing import Dict, List


# ---------------------------------------------------------------------------
# Platform mappings
# ---------------------------------------------------------------------------

# Windows (WinAppDriver) — UIA ControlTypes
WINDOWS_MAP: Dict[str, List[str]] = {
    "button":    ["Button", "SplitButton", "MenuButton"],
    "input":     ["Edit", "TextBox"],
    "text":      ["Text", "TextBlock"],
    "checkbox":  ["CheckBox"],
    "radio":     ["RadioButton"],
    "select":    ["ComboBox"],
    "link":      ["Hyperlink"],
    "list":      ["List", "ListItem"],
    "menu":      ["Menu", "MenuItem"],
    "tab":       ["TabItem"],
    "table":     ["Table", "DataGrid"],
    "row":       ["DataItem", "Row", "TableRow"],
    "image":     ["Image"],
    "heading":   ["Text", "Group"],          # no native heading; best guess
    "element":   ["*"],                      # wildcard fallback
    "window":    ["Window"],
    "dialog":    ["Window", "Dialog"],
    "slider":    ["Slider"],
    "tree":      ["Tree", "TreeItem"],
    "toolbar":   ["ToolBar"],
    "scrollbar": ["ScrollBar"],
}

# macOS (Mac2 / XCTest) — XCUIElementType names
MAC_MAP: Dict[str, List[str]] = {
    "button":    ["XCUIElementTypeButton"],
    "input":     ["XCUIElementTypeTextField", "XCUIElementTypeSecureTextField"],
    "text":      ["XCUIElementTypeStaticText"],
    "checkbox":  ["XCUIElementTypeCheckBox"],
    "radio":     ["XCUIElementTypeRadioButton"],
    "select":    ["XCUIElementTypePopUpButton", "XCUIElementTypeComboBox"],
    "link":      ["XCUIElementTypeLink"],
    "list":      ["XCUIElementTypeList", "XCUIElementTypeCell"],
    "menu":      ["XCUIElementTypeMenu", "XCUIElementTypeMenuItem"],
    "tab":       ["XCUIElementTypeTab"],
    "table":     ["XCUIElementTypeTable"],
    "row":       ["XCUIElementTypeTableRow", "XCUIElementTypeCell"],
    "image":     ["XCUIElementTypeImage"],
    "heading":   ["XCUIElementTypeStaticText"],
    "element":   ["*"],
    "window":    ["XCUIElementTypeWindow"],
    "dialog":    ["XCUIElementTypeSheet", "XCUIElementTypeDialog"],
    "slider":    ["XCUIElementTypeSlider"],
    "tree":      ["XCUIElementTypeOutline", "XCUIElementTypeOutlineRow"],
    "toolbar":   ["XCUIElementTypeToolbar"],
    "scrollbar": ["XCUIElementTypeScrollBar"],
}

# Linux (AT-SPI2) — role names; Appium Linux support is limited
LINUX_MAP: Dict[str, List[str]] = {
    "button":    ["push button", "toggle button"],
    "input":     ["text", "entry", "password text"],
    "text":      ["label", "static"],
    "checkbox":  ["check box"],
    "radio":     ["radio button"],
    "select":    ["combo box"],
    "link":      ["link"],
    "list":      ["list", "list item"],
    "menu":      ["menu", "menu item"],
    "tab":       ["page tab"],
    "table":     ["table", "table cell"],
    "row":       ["table row"],
    "image":     ["image", "icon"],
    "heading":   ["heading", "label"],
    "element":   ["*"],
    "window":    ["frame", "window"],
    "dialog":    ["dialog"],
    "slider":    ["slider"],
    "tree":      ["tree", "tree item"],
    "toolbar":   ["tool bar"],
    "scrollbar": ["scroll bar"],
}

# Convenience lookup
_PLATFORM_MAPS = {
    "windows": WINDOWS_MAP,
    "mac":     MAC_MAP,
    "linux":   LINUX_MAP,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_native_tags(element_type: str, platform: str) -> List[str]:
    """
    Given a WebSpec element type keyword and a platform name,
    return the list of native tag/type names the resolver should
    search for in the accessibility XML.

    >>> get_native_tags("button", "windows")
    ['Button', 'SplitButton', 'MenuButton']
    >>> get_native_tags("input", "mac")
    ['XCUIElementTypeTextField', 'XCUIElementTypeSecureTextField']
    """
    platform_key = platform.lower()
    mapping = _PLATFORM_MAPS.get(platform_key)
    if mapping is None:
        raise ValueError(
            f"No native type map for platform {platform!r}. "
            f"Supported: {list(_PLATFORM_MAPS.keys())}"
        )

    key = element_type.lower()
    if key in mapping:
        return mapping[key]

    # Fallback: return the raw name as-is so the resolver
    # can attempt a direct tag-name match in the XML
    return [element_type]


def is_native_mode(driver) -> bool:
    """Check whether a driver is an Appium remote session (heuristic)."""
    # Appium sessions have appium-specific capabilities
    try:
        caps = driver.capabilities or {}
        return (
            "appium" in str(caps.get("automationName", "")).lower()
            or "appium" in str(type(driver)).lower()
            or caps.get("platformName", "").lower() in ("windows", "mac", "linux")
        )
    except Exception:
        return False