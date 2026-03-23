import pytest
from selenium.webdriver.common.by import By

from webspec_resolver import SmartResolver
from webspec_ast import RawElementRef, VarElementRef


class FakeDriver:
    def __init__(self):
        self.page_source = "<html><body></body></html>"
        self.calls = []
        self._css_results = ["css-el-1", "css-el-2"]
        self._xpath_results = ["xpath-el-1", "xpath-el-2", "xpath-el-3"]

    def find_elements(self, by, locator):
        self.calls.append((by, locator))
        if by == By.CSS_SELECTOR:
            return self._css_results
        if by == By.XPATH:
            return self._xpath_results
        return []


@pytest.fixture
def resolver():
    return SmartResolver(FakeDriver(), retry_timeout=0.01, retry_interval=0.0)


def test_resolve_all_raw_css_ref_returns_all_matches(resolver):
    ref = RawElementRef(locator=".item")
    result = resolver.resolve_all(ref)

    assert result == ["css-el-1", "css-el-2"]
    assert resolver.driver.calls[-1] == (By.CSS_SELECTOR, ".item")


def test_resolve_all_raw_xpath_ref_returns_all_matches(resolver):
    ref = RawElementRef(locator='//div[@class="item"]')
    result = resolver.resolve_all(ref)

    assert result == ["xpath-el-1", "xpath-el-2", "xpath-el-3"]
    assert resolver.driver.calls[-1] == (By.XPATH, '//div[@class="item"]')


def test_resolve_all_var_element_ref_single_returns_singleton_list(resolver):
    stored_el = object()
    ref = VarElementRef(var_name="saved")

    result = resolver.resolve_all(ref, variables={"saved": stored_el})

    assert result == [stored_el]


def test_resolve_all_var_element_ref_list_returns_list_unchanged(resolver):
    stored = [object(), object()]
    ref = VarElementRef(var_name="saved")

    result = resolver.resolve_all(ref, variables={"saved": stored})

    # Use identity here to enforce true pass-through behavior.
    assert result is stored


@pytest.mark.parametrize(
    "template, expected",
    [
        ("Hello ${name}", "Hello World"),
        ("Hello $name", "Hello World"),
        ("${greet}, $name!", "Hi, World!"),
    ],
)
def test_selector_interpolation_supports_braced_and_unbraced_vars(
    resolver, template, expected
):
    actual = resolver._interpolate(
        template,
        {"name": "World", "greet": "Hi"},
    )
    assert actual == expected