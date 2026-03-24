"""
Tests for the WebSpec PLY parser.
Verifies that token streams produce correct AST nodes.
"""

import pytest
from webspec_lexer import lexer
from webspec_parser import parser
from webspec_ast import *


def parse(text):
    """Helper: parse a script and return the Program AST."""
    lexer.lineno = 1
    return parser.parse(text, lexer=lexer)


def parse_one(text):
    """Parse a single-statement script and return just that statement."""
    prog = parse(text)
    assert isinstance(prog, Program)
    stmts = [s for s in prog.statements if s is not None]
    assert len(stmts) == 1, f"Expected 1 statement, got {len(stmts)}: {stmts}"
    return stmts[0]


# ═══════════════════════════════════════════════════════════
#  Navigation
# ═══════════════════════════════════════════════════════════

class TestNavigation:
    def test_navigate_to(self):
        node = parse_one('navigate to "https://example.com"')
        assert isinstance(node, Navigate)
        assert isinstance(node.url, StringLiteral)
        assert node.url.value == 'https://example.com'

    def test_go_back(self):
        node = parse_one('go back')
        assert isinstance(node, GoBack)

    def test_go_forward(self):
        node = parse_one('go forward')
        assert isinstance(node, GoForward)

    def test_refresh(self):
        node = parse_one('refresh')
        assert isinstance(node, Refresh)

    def test_switch_tab(self):
        node = parse_one('switch to tab 2')
        assert isinstance(node, SwitchTab)
        assert node.index == 2


# ═══════════════════════════════════════════════════════════
#  Element references
# ═══════════════════════════════════════════════════════════

class TestElementRefs:
    def test_simple_type(self):
        node = parse_one('click the button')
        assert isinstance(node, Click)
        assert isinstance(node.target, ElementRef)
        assert node.target.elem_type == 'button'

    def test_type_with_text(self):
        node = parse_one('click the button "Submit"')
        ref = node.target
        assert ref.elem_type == 'button'
        assert len(ref.selectors) == 1
        assert ref.selectors[0].kind == 'text'
        assert ref.selectors[0].value == 'Submit'

    def test_ordinal(self):
        node = parse_one('click the 3rd button "Save"')
        ref = node.target
        assert ref.ordinal == 3
        assert ref.elem_type == 'button'

    def test_with_class(self):
        node = parse_one('click the element with class "main-nav"')
        ref = node.target
        assert ref.selectors[0].kind == 'class'
        assert ref.selectors[0].value == 'main-nav'

    def test_with_id(self):
        node = parse_one('click the element with id "submit-btn"')
        ref = node.target
        assert ref.selectors[0].kind == 'id'
        assert ref.selectors[0].value == 'submit-btn'

    def test_with_attr(self):
        node = parse_one('click the input with attr "name" is "email"')
        ref = node.target
        assert ref.selectors[0].kind == 'attr'
        assert ref.selectors[0].extra == 'name'
        assert ref.selectors[0].value == 'email'

    def test_with_placeholder(self):
        node = parse_one('click the input with placeholder "Search..."')
        ref = node.target
        assert ref.selectors[0].kind == 'placeholder'

    def test_containing(self):
        node = parse_one('click the heading containing "Welcome"')
        ref = node.target
        assert ref.selectors[0].kind == 'containing'
        assert ref.selectors[0].value == 'Welcome'

    def test_matching_regex(self):
        node = parse_one('click the element matching "user-\\d+"')
        ref = node.target
        assert ref.selectors[0].kind == 'matching'

    def test_near(self):
        node = parse_one('click the input near "Email"')
        ref = node.target
        assert ref.selectors[0].kind == 'near'
        assert ref.selectors[0].value == 'Email'

    def test_inside(self):
        node = parse_one(
            'click the button "Delete" inside the dialog "Confirm"')
        ref = node.target
        assert ref.selectors[0].kind == 'text'
        assert ref.selectors[0].value == 'Delete'
        assert ref.selectors[1].kind == 'inside'
        child = ref.selectors[1].child
        assert isinstance(child, ElementRef)
        assert child.elem_type == 'dialog'

    def test_chained_selectors(self):
        node = parse_one(
            'click the button "OK" with class "primary" inside the form "login"')
        ref = node.target
        assert len(ref.selectors) == 3
        assert ref.selectors[0].kind == 'text'
        assert ref.selectors[1].kind == 'class'
        assert ref.selectors[2].kind == 'inside'

    def test_raw_element_css(self):
        node = parse_one('click element "div.container > button.primary"')
        assert isinstance(node.target, RawElementRef)
        assert node.target.locator == 'div.container > button.primary'

    def test_raw_element_xpath(self):
        node = parse_one('click element "//div[@class=\'main\']/button"')
        assert isinstance(node.target, RawElementRef)

    def test_variable_ref(self):
        node = parse_one('click $my_element')
        assert isinstance(node.target, VarElementRef)
        assert node.target.var_name == 'my_element'

    @pytest.mark.parametrize("elem_type", [
        'button', 'link', 'input', 'dropdown', 'checkbox', 'radio',
        'image', 'heading', 'table', 'row', 'cell', 'element',
        'field', 'form', 'section', 'dialog', 'menu', 'item',
    ])
    def test_all_element_types(self, elem_type):
        node = parse_one(f'click the {elem_type}')
        assert node.target.elem_type == elem_type


# ═══════════════════════════════════════════════════════════
#  Actions
# ═══════════════════════════════════════════════════════════

class TestActions:
    def test_click(self):
        node = parse_one('click the button "Go"')
        assert isinstance(node, Click)
        assert node.click_type == 'single'

    def test_double_click(self):
        node = parse_one('double click the element "row"')
        assert isinstance(node, Click)
        assert node.click_type == 'double'

    def test_right_click(self):
        node = parse_one('right click the image "logo"')
        assert isinstance(node, Click)
        assert node.click_type == 'right'

    def test_type_into(self):
        node = parse_one('type "hello" into the input "name"')
        assert isinstance(node, TypeText)
        assert isinstance(node.text, StringLiteral)
        assert node.text.value == 'hello'

    def test_type_variable(self):
        node = parse_one('type $username into the field "login"')
        assert isinstance(node, TypeText)
        assert isinstance(node.text, VarRef)
        assert node.text.name == 'username'

    def test_type_concat(self):
        node = parse_one('type "user" + "@test.com" into the input "email"')
        assert isinstance(node, TypeText)
        assert isinstance(node.text, Concat)

    def test_append(self):
        node = parse_one('append " world" to the input "msg"')
        assert isinstance(node, AppendText)

    def test_clear(self):
        node = parse_one('clear the input "name"')
        assert isinstance(node, Clear)

    # def test_select_from(self):
    #     node = parse_one('select "Option A" from the dropdown "choices"')
    #     assert isinstance(node, Select)
    #     assert node.option == 'Option A'

    def test_select_from(self):
        node = parse_one('select "Option A" from the dropdown "choices"')
        assert isinstance(node, Select)
        assert isinstance(node.option, StringLiteral)
        assert node.option.value == 'Option A'

    def test_check(self):
        node = parse_one('check the checkbox "agree"')
        assert isinstance(node, Check)
        assert node.state is True

    def test_uncheck(self):
        node = parse_one('uncheck the checkbox "agree"')
        assert isinstance(node, Check)
        assert node.state is False

    def test_toggle(self):
        node = parse_one('toggle the checkbox "dark_mode"')
        assert isinstance(node, Toggle)

    def test_hover(self):
        node = parse_one('hover the menu "File"')
        assert isinstance(node, Hover)

    def test_focus(self):
        node = parse_one('focus the input "search"')
        assert isinstance(node, Focus)

    def test_scroll_to(self):
        node = parse_one('scroll to the button "Submit"')
        assert isinstance(node, ScrollTo)

    def test_scroll_down(self):
        node = parse_one('scroll down 500 pixels')
        assert isinstance(node, ScrollBy)
        assert node.direction == 'down'
        assert node.pixels == 500

    def test_scroll_up(self):
        node = parse_one('scroll up 200 pixels')
        assert isinstance(node, ScrollBy)
        assert node.direction == 'up'
        assert node.pixels == 200

    def test_drag(self):
        node = parse_one('drag the element "card" to the element "target"')
        assert isinstance(node, DragTo)

    def test_press_key(self):
        node = parse_one('press key "enter"')
        assert isinstance(node, PressKey)
        assert node.key == 'enter'
        assert node.modifier is None

    def test_press_key_with_modifier(self):
        node = parse_one('press key "a" with "ctrl"')
        assert isinstance(node, PressKey)
        assert node.key == 'a'
        assert node.modifier == 'ctrl'

    def test_upload(self):
        node = parse_one('upload "/tmp/file.pdf" to the input "file"')
        assert isinstance(node, Upload)
        assert node.filepath == '/tmp/file.pdf'

    def test_submit(self):
        node = parse_one('submit the form "login"')
        assert isinstance(node, Submit)

    def test_execute_js(self):
        node = parse_one('execute "window.scrollTo(0,0)"')
        assert isinstance(node, ExecuteJS)
        assert node.script == 'window.scrollTo(0,0)'


# ═══════════════════════════════════════════════════════════
#  Assertions
# ═══════════════════════════════════════════════════════════

class TestAssertions:
    def test_verify_visible(self):
        node = parse_one('verify the button "OK" is visible')
        assert isinstance(node, VerifyState)
        assert node.state == 'visible'

    def test_verify_hidden(self):
        node = parse_one('verify the dialog "modal" is hidden')
        assert isinstance(node, VerifyState)
        assert node.state == 'hidden'

    @pytest.mark.parametrize("state", [
        'visible', 'hidden', 'enabled', 'disabled',
        'selected', 'checked', 'empty', 'focused',
    ])
    def test_all_visibility_states(self, state):
        node = parse_one(f'verify the element "x" is {state}')
        assert isinstance(node, VerifyState)
        assert node.state == state

    def test_verify_has_text(self):
        node = parse_one('verify the heading "title" has text "Welcome"')
        assert isinstance(node, VerifyText)
        assert node.mode == 'has'
        assert node.expected == 'Welcome'

    def test_verify_contains(self):
        node = parse_one('verify the element "msg" contains "success"')
        assert isinstance(node, VerifyText)
        assert node.mode == 'contains'

    def test_verify_matches_regex(self):
        node = parse_one('verify the element "code" matches "\\d{3}"')
        assert isinstance(node, VerifyText)
        assert node.mode == 'matches'

    def test_verify_attr(self):
        node = parse_one(
            'verify the input "email" has attr "type" is "email"')
        assert isinstance(node, VerifyAttr)
        assert node.attr_name == 'type'
        assert node.expected == 'email'

    def test_verify_has_class(self):
        node = parse_one('verify the button "go" has class "primary"')
        assert isinstance(node, VerifyAttr)
        assert node.attr_name == 'class'
        assert node.op == 'contains'

    def test_verify_style(self):
        node = parse_one(
            'verify the element "box" has style "color" is "red"')
        assert isinstance(node, VerifyStyle)
        assert node.prop == 'color'

    def test_verify_count(self):
        node = parse_one(
            'verify the element with class "item" count is 5')
        assert isinstance(node, VerifyCount)
        assert node.op == 'is'
        assert node.expected == 5

    def test_verify_count_gt(self):
        node = parse_one(
            'verify the row count greater than 0')
        assert isinstance(node, VerifyCount)
        assert node.op == 'greater_than'

    def test_verify_url(self):
        node = parse_one('verify url is "https://example.com"')
        assert isinstance(node, VerifyURL)
        assert node.op == 'is'

    def test_verify_url_contains(self):
        node = parse_one('verify url containing "/dashboard"')
        assert isinstance(node, VerifyURL)
        assert node.op == 'containing'

    def test_verify_title(self):
        node = parse_one('verify title is "Home"')
        assert isinstance(node, VerifyTitle)

    def test_verify_cookie(self):
        node = parse_one('verify cookie "session" is "abc123"')
        assert isinstance(node, VerifyCookie)
        assert node.name == 'session'

    def test_verify_downloaded(self):
        node = parse_one('verify downloaded "report.pdf"')
        assert isinstance(node, VerifyDownloaded)
        assert node.filename == 'report.pdf'


# ═══════════════════════════════════════════════════════════
#  Waits
# ═══════════════════════════════════════════════════════════

class TestWaits:
    def test_wait_seconds(self):
        node = parse_one('wait 3 seconds')
        assert isinstance(node, WaitSeconds)
        assert node.duration == 3

    def test_wait_seconds_float(self):
        node = parse_one('wait 0.5 seconds')
        assert isinstance(node, WaitSeconds)
        assert node.duration == 0.5

    def test_wait_for_element(self):
        node = parse_one('wait for the button "Submit"')
        assert isinstance(node, WaitForElement)
        assert node.state is None
        assert node.timeout is None

    def test_wait_for_state(self):
        node = parse_one('wait for the button "OK" to be visible')
        assert isinstance(node, WaitForElement)
        assert node.state == 'visible'

    def test_wait_with_timeout(self):
        node = parse_one('wait up to 30 seconds for the button "OK"')
        assert isinstance(node, WaitForElement)
        assert node.timeout == 30

    # def test_wait_until_url(self):
    #     node = parse_one('wait until url contains "/done"')
    #     assert isinstance(node, WaitUntilURL)
    #     assert node.expected == '/done'

    def test_wait_until_url(self):
        node = parse_one('wait until url contains "/done"')
        assert isinstance(node, WaitUntilURL)
        assert isinstance(node.expected, StringLiteral)
        assert node.expected.value == '/done'

    def test_wait_until_title(self):
        node = parse_one('wait until title contains "Dashboard"')
        assert isinstance(node, WaitUntilTitle)


# ═══════════════════════════════════════════════════════════
#  Variables
# ═══════════════════════════════════════════════════════════

class TestVariables:
    def test_set_string(self):
        node = parse_one('set $name to "Alice"')
        assert isinstance(node, SetVar)
        assert node.name == 'name'
        assert isinstance(node.value, StringLiteral)

    def test_set_number(self):
        node = parse_one('set $count to 42')
        assert isinstance(node, SetVar)
        assert isinstance(node.value, NumberLiteral)

    def test_set_text_of(self):
        node = parse_one('set $title to text of the heading "main"')
        assert isinstance(node, SetVar)
        assert node.extract == 'text'

    def test_set_attr_of(self):
        node = parse_one('set $href to attr "href" of the link "home"')
        assert isinstance(node, SetVar)
        assert node.extract == 'attr'
        assert node.attr_name == 'href'

    def test_set_value_of(self):
        node = parse_one('set $val to value of the input "qty"')
        assert isinstance(node, SetVar)
        assert node.extract == 'value'

    def test_set_count_of(self):
        node = parse_one('set $n to count of the row')
        assert isinstance(node, SetVar)
        assert node.extract == 'count'

    def test_set_url(self):
        node = parse_one('set $page to url')
        assert isinstance(node, SetVar)
        assert node.extract == 'url'

    def test_set_title(self):
        node = parse_one('set $t to title')
        assert isinstance(node, SetVar)
        assert node.extract == 'title'

    def test_set_concat_expr(self):
        node = parse_one('set $msg to "hello " + $name')
        assert isinstance(node, SetVar)
        assert isinstance(node.value, Concat)


# ═══════════════════════════════════════════════════════════
#  Control flow
# ═══════════════════════════════════════════════════════════

class TestControlFlow:
    def test_if_then(self):
        script = '''if the button "OK" is visible then
click the button "OK"
end'''
        node = parse_one(script)
        assert isinstance(node, IfStmt)
        assert isinstance(node.condition, StateCondition)
        assert len(node.then_body) == 1
        assert len(node.else_body) == 0

    def test_if_else(self):
        script = '''if the button "OK" is visible then
click the button "OK"
else
click the button "Cancel"
end'''
        node = parse_one(script)
        assert isinstance(node, IfStmt)
        assert len(node.then_body) == 1
        assert len(node.else_body) == 1

    def test_repeat_times(self):
        script = '''repeat 3 times
click the button "Next"
end'''
        node = parse_one(script)
        assert isinstance(node, RepeatTimes)
        assert node.count == 3
        assert len(node.body) == 1

    def test_repeat_while(self):
        script = '''repeat while the button "Next" is visible
click the button "Next"
end'''
        node = parse_one(script)
        assert isinstance(node, RepeatWhile)
        assert isinstance(node.condition, StateCondition)

    def test_for_each(self):
        script = '''for each the row inside the table as $row do
click the button "Edit" inside $row
end'''
        node = parse_one(script)
        assert isinstance(node, ForEach)
        assert node.var_name == 'row'
        assert len(node.body) == 1

    def test_try_catch(self):
        script = '''try
click the button "Delete"
on error
log "failed"
end'''
        node = parse_one(script)
        assert isinstance(node, TryCatch)
        assert len(node.try_body) == 1
        assert len(node.catch_body) == 1

    def test_define_and_call(self):
        script = '''define "login" as
type "user" into the input "email"
end'''
        node = parse_one(script)
        assert isinstance(node, DefineSub)
        assert node.name == 'login'

    def test_call_sub(self):
        node = parse_one('call "login"')
        assert isinstance(node, CallSub)
        assert node.name == 'login'

    def test_condition_not(self):
        script = '''if not the button "OK" is visible then
log "hidden"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, NotCondition)
        assert isinstance(node.condition.child, StateCondition)

    def test_condition_and(self):
        script = '''if the button "OK" is visible and the input "name" is enabled then
click the button "OK"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, BoolCondition)
        assert node.condition.op == 'and'

    def test_condition_url(self):
        script = '''if url contains "/dashboard" then
log "on dashboard"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, URLCondition)


# ═══════════════════════════════════════════════════════════
#  Misc statements
# ═══════════════════════════════════════════════════════════

class TestMisc:
    def test_log(self):
        node = parse_one('log "hello world"')
        assert isinstance(node, Log)

    def test_log_concat(self):
        node = parse_one('log "count: " + $n')
        assert isinstance(node, Log)
        assert isinstance(node.message, Concat)

    def test_screenshot(self):
        node = parse_one('take screenshot')
        assert isinstance(node, TakeScreenshot)
        assert node.filename is None

    def test_screenshot_named(self):
        node = parse_one('take screenshot as "result.png"')
        assert isinstance(node, TakeScreenshot)
        assert node.filename == 'result.png'

    def test_accept_alert(self):
        node = parse_one('accept alert')
        assert isinstance(node, AcceptAlert)

    def test_dismiss_alert(self):
        node = parse_one('dismiss alert')
        assert isinstance(node, DismissAlert)

    def test_switch_frame(self):
        node = parse_one('switch to frame "editor"')
        assert isinstance(node, SwitchFrame)

    def test_switch_default_frame(self):
        node = parse_one('switch to default frame')
        assert isinstance(node, SwitchFrame)
        assert node.target is None

    def test_open_window(self):
        node = parse_one('open new window')
        assert isinstance(node, OpenWindow)

    def test_close_window(self):
        node = parse_one('close window')
        assert isinstance(node, CloseWindow)

    def test_save_source(self):
        node = parse_one('save source as "page.html"')
        assert isinstance(node, SaveSource)

    def test_save_cookies(self):
        node = parse_one('save cookies as "cookies.json"')
        assert isinstance(node, SaveCookies)


# ═══════════════════════════════════════════════════════════
#  Multi-statement programs
# ═══════════════════════════════════════════════════════════

class TestMultiStatement:
    def test_two_statements(self):
        prog = parse('navigate to "https://x.com"\nclick the button "OK"')
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 2
        assert isinstance(stmts[0], Navigate)
        assert isinstance(stmts[1], Click)

    def test_full_script(self):
        script = '''navigate to "https://example.com/login"
type "admin" into the input near "Email"
type "pass123" into the input near "Password"
click the button "Sign In"
wait for the heading "Dashboard"
verify url contains "/dashboard"
take screenshot as "done.png"'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 7

    def test_syntax_error_bad_token(self):
        with pytest.raises(SyntaxError):
            parse('verify the button')  # incomplete


# ═══════════════════════════════════════════════════════════
#  Parse error reporting
# ═══════════════════════════════════════════════════════════

class TestParseErrors:
    def test_unexpected_token(self):
        with pytest.raises(SyntaxError, match="Unexpected"):
            parse('click click click')

    def test_missing_string(self):
        with pytest.raises(SyntaxError):
            parse('navigate to')


# ═══════════════════════════════════════════════════════════
#  Edge Cases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_leading_newlines(self):
        prog = parse('\n\nnavigate to "https://example.com"')
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 1
        assert isinstance(stmts[0], Navigate)

    def test_trailing_newlines(self):
        prog = parse('navigate to "https://example.com"\n\n\n')
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 1

    def test_comment_only_file(self):
        # Comments are stripped by lexer, leaving only newlines
        prog = parse('# just a comment\n')
        assert isinstance(prog, Program)
        assert len(prog.statements) == 0

    def test_empty_input(self):
        prog = parse('')
        assert isinstance(prog, Program)
        assert len(prog.statements) == 0

    def test_blank_lines_between_statements(self):
        script = '''navigate to "https://example.com"

click the button "OK"

take screenshot'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 3

    def test_comments_between_statements(self):
        script = '''navigate to "https://example.com"
# this is a comment
click the button "OK"
# another comment
take screenshot'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 3

    def test_heavily_commented_script(self):
        script = '''# Header comment
# Another comment

navigate to "https://example.com"

# Middle comment

click the button "Submit"

# Trailing comment
'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 2
        assert isinstance(stmts[0], Navigate)
        assert isinstance(stmts[1], Click)

    def test_setvar_to_execute_js(self):
        script = '''navigate to "https://example.com"
set $title to execute "document.title"

set $count to execute "document.querySelectorAll('.item').length"

log "Title: " + $title'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 4
        assert isinstance(stmts[0], Navigate)
        assert isinstance(stmts[1], SetVar)
        assert isinstance(stmts[2], SetVar)
        assert isinstance(stmts[3], Log)

class TestVariablesInSelectors:
    def test_containing_variable(self):
        node = parse_one('click the heading containing $title')
        ref = node.target
        assert ref.selectors[0].kind == 'containing'
        assert ref.selectors[0].value == '${title}'

    def test_near_variable(self):
        node = parse_one('type "hello" into the input near $label')
        ref = node.target
        assert ref.selectors[0].kind == 'near'
        assert ref.selectors[0].value == '${label}'

    def test_with_text_variable(self):
        node = parse_one('click the button with text $btn_text')
        ref = node.target
        assert ref.selectors[0].kind == 'with_text'
        assert ref.selectors[0].value == '${btn_text}'

    def test_with_class_variable(self):
        node = parse_one('click the element with class $cls')
        ref = node.target
        assert ref.selectors[0].kind == 'class'
        assert ref.selectors[0].value == '${cls}'

    def test_matching_variable(self):
        node = parse_one('click the element matching $pattern')
        ref = node.target
        assert ref.selectors[0].kind == 'matching'
        assert ref.selectors[0].value == '${pattern}'

    def test_text_selector_variable(self):
        node = parse_one('click the button $name')
        ref = node.target
        assert ref.selectors[0].kind == 'text'
        assert ref.selectors[0].value == '${name}'

    def test_chained_with_variable(self):
        node = parse_one(
            'verify the heading containing $title is visible')
        assert isinstance(node, VerifyState)
        assert node.state == 'visible'
        ref = node.target
        assert ref.elem_type == 'heading'
        assert ref.selectors[0].kind == 'containing'
        assert ref.selectors[0].value == '${title}'

    def test_mixed_literal_and_variable_selectors(self):
        node = parse_one(
            'click the button $label inside the form "login"')
        ref = node.target
        assert ref.selectors[0].kind == 'text'
        assert ref.selectors[0].value == '${label}'
        assert ref.selectors[1].kind == 'inside'

    def test_full_script_with_variables_in_selectors(self):
        script = '''set $title to "Welcome"
verify the heading containing $title is visible'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 2
        assert isinstance(stmts[0], SetVar)
        assert isinstance(stmts[1], VerifyState)


class TestVariableConditions:
    """Test the VARIABLE-starting condition rules that resolve ambiguity."""

    def test_var_is_string(self):
        script = '''if $status is "inactive" then
log "inactive"
end'''
        node = parse_one(script)
        assert isinstance(node, IfStmt)
        assert isinstance(node.condition, CompareCondition)
        assert isinstance(node.condition.left, VarRef)
        assert node.condition.left.name == 'status'
        assert node.condition.op == 'is'
        assert isinstance(node.condition.right, StringLiteral)
        assert node.condition.right.value == 'inactive'

    def test_var_is_number(self):
        script = '''if $count is 5 then
log "five"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, CompareCondition)
        assert isinstance(node.condition.right, NumberLiteral)

    def test_var_is_var(self):
        script = '''if $a is $b then
log "equal"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, CompareCondition)
        assert isinstance(node.condition.left, VarRef)
        assert isinstance(node.condition.right, VarRef)

    def test_var_equals_string(self):
        script = '''if $name equals "Alice" then
log "found alice"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, CompareCondition)
        assert node.condition.op == 'equals'

    def test_var_is_visible(self):
        """$element is visible should still be a state check."""
        script = '''if $btn is visible then
click $btn
end'''
        node = parse_one(script)
        assert isinstance(node.condition, StateCondition)
        assert isinstance(node.condition.target, VarElementRef)
        assert node.condition.state == 'visible'

    def test_var_is_hidden(self):
        script = '''if $el is hidden then
log "hidden"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, StateCondition)
        assert node.condition.state == 'hidden'

    def test_var_greater_than_number(self):
        script = '''if $count greater than 0 then
log "has items"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, CompareCondition)
        assert node.condition.op == 'greater_than'

    def test_var_less_than_number(self):
        script = '''if $count less than 100 then
log "under limit"
end'''
        node = parse_one(script)
        assert isinstance(node.condition, CompareCondition)
        assert node.condition.op == 'less_than'

    def test_complex_if_with_var_comparison(self):
        """Full script that was failing before."""
        script = '''set $status to "inactive"
if $status is "inactive" then
    log "Found inactive user"
end'''
        prog = parse(script)
        stmts = [s for s in prog.statements if s is not None]
        assert len(stmts) == 2
        assert isinstance(stmts[0], SetVar)
        assert isinstance(stmts[1], IfStmt)