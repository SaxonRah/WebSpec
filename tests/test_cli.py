# tests/test_cli.py
import sys
import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

import webspec_cli


class DummyDriver:
    def __init__(self):
        self.implicitly_wait_calls = []
        self.quit_called = False

    def implicitly_wait(self, value):
        self.implicitly_wait_calls.append(value)

    def quit(self):
        self.quit_called = True


class DummyRuntime:
    def __init__(self, driver, timeout, retry_timeout, retry_interval):
        self.driver = driver
        self.timeout = timeout
        self.retry_timeout = retry_timeout
        self.retry_interval = retry_interval
        self.variables = {}
        self.step_count = 7
        self.run_calls = []

    def run(self, ast):
        self.run_calls.append(ast)


class FakeOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        self.arguments.append(arg)


@pytest.fixture
def cli_env(monkeypatch, tmp_path):
    created = SimpleNamespace(
        chrome_options=[],
        firefox_options=[],
        edge_options=[],
        drivers=[],
        runtime=None,
        parsed_texts=[],
        parser_return=SimpleNamespace(kind="ast"),
        report_calls=[],
        print_lines=[],
    )

    # Capture print output from builtins, not from webspec_cli module
    monkeypatch.setattr(
        builtins,
        "print",
        lambda *args, **kwargs: created.print_lines.append(" ".join(str(a) for a in args)),
    )

    # Fake parser
    def fake_parse(script_text, lexer=None):
        created.parsed_texts.append(script_text)
        return created.parser_return

    monkeypatch.setattr(webspec_cli.parser, "parse", fake_parse)

    # Fake runtime
    def fake_runtime_ctor(driver, timeout, retry_timeout, retry_interval):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval)
        created.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", fake_runtime_ctor)

    # Fake webdriver options
    def chrome_options_ctor():
        opts = FakeOptions()
        created.chrome_options.append(opts)
        return opts

    def firefox_options_ctor():
        opts = FakeOptions()
        created.firefox_options.append(opts)
        return opts

    def edge_options_ctor():
        opts = FakeOptions()
        created.edge_options.append(opts)
        return opts

    # Fake webdriver constructors
    def chrome_ctor(options=None):
        d = DummyDriver()
        d.options = options
        d.browser = "chrome"
        created.drivers.append(d)
        return d

    def firefox_ctor(options=None):
        d = DummyDriver()
        d.options = options
        d.browser = "firefox"
        created.drivers.append(d)
        return d

    def edge_ctor(options=None):
        d = DummyDriver()
        d.options = options
        d.browser = "edge"
        created.drivers.append(d)
        return d

    monkeypatch.setattr(webspec_cli.webdriver, "ChromeOptions", chrome_options_ctor)
    monkeypatch.setattr(webspec_cli.webdriver, "FirefoxOptions", firefox_options_ctor)
    monkeypatch.setattr(webspec_cli.webdriver, "EdgeOptions", edge_options_ctor)
    monkeypatch.setattr(webspec_cli.webdriver, "Chrome", chrome_ctor)
    monkeypatch.setattr(webspec_cli.webdriver, "Firefox", firefox_ctor)
    monkeypatch.setattr(webspec_cli.webdriver, "Edge", edge_ctor)

    # Fake report module
    def fake_generate_report(runtime, script_name, output_path):
        created.report_calls.append(
            {
                "runtime": runtime,
                "script_name": script_name,
                "output_path": output_path,
            }
        )
        return str(tmp_path / "report.html")

    fake_report_module = SimpleNamespace(generate_report=fake_generate_report)
    monkeypatch.setitem(sys.modules, "webspec_report", fake_report_module)

    def run_cli(args):
        monkeypatch.setattr(sys, "argv", ["webspec_cli.py", *args])
        with pytest.raises(SystemExit) as exc:
            webspec_cli.main()
        return exc.value.code

    created.run_cli = run_cli
    return created


def write_script(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    return path


def test_cli_success_exit_zero_and_quits_driver(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli([str(script)])

    assert code == 0
    assert cli_env.runtime is not None
    assert cli_env.runtime.run_calls == [cli_env.parser_return]
    assert cli_env.drivers[0].quit_called is True
    assert any("PASSED" in line for line in cli_env.print_lines)


def test_cli_passes_timeout_and_retry_settings_to_runtime(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli(
        [
            str(script),
            "--timeout", "22",
            "--retry-timeout", "9.5",
            "--retry-interval", "0.75",
        ]
    )

    assert code == 0
    assert cli_env.runtime.timeout == 22
    assert cli_env.runtime.retry_timeout == 9.5
    assert cli_env.runtime.retry_interval == 0.75


def test_cli_injects_var_values_into_runtime(cli_env, tmp_path):
    script = write_script(tmp_path / "vars.ws", 'log "ok"\n')

    code = cli_env.run_cli(
        [
            str(script),
            "--var", "NAME=alice",
            "--var", "COUNT=42",
            "--var", "EMPTY=",
            "--var", "IGNORED_NO_EQUALS",
        ]
    )

    assert code == 0
    assert cli_env.runtime.variables["NAME"] == "alice"
    assert cli_env.runtime.variables["COUNT"] == "42"
    assert cli_env.runtime.variables["EMPTY"] == ""
    assert "IGNORED_NO_EQUALS" not in cli_env.runtime.variables


def test_cli_replaces_base_url_from_flag(cli_env, tmp_path):
    script = write_script(tmp_path / "uses_base.ws", 'open "BASE_URL"\n')

    code = cli_env.run_cli([str(script), "--base-url", "https://example.com"])

    assert code == 0
    assert cli_env.parsed_texts[-1] == 'open "https://example.com"\n'


def test_cli_replaces_base_url_from_local_test_site_html(cli_env, tmp_path):
    script = write_script(tmp_path / "uses_base.ws", 'open "BASE_URL"\n')
    html = tmp_path / "test_site.html"
    html.write_text("<html></html>", encoding="utf-8")

    code = cli_env.run_cli([str(script)])

    assert code == 0
    expected = html.resolve().as_uri()
    assert cli_env.parsed_texts[-1] == f'open "{expected}"\n'


def test_cli_replaces_base_url_from_fixtures_test_site_html(cli_env, tmp_path):
    script = write_script(tmp_path / "uses_base.ws", 'open "BASE_URL"\n')
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    html = fixtures_dir / "test_site.html"
    html.write_text("<html></html>", encoding="utf-8")

    code = cli_env.run_cli([str(script)])

    assert code == 0
    expected = html.resolve().as_uri()
    assert cli_env.parsed_texts[-1] == f'open "{expected}"\n'


def test_cli_leaves_script_unchanged_when_no_base_url_source_exists(cli_env, tmp_path):
    script = write_script(tmp_path / "uses_base.ws", 'open "BASE_URL"\n')

    code = cli_env.run_cli([str(script)])

    assert code == 0
    assert cli_env.parsed_texts[-1] == 'open "BASE_URL"\n'


def test_cli_generates_report_on_success_when_requested(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli([str(script), "--report", "--report-path", str(tmp_path / "out.html")])

    assert code == 0
    assert len(cli_env.report_calls) == 1
    call = cli_env.report_calls[0]
    assert call["runtime"] is cli_env.runtime
    assert call["script_name"] == "sample.ws"
    assert call["output_path"] == str(tmp_path / "out.html")
    assert any("Report:" in line for line in cli_env.print_lines)


def test_cli_runtime_failure_exits_one_generates_report_and_quits_driver(cli_env, tmp_path, monkeypatch):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    def fail_run(ast):
        raise AssertionError("boom")

    def fake_runtime_ctor(driver, timeout, retry_timeout, retry_interval):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval)
        rt.run = fail_run
        cli_env.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", fake_runtime_ctor)

    code = cli_env.run_cli([str(script), "--report"])

    assert code == 1
    assert len(cli_env.report_calls) == 1
    assert cli_env.drivers[0].quit_called is True
    assert any("FAILED" in line for line in cli_env.print_lines)


def test_cli_timeout_failure_exits_one(cli_env, tmp_path, monkeypatch):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    def fake_runtime_ctor(driver, timeout, retry_timeout, retry_interval):
        rt = DummyRuntime(driver, timeout, retry_timeout, retry_interval)

        def fail_run(ast):
            raise TimeoutError("too slow")

        rt.run = fail_run
        cli_env.runtime = rt
        return rt

    monkeypatch.setattr(webspec_cli, "WebSpecRuntime", fake_runtime_ctor)

    code = cli_env.run_cli([str(script)])

    assert code == 1
    assert any("FAILED" in line for line in cli_env.print_lines)
    assert cli_env.drivers[0].quit_called is True


def test_cli_parse_error_exits_two_and_quits_driver(cli_env, tmp_path, monkeypatch):
    script = write_script(tmp_path / "bad.ws", 'bad syntax\n')

    def raise_syntax(script_text, lexer=None):
        raise SyntaxError("parse broke")

    monkeypatch.setattr(webspec_cli.parser, "parse", raise_syntax)

    code = cli_env.run_cli([str(script)])

    assert code == 2
    assert any("PARSE ERROR" in line for line in cli_env.print_lines)
    assert cli_env.drivers[0].quit_called is True


def test_cli_uses_chrome_headless_new_flag(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli([str(script), "--browser", "chrome", "--headless"])

    assert code == 0
    assert len(cli_env.chrome_options) == 1
    assert "--headless=new" in cli_env.chrome_options[0].arguments
    assert cli_env.drivers[0].browser == "chrome"


def test_cli_uses_firefox_headless_flag(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli([str(script), "--browser", "firefox", "--headless"])

    assert code == 0
    assert len(cli_env.firefox_options) == 1
    assert "--headless" in cli_env.firefox_options[0].arguments
    assert cli_env.drivers[0].browser == "firefox"


def test_cli_uses_edge_headless_new_flag(cli_env, tmp_path):
    script = write_script(tmp_path / "sample.ws", 'log "ok"\n')

    code = cli_env.run_cli([str(script), "--browser", "edge", "--headless"])

    assert code == 0
    assert len(cli_env.edge_options) == 1
    assert "--headless=new" in cli_env.edge_options[0].arguments
    assert cli_env.drivers[0].browser == "edge"


def test_cli_driver_quit_still_runs_if_parser_raises(cli_env, tmp_path, monkeypatch):
    script = write_script(tmp_path / "bad.ws", 'bad syntax\n')

    def raise_syntax(script_text, lexer=None):
        raise SyntaxError("bad parse")

    monkeypatch.setattr(webspec_cli.parser, "parse", raise_syntax)

    code = cli_env.run_cli([str(script)])

    assert code == 2
    assert len(cli_env.drivers) == 1
    assert cli_env.drivers[0].quit_called is True


def test_cli_reads_script_as_utf8(cli_env, tmp_path):
    script = write_script(tmp_path / "utf8.ws", 'log "héllo"\n')

    code = cli_env.run_cli([str(script)])

    assert code == 0
    assert cli_env.parsed_texts[-1] == 'log "héllo"\n'