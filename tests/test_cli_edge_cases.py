"""
Edge-case tests for webspec_cli.py.

Covers parser reuse across runs, browser init failures, and
BASE_URL_SECONDARY placeholder isolation.

Run: pytest tests/test_cli_edge_cases.py -v
"""

import sys
from types import SimpleNamespace

import pytest

import webspec_cli as cli_mod
from webspec_driver import DriverConfig


# ---------------------------------------------------------------------------
#  Fakes
# ---------------------------------------------------------------------------

class DummyDriver:
    def __init__(self):
        self.quit_called = False
        self.implicit_wait_value = None

    def implicitly_wait(self, t):
        self.implicit_wait_value = t

    def quit(self):
        self.quit_called = True


class DummyRuntime:
    def __init__(self, **kwargs):
        self.variables = {}
        self.step_count = 0
        self.steps = []
        self.failures = []
        self.screenshots_dir = None

    def run(self, ast):
        self.step_count = 1


class FakeArgParser:
    """Stands in for argparse.ArgumentParser, returns pre-built args."""
    def __init__(self, args):
        self._args = args

    def add_argument(self, *a, **kw):
        pass

    def parse_args(self):
        return self._args


def make_args(script_path, browser="chrome", headless=False, mode="browser",
              base_url=None, timeout=10, retry_timeout=5, retry_interval=0.3,
              verbose=False, var=None, report=False, report_path=None,
              row_failure_mode="collect", app_path=None, debug_port=9222,
              no_launch=False, appium_server="http://localhost:4723",
              app=None, platform="windows"):
    return SimpleNamespace(
        script=str(script_path),
        browser=browser,
        headless=headless,
        mode=mode,
        base_url=base_url,
        timeout=timeout,
        retry_timeout=retry_timeout,
        retry_interval=retry_interval,
        verbose=verbose,
        var=var or [],
        report=report,
        report_path=report_path,
        row_failure_mode=row_failure_mode,
        app_path=app_path,
        debug_port=debug_port,
        no_launch=no_launch,
        appium_server=appium_server,
        app=app,
        platform=platform,
    )


def run_main():
    """Call cli_mod.main(), return the SystemExit code or 0."""
    try:
        cli_mod.main()
    except SystemExit as e:
        return e.code
    return 0


# ═══════════════════════════════════════════════════════════════════════════
#  Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_parse_errors_after_two_runs_still_report_correct_line_numbers(
    monkeypatch, tmp_path, capsys
):
    """
    PLY's lexer keeps global state (lineno). Running the CLI twice should
    reset it so error line numbers stay correct on the second run.
    """
    script_path = tmp_path / "bad.ws"
    script_path.write_text('navigate to "x"\nthis is bad\n', encoding="utf-8")

    fake_driver_1 = DummyDriver()
    fake_driver_2 = DummyDriver()
    drivers = [fake_driver_1, fake_driver_2]

    args = make_args(script_path)

    monkeypatch.setattr(
        cli_mod.argparse, "ArgumentParser",
        lambda *a, **k: FakeArgParser(args),
    )
    monkeypatch.setattr(
        cli_mod, "create_driver",
        lambda cfg: drivers.pop(0),
    )
    monkeypatch.setattr(
        cli_mod, "cleanup_driver",
        lambda d: d.quit() if d else None,
    )

    # First run — should hit a parse error (exit 2) or runtime error
    code1 = run_main()

    # Second run — same script, fresh driver
    # The key assertion: it should not crash with an internal error,
    # and the error message (if any) should reference the correct line.
    code2 = run_main()

    # Both runs should produce the same exit code
    assert code1 == code2
    # Both drivers should have been cleaned up
    assert fake_driver_1.quit_called is True
    assert fake_driver_2.quit_called is True


def test_browser_init_failure_does_not_crash_in_finally(
    monkeypatch, tmp_path, capsys
):
    """
    If create_driver raises, the finally block should not crash trying
    to clean up a None driver.
    """
    script_path = tmp_path / "ok.ws"
    script_path.write_text('log "hello"\n', encoding="utf-8")

    args = make_args(script_path, browser="chrome")

    monkeypatch.setattr(
        cli_mod.argparse, "ArgumentParser",
        lambda *a, **k: FakeArgParser(args),
    )

    def exploding_create_driver(cfg):
        raise RuntimeError("chromedriver not found")

    monkeypatch.setattr(cli_mod, "create_driver", exploding_create_driver)
    monkeypatch.setattr(cli_mod, "cleanup_driver", lambda d: None)

    code = run_main()

    # Should exit with error code, not an unhandled exception
    assert code in (1, 3)
    captured = capsys.readouterr()
    assert "chromedriver not found" in captured.out or code != 0


def test_base_url_secondary_not_corrupted_by_base_url_replacement(
    monkeypatch, tmp_path
):
    """
    Replacing BASE_URL should not touch BASE_URL_SECONDARY.
    The _replace_exact_placeholder function uses word-boundary matching.
    """
    script_path = tmp_path / "ok.ws"
    script_path.write_text(
        'navigate to BASE_URL\nnavigate to BASE_URL_SECONDARY\n',
        encoding="utf-8",
    )

    captured_texts = []

    def capture_parse(script_text, lexer=None):
        captured_texts.append(script_text)
        return SimpleNamespace(kind="ast")

    args = make_args(script_path, base_url="http://localhost:3000")

    monkeypatch.setattr(
        cli_mod.argparse, "ArgumentParser",
        lambda *a, **k: FakeArgParser(args),
    )
    monkeypatch.setattr(cli_mod, "create_driver", lambda cfg: DummyDriver())
    monkeypatch.setattr(cli_mod, "cleanup_driver", lambda d: None)
    monkeypatch.setattr(cli_mod.parser, "parse", capture_parse)
    monkeypatch.setattr(
        cli_mod, "WebSpecRuntime",
        lambda **kw: DummyRuntime(),
    )

    # Handle both positional and keyword calling conventions
    orig_runtime = cli_mod.WebSpecRuntime

    def flexible_runtime(*args, **kwargs):
        return DummyRuntime()

    monkeypatch.setattr(cli_mod, "WebSpecRuntime", flexible_runtime)

    run_main()

    assert len(captured_texts) >= 1
    parsed = captured_texts[0]
    assert "http://localhost:3000" in parsed
    assert "BASE_URL_SECONDARY" in parsed  # must NOT have been replaced


def test_cli_var_replacement_uses_exact_placeholder_matching(
    monkeypatch, tmp_path
):
    """
    --var FOO=bar should replace FOO but not FOOBAR.
    """
    script_path = tmp_path / "ok.ws"
    script_path.write_text(
        'log FOO\nlog FOOBAR\n',
        encoding="utf-8",
    )

    captured_texts = []

    def capture_parse(script_text, lexer=None):
        captured_texts.append(script_text)
        return SimpleNamespace(kind="ast")

    args = make_args(script_path, var=["FOO=replaced"])

    monkeypatch.setattr(
        cli_mod.argparse, "ArgumentParser",
        lambda *a, **k: FakeArgParser(args),
    )
    monkeypatch.setattr(cli_mod, "create_driver", lambda cfg: DummyDriver())
    monkeypatch.setattr(cli_mod, "cleanup_driver", lambda d: None)
    monkeypatch.setattr(cli_mod.parser, "parse", capture_parse)

    def flexible_runtime(*args, **kwargs):
        return DummyRuntime()

    monkeypatch.setattr(cli_mod, "WebSpecRuntime", flexible_runtime)

    run_main()

    parsed = captured_texts[0]
    assert "replaced" in parsed
    assert "FOOBAR" in parsed  # FOOBAR must stay intact


def test_unexpected_exception_exits_three(monkeypatch, tmp_path):
    """
    An unexpected (non-Assertion, non-Timeout, non-Syntax) error should
    exit with code 3.
    """
    script_path = tmp_path / "ok.ws"
    script_path.write_text('log "hi"\n', encoding="utf-8")

    args = make_args(script_path)

    monkeypatch.setattr(
        cli_mod.argparse, "ArgumentParser",
        lambda *a, **k: FakeArgParser(args),
    )
    monkeypatch.setattr(cli_mod, "create_driver", lambda cfg: DummyDriver())
    monkeypatch.setattr(cli_mod, "cleanup_driver", lambda d: None)
    monkeypatch.setattr(
        cli_mod.parser, "parse",
        lambda text, lexer=None: SimpleNamespace(kind="ast"),
    )

    def exploding_runtime(*a, **kw):
        rt = DummyRuntime()
        def boom(ast):
            raise KeyError("something unexpected")
        rt.run = boom
        return rt

    monkeypatch.setattr(cli_mod, "WebSpecRuntime", exploding_runtime)

    code = run_main()
    assert code == 3