"""
WebSpec DSL - PLY Lexer
Tokenizes English-like test scripts into a stream for the parser.
"""

import ply.lex as lex

# ── Reserved words ────────────────────────────────────────
reserved = {
    # navigation
    'navigate': 'NAVIGATE', 'go': 'GO', 'back': 'BACK',
    'forward': 'FORWARD', 'refresh': 'REFRESH', 'to': 'TO',
    # element types
    'button': 'BUTTON', 'link': 'LINK', 'input': 'INPUT',
    'dropdown': 'DROPDOWN', 'checkbox': 'CHECKBOX', 'radio': 'RADIO',
    'image': 'IMAGE', 'heading': 'HEADING', 'table': 'TABLE',
    'row': 'ROW', 'cell': 'CELL', 'element': 'ELEMENT',
    'field': 'FIELD', 'form': 'FORM', 'section': 'SECTION',
    'dialog': 'DIALOG', 'menu': 'MENU', 'item': 'ITEM',
    # selectors
    'the': 'THE', 'with': 'WITH', 'class': 'CLASS', 'id': 'ID',
    'text': 'TEXT', 'attr': 'ATTR', 'placeholder': 'PLACEHOLDER',
    'value': 'VALUE', 'containing': 'CONTAINING',
    'contains': 'CONTAINS', 'matches': 'MATCHES',
    'matching': 'MATCHING', 'near': 'NEAR', 'inside': 'INSIDE',
    'above': 'ABOVE', 'below': 'BELOW', 'after': 'AFTER',
    'before': 'BEFORE',
    # actions
    'click': 'CLICK', 'double': 'DOUBLE', 'right': 'RIGHT',
    'type': 'TYPE', 'into': 'INTO', 'append': 'APPEND',
    'clear': 'CLEAR', 'select': 'SELECT', 'from': 'FROM',
    'check': 'CHECK', 'uncheck': 'UNCHECK', 'toggle': 'TOGGLE',
    'hover': 'HOVER', 'focus': 'FOCUS', 'scroll': 'SCROLL',
    'drag': 'DRAG', 'press': 'PRESS', 'key': 'KEY',
    'upload': 'UPLOAD', 'submit': 'SUBMIT', 'execute': 'EXECUTE',
    'pixels': 'PIXELS', 'down': 'DOWN', 'up': 'UP',
    # assertions
    'verify': 'VERIFY', 'is': 'IS', 'has': 'HAS',
    'visible': 'VISIBLE', 'hidden': 'HIDDEN',
    'enabled': 'ENABLED', 'disabled': 'DISABLED',
    'selected': 'SELECTED', 'checked': 'CHECKED',
    'empty': 'EMPTY', 'focused': 'FOCUSED',
    'equals': 'EQUALS', 'count': 'COUNT',
    'starts': 'STARTS', 'ends': 'ENDS',
    'greater': 'GREATER', 'less': 'LESS', 'than': 'THAN',
    'style': 'STYLE',
    # waits
    'wait': 'WAIT', 'for': 'FOR', 'seconds': 'SECONDS',
    'until': 'UNTIL', 'be': 'BE',
    # variables
    'set': 'SET', 'of': 'OF',
    # control flow
    'if': 'IF', 'then': 'THEN', 'else': 'ELSE', 'end': 'END',
    'repeat': 'REPEAT', 'times': 'TIMES', 'while': 'WHILE',
    'each': 'EACH', 'as': 'AS', 'do': 'DO',
    'try': 'TRY', 'on': 'ON', 'error': 'ERROR',
    'call': 'CALL', 'define': 'DEFINE',
    'and': 'AND', 'or': 'OR', 'not': 'NOT',
    # misc
    'import': 'IMPORT', 'using': 'USING',
    'log': 'LOG', 'take': 'TAKE', 'screenshot': 'SCREENSHOT',
    'accept': 'ACCEPT', 'dismiss': 'DISMISS', 'alert': 'ALERT',
    'switch': 'SWITCH', 'frame': 'FRAME', 'default': 'DEFAULT',
    'window': 'WINDOW', 'open': 'OPEN', 'new': 'NEW',
    'close': 'CLOSE', 'tab': 'TAB',
    'save': 'SAVE', 'source': 'SOURCE', 'cookies': 'COOKIES',
    'cookie': 'COOKIE', 'downloaded': 'DOWNLOADED',
    'url': 'URL', 'title': 'TITLE',
}

tokens = list(set(reserved.values())) + [
    'STRING', 'NUMBER', 'VARIABLE', 'ORDINAL',
    'NEWLINE', 'PLUS', 'LPAREN', 'RPAREN',
]

# ── Simple tokens ────────────────────────────────────────
t_PLUS   = r'\+'
t_LPAREN = r'\('
t_RPAREN = r'\)'

# ── Ordinals: 1st, 2nd, 3rd, 4th ... ────────────────────
def t_ORDINAL(t):
    r'\d+(st|nd|rd|th)'
    t.value = int(t.value[:-2])  # strip suffix, keep int
    return t

# ── Numbers ──────────────────────────────────────────────
def t_NUMBER(t):
    r'\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

# ── Strings (double or single quoted) ───────────────────
def t_STRING(t):
    r'''("([^"\\]|\\.)*"|'([^'\\]|\\.)*')'''
    raw = t.value[1:-1]  # strip quotes
    # Process standard escape sequences
    t.value = raw.replace('\\\\', '\x00') \
                  .replace('\\"', '"') \
                  .replace("\\'", "'") \
                  .replace('\\n', '\n') \
                  .replace('\\t', '\t') \
                  .replace('\\r', '\r') \
                  .replace('\x00', '\\')
    return t

# ── Variables: $name or ${name} ──────────────────────────
def t_VARIABLE(t):
    r'\$\{?[a-zA-Z_][a-zA-Z0-9_]*\}?'
    t.value = t.value.strip('${}')
    return t

# ── Identifiers / reserved words ────────────────────────
def t_IDENT(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'STRING')
    if t.type == 'STRING':
        # bare word not in reserved - treat as unquoted string
        pass
    return t

# ── Newlines (significant - statement separators) ───────
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

# ── Comments ─────────────────────────────────────────────
def t_COMMENT(t):
    r'\#[^\n]*'
    pass  # discard

# ── Whitespace (spaces/tabs - not newlines) ─────────────
t_ignore = ' \t\r'

def t_error(t):
    raise SyntaxError(
        f"Unexpected character '{t.value[0]}' at line {t.lexer.lineno}"
    )

lexer = lex.lex()