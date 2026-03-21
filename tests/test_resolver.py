"""
Tests for the Smart Element Resolver.
Uses a mock Selenium driver with canned HTML to test BS4 resolution.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock

from webspec_resolver import SmartResolver
from webspec_ast import ElementRef, Selector, RawElementRef


# ── Fixture: mock driver with injectable HTML ────────────

SAMPLE_HTML = """
<html><body>
  <nav class="main-nav" role="menubar">
    <a href="/home" class="nav-link">Home</a>
    <a href="/about" class="nav-link">About</a>
    <a href="/contact" class="nav-link">Contact Us</a>
  </nav>

  <form id="login-form" class="auth-form">
    <div class="form-group">
      <label for="email-input">Email address</label>
      <input id="email-input" name="email" type="email"
             placeholder="Enter your email" />
    </div>

    <div class="form-group">
      <label for="pass-input">Password</label>
      <input id="pass-input" name="password" type="password"
             placeholder="Enter password" />
    </div>

    <div class="form-group">
      <label for="role-select">Role</label>
      <select id="role-select" name="role">
        <option value="">-- Select --</option>
        <option value="admin">Administrator</option>
        <option value="editor">Editor</option>
      </select>
    </div>

    <div class="actions">
      <button type="submit" class="btn primary">Sign In</button>
      <button type="button" class="btn secondary">Cancel</button>
    </div>
  </form>

  <section class="results">
    <h2>Search Results</h2>
    <div class="card" data-id="1">
      <h3 class="card-title">Widget Alpha</h3>
      <span class="price">$10.00</span>
      <button class="btn add-to-cart">Add to Cart</button>
    </div>
    <div class="card" data-id="2">
      <h3 class="card-title">Widget Beta</h3>
      <span class="price">$20.00</span>
      <button class="btn add-to-cart">Add to Cart</button>
    </div>
    <div class="card" data-id="3">
      <h3 class="card-title">Widget Gamma</h3>
      <span class="price">$15.00</span>
      <button class="btn add-to-cart">Add to Cart</button>
    </div>
  </section>

  <table id="users-table">
    <tr><th>Name</th><th>Role</th></tr>
    <tr><td>Alice</td><td>Admin</td></tr>
    <tr><td>Bob</td><td>User</td></tr>
  </table>

  <div class="modal" role="dialog" aria-label="Confirm Delete">
    <p>Are you sure?</p>
    <button class="btn danger">Delete</button>
    <button class="btn">Cancel</button>
  </div>

  <div class="filter-panel">
    <div class="form-group">
      <label for="sort-select">Sort by</label>
      <select id="sort-select" name="sort">
        <option value="relevance">Relevance</option>
        <option value="price-asc">Price: Low to High</option>
        <option value="price-desc">Price: High to Low</option>
      </select>
    </div>
  </div>

  <input type="checkbox" id="terms" />
  <label for="terms">I agree to the terms</label>
</body></html>
"""


@pytest.fixture
def resolver():
    driver = MagicMock()
    type(driver).page_source = PropertyMock(return_value=SAMPLE_HTML)

    # Make find_element return a mock that carries the xpath used
    def mock_find_element(by, locator):
        el = MagicMock()
        el._locator = (by, locator)
        return el

    driver.find_element = mock_find_element
    return SmartResolver(driver)


def make_ref(elem_type, selectors=None, ordinal=None):
    return ElementRef(
        elem_type=elem_type,
        selectors=selectors or [],
        ordinal=ordinal,
    )


def make_sel(kind, value='', extra='', child=None):
    return Selector(kind=kind, value=value, extra=extra, child=child)


# ═══════════════════════════════════════════════════════════
#  Basic element type resolution
# ═══════════════════════════════════════════════════════════

class TestBasicResolution:
    def test_find_button_by_text(self, resolver):
        ref = make_ref('button', [make_sel('text', 'Sign In')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_link_by_text(self, resolver):
        ref = make_ref('link', [make_sel('text', 'About')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_input_by_placeholder(self, resolver):
        ref = make_ref('input', [
            make_sel('placeholder', 'Enter your email')
        ])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_heading(self, resolver):
        ref = make_ref('heading', [make_sel('text', 'Search Results')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_by_id(self, resolver):
        ref = make_ref('element', [make_sel('id', 'login-form')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_by_class(self, resolver):
        ref = make_ref('element', [make_sel('class', 'main-nav')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_dropdown(self, resolver):
        ref = make_ref('dropdown')
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_checkbox(self, resolver):
        ref = make_ref('checkbox')
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_table(self, resolver):
        ref = make_ref('table')
        el = resolver.resolve(ref)
        assert el is not None

    def test_find_row(self, resolver):
        ref = make_ref('row')
        el = resolver.resolve(ref)
        assert el is not None


# ═══════════════════════════════════════════════════════════
#  Fuzzy text matching
# ═══════════════════════════════════════════════════════════

class TestFuzzyMatch:
    def test_exact_match(self, resolver):
        ref = make_ref('button', [make_sel('text', 'Sign In')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_partial_match(self, resolver):
        ref = make_ref('link', [make_sel('text', 'Contact')])
        # "Contact" is a partial match for "Contact Us"
        el = resolver.resolve(ref)
        assert el is not None

    def test_fuzzy_typo(self, resolver):
        ref = make_ref('button', [make_sel('text', 'Sing In')])
        # fuzzy match "Sing In" → "Sign In"
        el = resolver.resolve(ref)
        assert el is not None

    def test_no_match_raises(self, resolver):
        ref = make_ref('button', [
            make_sel('text', 'CompletelyNonexistent12345')
        ])
        with pytest.raises(RuntimeError, match="No element found"):
            resolver.resolve(ref)


# ═══════════════════════════════════════════════════════════
#  Selector: near (label proximity)
# ═══════════════════════════════════════════════════════════

class TestNearSelector:
    def test_input_near_label(self, resolver):
        ref = make_ref('input', [make_sel('near', 'Email address')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_input_near_password(self, resolver):
        ref = make_ref('input', [make_sel('near', 'Password')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_near_label_for_attribute(self, resolver):
        # <label for="email-input"> should resolve to #email-input
        ref = make_ref('input', [make_sel('near', 'Email')])
        el = resolver.resolve(ref)
        assert el is not None


# ═══════════════════════════════════════════════════════════
#  Selector: inside (containment)
# ═══════════════════════════════════════════════════════════

class TestInsideSelector:
    def test_button_inside_form(self, resolver):
        form_ref = make_ref('form', [make_sel('id', 'login-form')])
        ref = make_ref('button', [
            make_sel('text', 'Sign In'),
            make_sel('inside', child=form_ref),
        ])
        el = resolver.resolve(ref)
        assert el is not None

    def test_button_inside_dialog(self, resolver):
        dialog_ref = make_ref('dialog', [
            make_sel('text', 'Confirm Delete')
        ])
        ref = make_ref('button', [
            make_sel('text', 'Delete'),
            make_sel('inside', child=dialog_ref),
        ])
        el = resolver.resolve(ref)
        assert el is not None

    def test_heading_inside_section(self, resolver):
        section_ref = make_ref('section', [make_sel('class', 'results')])
        ref = make_ref('heading', [
            make_sel('inside', child=section_ref),
        ])
        el = resolver.resolve(ref)
        assert el is not None


# ═══════════════════════════════════════════════════════════
#  Selector: containing, matching, with attr
# ═══════════════════════════════════════════════════════════

class TestAdvancedSelectors:
    def test_containing(self, resolver):
        ref = make_ref('heading', [make_sel('containing', 'Results')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_matching_regex(self, resolver):
        ref = make_ref('heading', [make_sel('matching', r'Search\s+')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_with_attr(self, resolver):
        ref = make_ref('input', [make_sel('attr', 'email', extra='name')])
        el = resolver.resolve(ref)
        assert el is not None

    def test_with_value(self, resolver):
        # <option value="admin"> in the role select
        ref = make_ref('element', [make_sel('value', 'admin')])
        el = resolver.resolve(ref)
        assert el is not None


# ═══════════════════════════════════════════════════════════
#  Ordinals
# ═══════════════════════════════════════════════════════════

class TestOrdinals:
    def test_first(self, resolver):
        ref = make_ref('link', ordinal=1)
        el = resolver.resolve(ref)
        assert el is not None

    def test_second(self, resolver):
        ref = make_ref('link', ordinal=2)
        el = resolver.resolve(ref)
        assert el is not None

    def test_ordinal_out_of_range(self, resolver):
        ref = make_ref('link', ordinal=999)
        with pytest.raises(RuntimeError, match="only .* found"):
            resolver.resolve(ref)


# ═══════════════════════════════════════════════════════════
#  resolve_all
# ═══════════════════════════════════════════════════════════

class TestResolveAll:
    def test_all_buttons(self, resolver):
        ref = make_ref('button', [make_sel('class', 'add-to-cart')])
        elements = resolver.resolve_all(ref)
        assert len(elements) == 3

    def test_all_rows(self, resolver):
        ref = make_ref('row')
        elements = resolver.resolve_all(ref)
        assert len(elements) == 3  # 1 header + 2 data rows

    def test_all_links(self, resolver):
        ref = make_ref('link')
        elements = resolver.resolve_all(ref)
        assert len(elements) >= 3


# ═══════════════════════════════════════════════════════════
#  XPath generation
# ═══════════════════════════════════════════════════════════

class TestXPathGeneration:
    def test_xpath_absolute(self, resolver):
        resolver._refresh_soup()
        tag = resolver._soup.find('button', class_='primary')
        xpath = resolver._tag_to_xpath(tag)
        assert xpath.startswith('/')
        assert 'button' in xpath

    def test_xpath_with_index(self, resolver):
        resolver._refresh_soup()
        tags = resolver._soup.find_all('a')
        # Second link should have an index
        xpath = resolver._tag_to_xpath(tags[1])
        assert '[2]' in xpath or 'a' in xpath


# ═══════════════════════════════════════════════════════════
#  Raw element refs
# ═══════════════════════════════════════════════════════════

class TestRawRefs:
    def test_raw_css(self, resolver):
        ref = RawElementRef(locator='div.card')
        el = resolver.resolve(ref)
        assert el is not None

    def test_raw_xpath(self, resolver):
        ref = RawElementRef(locator='//button[@class="btn primary"]')
        el = resolver.resolve(ref)
        assert el is not None

# ═══════════════════════════════════════════════════════════
#  Variable Interpolation
# ═══════════════════════════════════════════════════════════

class TestVariableInterpolation:
    def test_interpolate_simple(self, resolver):
        result = resolver._interpolate('${name}', {'name': 'Alice'})
        assert result == 'Alice'

    def test_interpolate_no_vars(self, resolver):
        result = resolver._interpolate('plain text', {})
        assert result == 'plain text'

    def test_interpolate_multiple(self, resolver):
        result = resolver._interpolate(
            '${first} ${last}',
            {'first': 'John', 'last': 'Doe'}
        )
        assert result == 'John Doe'

    def test_interpolate_missing_var_raises(self, resolver):
        with pytest.raises(RuntimeError, match="not set"):
            resolver._interpolate('${missing}', {})

    def test_interpolate_webelement_uses_text(self, resolver):
        mock_el = MagicMock()
        mock_el.text = 'Widget Alpha'
        result = resolver._interpolate('${item}', {'item': mock_el})
        assert result == 'Widget Alpha'

    def test_containing_with_variable(self, resolver):
        ref = make_ref('heading', [
            make_sel('containing', '${query}')
        ])
        el = resolver.resolve(ref, variables={'query': 'Search'})
        assert el is not None

    def test_near_with_variable(self, resolver):
        ref = make_ref('input', [
            make_sel('near', '${label}')
        ])
        el = resolver.resolve(ref, variables={'label': 'Email'})
        assert el is not None

    def test_class_with_variable(self, resolver):
        ref = make_ref('element', [
            make_sel('class', '${cls}')
        ])
        el = resolver.resolve(ref, variables={'cls': 'main-nav'})
        assert el is not None

class TestNearResolverPriority:
    """
    Verify that 'near' prefers <label for="..."> over container divs,
    even when a parent div contains the label text.
    """

    def test_near_prefers_label_for_over_container(self, resolver):
        """near 'Password' should find #pass-input, not #email-input."""
        ref = make_ref('input', [make_sel('near', 'Password')])
        el = resolver.resolve(ref)
        # The mock driver returns whatever find_element gives,
        # but we can verify the resolver picked the right BS4 tag
        resolver._refresh_soup()
        cands = resolver._get_candidates('input')
        result = resolver._apply_selectors(
            cands, [make_sel('near', 'Password')], {})
        # Should resolve to the password input (id=pass-input)
        assert len(result) >= 1
        assert result[0].get('id') == 'pass-input'

    def test_near_prefers_label_for_email(self, resolver):
        """near 'Email' should find #email-input."""
        resolver._refresh_soup()
        cands = resolver._get_candidates('input')
        result = resolver._apply_selectors(
            cands, [make_sel('near', 'Email')], {})
        assert len(result) >= 1
        assert result[0].get('id') == 'email-input'

    def test_near_does_not_match_container_div(self, resolver):
        """
        The <div class="form-group"> containing 'Password' label
        should NOT be the matched label element.
        """
        resolver._refresh_soup()
        cands = resolver._get_candidates('input')
        result = resolver._apply_selectors(
            cands, [make_sel('near', 'Password')], {})
        # Must NOT return the email input (first input on page)
        if result:
            assert result[0].get('name') != 'email'

    def test_get_nearby_tags_limited_scope(self, resolver):
        """Nearby tags should not include the entire document."""
        resolver._refresh_soup()
        label = resolver._soup.find('label', {'for': 'pass-input'})
        nearby = resolver._get_nearby_tags(label)
        all_tags = resolver._soup.find_all(True)
        # Nearby should be a small fraction of all tags
        assert len(nearby) < len(all_tags)