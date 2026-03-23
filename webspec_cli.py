"""
WebSpec DSL - CLI Entry Point
Usage: python webspec_cli.py test_script.ws [--browser chrome|firefox]
"""

import argparse
import logging
import sys
from pathlib import Path
import re

from selenium import webdriver

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime

def _parse_cli_vars(var_args):
    parsed = {}
    for var_str in var_args:
        if '=' in var_str:
            name, value = var_str.split('=', 1)
            parsed[name] = value
    return parsed

def _replace_exact_placeholder(script_text: str, name: str, value: str) -> str:
    """
    Replace only the exact placeholder token, not prefixes of longer names.

    Examples:
      BASE_URL            -> replaced
      "BASE_URL"          -> replaced
      BASE_URL_SECONDARY  -> NOT touched when name == "BASE_URL"
    """
    pattern = rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])'
    return re.sub(pattern, value, script_text)

def main():
    ap = argparse.ArgumentParser(description='WebSpec DSL Test Runner')
    ap.add_argument('script', help='Path to .ws test script')
    ap.add_argument('--browser', default='chrome', choices=['chrome', 'firefox', 'edge'])
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--timeout', type=int, default=10)
    ap.add_argument('--retry-timeout', type=float, default=5,
                    help='Auto-retry timeout for element resolution (seconds)')
    ap.add_argument('--retry-interval', type=float, default=0.3,
                    help='Interval between retry attempts (seconds)')
    ap.add_argument('--verbose', '-v', action='store_true')
    ap.add_argument('--base-url', default=None,
                    help='Replace BASE_URL in script with this value')
    ap.add_argument('--var', action='append', default=[],
                    help='Set a variable: --var NAME=VALUE (repeatable)')
    ap.add_argument('--report', action='store_true',
                    help='Generate HTML test report')
    ap.add_argument('--report-path', default=None,
                    help='Output path for HTML report')
    ap.add_argument('--row-failure-mode', default='collect',
                    choices=['collect', 'fail_fast'],
                    help='Behavior for USING data rows: collect all row failures or stop on first failure')
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, 'verbose', False) else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    driver = None
    runtime = None

    try:
        browser = getattr(args, 'browser', 'chrome')
        headless = getattr(args, 'headless', False)
        timeout = getattr(args, 'timeout', 10)
        retry_timeout = getattr(args, 'retry_timeout', 5)
        retry_interval = getattr(args, 'retry_interval', 0.3)
        base_url = getattr(args, 'base_url', None)
        cli_var_args = getattr(args, 'var', []) or []
        report = getattr(args, 'report', False)
        report_path = getattr(args, 'report_path', None)
        row_failure_mode = getattr(args, 'row_failure_mode', 'collect')

        # Set up browser
        if browser == 'chrome':
            opts = webdriver.ChromeOptions()
            if headless:
                opts.add_argument('--headless=new')
            driver = webdriver.Chrome(options=opts)
        elif browser == 'firefox':
            opts = webdriver.FirefoxOptions()
            if headless:
                opts.add_argument('--headless')
            driver = webdriver.Firefox(options=opts)
        elif browser == 'edge':
            opts = webdriver.EdgeOptions()
            if headless:
                opts.add_argument('--headless=new')
            driver = webdriver.Edge(options=opts)
        else:
            raise RuntimeError(f"Unsupported browser: {browser}")

        driver.implicitly_wait(2)

        script_path = Path(args.script)
        script_text = script_path.read_text(encoding='utf-8')

        cli_vars = _parse_cli_vars(cli_var_args)

        # Resolve BASE_URL without corrupting longer placeholder names
        if base_url:
            script_text = _replace_exact_placeholder(script_text, 'BASE_URL', base_url)
        else:
            fixture_candidates = [
                script_path.parent / 'test_site.html',
                script_path.parent / 'fixtures' / 'test_site.html',
                Path.cwd() / 'test_site.html',
                Path.cwd() / 'fixtures' / 'test_site.html',
            ]
            fixture_html = next((p for p in fixture_candidates if p.exists()), None)
            if fixture_html is not None:
                file_url = fixture_html.resolve().as_uri()
                script_text = _replace_exact_placeholder(script_text, 'BASE_URL', file_url)

        for name, value in cli_vars.items():
            script_text = _replace_exact_placeholder(script_text, name, value)

        lexer.lineno = 1
        ast = parser.parse(script_text, lexer=lexer)

        try:
            runtime = WebSpecRuntime(
                driver=driver,
                timeout=timeout,
                retry_timeout=retry_timeout,
                retry_interval=retry_interval,
                row_failure_mode=row_failure_mode,
            )
        except TypeError as e:
            if "row_failure_mode" not in str(e):
                raise
            runtime = WebSpecRuntime(
                driver=driver,
                timeout=timeout,
                retry_timeout=retry_timeout,
                retry_interval=retry_interval,
            )

        for name, value in cli_vars.items():
            runtime.variables[name] = value

        runtime.run(ast)

        print(f"\n✓ PASSED - {runtime.step_count} steps, 0 errors")

        if report and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=script_path.name,
                output_path=report_path,
            )
            print(f" Report: {path}")

        sys.exit(0)

    except (AssertionError, TimeoutError, RuntimeError) as e:
        print(f"\n✗ FAILED - {e}")

        if getattr(args, 'report', False) and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=Path(args.script).name,
                output_path=getattr(args, 'report_path', None),
            )
            print(f" Report: {path}")

        sys.exit(1)

    except SyntaxError as e:
        print(f"\n✗ PARSE ERROR - {e}")
        sys.exit(2)

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR - {e}")

        if getattr(args, 'report', False) and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=Path(args.script).name,
                output_path=getattr(args, 'report_path', None),
            )
            print(f" Report: {path}")

        sys.exit(3)

    finally:
        if driver is not None:
            driver.quit()


if __name__ == '__main__':
    main()