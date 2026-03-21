"""
Shared pytest configuration.
Auto-discovers and runs .ws script files as test items.
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Check Chrome availability once ──────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    _opts = Options()
    _opts.add_argument('--headless=new')
    _opts.add_argument('--no-sandbox')
    _d = webdriver.Chrome(options=_opts)
    _d.quit()
    CHROME_AVAILABLE = True
except Exception:
    CHROME_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
#  .ws file collection plugin
# ═══════════════════════════════════════════════════════════

def pytest_collect_file(parent, file_path):
    """Collect .ws files as test items."""
    if file_path.suffix == '.ws' and file_path.name != '__pycache__':
        return WSFile.from_parent(parent, path=file_path)


class WSFile(pytest.File):
    """A .ws script file collected by pytest."""

    def collect(self):
        yield WSItem.from_parent(
            self,
            name=self.path.stem,
            callobj=None,
        )


class WSItem(pytest.Item):
    """A single .ws script test item."""

    def __init__(self, name, parent, callobj):
        super().__init__(name, parent)
        self.script_path = parent.path

    def runtest(self):
        if not CHROME_AVAILABLE:
            pytest.skip("Chrome/chromedriver not available")

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webspec_lexer import lexer
        from webspec_parser import parser
        from webspec_runtime import WebSpecRuntime

        # Read script
        text = self.script_path.read_text(encoding='utf-8')

        # ── URL substitution logic ───────────────────────
        fixtures_dir = Path(__file__).parent / 'fixtures'

        # Mega test: has both BASE_URL_SECONDARY and BASE_URL
        if 'BASE_URL_SECONDARY' in text:
            secondary = fixtures_dir / 'test_site.html'
            if secondary.exists():
                text = text.replace(
                    'BASE_URL_SECONDARY',
                    secondary.resolve().as_uri())

        # Standard fixtures: BASE_URL
        if 'BASE_URL' in text:
            resolved = False

            # Priority 1: HTML file with same stem as the script
            # mega_test.ws → mega_test.html
            same_stem = self.script_path.parent / (
                    self.script_path.stem + '.html')
            if same_stem.exists():
                text = text.replace(
                    'BASE_URL', same_stem.resolve().as_uri())
                resolved = True

            # Priority 2: HTML file next to the script
            if not resolved:
                for html_name in ['test_site.html']:
                    html_file = self.script_path.parent / html_name
                    if html_file.exists():
                        text = text.replace(
                            'BASE_URL', html_file.resolve().as_uri())
                        resolved = True
                        break

            # Priority 3: fixtures directory
            if not resolved:
                for html_name in ['test_site.html']:
                    html_file = fixtures_dir / html_name
                    if html_file.exists():
                        text = text.replace(
                            'BASE_URL', html_file.resolve().as_uri())
                        break

        # ── Launch browser and run ───────────────────────
        opts = Options()
        opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1280,900')
        driver = webdriver.Chrome(options=opts)
        driver.implicitly_wait(2)

        try:
            lexer.lineno = 1
            ast = parser.parse(text, lexer=lexer)

            rt = WebSpecRuntime(
                driver=driver,
                timeout=10,
                screenshot_dir=str(
                    self.script_path.parent / 'screenshots'),
            )
            rt.run(ast)

            if rt.errors:
                raise AssertionError(
                    f"{len(rt.errors)} error(s): {rt.errors[0]}")

        finally:
            driver.quit()

    def repr_failure(self, excinfo):
        """Custom failure representation."""
        if isinstance(excinfo.value, SyntaxError):
            return f"PARSE ERROR in {self.script_path.name}: {excinfo.value}"
        if isinstance(excinfo.value, AssertionError):
            return f"ASSERTION FAILED in {self.script_path.name}: {excinfo.value}"
        return f"ERROR in {self.script_path.name}: {excinfo.value}"

    def reportinfo(self):
        return self.path, None, f"webspec: {self.script_path.name}"