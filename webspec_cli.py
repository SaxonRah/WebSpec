"""
WebSpec DSL - CLI Entry Point (updated for multi-backend support)

Usage:
  python webspec_cli.py test.ws --browser chrome
  python webspec_cli.py test.ws --mode electron --app-path /path/to/app
  python webspec_cli.py test.ws --mode appium --app /path/to/app --platform windows
"""

import argparse
import logging
import sys
from pathlib import Path
import re

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime
from webspec_driver import DriverConfig, create_driver, cleanup_driver


def _parse_cli_vars(var_args):
    parsed = {}
    for var_str in var_args:
        if '=' in var_str:
            name, value = var_str.split('=', 1)
            parsed[name] = value
    return parsed


def _replace_exact_placeholder(script_text: str, name: str, value: str) -> str:
    pattern = rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])'
    return re.sub(pattern, value, script_text)


def main():
    ap = argparse.ArgumentParser(description='WebSpec DSL Test Runner')
    ap.add_argument('script', help='Path to .ws test script')

    # -- driver mode --------------------------------------------------------
    ap.add_argument('--mode', default='browser',
                    choices=['browser', 'electron', 'appium'],
                    help='Driver backend (default: browser)')
    ap.add_argument('--browser', default='chrome',
                    choices=['chrome', 'firefox', 'edge'])
    ap.add_argument('--headless', action='store_true')

    # -- electron -----------------------------------------------------------
    ap.add_argument('--app-path', default=None,
                    help='(electron) Path to the Electron/CEF binary')
    ap.add_argument('--debug-port', type=int, default=9222,
                    help='(electron) Chrome DevTools debug port')
    ap.add_argument('--no-launch', action='store_true',
                    help='(electron) Assume app is already running')

    # -- appium -------------------------------------------------------------
    ap.add_argument('--appium-server', default='http://localhost:4723',
                    help='(appium) Appium server URL')
    ap.add_argument('--app', default=None,
                    help='(appium) Path or bundle ID of the app under test')
    ap.add_argument('--platform', default='windows',
                    choices=['windows', 'mac', 'linux'],
                    help='(appium) Target platform')

    # -- shared -------------------------------------------------------------
    ap.add_argument('--timeout', type=int, default=10)
    ap.add_argument('--retry-timeout', type=float, default=5)
    ap.add_argument('--retry-interval', type=float, default=0.3)
    ap.add_argument('--verbose', '-v', action='store_true')
    ap.add_argument('--base-url', default=None)
    ap.add_argument('--var', action='append', default=[])
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--report-path', default=None)
    ap.add_argument('--row-failure-mode', default='collect',
                    choices=['collect', 'fail_fast'])
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    driver = None
    runtime = None
    try:
        # Build driver config from CLI args
        cfg = DriverConfig(
            mode=args.mode,
            browser=args.browser,
            headless=args.headless,
            app_path=args.app_path,
            debug_port=args.debug_port,
            launch_app=not args.no_launch,
            appium_server=args.appium_server,
            app=args.app,
            platform=args.platform,
        )
        driver = create_driver(cfg)
        driver.implicitly_wait(2)

        # ---- rest of main() is unchanged from here ----
        script_path = Path(args.script)
        script_text = script_path.read_text(encoding='utf-8')
        cli_vars = _parse_cli_vars(args.var or [])

        if args.base_url:
            script_text = _replace_exact_placeholder(
                script_text, 'BASE_URL', args.base_url)
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
                script_text = _replace_exact_placeholder(
                    script_text, 'BASE_URL', file_url)

        for name, value in cli_vars.items():
            script_text = _replace_exact_placeholder(script_text, name, value)

        lexer.lineno = 1
        ast = parser.parse(script_text, lexer=lexer)

        try:
            runtime = WebSpecRuntime(
                driver=driver,
                timeout=args.timeout,
                retry_timeout=args.retry_timeout,
                retry_interval=args.retry_interval,
                row_failure_mode=args.row_failure_mode,
            )
        except TypeError as e:
            if "row_failure_mode" not in str(e):
                raise
            runtime = WebSpecRuntime(
                driver=driver,
                timeout=args.timeout,
                retry_timeout=args.retry_timeout,
                retry_interval=args.retry_interval,
            )

        for name, value in cli_vars.items():
            runtime.variables[name] = value

        runtime.run(ast)
        print(f"\n✓ PASSED - {runtime.step_count} steps, 0 errors")

        if args.report and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime, script_name=script_path.name,
                output_path=args.report_path)
            print(f"  Report: {path}")
        sys.exit(0)

    except (AssertionError, TimeoutError, RuntimeError) as e:
        print(f"\n✗ FAILED - {e}")
        if args.report and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime, script_name=Path(args.script).name,
                output_path=args.report_path)
            print(f"  Report: {path}")
        sys.exit(1)

    except SyntaxError as e:
        print(f"\n✗ PARSE ERROR - {e}")
        sys.exit(2)

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR - {e}")
        if args.report and runtime is not None:
            from webspec_report import generate_report
            path = generate_report(
                runtime, script_name=Path(args.script).name,
                output_path=args.report_path)
            print(f"  Report: {path}")
        sys.exit(3)

    finally:
        cleanup_driver(driver)


if __name__ == '__main__':
    main()