import sys
from pathlib import Path

import pytest

import webspec_cli as cli_mod


class DummyOptions:
    def add_argument(self, *args, **kwargs):
        return None


class FakeParserObj:
    def __init__(self, args):
        self._args = args

    def add_argument(self, *args, **kwargs):
        return None

    def parse_args(self):
        return self._args


class FakeDriver:
    def __init__(self):
        self.quit_called = False
        self.wait_value = None

    def implicitly_wait(self, value):
        self.wait_value = value

    def quit(self):
        self.quit_called = True


class FakeRuntime:
    def __init__(self, driver, timeout, retry_timeout, retry_interval):
        self.driver = driver
        self.timeout = timeout
        self.retry_timeout = retry_timeout
        self.retry_interval = retry_interval
        self.variables = {}
        self.step_count = 0

    def run(self, ast):
        return None


def make_args(script_path, browser="chrome", report=False):
    class Args:
        pass
    args = Args()
    args.script = str(script_path)
    args.browser = browser
    args.headless = False
    args.timeout = 10
    args.retry_timeout = 5
    args.retry_interval = 0.3
    args.verbose = False
    args.base_url = None
    args.var = []
    args.report = report
    args.report_path = None
    return args


def test_parse_errors_after_two_runs_still_report_correct_line_numbers(
    monkeypatch, tmp_path, capsys
):
    script_path = tmp_path / "bad.ws"
    script_path.write_text('navigate to "x"\nthis is bad\n', encoding="utf-8")

    fake_driver_1 = FakeDriver()
    fake_driver_2 = FakeDriver()
    drivers = [fake_driver_1, fake_driver_2]

    args = make_args(script_path)

    monkeypatch.setattr(cli_mod.argparse, "ArgumentParser", lambda *a, **k: FakeParserObj(args))
    monkeypatch.setattr(cli_mod.webdriver, "ChromeOptions", lambda: DummyOptions())
    monkeypatch.setattr(cli_mod.webdriver, "Chrome", lambda options=None: drivers.pop(0))

    def fake_parse(script_text, lexer):
        # Simulate parser mutating lexer state before failing.
        lexer.lineno += 17
        raise SyntaxError(f"line {lexer.lineno}")

    monkeypatch.setattr(cli_mod.parser, "parse", fake_parse)
    monkeypatch.setattr(cli_mod, "WebSpecRuntime", FakeRuntime)

    with pytest.raises(SystemExit) as exc1:
        cli_mod.main()
    out1 = capsys.readouterr().out
    assert exc1.value.code == 2
    assert "PARSE ERROR - line 18" in out1

    with pytest.raises(SystemExit) as exc2:
        cli_mod.main()
    out2 = capsys.readouterr().out
    assert exc2.value.code == 2
    assert "PARSE ERROR - line 18" in out2

    assert fake_driver_1.quit_called is True
    assert fake_driver_2.quit_called is True


def test_browser_init_failure_does_not_crash_in_finally(monkeypatch, tmp_path, capsys):
    script_path = tmp_path / "ok.ws"
    script_path.write_text('log "hello"\n', encoding="utf-8")

    args = make_args(script_path, browser="chrome")

    monkeypatch.setattr(cli_mod.argparse, "ArgumentParser", lambda *a, **k: FakeParserObj(args))
    monkeypatch.setattr(cli_mod.webdriver, "ChromeOptions", lambda: DummyOptions())

    def boom(*args, **kwargs):
        raise Exception("driver init blew up")

    monkeypatch.setattr(cli_mod.webdriver, "Chrome", boom)

    with pytest.raises(SystemExit) as exc:
        cli_mod.main()

    out = capsys.readouterr().out
    assert exc.value.code == 3
    assert "UNEXPECTED ERROR - driver init blew up" in out