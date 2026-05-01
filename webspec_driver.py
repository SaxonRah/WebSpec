"""
WebSpec DSL - Driver Factory

Abstracts driver creation so the runtime doesn't care whether it's
talking to a browser, an Electron app, or a native app via Appium.
"""

import subprocess
import sys
import time
import logging
import socket
from dataclasses import dataclass, field
from typing import Optional

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class DriverConfig:
    """Everything the factory needs to build a driver."""
    mode: str = "browser"                    # browser | electron | appium
    browser: str = "chrome"                  # chrome | firefox | edge  (browser mode)
    headless: bool = False

    # Electron / CEF
    app_path: Optional[str] = None           # path to the Electron binary
    debug_port: int = 9222
    launch_app: bool = True                  # False = assume app is already running

    # Appium
    appium_server: str = "http://localhost:4723"
    app: Optional[str] = None                # path or bundle id
    platform: str = "windows"                # windows | mac | linux
    appium_caps: dict = field(default_factory=dict)  # extra desired capabilities


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    """Block until a TCP port is accepting connections, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _detect_electron(app_path: str) -> bool:
    """
    Heuristic: try to detect if a binary is an Electron app.
    Runs `<app> --version` and checks for 'Electron' in the output.
    Returns False on any failure — caller should still try connecting.
    """
    try:
        result = subprocess.run(
            [app_path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        combined = result.stdout + result.stderr
        return "electron" in combined.lower() or "chromium" in combined.lower()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_driver(cfg: DriverConfig) -> WebDriver:
    """Build and return a WebDriver for the given mode."""

    if cfg.mode == "browser":
        return _create_browser_driver(cfg)
    elif cfg.mode == "electron":
        return _create_electron_driver(cfg)
    elif cfg.mode == "appium":
        return _create_appium_driver(cfg)
    else:
        raise ValueError(f"Unknown driver mode: {cfg.mode!r}")


# -- browser (existing behaviour, extracted) --------------------------------

def _create_browser_driver(cfg: DriverConfig) -> WebDriver:
    if cfg.browser == "chrome":
        opts = webdriver.ChromeOptions()
        if cfg.headless:
            opts.add_argument("--headless=new")
        return webdriver.Chrome(options=opts)

    elif cfg.browser == "firefox":
        opts = webdriver.FirefoxOptions()
        if cfg.headless:
            opts.add_argument("--headless")
        return webdriver.Firefox(options=opts)

    elif cfg.browser == "edge":
        opts = webdriver.EdgeOptions()
        if cfg.headless:
            opts.add_argument("--headless=new")
        return webdriver.Edge(options=opts)

    raise ValueError(f"Unsupported browser: {cfg.browser!r}")


# -- electron / CEF --------------------------------------------------------

def _create_electron_driver(cfg: DriverConfig) -> WebDriver:
    """
    Connect ChromeDriver to an Electron/CEF app's DevTools port.

    If launch_app is True, starts the app binary with
    --remote-debugging-port and waits for the port to open.
    Otherwise assumes the app is already running.
    """
    if not cfg.app_path:
        raise ValueError("electron mode requires --app-path")

    proc = None
    if cfg.launch_app:
        cmd = [cfg.app_path, f"--remote-debugging-port={cfg.debug_port}"]
        logger.info("Launching Electron app: %s", " ".join(cmd))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not _wait_for_port("127.0.0.1", cfg.debug_port):
            proc.terminate()
            raise RuntimeError(
                f"Electron app did not open debug port {cfg.debug_port} within timeout"
            )

    opts = webdriver.ChromeOptions()
    opts.debugger_address = f"127.0.0.1:{cfg.debug_port}"

    if cfg.headless:
        opts.add_argument("--headless=new")

    driver = webdriver.Chrome(options=opts)

    # Stash the subprocess so we can clean up later
    driver._webspec_app_proc = proc
    return driver


# -- appium -----------------------------------------------------------------

# Map WebSpec's platform names to Appium platformName values
_APPIUM_PLATFORM_MAP = {
    "windows": "Windows",
    "mac":     "mac",
    "linux":   "Linux",
}

# Map WebSpec's platform names to Appium automationName values
_APPIUM_AUTOMATION_MAP = {
    "windows": "Windows",      # WinAppDriver
    "mac":     "Mac2",         # XCTest-based
    "linux":   "Linux",        # experimental
}


def _create_appium_driver(cfg: DriverConfig) -> WebDriver:
    """
    Create an Appium Remote driver for native desktop app testing.

    Requires:
      - Appium server running at cfg.appium_server
      - WinAppDriver (Windows), mac2 driver (Mac), or equivalent
    """
    if not cfg.app:
        raise ValueError("appium mode requires --app (path or bundle ID)")

    platform_key = cfg.platform.lower()
    if platform_key not in _APPIUM_PLATFORM_MAP:
        raise ValueError(
            f"Unsupported platform {cfg.platform!r}. "
            f"Supported: {list(_APPIUM_PLATFORM_MAP.keys())}"
        )

    caps = {
        "platformName":    _APPIUM_PLATFORM_MAP[platform_key],
        "appium:automationName": _APPIUM_AUTOMATION_MAP[platform_key],
        "appium:app":      cfg.app,
    }
    # Merge any extra capabilities (user-provided overrides win)
    caps.update(cfg.appium_caps)

    from selenium.webdriver.common.options import ArgOptions

    options = ArgOptions()
    for k, v in caps.items():
        options.set_capability(k, v)

    driver = webdriver.Remote(
        command_executor=cfg.appium_server,
        options=options,
    )
    return driver


# ---------------------------------------------------------------------------
# Cleanup helper
# ---------------------------------------------------------------------------

def cleanup_driver(driver: Optional[WebDriver]):
    """Quit the driver and kill any app process we launched."""
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        pass
    proc = getattr(driver, "_webspec_app_proc", None)
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
