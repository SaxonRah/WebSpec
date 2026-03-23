"""
WebSpec DSL - AST Nodes
Every grammar rule produces one of these typed nodes.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Base ─────────────────────────────────────────────────
@dataclass
class Node:
    line: int = 0


# ── Program ──────────────────────────────────────────────
@dataclass
class Program(Node):
    statements: list = field(default_factory=list)


# ── Element references ───────────────────────────────────

ElementRefType = 'ElementRef | VarElementRef | RawElementRef'

@dataclass
class ElementRef(Node):
    """Smart element reference with chainable selectors."""
    elem_type: str = 'element'           # button, link, input ...
    ordinal: Optional[int] = None        # 1st, 2nd, 3rd ...
    selectors: list = field(default_factory=list)  # list of Selector


@dataclass
class RawElementRef(Node):
    """Raw CSS selector or XPath passed through."""
    locator: str = ''


@dataclass
class VarElementRef(Node):
    """Element stored in a variable."""
    var_name: str = ''


@dataclass
class Selector(Node):
    kind: str = ''      # 'text', 'class', 'id', 'attr', 'containing',
                        # 'matching', 'near', 'inside', 'above', 'below',
                        # 'after', 'before', 'placeholder', 'value'
    value: str = ''
    extra: str = ''     # for attr: attr_name; for 'near': label text
    child: Optional['ElementRef'] = None  # for inside/above/below


# ── Navigation ───────────────────────────────────────────
@dataclass
class Navigate(Node):
    url: str = ''

@dataclass
class GoBack(Node): pass

@dataclass
class GoForward(Node): pass

@dataclass
class Refresh(Node): pass

@dataclass
class SwitchTab(Node):
    index: int = 0


# ── Actions ──────────────────────────────────────────────
@dataclass
class Click(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    click_type: str = 'single'  # single, double, right

@dataclass
class TypeText(Node):
    text: 'Expr' = None
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class AppendText(Node):
    text: 'Expr' = None
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Clear(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Select(Node):
    # option: str = ''
    option: 'Expr | str' = ''
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Check(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    state: bool = True  # True=check, False=uncheck

@dataclass
class Toggle(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Hover(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Focus(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class ScrollTo(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class ScrollBy(Node):
    direction: str = 'down'
    pixels: int = 300

@dataclass
class DragTo(Node):
    source: 'ElementRef | VarElementRef | RawElementRef' = None
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class PressKey(Node):
    key: str = ""
    modifier: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.modifiers and self.modifier is None:
            self.modifier = "+".join(self.modifiers)
        elif self.modifier and not self.modifiers:
            self.modifiers = [m.strip() for m in self.modifier.split("+") if m.strip()]

@dataclass
class Upload(Node):
    filepath: str = ''
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class Submit(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None

@dataclass
class ExecuteJS(Node):
    script: str = ''


# ── Assertions ───────────────────────────────────────────
@dataclass
class VerifyState(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    state: str = ''   # visible, hidden, enabled, disabled ...

@dataclass
class VerifyText(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    expected: str = ''
    mode: str = 'has'  # 'has' (exact), 'contains', 'matches' (regex)

@dataclass
class VerifyAttr(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    attr_name: str = ''
    expected: str = ''
    op: str = 'is'  # is, contains, starts_with, ends_with

@dataclass
class VerifyCount(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    op: str = 'is' # is, equals, greater_than, less_than
    expected: int = 0

@dataclass
class VerifyURL(Node):
    expected: str = ''
    op: str = 'is'

@dataclass
class VerifyTitle(Node):
    expected: str = ''
    op: str = 'is'

@dataclass
class VerifyCookie(Node):
    name: str = ''
    expected: str = ''
    op: str = 'is'

@dataclass
class VerifyDownloaded(Node):
    filename: str = ''

@dataclass
class VerifyStyle(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    prop: str = ''
    expected: str = ''
    op: str = 'is'


# ── Waits ────────────────────────────────────────────────
@dataclass
class WaitSeconds(Node):
    duration: float = 0

@dataclass
class WaitForElement(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    state: Optional[str] = None  # None = exists, or visible/enabled/...
    timeout: Optional[float] = None


@dataclass
class WaitUntilURL(Node):
    expected: str = ''

@dataclass
class WaitUntilTitle(Node):
    expected: str = ''


# ── Variables & Expressions ──────────────────────────────
@dataclass
class Expr(Node):
    pass

@dataclass
class StringLiteral(Expr):
    value: str = ''

@dataclass
class NumberLiteral(Expr):
    value: float = 0

@dataclass
class VarRef(Expr):
    name: str = ''

@dataclass
class Concat(Expr):
    left: Expr = None
    right: Expr = None

@dataclass
class SetVar(Node):
    name: str = ''
    value: 'Expr | ElementRef' = None
    extract: Optional[str] = None  # 'text', 'attr', 'value', 'count', 'url', 'title'
    attr_name: Optional[str] = None
    target: Optional[ElementRef] = None


# ── Control flow ─────────────────────────────────────────
@dataclass
class Condition(Node):
    pass

@dataclass
class StateCondition(Condition):
    target: 'ElementRef | VarElementRef' = None
    state: str = ''

@dataclass
class CompareCondition(Condition):
    left: Expr = None
    op: str = ''
    right: Expr = None

@dataclass
class URLCondition(Condition):
    expected: str = ''

@dataclass
class NotCondition(Condition):
    child: Condition = None

@dataclass
class BoolCondition(Condition):
    left: Condition = None
    op: str = ''  # 'and', 'or'
    right: Condition = None


@dataclass
class IfStmt(Node):
    condition: Condition = None
    then_body: list = field(default_factory=list)
    else_body: list = field(default_factory=list)

@dataclass
class RepeatTimes(Node):
    count: int = 0
    body: list = field(default_factory=list)

@dataclass
class RepeatWhile(Node):
    condition: Condition = None
    body: list = field(default_factory=list)

@dataclass
class ForEach(Node):
    target: 'ElementRef | VarElementRef | RawElementRef' = None
    var_name: str = ''
    body: list = field(default_factory=list)

@dataclass
class TryCatch(Node):
    try_body: list = field(default_factory=list)
    catch_body: list = field(default_factory=list)

@dataclass
class CallSub(Node):
    name: str = ''

@dataclass
class DefineSub(Node):
    name: str = ''
    body: list = field(default_factory=list)


# ── Misc ─────────────────────────────────────────────────
@dataclass
class Import(Node):
    filepath: str = ''

@dataclass
class WithData(Node):
    filepath: str = ''
    body: list = field(default_factory=list)

@dataclass
class Log(Node):
    message: Expr = None

@dataclass
class TakeScreenshot(Node):
    filename: Optional[str] = None

@dataclass
class AcceptAlert(Node): pass

@dataclass
class DismissAlert(Node): pass

@dataclass
class VerifyAlert(Node):
    expected: str = ''

@dataclass
class SwitchFrame(Node):
    target: 'ElementRef | VarElementRef | RawElementRef | str | None' = None  # None = default

@dataclass
class SwitchWindow(Node):
    name: str = ''

@dataclass
class OpenWindow(Node): pass

@dataclass
class CloseWindow(Node): pass

@dataclass
class SaveSource(Node):
    filename: str = ''

@dataclass
class SaveCookies(Node):
    filename: str = ''