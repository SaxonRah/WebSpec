"""
Tests for the five new features:
  1. Auto-retry smart waits
  2. Import system
  3. Data-driven testing
  4. REPL (smoke test only - interactive)
  5. HTML report generation
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_ast import *
from webspec_runtime import WebSpecRuntime


def parse(text):
    lexer.lineno = 1
    return parser.parse(text, lexer=lexer)


def parse_one(text):
    prog = parse(text)
    stmts = [s for s in prog.statements if s is not None]
    assert len(stmts) == 1
    return stmts[0]


# ═══════════════════════════════════════════════════════════
#  Import System
# ═══════════════════════════════════════════════════════════

class TestImportParsing:
    def test_import_parses(self):
        node = parse_one('import "common/login.ws"')
        assert isinstance(node, Import)
        assert node.filepath == 'common/login.ws'

    def test_import_in_script(self):
        script = '''import "setup.ws"
click the button "Go"'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 2
        assert isinstance(stmts[0], Import)
        assert isinstance(stmts[1], Click)


# ═══════════════════════════════════════════════════════════
#  Data-Driven Testing
# ═══════════════════════════════════════════════════════════

class TestDataDrivenParsing:
    def test_using_parses(self):
        script = '''using "users.csv"
log $name
end'''
        node = parse_one(script)
        assert isinstance(node, WithData)
        assert node.filepath == 'users.csv'
        assert len(node.body) == 1

    def test_using_json(self):
        script = '''using "config.json"
navigate to $url
click the button $action
end'''
        node = parse_one(script)
        assert isinstance(node, WithData)
        assert len(node.body) == 2


class TestDataDrivenRuntime:
    def test_csv_iteration(self, tmp_path):
        csv_file = tmp_path / 'test.csv'
        csv_file.write_text(
            'name,email\nAlice,a@test.com\nBob,b@test.com',
            encoding='utf-8'
        )

        driver = MagicMock()
        type(driver).page_source = PropertyMock(return_value='<html></html>')
        type(driver).current_url = PropertyMock(return_value='http://x.com')
        type(driver).title = PropertyMock(return_value='Test')

        rt = WebSpecRuntime(driver=driver, timeout=2)

        seen = []

        original_exec_log = rt._exec_Log

        def capture_log(t_node):
            seen.append(rt._eval_expr(t_node.message))

        rt._exec_Log = capture_log

        node = WithData(
            filepath=str(csv_file),
            body=[Log(message=VarRef(name='name'))],
        )
        rt._exec(node)

        assert seen == ['Alice', 'Bob']
        assert rt.variables == {}
        assert rt.errors == []

    def test_json_iteration(self, tmp_path):
        json_file = tmp_path / 'test.json'
        json_file.write_text(
            json.dumps([
                {'url': 'http://a.com', 'title': 'A'},
                {'url': 'http://b.com', 'title': 'B'},
            ]),
            encoding='utf-8'
        )

        driver = MagicMock()
        type(driver).page_source = PropertyMock(return_value='<html></html>')
        type(driver).current_url = PropertyMock(return_value='http://x.com')
        type(driver).title = PropertyMock(return_value='Test')

        rt = WebSpecRuntime(driver=driver, timeout=2)

        seen = []

        def capture_log(t_node):
            seen.append(rt._eval_expr(t_node.message))

        rt._exec_Log = capture_log

        node = WithData(
            filepath=str(json_file),
            body=[Log(message=VarRef(name='url'))],
        )
        rt._exec(node)

        assert seen == ['http://a.com', 'http://b.com']
        assert rt.variables == {}
        assert rt.errors == []

    def test_missing_file_raises(self):
        driver = MagicMock()
        type(driver).page_source = PropertyMock(return_value='<html></html>')

        rt = WebSpecRuntime(driver=driver)
        node = WithData(filepath='nonexistent.csv', body=[])

        with pytest.raises(RuntimeError, match="not found"):
            rt._exec(node)


# ═══════════════════════════════════════════════════════════
#  Auto-Retry Smart Waits
# ═══════════════════════════════════════════════════════════

class TestAutoRetry:
    def test_retry_succeeds_on_second_attempt(self):
        from webspec_resolver import SmartResolver

        html_v1 = '<html><body></body></html>'
        html_v2 = '<html><body><button id="btn">OK</button></body></html>'

        call_count = 0

        def get_source():
            nonlocal call_count
            call_count += 1
            return html_v2 if call_count > 1 else html_v1

        driver = MagicMock()
        type(driver).page_source = PropertyMock(side_effect=get_source)
        driver.find_element.return_value = MagicMock()

        resolver = SmartResolver(driver, retry_timeout=2, retry_interval=0.1)
        ref = ElementRef(elem_type='button', selectors=[
            Selector(kind='text', value='OK')
        ])

        el = resolver.resolve(ref)
        assert el is not None
        assert call_count >= 2  # Had to retry at least once

    def test_retry_times_out(self):
        from webspec_resolver import SmartResolver

        driver = MagicMock()
        type(driver).page_source = PropertyMock(
            return_value='<html><body></body></html>')

        resolver = SmartResolver(driver, retry_timeout=0.5, retry_interval=0.1)
        ref = ElementRef(elem_type='button', selectors=[
            Selector(kind='text', value='Nonexistent')
        ])

        with pytest.raises(RuntimeError, match="No element found"):
            resolver.resolve(ref)


# ═══════════════════════════════════════════════════════════
#  HTML Report Generation
# ═══════════════════════════════════════════════════════════

class TestReportGeneration:
    def test_report_creates_file(self, tmp_path):
        from webspec_report import generate_report

        driver = MagicMock()
        type(driver).page_source = PropertyMock(return_value='<html></html>')

        rt = WebSpecRuntime(driver=driver,
                            screenshot_dir=str(tmp_path / 'screenshots'))
        rt.step_timings = [
            {'step': 1, 'type': 'Navigate', 'line': 1,
             'status': 'pass', 'duration': 0.5, 'error': None},
            {'step': 2, 'type': 'Click', 'line': 2,
             'status': 'pass', 'duration': 0.2, 'error': None},
            {'step': 3, 'type': 'VerifyState', 'line': 3,
             'status': 'fail', 'duration': 0.1,
             'error': 'Element is not visible'},
        ]
        rt.variables = {'page': 'http://example.com', 'count': '5'}

        output = tmp_path / 'report.html'
        path = generate_report(
            rt, script_name='test.ws', output_path=str(output))

        assert Path(path).exists()
        content = Path(path).read_text()
        assert 'FAILED' in content
        assert '2/3 steps passed' in content
        assert 'Navigate' in content
        assert 'Element is not visible' in content
        assert '$page' in content

    def test_report_all_pass(self, tmp_path):
        from webspec_report import generate_report

        driver = MagicMock()
        type(driver).page_source = PropertyMock(return_value='<html></html>')

        rt = WebSpecRuntime(driver=driver,
                            screenshot_dir=str(tmp_path / 'screenshots'))
        rt.step_timings = [
            {'step': 1, 'type': 'Navigate', 'line': 1,
             'status': 'pass', 'duration': 0.3, 'error': None},
        ]

        output = tmp_path / 'report.html'
        path = generate_report(
            rt, script_name='test.ws', output_path=str(output))

        content = Path(path).read_text()
        assert 'PASSED' in content
        assert '1/1 steps passed' in content