"""
Unit tests for webspec_cli.py — the CLI entry point.

All driver creation is mocked via webspec_driver.create_driver / cleanup_driver.
No real browser is launched.

Run: pytest tests/test_cli.py -v
"""

import builtins
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

import webspec_cli
from webspec_driver import DriverConfig


# ---------------------------------------------------------------------------
#  Fakes
# ---------------------------------------------------------------------------

class DummyDriver:
    def __init__(self):
        self.quit_called = False
        self.implicit_wait_value = None
        self.browser = "chrome"
        self.mode = "browser"
        self.headless = False

    def implicitly_wait(self, t):
        self.implicit_wait_value = t

    def quit(self):
        self.quit_called = True


class DummyRuntime:
    def __init__(self, driver, timeout, retry_timeout, retry_interval,
                 row_failure_mode="collect"):
        self.driver = driver
        self.timeout = timeout
        self.retry_timeout = retry_timeout
        self.retry_interval = retry_interval
        self.row_failure_mode = row_failure_mode
        self.variables = {}
        self.step_count = 0
        self.steps = []
        self.failures = []
        self.screenshots_dir = None
        self._should_raise = None

    def run(self, ast):
        self.step_count = 1
        if self._should_raise:
            raise self._should_raise


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def run_cli(argv):
    """Run webspec_cli.main() with the given sys.argv, catching SystemExit."""
    old_argv = sys.argv
    try:
        sys.argv = argv
        webspec_cli.main()
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = old_argv
    return 0


# ---------------------------------------------------------------------------
#  Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_env(monkeypatch, tmp_path):
    created = SimpleNamespace(
        drivers=[],
        runtime=None,
        parsed_texts=[],
        parser_return=SimpleNamespace(kind="ast"),
        report_calls=[],
        print_lines=[],
        last_config=None,
    )

    # Capture print output
    monkeypatch.setattr(
        builtins, "print",
        lambda *args, **kwargs: created.print_lines.append(
            " ".join(str(a) for a in args)
        ),
    )

    # Fake parser
    def fake_parse(script_text, lexer=None):
        created.parsed_texts.append(script_text)
        return created.parser_return

    monkeypatch.setattr(webspec_cli.parser, "parse", fake_parse)

    # Fake runtime
    def fake_runtime_ctor(driver, timeout, retry_timeout, retry_interval,
                          row_failure_mode="collect"):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval,
                          row_failure_mode=row_failure_mode)
        created.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", fake_runtime_ctor)

    # Fake driver factory
    def fake_create_driver(cfg):
        created.last_config = cfg
        d = DummyDriver()
        d.browser = cfg.browser
        d.mode = cfg.mode
        d.headless = cfg.headless
        created.drivers.append(d)
        return d

    monkeypatch.setattr(webspec_cli, "create_driver", fake_create_driver)
    monkeypatch.setattr(
        webspec_cli, "cleanup_driver",
        lambda d: d.quit() if d and hasattr(d, "quit") else None,
    )

    # Fake report generator
    def fake_generate_report(runtime, script_name=None, output_path=None):
        created.report_calls.append({
            "runtime": runtime,
            "script_name": script_name,
            "output_path": output_path,
        })
        return output_path or "reports/report.html"

    # monkeypatch.setattr(webspec_cli, "generate_report", fake_generate_report, raising=False)
    import webspec_report
    monkeypatch.setattr(webspec_report, "generate_report", fake_generate_report)

    # Reset lexer state
    webspec_cli.lexer.lineno = 1

    yield created


# ═══════════════════════════════════════════════════════════════════════════
#  Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_success_exit_zero_and_quits_driver(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hello"\n', encoding="utf-8")

    code = run_cli(["prog", str(script), "--browser", "chrome"])

    assert code == 0
    assert len(cli_env.drivers) == 1
    assert cli_env.drivers[0].quit_called is True
    assert any("PASSED" in line for line in cli_env.print_lines)


def test_cli_passes_timeout_and_retry_settings_to_runtime(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--timeout", "20",
        "--retry-timeout", "8.5",
        "--retry-interval", "0.7",
    ])

    rt = cli_env.runtime
    assert rt.timeout == 20
    assert rt.retry_timeout == 8.5
    assert rt.retry_interval == 0.7


def test_cli_injects_var_values_into_runtime(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--var", "USER=alice",
        "--var", "PASS=secret",
    ])

    rt = cli_env.runtime
    assert rt.variables["USER"] == "alice"
    assert rt.variables["PASS"] == "secret"


def test_cli_replaces_base_url_from_flag(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('navigate to BASE_URL\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--base-url", "http://localhost:3000",
    ])

    parsed = cli_env.parsed_texts[0]
    assert "BASE_URL" not in parsed
    assert "http://localhost:3000" in parsed


def test_cli_replaces_base_url_from_local_test_site_html(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('navigate to BASE_URL\n', encoding="utf-8")

    fixture = tmp_path / "test_site.html"
    fixture.write_text("<html></html>", encoding="utf-8")

    run_cli(["prog", str(script)])

    parsed = cli_env.parsed_texts[0]
    assert "BASE_URL" not in parsed
    assert "test_site.html" in parsed


def test_cli_replaces_base_url_from_fixtures_test_site_html(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('navigate to BASE_URL\n', encoding="utf-8")

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    fixture = fixtures_dir / "test_site.html"
    fixture.write_text("<html></html>", encoding="utf-8")

    run_cli(["prog", str(script)])

    parsed = cli_env.parsed_texts[0]
    assert "BASE_URL" not in parsed
    assert "test_site.html" in parsed


def test_cli_leaves_script_unchanged_when_no_base_url_source_exists(
    cli_env, tmp_path, monkeypatch
):
    # Use a subdirectory with no test_site.html anywhere nearby
    sub = tmp_path / "isolated"
    sub.mkdir()
    script = sub / "ok.ws"
    script.write_text('navigate to BASE_URL\n', encoding="utf-8")

    # Ensure cwd doesn't have a fixtures/test_site.html either
    monkeypatch.chdir(sub)

    run_cli(["prog", str(script)])

    parsed = cli_env.parsed_texts[0]
    assert "BASE_URL" in parsed


def test_cli_generates_report_on_success_when_requested(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli(["prog", str(script), "--report"])

    assert len(cli_env.report_calls) == 1
    assert cli_env.report_calls[0]["script_name"] == "ok.ws"


def test_cli_runtime_failure_exits_one_generates_report_and_quits_driver(
    cli_env, tmp_path, monkeypatch
):
    script = tmp_path / "fail.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    # Make runtime.run() raise
    orig_ctor = webspec_cli.WebSpecRuntime

    def failing_runtime_ctor(**kwargs):
        # Handle both positional and keyword styles
        pass

    def make_failing_runtime(driver, timeout, retry_timeout, retry_interval,
                             row_failure_mode="collect"):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval,
                          row_failure_mode=row_failure_mode)
        rt._should_raise = AssertionError("element not found")
        cli_env.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", make_failing_runtime)

    code = run_cli(["prog", str(script), "--report"])

    assert code == 1
    assert cli_env.drivers[0].quit_called is True
    assert len(cli_env.report_calls) == 1
    assert any("FAILED" in line for line in cli_env.print_lines)


def test_cli_timeout_failure_exits_one(cli_env, tmp_path, monkeypatch):
    script = tmp_path / "fail.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    def make_timeout_runtime(driver, timeout, retry_timeout, retry_interval,
                             row_failure_mode="collect"):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval)
        rt._should_raise = TimeoutError("timed out")
        cli_env.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", make_timeout_runtime)

    code = run_cli(["prog", str(script)])
    assert code == 1


def test_cli_parse_error_exits_two_and_quits_driver(
    cli_env, tmp_path, monkeypatch
):
    script = tmp_path / "bad.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    def exploding_parse(script_text, lexer=None):
        raise SyntaxError("unexpected token")

    monkeypatch.setattr(webspec_cli.parser, "parse", exploding_parse)

    code = run_cli(["prog", str(script)])

    assert code == 2
    assert cli_env.drivers[0].quit_called is True


def test_cli_uses_chrome_headless_new_flag(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli(["prog", str(script), "--browser", "chrome", "--headless"])

    cfg = cli_env.last_config
    assert cfg.browser == "chrome"
    assert cfg.headless is True
    assert cfg.mode == "browser"


def test_cli_uses_firefox_headless_flag(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli(["prog", str(script), "--browser", "firefox", "--headless"])

    cfg = cli_env.last_config
    assert cfg.browser == "firefox"
    assert cfg.headless is True


def test_cli_uses_edge_headless_new_flag(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli(["prog", str(script), "--browser", "edge", "--headless"])

    cfg = cli_env.last_config
    assert cfg.browser == "edge"
    assert cfg.headless is True


def test_cli_driver_quit_still_runs_if_parser_raises(
    cli_env, tmp_path, monkeypatch
):
    script = tmp_path / "bad.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    def exploding_parse(script_text, lexer=None):
        raise SyntaxError("boom")

    monkeypatch.setattr(webspec_cli.parser, "parse", exploding_parse)

    run_cli(["prog", str(script)])

    assert len(cli_env.drivers) == 1
    assert cli_env.drivers[0].quit_called is True


def test_cli_reads_script_as_utf8(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "héllo wörld"\n', encoding="utf-8")

    code = run_cli(["prog", str(script)])

    assert code == 0
    parsed = cli_env.parsed_texts[0]
    assert "héllo wörld" in parsed


# ═══════════════════════════════════════════════════════════════════════════
#  New mode flags (electron / appium)
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_electron_mode_sets_config(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--mode", "electron",
        "--app-path", "/usr/bin/my-app",
        "--debug-port", "9333",
    ])

    cfg = cli_env.last_config
    assert cfg.mode == "electron"
    assert cfg.app_path == "/usr/bin/my-app"
    assert cfg.debug_port == 9333
    assert cfg.launch_app is True


def test_cli_electron_no_launch_flag(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--mode", "electron",
        "--app-path", "/app",
        "--no-launch",
    ])

    cfg = cli_env.last_config
    assert cfg.launch_app is False


def test_cli_appium_mode_sets_config(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli([
        "prog", str(script),
        "--mode", "appium",
        "--app", r"C:\MyApp\app.exe",
        "--platform", "windows",
        "--appium-server", "http://10.0.0.5:4723",
    ])

    cfg = cli_env.last_config
    assert cfg.mode == "appium"
    assert cfg.app == r"C:\MyApp\app.exe"
    assert cfg.platform == "windows"
    assert cfg.appium_server == "http://10.0.0.5:4723"


def test_cli_default_mode_is_browser(cli_env, tmp_path):
    script = tmp_path / "ok.ws"
    script.write_text('log "hi"\n', encoding="utf-8")

    run_cli(["prog", str(script)])

    cfg = cli_env.last_config
    assert cfg.mode == "browser"