"""
Unit tests for webspec_driver.py — Electron and Appium driver backends.

All external dependencies (Selenium, subprocess, sockets) are mocked.
These tests verify wiring and configuration logic only.

Run: pytest tests/test_driver.py -v
"""

import socket
import subprocess
from unittest import mock
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from webspec_driver import (
    DriverConfig,
    create_driver,
    cleanup_driver,
    _wait_for_port,
    _detect_electron,
    _create_electron_driver,
    _create_appium_driver,
    _create_browser_driver,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Browser mode (regression — existing behaviour still works)
# ═══════════════════════════════════════════════════════════════════════════

class TestBrowserDriver:
    """Ensure the factory still produces browser drivers the old way."""

    @patch("webspec_driver.webdriver.Chrome")
    def test_chrome_default(self, mock_chrome):
        cfg = DriverConfig(mode="browser", browser="chrome")
        driver = create_driver(cfg)
        mock_chrome.assert_called_once()
        assert driver == mock_chrome.return_value

    @patch("webspec_driver.webdriver.Chrome")
    def test_chrome_headless(self, mock_chrome):
        cfg = DriverConfig(mode="browser", browser="chrome", headless=True)
        create_driver(cfg)
        opts = mock_chrome.call_args[1]["options"]
        assert any("--headless" in str(a) for a in opts.arguments)

    @patch("webspec_driver.webdriver.Firefox")
    def test_firefox(self, mock_ff):
        cfg = DriverConfig(mode="browser", browser="firefox")
        driver = create_driver(cfg)
        mock_ff.assert_called_once()
        assert driver == mock_ff.return_value

    @patch("webspec_driver.webdriver.Edge")
    def test_edge(self, mock_edge):
        cfg = DriverConfig(mode="browser", browser="edge")
        driver = create_driver(cfg)
        mock_edge.assert_called_once()

    def test_unsupported_browser_raises(self):
        cfg = DriverConfig(mode="browser", browser="safari")
        with pytest.raises(ValueError, match="Unsupported browser"):
            create_driver(cfg)

    def test_unknown_mode_raises(self):
        cfg = DriverConfig(mode="quantum")
        with pytest.raises(ValueError, match="Unknown driver mode"):
            create_driver(cfg)


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 1: Electron / CEF
# ═══════════════════════════════════════════════════════════════════════════

class TestElectronDriver:

    @patch("webspec_driver._wait_for_port", return_value=True)
    @patch("webspec_driver.subprocess.Popen")
    @patch("webspec_driver.webdriver.Chrome")
    def test_launches_app_and_connects(self, mock_chrome, mock_popen, mock_wait):
        """Happy path: app launches, debug port opens, ChromeDriver connects."""
        cfg = DriverConfig(
            mode="electron",
            app_path="/usr/bin/my-electron-app",
            debug_port=9222,
            launch_app=True,
        )
        driver = create_driver(cfg)

        # App was launched with the debug flag
        mock_popen.assert_called_once()
        launch_cmd = mock_popen.call_args[0][0]
        assert "/usr/bin/my-electron-app" in launch_cmd
        assert "--remote-debugging-port=9222" in launch_cmd

        # Port was waited on
        mock_wait.assert_called_once_with("127.0.0.1", 9222)

        # ChromeDriver was told to attach to the debug address
        opts = mock_chrome.call_args[1]["options"]
        assert opts.debugger_address == "127.0.0.1:9222"

        # Subprocess is stashed for cleanup
        assert driver._webspec_app_proc == mock_popen.return_value

    @patch("webspec_driver._wait_for_port", return_value=True)
    @patch("webspec_driver.subprocess.Popen")
    @patch("webspec_driver.webdriver.Chrome")
    def test_custom_debug_port(self, mock_chrome, mock_popen, mock_wait):
        cfg = DriverConfig(
            mode="electron",
            app_path="/app",
            debug_port=9333,
        )
        create_driver(cfg)
        launch_cmd = mock_popen.call_args[0][0]
        assert "--remote-debugging-port=9333" in launch_cmd
        mock_wait.assert_called_once_with("127.0.0.1", 9333)
        opts = mock_chrome.call_args[1]["options"]
        assert opts.debugger_address == "127.0.0.1:9333"

    @patch("webspec_driver.webdriver.Chrome")
    def test_no_launch_skips_subprocess(self, mock_chrome):
        """When launch_app=False, we just attach — no subprocess."""
        cfg = DriverConfig(
            mode="electron",
            app_path="/app",
            debug_port=9222,
            launch_app=False,
        )
        driver = create_driver(cfg)
        assert driver._webspec_app_proc is None

    @patch("webspec_driver._wait_for_port", return_value=False)
    @patch("webspec_driver.subprocess.Popen")
    def test_timeout_kills_app_and_raises(self, mock_popen, mock_wait):
        """If the debug port never opens, we kill the app and raise."""
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        cfg = DriverConfig(mode="electron", app_path="/app")
        with pytest.raises(RuntimeError, match="did not open debug port"):
            create_driver(cfg)

        mock_proc.terminate.assert_called_once()

    def test_missing_app_path_raises(self):
        cfg = DriverConfig(mode="electron", app_path=None)
        with pytest.raises(ValueError, match="requires --app-path"):
            create_driver(cfg)

    @patch("webspec_driver._wait_for_port", return_value=True)
    @patch("webspec_driver.subprocess.Popen")
    @patch("webspec_driver.webdriver.Chrome")
    def test_headless_flag_passed_through(self, mock_chrome, mock_popen, mock_wait):
        cfg = DriverConfig(
            mode="electron",
            app_path="/app",
            headless=True,
        )
        create_driver(cfg)
        opts = mock_chrome.call_args[1]["options"]
        assert any("--headless" in str(a) for a in opts.arguments)


class TestElectronDetection:

    @patch("webspec_driver.subprocess.run")
    def test_detects_electron_version_string(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="v28.0.0", stderr="Electron 28.0.0", returncode=0
        )
        assert _detect_electron("/usr/bin/slack") is True

    @patch("webspec_driver.subprocess.run")
    def test_detects_chromium_version_string(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="Chromium 120.0.6099.109", stderr="", returncode=0
        )
        assert _detect_electron("/usr/bin/cef-app") is True

    @patch("webspec_driver.subprocess.run")
    def test_rejects_non_electron(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="MyApp 2.1.0", stderr="", returncode=0
        )
        assert _detect_electron("/usr/bin/native-app") is False

    @patch("webspec_driver.subprocess.run", side_effect=FileNotFoundError)
    def test_handles_missing_binary(self, mock_run):
        assert _detect_electron("/no/such/binary") is False

    @patch("webspec_driver.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 5))
    def test_handles_timeout(self, mock_run):
        assert _detect_electron("/usr/bin/hung-app") is False


class TestWaitForPort:

    @patch("webspec_driver.socket.create_connection")
    def test_returns_true_when_port_opens(self, mock_conn):
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()
        assert _wait_for_port("127.0.0.1", 9222, timeout=1.0) is True

    @patch("webspec_driver.socket.create_connection", side_effect=OSError)
    @patch("webspec_driver.time.sleep")
    def test_returns_false_on_timeout(self, mock_sleep, mock_conn):
        # Force time to expire after first attempt
        with patch("webspec_driver.time.time", side_effect=[0.0, 0.0, 100.0]):
            assert _wait_for_port("127.0.0.1", 9222, timeout=0.01) is False


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 2: Appium
# ═══════════════════════════════════════════════════════════════════════════

class TestAppiumDriver:

    @patch("webspec_driver.webdriver.Remote")
    def test_windows_capabilities(self, mock_remote):
        cfg = DriverConfig(
            mode="appium",
            app=r"C:\Program Files\MyApp\app.exe",
            platform="windows",
            appium_server="http://localhost:4723",
        )
        driver = create_driver(cfg)

        mock_remote.assert_called_once()
        call_kwargs = mock_remote.call_args[1]
        assert call_kwargs["command_executor"] == "http://localhost:4723"

        options = call_kwargs["options"]
        caps = options.capabilities
        assert caps["platformName"] == "Windows"
        assert caps["appium:automationName"] == "Windows"
        assert caps["appium:app"] == r"C:\Program Files\MyApp\app.exe"

    @patch("webspec_driver.webdriver.Remote")
    def test_mac_capabilities(self, mock_remote):
        cfg = DriverConfig(
            mode="appium",
            app="/Applications/MyApp.app",
            platform="mac",
        )
        create_driver(cfg)

        options = mock_remote.call_args[1]["options"]
        caps = options.capabilities
        assert caps["platformName"] == "mac"
        assert caps["appium:automationName"] == "Mac2"
        assert caps["appium:app"] == "/Applications/MyApp.app"

    @patch("webspec_driver.webdriver.Remote")
    def test_linux_capabilities(self, mock_remote):
        cfg = DriverConfig(
            mode="appium",
            app="/usr/bin/my-gtk-app",
            platform="linux",
        )
        create_driver(cfg)

        options = mock_remote.call_args[1]["options"]
        caps = options.capabilities
        assert caps["platformName"] == "Linux"
        assert caps["appium:automationName"] == "Linux"

    @patch("webspec_driver.webdriver.Remote")
    def test_custom_appium_server(self, mock_remote):
        cfg = DriverConfig(
            mode="appium",
            app="/app",
            platform="windows",
            appium_server="http://10.0.0.5:4723",
        )
        create_driver(cfg)
        assert mock_remote.call_args[1]["command_executor"] == "http://10.0.0.5:4723"

    @patch("webspec_driver.webdriver.Remote")
    def test_extra_capabilities_merged(self, mock_remote):
        cfg = DriverConfig(
            mode="appium",
            app="/app",
            platform="windows",
            appium_caps={
                "appium:newCommandTimeout": 300,
                "appium:createSessionTimeout": 30000,
            },
        )
        create_driver(cfg)

        options = mock_remote.call_args[1]["options"]
        caps = options.capabilities
        assert caps["appium:newCommandTimeout"] == 300
        assert caps["appium:createSessionTimeout"] == 30000

    @patch("webspec_driver.webdriver.Remote")
    def test_extra_caps_override_defaults(self, mock_remote):
        """User-provided caps should win over auto-generated ones."""
        cfg = DriverConfig(
            mode="appium",
            app="/app",
            platform="windows",
            appium_caps={"appium:automationName": "CustomDriver"},
        )
        create_driver(cfg)

        options = mock_remote.call_args[1]["options"]
        caps = options.capabilities
        assert caps["appium:automationName"] == "CustomDriver"

    def test_missing_app_raises(self):
        cfg = DriverConfig(mode="appium", app=None, platform="windows")
        with pytest.raises(ValueError, match="requires --app"):
            create_driver(cfg)

    def test_unsupported_platform_raises(self):
        cfg = DriverConfig(mode="appium", app="/app", platform="android")
        with pytest.raises(ValueError, match="Unsupported platform"):
            create_driver(cfg)

    @patch("webspec_driver.webdriver.Remote")
    def test_case_insensitive_platform(self, mock_remote):
        cfg = DriverConfig(mode="appium", app="/app", platform="Windows")
        create_driver(cfg)
        options = mock_remote.call_args[1]["options"]
        assert options.capabilities["platformName"] == "Windows"


# ═══════════════════════════════════════════════════════════════════════════
#  Cleanup
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanup:

    def test_cleanup_quits_driver(self):
        driver = MagicMock()
        cleanup_driver(driver)
        driver.quit.assert_called_once()

    def test_cleanup_kills_app_process(self):
        driver = MagicMock()
        proc = MagicMock()
        driver._webspec_app_proc = proc

        cleanup_driver(driver)
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once()

    def test_cleanup_handles_none(self):
        cleanup_driver(None)  # should not raise

    def test_cleanup_survives_quit_exception(self):
        driver = MagicMock()
        driver.quit.side_effect = Exception("already dead")
        cleanup_driver(driver)  # should not raise

    def test_cleanup_force_kills_stubborn_process(self):
        driver = MagicMock()
        proc = MagicMock()
        proc.wait.side_effect = subprocess.TimeoutExpired("x", 5)
        driver._webspec_app_proc = proc

        cleanup_driver(driver)
        proc.kill.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
#  DriverConfig defaults
# ═══════════════════════════════════════════════════════════════════════════

class TestDriverConfig:

    def test_defaults(self):
        cfg = DriverConfig()
        assert cfg.mode == "browser"
        assert cfg.browser == "chrome"
        assert cfg.headless is False
        assert cfg.debug_port == 9222
        assert cfg.launch_app is True
        assert cfg.appium_server == "http://localhost:4723"
        assert cfg.platform == "windows"
        assert cfg.appium_caps == {}

    def test_dataclass_is_mutable(self):
        cfg = DriverConfig()
        cfg.mode = "electron"
        cfg.app_path = "/my/app"
        assert cfg.mode == "electron"