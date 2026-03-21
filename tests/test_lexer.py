"""
Tests for the WebSpec PLY lexer.
Verifies that every token category lexes correctly.
"""

import pytest
from webspec_lexer import lexer


def lex_all(text):
    """Helper: lex input and return list of (type, value) tuples."""
    lexer.input(text)
    lexer.lineno = 1
    result = []
    for tok in lexer:
        result.append((tok.type, tok.value))
    return result


# ═══════════════════════════════════════════════════════════
#  Strings
# ═══════════════════════════════════════════════════════════

class TestStrings:
    def test_double_quoted(self):
        tokens = lex_all('"hello world"')
        assert tokens == [('STRING', 'hello world')]

    def test_single_quoted(self):
        tokens = lex_all("'hello world'")
        assert tokens == [('STRING', 'hello world')]

    def test_escaped_quotes(self):
        tokens = lex_all(r'"say \"hi\""')
        assert tokens == [('STRING', 'say "hi"')]

    def test_empty_string(self):
        tokens = lex_all('""')
        assert tokens == [('STRING', '')]

    def test_string_with_special_chars(self):
        tokens = lex_all('"user@test.com"')
        assert tokens == [('STRING', 'user@test.com')]

    def test_string_with_url(self):
        tokens = lex_all('"https://example.com/login?q=1&b=2"')
        assert tokens[0][0] == 'STRING'
        assert 'https://example.com' in tokens[0][1]


# ═══════════════════════════════════════════════════════════
#  Numbers & Ordinals
# ═══════════════════════════════════════════════════════════

class TestNumbers:
    def test_integer(self):
        tokens = lex_all('42')
        assert tokens == [('NUMBER', 42)]

    def test_float(self):
        tokens = lex_all('3.5')
        assert tokens == [('NUMBER', 3.5)]

    def test_ordinal_1st(self):
        tokens = lex_all('1st')
        assert tokens == [('ORDINAL', 1)]

    def test_ordinal_2nd(self):
        tokens = lex_all('2nd')
        assert tokens == [('ORDINAL', 2)]

    def test_ordinal_3rd(self):
        tokens = lex_all('3rd')
        assert tokens == [('ORDINAL', 3)]

    def test_ordinal_4th(self):
        tokens = lex_all('4th')
        assert tokens == [('ORDINAL', 4)]

    def test_ordinal_21st(self):
        tokens = lex_all('21st')
        assert tokens == [('ORDINAL', 21)]


# ═══════════════════════════════════════════════════════════
#  Variables
# ═══════════════════════════════════════════════════════════

class TestVariables:
    def test_dollar_name(self):
        tokens = lex_all('$count')
        assert tokens == [('VARIABLE', 'count')]

    def test_dollar_braces(self):
        tokens = lex_all('${my_var}')
        assert tokens == [('VARIABLE', 'my_var')]

    def test_dollar_underscore(self):
        tokens = lex_all('$_error')
        assert tokens == [('VARIABLE', '_error')]


# ═══════════════════════════════════════════════════════════
#  Reserved words
# ═══════════════════════════════════════════════════════════

class TestReservedWords:
    @pytest.mark.parametrize("word,expected_type", [
        ('navigate', 'NAVIGATE'),
        ('click', 'CLICK'),
        ('verify', 'VERIFY'),
        ('the', 'THE'),
        ('button', 'BUTTON'),
        ('visible', 'VISIBLE'),
        ('contains', 'CONTAINS'),
        ('containing', 'CONTAINING'),
        ('matches', 'MATCHES'),
        ('matching', 'MATCHING'),
        ('wait', 'WAIT'),
        ('if', 'IF'),
        ('then', 'THEN'),
        ('else', 'ELSE'),
        ('end', 'END'),
        ('for', 'FOR'),
        ('each', 'EACH'),
        ('repeat', 'REPEAT'),
        ('set', 'SET'),
        ('to', 'TO'),
        ('into', 'INTO'),
        ('select', 'SELECT'),
        ('from', 'FROM'),
        ('near', 'NEAR'),
        ('inside', 'INSIDE'),
        ('above', 'ABOVE'),
        ('below', 'BELOW'),
    ])
    def test_reserved(self, word, expected_type):
        tokens = lex_all(word)
        assert tokens[0][0] == expected_type

    def test_case_insensitive(self):
        tokens = lex_all('Navigate')
        assert tokens[0][0] == 'NAVIGATE'

    def test_unknown_bare_word_becomes_string(self):
        tokens = lex_all('foobar')
        assert tokens[0][0] == 'STRING'


# ═══════════════════════════════════════════════════════════
#  Comments & whitespace
# ═══════════════════════════════════════════════════════════

class TestCommentsAndWhitespace:
    def test_comment_stripped(self):
        tokens = lex_all('click # this is a comment')
        assert tokens == [('CLICK', 'click')]

    def test_blank_lines_produce_newlines(self):
        tokens = lex_all('click\n\nverify')
        types = [t[0] for t in tokens]
        assert 'NEWLINE' in types

    def test_tabs_and_spaces_ignored(self):
        tokens = lex_all('  click   the   button  ')
        types = [t[0] for t in tokens]
        assert 'CLICK' in types
        assert 'THE' in types
        assert 'BUTTON' in types


# ═══════════════════════════════════════════════════════════
#  Operators
# ═══════════════════════════════════════════════════════════

class TestOperators:
    def test_plus(self):
        tokens = lex_all('"a" + "b"')
        assert tokens[1] == ('PLUS', '+')

    def test_parens(self):
        tokens = lex_all('($x)')
        types = [t[0] for t in tokens]
        assert types == ['LPAREN', 'VARIABLE', 'RPAREN']


# ═══════════════════════════════════════════════════════════
#  Full statement tokenization
# ═══════════════════════════════════════════════════════════

class TestFullStatements:
    def test_navigate(self):
        tokens = lex_all('navigate to "https://example.com"')
        types = [t[0] for t in tokens]
        assert types == ['NAVIGATE', 'TO', 'STRING']

    def test_click_button(self):
        tokens = lex_all('click the button "Submit"')
        types = [t[0] for t in tokens]
        assert types == ['CLICK', 'THE', 'BUTTON', 'STRING']

    def test_type_into(self):
        tokens = lex_all('type "hello" into the input near "Name"')
        types = [t[0] for t in tokens]
        assert types == ['TYPE', 'STRING', 'INTO', 'THE', 'INPUT',
                         'NEAR', 'STRING']

    def test_verify_contains(self):
        tokens = lex_all('verify the heading contains "Dashboard"')
        types = [t[0] for t in tokens]
        assert types == ['VERIFY', 'THE', 'HEADING', 'CONTAINS', 'STRING']

    def test_set_variable(self):
        tokens = lex_all('set $name to text of the input "email"')
        types = [t[0] for t in tokens]
        assert types == ['SET', 'VARIABLE', 'TO', 'TEXT', 'OF',
                         'THE', 'INPUT', 'STRING']

    def test_wait_with_timeout(self):
        tokens = lex_all('wait up to 30 seconds for the button "OK"')
        types = [t[0] for t in tokens]
        assert types == ['WAIT', 'UP', 'TO', 'NUMBER', 'SECONDS',
                         'FOR', 'THE', 'BUTTON', 'STRING']

    def test_ordinal_element(self):
        tokens = lex_all('click the 2nd button "Delete"')
        types = [t[0] for t in tokens]
        assert types == ['CLICK', 'THE', 'ORDINAL', 'BUTTON', 'STRING']

    def test_error_on_bad_char(self):
        with pytest.raises(SyntaxError, match="Unexpected character"):
            lex_all('click @badchar')