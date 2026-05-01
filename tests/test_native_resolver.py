"""
Unit tests for webspec_native_resolver.py — native element type mapping.

Run: pytest tests/test_native_resolver.py -v
"""

import pytest

from webspec_native_resolver import (
    get_native_tags,
    is_native_mode,
    WINDOWS_MAP,
    MAC_MAP,
    LINUX_MAP,
)
from unittest.mock import MagicMock, PropertyMock


# ═══════════════════════════════════════════════════════════════════════════
#  Tag mapping
# ═══════════════════════════════════════════════════════════════════════════

class TestGetNativeTags:
    """Verify WebSpec element names map to correct platform-native types."""

    # -- Windows (WinAppDriver / UIA) --------------------------------------

    def test_windows_button(self):
        tags = get_native_tags("button", "windows")
        assert "Button" in tags

    def test_windows_input(self):
        tags = get_native_tags("input", "windows")
        assert "Edit" in tags

    def test_windows_checkbox(self):
        tags = get_native_tags("checkbox", "windows")
        assert "CheckBox" in tags

    def test_windows_select(self):
        tags = get_native_tags("select", "windows")
        assert "ComboBox" in tags

    def test_windows_element_is_wildcard(self):
        tags = get_native_tags("element", "windows")
        assert tags == ["*"]

    def test_windows_text(self):
        tags = get_native_tags("text", "windows")
        assert "Text" in tags

    def test_windows_table(self):
        tags = get_native_tags("table", "windows")
        assert "Table" in tags or "DataGrid" in tags

    # -- macOS (XCTest / Mac2) ---------------------------------------------

    def test_mac_button(self):
        tags = get_native_tags("button", "mac")
        assert "XCUIElementTypeButton" in tags

    def test_mac_input(self):
        tags = get_native_tags("input", "mac")
        assert "XCUIElementTypeTextField" in tags
        assert "XCUIElementTypeSecureTextField" in tags

    def test_mac_checkbox(self):
        tags = get_native_tags("checkbox", "mac")
        assert "XCUIElementTypeCheckBox" in tags

    def test_mac_select(self):
        tags = get_native_tags("select", "mac")
        assert "XCUIElementTypePopUpButton" in tags

    def test_mac_text(self):
        tags = get_native_tags("text", "mac")
        assert "XCUIElementTypeStaticText" in tags

    # -- Linux (AT-SPI2) ---------------------------------------------------

    def test_linux_button(self):
        tags = get_native_tags("button", "linux")
        assert "push button" in tags

    def test_linux_input(self):
        tags = get_native_tags("input", "linux")
        assert "text" in tags or "entry" in tags

    def test_linux_checkbox(self):
        tags = get_native_tags("checkbox", "linux")
        assert "check box" in tags

    # -- Cross-platform behaviours -----------------------------------------

    def test_case_insensitive_element_type(self):
        """'Button', 'BUTTON', 'button' should all work."""
        assert get_native_tags("Button", "windows") == get_native_tags("button", "windows")
        assert get_native_tags("INPUT", "mac") == get_native_tags("input", "mac")

    def test_case_insensitive_platform(self):
        assert get_native_tags("button", "Windows") == get_native_tags("button", "windows")
        assert get_native_tags("button", "MAC") == get_native_tags("button", "mac")

    def test_unknown_element_returns_raw(self):
        """If the element type isn't in the map, pass it through as-is."""
        tags = get_native_tags("customwidget", "windows")
        assert tags == ["customwidget"]

    def test_unsupported_platform_raises(self):
        with pytest.raises(ValueError, match="No native type map"):
            get_native_tags("button", "android")

    # -- Completeness checks -----------------------------------------------

    @pytest.mark.parametrize("element_type", [
        "button", "input", "text", "checkbox", "radio", "select",
        "link", "list", "menu", "tab", "table", "row", "image",
        "heading", "element",
    ])
    def test_core_types_mapped_on_all_platforms(self, element_type):
        """Every core WebSpec element type should have a mapping everywhere."""
        for platform in ("windows", "mac", "linux"):
            tags = get_native_tags(element_type, platform)
            assert len(tags) >= 1, f"{element_type} not mapped on {platform}"

    def test_all_maps_have_same_keys(self):
        """All three platform maps should cover the same element types."""
        assert set(WINDOWS_MAP.keys()) == set(MAC_MAP.keys())
        assert set(WINDOWS_MAP.keys()) == set(LINUX_MAP.keys())


# ═══════════════════════════════════════════════════════════════════════════
#  Appium detection heuristic
# ═══════════════════════════════════════════════════════════════════════════

class TestIsNativeMode:

    def test_detects_appium_automation_name(self):
        driver = MagicMock()
        driver.capabilities = {
            "automationName": "Windows",
            "platformName": "Windows",
        }
        assert is_native_mode(driver) is True

    def test_detects_platform_name_only(self):
        driver = MagicMock()
        driver.capabilities = {"platformName": "mac"}
        assert is_native_mode(driver) is True

    def test_rejects_browser_driver(self):
        driver = MagicMock()
        driver.capabilities = {
            "browserName": "chrome",
            "platformName": "any",
        }
        # "any" isn't in (windows, mac, linux) and automationName is absent
        assert is_native_mode(driver) is False

    def test_handles_no_capabilities(self):
        driver = MagicMock()
        driver.capabilities = None
        assert is_native_mode(driver) is False

    def test_handles_exception(self):
        driver = MagicMock()
        type(driver).capabilities = PropertyMock(side_effect=Exception("boom"))
        assert is_native_mode(driver) is False