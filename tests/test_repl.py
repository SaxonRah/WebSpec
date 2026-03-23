# tests/test_repl.py
import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import webspec_repl


class DummyDriver:
    def __init__(self):
        self.current_url = "https://example.test/page"
        self.title = "Example Title"
        self.page_source = "<html><body>hello</body></html>"
        self.quit_called = False
        self.implicitly_wait_calls = []
        self.get_calls = []
        self.saved_screenshots = []

    def implicitly_wait(self, value):
        self.implicitly_wait_calls.append(value)

    def get(self, url):
        self.get_calls.append(url)
        self.current_url = url

    def save_screenshot(self, path):
        self.saved_screenshots.append(path)
        Path(path).write_bytes(b"fakepng")
        return True

    def quit(self):
        self.quit_called = True


class DummyRuntime:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout
        self.variables = {}
        self.step_count = 0
        self.run_calls = []
        self.exec_block_calls = []

    def run(self, ast):
        self.run_calls.append(ast)

    def exec_block(self, statements):
        self.exec_block_calls.append(statements)
        self.step_count += len(statements)


class FakeOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        self.arguments.append(arg)


class FakeAST:
    def __init__(self, statements=None):
        self.statements = statements if statements is not None else [object()]


@pytest.fixture
def repl_env(monkeypatch, tmp_path):
    created = SimpleNamespace(
        chrome_options=[],
        firefox_options=[],
        edge_options=[],
        drivers=[],
        runtime=None,
        parsed_texts=[],
    )

    monkeypatch.chdir(tmp_path)

    def fake_parse(script_text, lexer=None):
        created.parsed_texts.append(script_text)
        return FakeAST()

    monkeypatch.setattr(webspec_repl.parser, "parse", fake_parse)

    def fake_runtime_ctor(driver, timeout):
        rt = DummyRuntime(driver=driver, timeout=timeout)
        created.runtime = rt
        return rt

    monkeypatch.setattr(webspec_repl, "WebSpecRuntime", fake_runtime_ctor)

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

    monkeypatch.setattr(webspec_repl.webdriver, "ChromeOptions", chrome_options_ctor)
    monkeypatch.setattr(webspec_repl.webdriver, "FirefoxOptions", firefox_options_ctor)
    monkeypatch.setattr(webspec_repl.webdriver, "EdgeOptions", edge_options_ctor)
    monkeypatch.setattr(webspec_repl.webdriver, "Chrome", chrome_ctor)
    monkeypatch.setattr(webspec_repl.webdriver, "Firefox", firefox_ctor)
    monkeypatch.setattr(webspec_repl.webdriver, "Edge", edge_ctor)

    def run_main(args=None, inputs=None):
        args = args or []
        inputs = list(inputs or [])

        it = iter(inputs)

        def fake_input(prompt=""):
            try:
                return next(it)
            except StopIteration:
                raise EOFError()

        monkeypatch.setattr(sys, "argv", ["webspec_repl.py", *args])
        monkeypatch.setattr(builtins, "input", fake_input)

        webspec_repl.main()

    created.run_main = run_main
    return created


def test_is_block_start_empty_and_whitespace_false():
    assert webspec_repl.is_block_start("") is False
    assert webspec_repl.is_block_start("   ") is False
    assert webspec_repl.is_block_start("\t  ") is False


@pytest.mark.parametrize(
    "line",
    [
        'if url contains "x" then',
        "repeat 3 times",
        "for each row in table",
        "try",
        "define login:",
        "using data.csv",
        "IF something",
        "  For item in list",
    ],
)
def test_is_block_start_recognizes_keywords(line):
    assert webspec_repl.is_block_start(line) is True


def test_clear_empties_variables_and_vars_command_prints(capsys, repl_env, monkeypatch):
    def fake_runtime_ctor(driver, timeout):
        rt = DummyRuntime(driver=driver, timeout=timeout)
        rt.variables = {"name": "alice", "count": 42}
        repl_env.runtime = rt
        return rt

    monkeypatch.setattr(webspec_repl, "WebSpecRuntime", fake_runtime_ctor)

    repl_env.run_main(inputs=[":vars", ":clear", ":vars", ":quit"])
    out = capsys.readouterr().out

    assert "$name = alice" in out
    assert "$count = 42" in out
    assert "Variables cleared" in out
    assert "(no variables set)" in out
    assert repl_env.runtime.variables == {}
    assert repl_env.drivers[0].quit_called is True


def test_run_missing_file_fails_cleanly(capsys, repl_env):
    repl_env.run_main(inputs=[":run missing.ws", ":quit"])
    out = capsys.readouterr().out

    assert "✗" in out
    assert "missing.ws" in out or "No such file" in out or "cannot find" in out.lower()
    assert repl_env.drivers[0].quit_called is True


def test_multiline_backslash_continuation_combines_lines(capsys, repl_env):
    repl_env.run_main(
        inputs=[
            'log "hello"\\',
            '+ " world"',
            ":quit",
        ]
    )
    out = capsys.readouterr().out

    assert repl_env.parsed_texts[-1] == 'log "hello"\n+ " world"'
    assert "✓ OK" in out
    assert repl_env.runtime.exec_block_calls
    assert repl_env.drivers[0].quit_called is True


def test_block_construct_auto_detect_reads_until_end(capsys, repl_env):
    repl_env.run_main(
        inputs=[
            'if url contains "x" then',
            'log "inside"',
            "end",
            ":quit",
        ]
    )
    out = capsys.readouterr().out

    assert repl_env.parsed_texts[-1] == 'if url contains "x" then\nlog "inside"\nend'
    assert "✓ OK" in out
    assert repl_env.drivers[0].quit_called is True


def test_history_vars_url_title_and_source_commands_do_not_crash(capsys, repl_env, tmp_path):
    repl_env.run_main(
        inputs=[
            'log "first"',
            ":history",
            ":vars",
            ":url",
            ":title",
            ":source",
            ":quit",
        ]
    )
    out = capsys.readouterr().out

    assert '1: log "first"' in out
    assert "(no variables set)" in out
    assert "https://example.test/page" in out
    assert "Example Title" in out
    assert "Saved: repl_source.html" in out

    source_path = tmp_path / "repl_source.html"
    assert source_path.exists()
    assert "hello" in source_path.read_text(encoding="utf-8")

    assert repl_env.drivers[0].quit_called is True


def test_screenshot_command_saves_file(capsys, repl_env, tmp_path):
    repl_env.run_main(inputs=[":screenshot", ":quit"])
    out = capsys.readouterr().out

    assert "Saved: repl_screenshot_0.png" in out
    shot = tmp_path / "repl_screenshot_0.png"
    assert shot.exists()
    assert repl_env.drivers[0].saved_screenshots == ["repl_screenshot_0.png"]
    assert repl_env.drivers[0].quit_called is True


def test_run_command_executes_script_file(capsys, repl_env, tmp_path):
    script = tmp_path / "sample.ws"
    script.write_text('log "from file"\n', encoding="utf-8")

    repl_env.run_main(inputs=[f":run {script}", ":quit"])
    out = capsys.readouterr().out

    assert repl_env.parsed_texts[-1] == 'log "from file"\n'
    assert repl_env.runtime.run_calls
    assert "completed" in out
    assert repl_env.drivers[0].quit_called is True


def test_startup_url_navigates_driver(capsys, repl_env):
    repl_env.run_main(args=["--url", "https://start.example"], inputs=[":quit"])
    out = capsys.readouterr().out

    assert "Navigated to: https://start.example" in out
    assert repl_env.drivers[0].get_calls == ["https://start.example"]
    assert repl_env.drivers[0].current_url == "https://start.example"
    assert repl_env.drivers[0].quit_called is True


def test_headless_browser_flags_are_applied(capsys, repl_env):
    repl_env.run_main(args=["--browser", "chrome", "--headless"], inputs=[":quit"])
    _ = capsys.readouterr()

    assert repl_env.drivers[0].browser == "chrome"
    assert "--headless=new" in repl_env.chrome_options[0].arguments

    repl_env.run_main(args=["--browser", "firefox", "--headless"], inputs=[":quit"])
    _ = capsys.readouterr()

    assert repl_env.drivers[1].browser == "firefox"
    assert "--headless" in repl_env.firefox_options[0].arguments

    repl_env.run_main(args=["--browser", "edge", "--headless"], inputs=[":quit"])
    _ = capsys.readouterr()

    assert repl_env.drivers[2].browser == "edge"
    assert "--headless=new" in repl_env.edge_options[0].arguments


def test_unknown_command_does_not_crash(capsys, repl_env):
    repl_env.run_main(inputs=[":doesnotexist", ":quit"])
    out = capsys.readouterr().out

    assert "Unknown command" in out
    assert repl_env.drivers[0].quit_called is True