"""
Tests for the WebSpec transpiler.
Verifies that captured events produce idiomatic WebSpec output.
"""

# import pytest
from webspec_transpiler import WebSpecTranspiler, _is_autogen_id, _is_semantic_class


# ═══════════════════════════════════════════════════════════
#  Utility function tests
# ═══════════════════════════════════════════════════════════

class TestHelpers:
    def test_autogen_id_ember(self):
        assert _is_autogen_id('ember-123') is True

    def test_autogen_id_react(self):
        assert _is_autogen_id(':r0:') is True

    def test_autogen_id_numeric(self):
        assert _is_autogen_id('12345') is True

    def test_autogen_id_long(self):
        assert _is_autogen_id('a' * 40) is True

    def test_readable_id(self):
        assert _is_autogen_id('email-input') is False

    def test_readable_id_short(self):
        assert _is_autogen_id('login-form') is False

    def test_semantic_class_found(self):
        assert _is_semantic_class('btn btn-primary submit-button') == 'btn'

    def test_semantic_class_skip_utility(self):
        assert _is_semantic_class('col-md-6 d-flex') is None

    def test_semantic_class_mixed(self):
        result = _is_semantic_class('col-md-6 product-card d-flex')
        assert result == 'product-card'

    def test_semantic_class_empty(self):
        assert _is_semantic_class('') is None

    def test_semantic_class_none(self):
        assert _is_semantic_class(None) is None


# ═══════════════════════════════════════════════════════════
#  Transpiler - selector strategy
# ═══════════════════════════════════════════════════════════

class TestSelectorStrategy:
    def setup_method(self):
        self.t = WebSpecTranspiler()

    def test_button_with_text(self):
        ref = self.t._build_ref({
            'elemType': 'button',
            'text': 'Submit',
            'label': '',
            'attrs': {},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the button "Submit"'

    def test_input_near_label(self):
        ref = self.t._build_ref({
            'elemType': 'input',
            'text': '',
            'label': 'Email address',
            'attrs': {'type': 'email'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the input near "Email address"'

    def test_dropdown_near_label(self):
        ref = self.t._build_ref({
            'elemType': 'dropdown',
            'text': '',
            'label': 'Country',
            'attrs': {},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the dropdown near "Country"'

    def test_checkbox_near_label(self):
        ref = self.t._build_ref({
            'elemType': 'checkbox',
            'text': '',
            'label': 'Remember me',
            'attrs': {'type': 'checkbox'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the checkbox near "Remember me"'

    def test_input_with_placeholder(self):
        ref = self.t._build_ref({
            'elemType': 'input',
            'text': '',
            'label': '',
            'attrs': {'placeholder': 'Search products...'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the input with placeholder "Search products..."'

    def test_link_with_text(self):
        ref = self.t._build_ref({
            'elemType': 'link',
            'text': 'Buy moisturizers',
            'label': '',
            'attrs': {'href': '/moisturizer'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the link "Buy moisturizers"'

    def test_ordinal_button(self):
        ref = self.t._build_ref({
            'elemType': 'button',
            'text': 'Add',
            'label': '',
            'attrs': {},
            'ordinal': 3,
            'siblingCount': 6,
        })
        assert ref == 'the 3rd button "Add"'

    def test_readable_id_fallback(self):
        ref = self.t._build_ref({
            'elemType': 'element',
            'text': '',
            'label': '',
            'attrs': {'id': 'temperature'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the element with id "temperature"'

    def test_semantic_class_fallback(self):
        ref = self.t._build_ref({
            'elemType': 'element',
            'text': '',
            'label': '',
            'attrs': {'class': 'col-md-4 product-card d-flex'},
            'ordinal': 2,
            'siblingCount': 6,
        })
        assert ref == 'the 2nd element with class "product-card"'

    def test_data_testid_fallback(self):
        ref = self.t._build_ref({
            'elemType': 'button',
            'text': '',
            'label': '',
            'attrs': {'data-testid': 'checkout-btn'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the button with attr "data-testid" is "checkout-btn"'

    def test_aria_label(self):
        ref = self.t._build_ref({
            'elemType': 'button',
            'text': '',
            'label': '',
            'attrs': {'aria-label': 'Close dialog'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert ref == 'the button "Close dialog"'

    def test_long_text_uses_containing(self):
        ref = self.t._build_ref({
            'elemType': 'element',
            'text': 'This is a very long piece of text that exceeds the forty character limit',
            'label': '',
            'attrs': {},
            'ordinal': 1,
            'siblingCount': 1,
        })
        assert 'containing' in ref

    def test_autogen_id_skipped(self):
        ref = self.t._build_ref({
            'elemType': 'element',
            'text': '',
            'label': '',
            'attrs': {'id': 'ember-456', 'class': 'action-panel'},
            'ordinal': 1,
            'siblingCount': 1,
        })
        # Should skip the autogen ID and use the class
        assert 'ember-456' not in ref
        assert 'action-panel' in ref


# ═══════════════════════════════════════════════════════════
#  Transpiler - full event sequences
# ═══════════════════════════════════════════════════════════

class TestFullTranspilation:
    def setup_method(self):
        self.t = WebSpecTranspiler()

    def test_click_event(self):
        script = self.t.transpile([{
            'eventType': 'click',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'context': {
                'elemType': 'button',
                'text': 'Submit',
                'label': '', 'attrs': {},
                'ordinal': 1, 'siblingCount': 1,
            }
        }])
        assert 'navigate to "https://example.com/"' in script
        assert 'click the button "Submit"' in script

    def test_type_event(self):
        script = self.t.transpile([{
            'eventType': 'type',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'context': {
                'elemType': 'input',
                'text': '', 'label': 'Email',
                'attrs': {'type': 'email'},
                'ordinal': 1, 'siblingCount': 1,
            },
            'value': 'user@test.com',
        }])
        assert 'type "user@test.com" into the input near "Email"' in script

    def test_select_event(self):
        script = self.t.transpile([{
            'eventType': 'select',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'context': {
                'elemType': 'dropdown',
                'text': '', 'label': 'Country',
                'attrs': {},
                'ordinal': 1, 'siblingCount': 1,
            },
            'option': 'United States',
        }])
        assert 'select "United States" from the dropdown near "Country"' in script

    def test_check_event(self):
        script = self.t.transpile([{
            'eventType': 'check',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'context': {
                'elemType': 'checkbox',
                'text': '', 'label': 'I agree',
                'attrs': {'type': 'checkbox'},
                'ordinal': 1, 'siblingCount': 1,
            },
        }])
        assert 'check the checkbox near "I agree"' in script

    def test_navigation_detection(self):
        script = self.t.transpile([
            {
                'eventType': 'click',
                'timestamp': 1000,
                'url': 'https://example.com/',
                'context': {
                    'elemType': 'link', 'text': 'Products',
                    'label': '', 'attrs': {},
                    'ordinal': 1, 'siblingCount': 1,
                },
            },
            {
                'eventType': 'click',
                'timestamp': 2000,
                'url': 'https://example.com/products',
                'context': {
                    'elemType': 'button', 'text': 'Add',
                    'label': '', 'attrs': {},
                    'ordinal': 1, 'siblingCount': 1,
                },
            },
        ])
        assert 'click the link "Products"' in script
        assert 'wait until url contains "/products"' in script
        assert 'click the button "Add"' in script

    def test_keypress_event(self):
        script = self.t.transpile([{
            'eventType': 'keypress',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'key': 'Enter',
            'ctrl': False, 'shift': False, 'alt': False,
        }])
        assert 'press key "enter"' in script

    def test_keypress_with_modifier(self):
        script = self.t.transpile([{
            'eventType': 'keypress',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'key': 'Enter',
            'ctrl': True, 'shift': False, 'alt': False,
        }])
        assert 'press key "enter" with "ctrl"' in script

    def test_scroll_event(self):
        script = self.t.transpile([{
            'eventType': 'scroll',
            'timestamp': 1000,
            'url': 'https://example.com/',
            'direction': 'down',
            'pixels': 500,
        }])
        assert 'scroll down 500 pixels' in script

    def test_full_login_flow(self):
        events = [
            {'eventType': 'type', 'timestamp': 1000,
             'url': 'https://app.com/login',
             'context': {'elemType': 'input', 'text': '',
                         'label': 'Email', 'attrs': {},
                         'ordinal': 1, 'siblingCount': 1},
             'value': 'admin@test.com'},
            {'eventType': 'type', 'timestamp': 2000,
             'url': 'https://app.com/login',
             'context': {'elemType': 'input', 'text': '',
                         'label': 'Password',
                         'attrs': {'type': 'password'},
                         'ordinal': 1, 'siblingCount': 1},
             'value': 'secret123'},
            {'eventType': 'click', 'timestamp': 3000,
             'url': 'https://app.com/login',
             'context': {'elemType': 'button', 'text': 'Sign In',
                         'label': '', 'attrs': {},
                         'ordinal': 1, 'siblingCount': 1}},
        ]
        script = self.t.transpile(events)
        assert 'navigate to "https://app.com/login"' in script
        assert 'type "admin@test.com" into the input near "Email"' in script
        assert 'type "secret123" into the input near "Password"' in script
        assert 'click the button "Sign In"' in script

    def test_empty_events(self):
        script = self.t.transpile([])
        assert 'Recording playback complete' in script

    # Edge Cases

    def test_captured_keypress_with_ctrl_shift_transpiles_correctly(self):
        events = [
            {
                "eventType": "keypress",
                "key": "X",
                "ctrl": True,
                "shift": True,
                "alt": False,
                "url": "https://example.com/app",
            }
        ]

        out = WebSpecTranspiler().transpile(events)
        assert 'press key "x" with "ctrl+shift"' in out
