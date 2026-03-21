"""
Mega test integration — runs the monolithic mega_test.ws
against mega_test.html with a URL transition to test_site.html.
"""

import pytest
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    _d = webdriver.Chrome(options=opts)
    _d.quit()
    CHROME_AVAILABLE = True
except Exception:
    CHROME_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CHROME_AVAILABLE, reason="Chrome not available")

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_runtime import WebSpecRuntime


FIXTURES = Path(__file__).parent / 'fixtures'
MEGA_HTML = FIXTURES / 'mega_test.html'
SECONDARY_HTML = FIXTURES / 'test_site.html'
MEGA_SCRIPT = FIXTURES / 'mega_test.ws'


@pytest.fixture(scope='module')
def driver():
    drv_opts = Options()
    drv_opts.add_argument('--headless=new')
    drv_opts.add_argument('--no-sandbox')
    drv_opts.add_argument('--disable-dev-shm-usage')
    drv_opts.add_argument('--window-size=1280,900')
    d = webdriver.Chrome(options=drv_opts)
    d.implicitly_wait(2)
    yield d
    d.quit()


class TestMega:
    def test_mega_script(self, driver):
        text = MEGA_SCRIPT.read_text(encoding='utf-8')
        text = text.replace('BASE_URL_SECONDARY',
                            SECONDARY_HTML.resolve().as_uri())
        text = text.replace('BASE_URL',
                            MEGA_HTML.resolve().as_uri())

        lexer.lineno = 1
        ast = parser.parse(text, lexer=lexer)

        rt = WebSpecRuntime(
            driver=driver, timeout=10,
            screenshot_dir=str(FIXTURES / 'screenshots'))
        rt.run(ast)

        assert len(rt.errors) == 0, f"Errors: {rt.errors}"
        assert rt.step_count > 100, (
            f"Expected 100+ steps, got {rt.step_count}")
        print(f"\nMEGA TEST: {rt.step_count} steps, 0 errors")