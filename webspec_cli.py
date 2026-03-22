"""
WebSpec DSL - CLI Entry Point
Usage: python webspec_cli.py test_script.ws [--browser chrome|firefox]
"""

import argparse
import logging
import sys
from pathlib import Path

from selenium import webdriver

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime


def main():
    ap = argparse.ArgumentParser(description='WebSpec DSL Test Runner')
    ap.add_argument('script', help='Path to .ws test script')
    ap.add_argument('--browser', default='chrome',
                    choices=['chrome', 'firefox', 'edge'])
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
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Set up browser
    driver = None
    if args.browser == 'chrome':
        opts = webdriver.ChromeOptions()
        if args.headless:
            opts.add_argument('--headless=new')
        driver = webdriver.Chrome(options=opts)
    elif args.browser == 'firefox':
        opts = webdriver.FirefoxOptions()
        if args.headless:
            opts.add_argument('--headless')
        driver = webdriver.Firefox(options=opts)
    elif args.browser == 'edge':
        opts = webdriver.EdgeOptions()
        if args.headless:
            opts.add_argument('--headless=new')
        driver = webdriver.Edge(options=opts)

    driver.implicitly_wait(2)

    script_path = Path(args.script)
    script_text = script_path.read_text(encoding='utf-8')

    # Resolve BASE_URL
    if args.base_url:
        script_text = script_text.replace('BASE_URL', args.base_url)
    else:
        fixture_html = script_path.parent / 'test_site.html'
        if not fixture_html.exists():
            fixture_html = script_path.parent / 'fixtures' / 'test_site.html'
        if fixture_html.exists():
            file_url = fixture_html.resolve().as_uri()
            script_text = script_text.replace('BASE_URL', file_url)

    runtime = None
    try:
        ast = parser.parse(script_text, lexer=lexer)
        runtime = WebSpecRuntime(
            driver=driver,
            timeout=args.timeout,
            retry_timeout=args.retry_timeout,
            retry_interval=args.retry_interval,
        )

        # Inject CLI --var values
        for var_str in args.var:
            if '=' in var_str:
                name, value = var_str.split('=', 1)
                runtime.variables[name] = value

        runtime.run(ast)
        print(f"\n✓ PASSED - {runtime.step_count} steps, 0 errors")

        if args.report:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=script_path.name,
                output_path=args.report_path,
            )
            print(f"  Report: {path}")

        sys.exit(0)
    # except (AssertionError, TimeoutError, RuntimeError) as e:
    #     print(f"\n✗ FAILED - {e}")
    #
    #     if args.report:
    #         from webspec_report import generate_report
    #         path = generate_report(
    #             runtime,
    #             script_name=script_path.name,
    #             output_path=args.report_path,
    #         )
    #         print(f"  Report: {path}")
    #
    #     sys.exit(1)
    # except SyntaxError as e:
    #     print(f"\n✗ PARSE ERROR - {e}")
    #     sys.exit(2)
    except (AssertionError, TimeoutError, RuntimeError) as e:
        print(f"\n✗ FAILED - {e}")
        if args.report:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=script_path.name,
                output_path=args.report_path,
            )
            print(f" Report: {path}")
        sys.exit(1)

    except SyntaxError as e:
        print(f"\n✗ PARSE ERROR - {e}")
        sys.exit(2)

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR - {e}")
        if args.report:
            from webspec_report import generate_report
            path = generate_report(
                runtime,
                script_name=script_path.name,
                output_path=args.report_path,
            )
            print(f" Report: {path}")
        sys.exit(3)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()