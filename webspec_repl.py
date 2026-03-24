"""
WebSpec DSL - Interactive REPL
Type WebSpec commands one at a time against a live browser.
"""

# import sys
import logging

try:
    import readline  # enables arrow-key history and line editing
except ImportError:
    pass  # readline not available (some Windows installs)

from pathlib import Path

from selenium import webdriver

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('webspec.repl')

BANNER = """
╔══════════════════════════════════════════╗
║          WebSpec Interactive REPL        ║
║  Type commands one line at a time.       ║
║  Multi-line: end with \\ then continue.  ║
║  Commands: :help :vars :quit :screenshot ║
╚══════════════════════════════════════════╝
"""

HELP_TEXT = """
REPL Commands:
  :help          Show this help
  :vars          Show all variables
  :quit / :exit  Close browser and exit
  :screenshot    Take a screenshot
  :url           Show current URL
  :title         Show current page title
  :source        Save page source to repl_source.html
  :clear         Clear all variables
  :run <file>    Run a .ws script file
  :history       Show command history

Everything else is parsed as WebSpec DSL.
Multi-line input: end a line with \\ to continue on next line.
Block constructs (if/repeat/for/try/define) auto-detect.
"""

BLOCK_STARTERS = {'if', 'repeat', 'for', 'try', 'define', 'using'}


def is_block_start(line):
    """Check if a line starts a multi-line block."""
    first_word = line.strip().split()[0].lower() if line.strip() else ''
    return first_word in BLOCK_STARTERS


def main():
    import argparse
    ap = argparse.ArgumentParser(description='WebSpec REPL')
    ap.add_argument('--browser', default='chrome',
                    choices=['chrome', 'firefox', 'edge'])
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--url', default=None,
                    help='Navigate to this URL on startup')
    args = ap.parse_args()

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
    runtime = WebSpecRuntime(driver=driver, timeout=10)

    print(BANNER)

    if args.url:
        driver.get(args.url)
        print(f"  Navigated to: {args.url}\n")

    history = []

    while True:
        line = None
        try:
            line = input('webspec> ').rstrip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye!')
            break

        if not line.strip():
            continue

        # ── REPL meta-commands ───────────────────────────
        if line.startswith(':'):
            cmd = line.lower().strip()

            if cmd in (':quit', ':exit', ':q'):
                print('Bye!')
                break
            elif cmd == ':help':
                print(HELP_TEXT)
            elif cmd == ':vars':
                if runtime.variables:
                    for k, v in runtime.variables.items():
                        val = str(v)[:80]
                        print(f'  ${k} = {val}')
                else:
                    print('  (no variables set)')
            elif cmd == ':screenshot':
                path = f'repl_screenshot_{runtime.step_count}.png'
                driver.save_screenshot(path)
                print(f'  Saved: {path}')
            elif cmd == ':url':
                print(f'  {driver.current_url}')
            elif cmd == ':title':
                print(f'  {driver.title}')
            elif cmd == ':source':
                Path('repl_source.html').write_text(
                    driver.page_source, encoding='utf-8')
                print('  Saved: repl_source.html')
            elif cmd == ':clear':
                runtime.variables.clear()
                print('  Variables cleared')
            elif cmd == ':history':
                for i, h in enumerate(history, 1):
                    print(f'  {i}: {h[:80]}')
            elif cmd.startswith(':run '):
                filepath = cmd[5:].strip()
                try:
                    script = Path(filepath).read_text(encoding='utf-8')
                    lexer.lineno = 1
                    ast = parser.parse(script, lexer=lexer)
                    runtime.run(ast)
                    print(f'  ✓ {filepath} completed')
                except Exception as e:
                    print(f'  ✗ {e}')
            else:
                print(f'  Unknown command: {cmd}')
            continue

        # ── Multi-line input ─────────────────────────────
        # Line continuation with backslash
        while line.endswith('\\'):
            line = line[:-1] + '\n'
            try:
                line += input('     ... ')
            except (EOFError, KeyboardInterrupt):
                break

        # Auto-detect block constructs
        if is_block_start(line):
            block = line
            depth = 1
            while depth > 0:
                try:
                    next_line = input('     ... ')
                except (EOFError, KeyboardInterrupt):
                    break
                block += '\n' + next_line
                stripped = next_line.strip().lower()
                # Track nesting
                first = stripped.split()[0] if stripped else ''
                if first in BLOCK_STARTERS:
                    depth += 1
                if stripped == 'end':
                    depth -= 1
            line = block

        # ── Parse and execute ────────────────────────────
        history.append(line)

        try:
            lexer.lineno = 1
            ast = parser.parse(line, lexer=lexer)
            if ast and ast.statements:
                runtime.exec_block(
                    [s for s in ast.statements if s is not None])
                print(f'  ✓ OK ({runtime.step_count} total steps)')
        except SyntaxError as e:
            print(f'  ✗ Parse error: {e}')
        except AssertionError as e:
            print(f'  ✗ Assertion failed: {e}')
        except Exception as e:
            print(f'  ✗ Error: {e}')

    driver.quit()


if __name__ == '__main__':
    main()