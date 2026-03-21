"""
Integration tests — runs .ws scripts against the local HTML fixture
with a real (headless) Chrome browser.

Requires: Chrome + chromedriver installed.
Skip gracefully if not available.
"""

import pytest
from pathlib import Path

# Skip all integration tests if Chrome not available
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    _test_driver = webdriver.Chrome(options=opts)
    _test_driver.quit()
    CHROME_AVAILABLE = True
except Exception:
    CHROME_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CHROME_AVAILABLE,
    reason="Chrome/chromedriver not available"
)

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime


FIXTURES_DIR = Path(__file__).parent / 'fixtures'
HTML_FILE = FIXTURES_DIR / 'test_site.html'
FILE_URL = HTML_FILE.as_uri()


@pytest.fixture(scope='module')
def driver():
    """Shared headless Chrome for all integration tests."""
    drv_opts = Options()
    drv_opts.add_argument('--headless=new')
    drv_opts.add_argument('--no-sandbox')
    drv_opts.add_argument('--disable-dev-shm-usage')
    drv_opts.add_argument('--window-size=1280,900')
    d = webdriver.Chrome(options=drv_opts)
    d.implicitly_wait(2)
    yield d
    d.quit()


def run_script(driver, script_path):
    """Parse and execute a .ws script, returning the runtime."""
    text = script_path.read_text()
    # Inject the real file:// URL
    text = text.replace('BASE_URL', FILE_URL)

    lexer.lineno = 1
    ast = parser.parse(text, lexer=lexer)
    rt = WebSpecRuntime(driver=driver, timeout=10,
                        screenshot_dir=str(FIXTURES_DIR / 'screenshots'))
    rt.run(ast)
    return rt


class TestLoginIntegration:
    def test_full_login_flow(self, driver):
        rt = run_script(driver, FIXTURES_DIR / 'test_login.ws')
        assert len(rt.errors) == 0
        assert rt.step_count > 0
        # Verify the runtime captured the title
        assert 'page_title' in rt.variables
        assert 'Dashboard' in rt.variables['page_title']


class TestSearchIntegration:
    def test_search_and_filter(self, driver):
        rt = run_script(driver, FIXTURES_DIR / 'test_search.ws')
        assert len(rt.errors) == 0
        # Verify extracted data
        assert rt.variables.get('count') == 3
        assert rt.variables.get('title') == 'Wireless Pro Headphones'
        assert rt.variables.get('price') == '$79.99'


class TestTableIntegration:
    def test_table_operations(self, driver):
        rt = run_script(driver, FIXTURES_DIR / 'test_table.ws')
        assert len(rt.errors) == 0
        assert rt.step_count > 0


class TestCounterIntegration:
    def test_counter_flow(self, driver):
        rt = run_script(driver, FIXTURES_DIR / 'test_counter.ws')
        assert len(rt.errors) == 0
        assert rt.variables.get('val') == '3'