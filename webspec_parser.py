"""
WebSpec DSL - PLY Parser
Hybrid parser:
- keeps backward compatibility for VARIABLE-starting conditions like:
      if $dialog is visible
- allows blank lines in blocks
- allows expr in SELECT and WAIT UNTIL URL/TITLE CONTAINS
"""

import ply.yacc as yacc
from webspec_lexer import tokens  # noqa
from webspec_ast import *

precedence = (
    ("left", "OR"),
    ("left", "AND"),
    ("right", "NOT"),
    ("left", "PLUS"),
)


# ══════════════════════════════════════════════════════════
# Program / newlines / statement lists
# ══════════════════════════════════════════════════════════

def p_program(p):
    """program : opt_newlines opt_statement_list opt_newlines"""
    p[0] = Program(statements=p[2] or [])


def p_opt_newlines(p):
    """opt_newlines :
                    | newlines"""
    pass


def p_newlines(p):
    """newlines : NEWLINE
                | newlines NEWLINE"""
    pass


def p_opt_statement_list(p):
    """opt_statement_list :
                          | statement_list"""
    p[0] = [] if len(p) == 1 else p[1]


def p_statement_list_single(p):
    """statement_list : statement"""
    p[0] = [p[1]] if p[1] else []


def p_statement_list_more(p):
    """statement_list : statement_list separator statement"""
    p[0] = p[1] + ([p[3]] if p[3] else [])


def p_statement_list_trailing_sep(p):
    """statement_list : statement_list separator"""
    p[0] = p[1]


def p_separator(p):
    """separator : NEWLINE
                 | separator NEWLINE"""
    pass


def p_block(p):
    """block : opt_newlines opt_statement_list opt_newlines"""
    p[0] = p[2] or []


def p_statement(p):
    """statement : nav_stmt
                 | action_stmt
                 | assertion_stmt
                 | wait_stmt
                 | var_stmt
                 | control_stmt
                 | log_stmt
                 | screenshot_stmt
                 | alert_stmt
                 | frame_stmt
                 | window_stmt
                 | extract_stmt
                 | import_stmt"""
    p[0] = p[1]


# ══════════════════════════════════════════════════════════
# Element refs
# ══════════════════════════════════════════════════════════

def p_element_ref_typed(p):
    """element_ref : THE elem_type selector_chain"""
    p[0] = ElementRef(elem_type=p[2], selectors=p[3], line=p.lineno(1))


def p_element_ref_typed_no_selectors(p):
    """element_ref : THE elem_type"""
    p[0] = ElementRef(elem_type=p[2], line=p.lineno(1))


def p_element_ref_ordinal(p):
    """element_ref : THE ORDINAL elem_type selector_chain"""
    p[0] = ElementRef(
        elem_type=p[3],
        ordinal=p[2],
        selectors=p[4],
        line=p.lineno(1),
    )


def p_element_ref_ordinal_no_selectors(p):
    """element_ref : THE ORDINAL elem_type"""
    p[0] = ElementRef(
        elem_type=p[3],
        ordinal=p[2],
        line=p.lineno(1),
    )


def p_element_ref_raw_locator(p):
    """element_ref : ELEMENT STRING"""
    p[0] = RawElementRef(locator=p[2], line=p.lineno(1))


def p_element_ref_explicit_var(p):
    """element_ref : ELEMENT VARIABLE"""
    p[0] = VarElementRef(var_name=p[2], line=p.lineno(1))


def p_element_ref_bare_variable_compat(p):
    """element_ref : VARIABLE"""
    # Compatibility path:
    # lets old syntax like:
    #   if $dialog is visible
    # continue to work.
    p[0] = VarElementRef(var_name=p[1], line=p.lineno(1))


def p_elem_type(p):
    """elem_type : BUTTON
                 | LINK
                 | INPUT
                 | DROPDOWN
                 | CHECKBOX
                 | RADIO
                 | IMAGE
                 | HEADING
                 | TABLE
                 | ROW
                 | CELL
                 | ELEMENT
                 | FIELD
                 | FORM
                 | SECTION
                 | DIALOG
                 | MENU
                 | ITEM"""
    p[0] = p[1].lower()


# ══════════════════════════════════════════════════════════
# Selector chains
# ══════════════════════════════════════════════════════════

def p_text_value_string(p):
    """text_value : STRING"""
    p[0] = p[1]


def p_text_value_variable(p):
    """text_value : VARIABLE"""
    p[0] = f"${{{p[1]}}}"


def p_selector_chain_single(p):
    """selector_chain : selector"""
    p[0] = [p[1]]


def p_selector_chain_more(p):
    """selector_chain : selector_chain selector"""
    p[0] = p[1] + [p[2]]


def p_selector_text(p):
    """selector : text_value"""
    p[0] = Selector(kind="text", value=p[1])


def p_selector_with_class(p):
    """selector : WITH CLASS text_value"""
    p[0] = Selector(kind="class", value=p[3])


def p_selector_with_id(p):
    """selector : WITH ID text_value"""
    p[0] = Selector(kind="id", value=p[3])


def p_selector_with_text(p):
    """selector : WITH TEXT text_value"""
    p[0] = Selector(kind="with_text", value=p[3])


def p_selector_with_attr(p):
    """selector : WITH ATTR text_value IS text_value"""
    p[0] = Selector(kind="attr", extra=p[3], value=p[5])


def p_selector_with_placeholder(p):
    """selector : WITH PLACEHOLDER text_value"""
    p[0] = Selector(kind="placeholder", value=p[3])


def p_selector_with_value(p):
    """selector : WITH VALUE text_value"""
    p[0] = Selector(kind="value", value=p[3])


def p_selector_containing(p):
    """selector : CONTAINING text_value"""
    p[0] = Selector(kind="containing", value=p[2])


def p_selector_matching(p):
    """selector : MATCHING text_value"""
    p[0] = Selector(kind="matching", value=p[2])


def p_selector_near(p):
    """selector : NEAR text_value"""
    p[0] = Selector(kind="near", value=p[2])


def p_selector_inside(p):
    """selector : INSIDE element_ref"""
    p[0] = Selector(kind="inside", child=p[2])


def p_selector_above(p):
    """selector : ABOVE element_ref"""
    p[0] = Selector(kind="above", child=p[2])


def p_selector_below(p):
    """selector : BELOW element_ref"""
    p[0] = Selector(kind="below", child=p[2])


def p_selector_after(p):
    """selector : AFTER element_ref"""
    p[0] = Selector(kind="after", child=p[2])


def p_selector_before(p):
    """selector : BEFORE element_ref"""
    p[0] = Selector(kind="before", child=p[2])


# ══════════════════════════════════════════════════════════
# Navigation
# ══════════════════════════════════════════════════════════

def p_nav_navigate(p):
    """nav_stmt : NAVIGATE TO expr"""
    p[0] = Navigate(url=p[3], line=p.lineno(1))


def p_nav_go_back(p):
    """nav_stmt : GO BACK"""
    p[0] = GoBack(line=p.lineno(1))


def p_nav_go_forward(p):
    """nav_stmt : GO FORWARD"""
    p[0] = GoForward(line=p.lineno(1))


def p_nav_refresh(p):
    """nav_stmt : REFRESH"""
    p[0] = Refresh(line=p.lineno(1))


def p_nav_switch_tab(p):
    """nav_stmt : SWITCH TO TAB NUMBER"""
    p[0] = SwitchTab(index=int(p[4]), line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════

def p_action_click(p):
    """action_stmt : CLICK element_ref"""
    p[0] = Click(target=p[2], click_type="single", line=p.lineno(1))


def p_action_double_click(p):
    """action_stmt : DOUBLE CLICK element_ref"""
    p[0] = Click(target=p[3], click_type="double", line=p.lineno(1))


def p_action_right_click(p):
    """action_stmt : RIGHT CLICK element_ref"""
    p[0] = Click(target=p[3], click_type="right", line=p.lineno(1))


def p_action_type(p):
    """action_stmt : TYPE expr INTO element_ref"""
    p[0] = TypeText(text=p[2], target=p[4], line=p.lineno(1))


def p_action_append(p):
    """action_stmt : APPEND expr TO element_ref"""
    p[0] = AppendText(text=p[2], target=p[4], line=p.lineno(1))


def p_action_clear(p):
    """action_stmt : CLEAR element_ref"""
    p[0] = Clear(target=p[2], line=p.lineno(1))


def p_action_select(p):
    """action_stmt : SELECT expr FROM element_ref"""
    p[0] = Select(option=p[2], target=p[4], line=p.lineno(1))


def p_action_check(p):
    """action_stmt : CHECK element_ref"""
    p[0] = Check(target=p[2], state=True, line=p.lineno(1))


def p_action_uncheck(p):
    """action_stmt : UNCHECK element_ref"""
    p[0] = Check(target=p[2], state=False, line=p.lineno(1))


def p_action_toggle(p):
    """action_stmt : TOGGLE element_ref"""
    p[0] = Toggle(target=p[2], line=p.lineno(1))


def p_action_hover(p):
    """action_stmt : HOVER element_ref"""
    p[0] = Hover(target=p[2], line=p.lineno(1))


def p_action_focus(p):
    """action_stmt : FOCUS element_ref"""
    p[0] = Focus(target=p[2], line=p.lineno(1))


def p_action_scroll_to(p):
    """action_stmt : SCROLL TO element_ref"""
    p[0] = ScrollTo(target=p[3], line=p.lineno(1))


def p_action_scroll_by(p):
    """action_stmt : SCROLL DOWN NUMBER PIXELS
                   | SCROLL UP NUMBER PIXELS"""
    p[0] = ScrollBy(direction=p[2].lower(), pixels=int(p[3]), line=p.lineno(1))


def p_action_drag(p):
    """action_stmt : DRAG element_ref TO element_ref"""
    p[0] = DragTo(source=p[2], target=p[4], line=p.lineno(1))


def p_action_press_key(p):
    """action_stmt : PRESS KEY STRING"""
    p[0] = PressKey(key=p[3], line=p.lineno(1))


def p_action_press_key_with_modifier(p):
    """action_stmt : PRESS KEY STRING WITH STRING"""
    p[0] = PressKey(key=p[3], modifier=p[5], line=p.lineno(1))


def p_action_upload(p):
    """action_stmt : UPLOAD STRING TO element_ref"""
    p[0] = Upload(filepath=p[2], target=p[4], line=p.lineno(1))


def p_action_submit(p):
    """action_stmt : SUBMIT element_ref"""
    p[0] = Submit(target=p[2], line=p.lineno(1))


def p_action_execute(p):
    """action_stmt : EXECUTE STRING"""
    p[0] = ExecuteJS(script=p[2], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Assertions
# ══════════════════════════════════════════════════════════

def p_visibility(p):
    """visibility : VISIBLE
                  | HIDDEN
                  | ENABLED
                  | DISABLED
                  | SELECTED
                  | CHECKED
                  | EMPTY
                  | FOCUSED"""
    p[0] = p[1].lower()


def p_assert_state(p):
    """assertion_stmt : VERIFY element_ref IS visibility"""
    p[0] = VerifyState(target=p[2], state=p[4], line=p.lineno(1))


def p_assert_has_text(p):
    """assertion_stmt : VERIFY element_ref HAS TEXT text_value"""
    p[0] = VerifyText(target=p[2], expected=p[5], mode="has", line=p.lineno(1))


def p_assert_contains(p):
    """assertion_stmt : VERIFY element_ref CONTAINS text_value"""
    p[0] = VerifyText(target=p[2], expected=p[4], mode="contains", line=p.lineno(1))


def p_assert_matches(p):
    """assertion_stmt : VERIFY element_ref MATCHES text_value"""
    p[0] = VerifyText(target=p[2], expected=p[4], mode="matches", line=p.lineno(1))


def p_assert_attr(p):
    """assertion_stmt : VERIFY element_ref HAS ATTR STRING eq_op text_value"""
    p[0] = VerifyAttr(
        target=p[2],
        attr_name=p[5],
        expected=p[7],
        op=p[6],
        line=p.lineno(1),
    )


def p_assert_has_class(p):
    """assertion_stmt : VERIFY element_ref HAS CLASS text_value"""
    p[0] = VerifyAttr(
        target=p[2],
        attr_name="class",
        expected=p[5],
        op="contains",
        line=p.lineno(1),
    )


def p_assert_style(p):
    """assertion_stmt : VERIFY element_ref HAS STYLE STRING eq_op text_value"""
    p[0] = VerifyStyle(
        target=p[2],
        prop=p[5],
        expected=p[7],
        op=p[6],
        line=p.lineno(1),
    )


def p_assert_count(p):
    """assertion_stmt : VERIFY element_ref COUNT comparator NUMBER"""
    p[0] = VerifyCount(target=p[2], op=p[4], expected=int(p[5]), line=p.lineno(1))


def p_comparator(p):
    """comparator : IS
                  | EQUALS
                  | GREATER THAN
                  | LESS THAN"""
    if len(p) == 2:
        p[0] = p[1].lower()
    else:
        p[0] = f"{p[1].lower()}_{p[2].lower()}"


def p_eq_op(p):
    """eq_op : IS
             | EQUALS
             | CONTAINS
             | CONTAINING
             | MATCHES
             | STARTS WITH
             | ENDS WITH"""
    if len(p) == 2:
        val = p[1].lower()
        if val == "contains":
            val = "containing"
        if val == "matches":
            val = "matching"
        p[0] = val
    else:
        p[0] = f"{p[1].lower()}_{p[2].lower()}"


def p_assert_url(p):
    """assertion_stmt : VERIFY URL eq_op text_value"""
    p[0] = VerifyURL(expected=p[4], op=p[3], line=p.lineno(1))


def p_assert_title(p):
    """assertion_stmt : VERIFY TITLE eq_op text_value"""
    p[0] = VerifyTitle(expected=p[4], op=p[3], line=p.lineno(1))


def p_assert_cookie(p):
    """assertion_stmt : VERIFY COOKIE STRING eq_op text_value"""
    p[0] = VerifyCookie(name=p[3], expected=p[5], op=p[4], line=p.lineno(1))


def p_assert_downloaded(p):
    """assertion_stmt : VERIFY DOWNLOADED STRING"""
    p[0] = VerifyDownloaded(filename=p[3], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Waits
# ══════════════════════════════════════════════════════════

def p_wait_seconds(p):
    """wait_stmt : WAIT NUMBER SECONDS"""
    p[0] = WaitSeconds(duration=p[2], line=p.lineno(1))


def p_wait_for_element(p):
    """wait_stmt : WAIT FOR element_ref"""
    p[0] = WaitForElement(target=p[3], line=p.lineno(1))


def p_wait_for_state(p):
    """wait_stmt : WAIT FOR element_ref TO BE visibility"""
    p[0] = WaitForElement(target=p[3], state=p[6], line=p.lineno(1))


def p_wait_up_to_for_element(p):
    """wait_stmt : WAIT UP TO NUMBER SECONDS FOR element_ref"""
    p[0] = WaitForElement(target=p[7], timeout=p[4], line=p.lineno(1))


def p_wait_until_url_contains(p):
    """wait_stmt : WAIT UNTIL URL CONTAINS expr"""
    p[0] = WaitUntilURL(expected=p[5], line=p.lineno(1))


def p_wait_until_title_contains(p):
    """wait_stmt : WAIT UNTIL TITLE CONTAINS expr"""
    p[0] = WaitUntilTitle(expected=p[5], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Expressions / variables
# ══════════════════════════════════════════════════════════

def p_expr_string(p):
    """expr : STRING"""
    p[0] = StringLiteral(value=p[1])


def p_expr_number(p):
    """expr : NUMBER"""
    p[0] = NumberLiteral(value=p[1])


def p_expr_variable(p):
    """expr : VARIABLE"""
    p[0] = VarRef(name=p[1])


def p_expr_concat(p):
    """expr : expr PLUS expr"""
    p[0] = Concat(left=p[1], right=p[3])


def p_expr_parens(p):
    """expr : LPAREN expr RPAREN"""
    p[0] = p[2]


def p_var_set_expr(p):
    """var_stmt : SET VARIABLE TO expr"""
    p[0] = SetVar(name=p[2], value=p[4], line=p.lineno(1))


def p_var_set_text_of(p):
    """var_stmt : SET VARIABLE TO TEXT OF element_ref"""
    p[0] = SetVar(name=p[2], extract="text", target=p[6], line=p.lineno(1))


def p_var_set_attr_of(p):
    """var_stmt : SET VARIABLE TO ATTR STRING OF element_ref"""
    p[0] = SetVar(
        name=p[2],
        extract="attr",
        attr_name=p[5],
        target=p[7],
        line=p.lineno(1),
    )


def p_var_set_value_of(p):
    """var_stmt : SET VARIABLE TO VALUE OF element_ref"""
    p[0] = SetVar(name=p[2], extract="value", target=p[6], line=p.lineno(1))


def p_var_set_count_of(p):
    """var_stmt : SET VARIABLE TO COUNT OF element_ref"""
    p[0] = SetVar(name=p[2], extract="count", target=p[6], line=p.lineno(1))


def p_var_set_url(p):
    """var_stmt : SET VARIABLE TO URL"""
    p[0] = SetVar(name=p[2], extract="url", line=p.lineno(1))


def p_var_set_title(p):
    """var_stmt : SET VARIABLE TO TITLE"""
    p[0] = SetVar(name=p[2], extract="title", line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Control flow
# ══════════════════════════════════════════════════════════

def p_if_stmt(p):
    """control_stmt : IF condition THEN block END"""
    p[0] = IfStmt(condition=p[2], then_body=p[4], line=p.lineno(1))


def p_if_else_stmt(p):
    """control_stmt : IF condition THEN block ELSE block END"""
    p[0] = IfStmt(
        condition=p[2],
        then_body=p[4],
        else_body=p[6],
        line=p.lineno(1),
    )


def p_repeat_times(p):
    """control_stmt : REPEAT NUMBER TIMES block END"""
    p[0] = RepeatTimes(count=int(p[2]), body=p[4], line=p.lineno(1))


def p_repeat_while(p):
    """control_stmt : REPEAT WHILE condition block END"""
    p[0] = RepeatWhile(condition=p[3], body=p[4], line=p.lineno(1))


def p_for_each_with_do(p):
    """control_stmt : FOR EACH element_ref AS VARIABLE DO block END"""
    p[0] = ForEach(target=p[3], var_name=p[5], body=p[7], line=p.lineno(1))


def p_for_each_without_do(p):
    """control_stmt : FOR EACH element_ref AS VARIABLE block END"""
    p[0] = ForEach(target=p[3], var_name=p[5], body=p[6], line=p.lineno(1))


def p_try_catch(p):
    """control_stmt : TRY block ON ERROR block END"""
    p[0] = TryCatch(try_body=p[2], catch_body=p[5], line=p.lineno(1))


def p_call_sub(p):
    """control_stmt : CALL STRING"""
    p[0] = CallSub(name=p[2], line=p.lineno(1))


def p_define_sub(p):
    """control_stmt : DEFINE STRING AS block END"""
    p[0] = DefineSub(name=p[2], body=p[4], line=p.lineno(1))


def p_with_data(p):
    """control_stmt : USING STRING block END"""
    p[0] = WithData(filepath=p[2], body=p[3], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
# Conditions
# ══════════════════════════════════════════════════════════

def p_condition_element_state(p):
    """condition : element_ref IS visibility"""
    p[0] = StateCondition(target=p[1], state=p[3])


def p_condition_compare(p):
    """condition : expr comparator expr"""
    p[0] = CompareCondition(left=p[1], op=p[2], right=p[3])


def p_condition_url_contains(p):
    """condition : URL CONTAINS text_value"""
    p[0] = URLCondition(expected=p[3])


def p_condition_not(p):
    """condition : NOT condition"""
    p[0] = NotCondition(child=p[2])


def p_condition_and(p):
    """condition : condition AND condition"""
    p[0] = BoolCondition(left=p[1], op="and", right=p[3])


def p_condition_or(p):
    """condition : condition OR condition"""
    p[0] = BoolCondition(left=p[1], op="or", right=p[3])


def p_condition_parens(p):
    """condition : LPAREN condition RPAREN"""
    p[0] = p[2]


# ── Variable-starting conditions (compatibility shim) ──
# These resolve the VARIABLE ambiguity between:
#   element_ref : VARIABLE
# and
#   expr : VARIABLE
#
# We keep them so legacy syntax like:
#   if $dialog is visible
# continues to parse, while also allowing:
#   if $count is 3
#
# If you ever want a cleaner DSL later, this is the section to remove.

def p_condition_var_state(p):
    """condition : VARIABLE IS visibility"""
    p[0] = StateCondition(
        target=VarElementRef(var_name=p[1], line=p.lineno(1)),
        state=p[3],
    )


def p_condition_var_compare_is(p):
    """condition : VARIABLE IS expr"""
    p[0] = CompareCondition(
        left=VarRef(name=p[1]),
        op="is",
        right=p[3],
    )


def p_condition_var_compare_equals(p):
    """condition : VARIABLE EQUALS expr"""
    p[0] = CompareCondition(
        left=VarRef(name=p[1]),
        op="equals",
        right=p[3],
    )


def p_condition_var_compare_greater(p):
    """condition : VARIABLE GREATER THAN expr"""
    p[0] = CompareCondition(
        left=VarRef(name=p[1]),
        op="greater_than",
        right=p[4],
    )


def p_condition_var_compare_less(p):
    """condition : VARIABLE LESS THAN expr"""
    p[0] = CompareCondition(
        left=VarRef(name=p[1]),
        op="less_than",
        right=p[4],
    )


# ══════════════════════════════════════════════════════════
# Misc statements
# ══════════════════════════════════════════════════════════

def p_import_stmt(p):
    """import_stmt : IMPORT STRING"""
    p[0] = Import(filepath=p[2], line=p.lineno(1))


def p_log_stmt(p):
    """log_stmt : LOG expr"""
    p[0] = Log(message=p[2], line=p.lineno(1))


def p_screenshot_stmt(p):
    """screenshot_stmt : TAKE SCREENSHOT"""
    p[0] = TakeScreenshot(line=p.lineno(1))


def p_screenshot_named(p):
    """screenshot_stmt : TAKE SCREENSHOT AS STRING"""
    p[0] = TakeScreenshot(filename=p[4], line=p.lineno(1))


def p_alert_accept(p):
    """alert_stmt : ACCEPT ALERT"""
    p[0] = AcceptAlert(line=p.lineno(1))


def p_alert_dismiss(p):
    """alert_stmt : DISMISS ALERT"""
    p[0] = DismissAlert(line=p.lineno(1))


def p_alert_verify(p):
    """alert_stmt : VERIFY ALERT HAS TEXT text_value"""
    p[0] = VerifyAlert(expected=p[5], line=p.lineno(1))


def p_frame_switch_element(p):
    """frame_stmt : SWITCH TO FRAME element_ref"""
    p[0] = SwitchFrame(target=p[4], line=p.lineno(1))


def p_frame_switch_string(p):
    """frame_stmt : SWITCH TO FRAME STRING"""
    p[0] = SwitchFrame(target=p[4], line=p.lineno(1))


def p_frame_switch_default(p):
    """frame_stmt : SWITCH TO DEFAULT FRAME"""
    p[0] = SwitchFrame(target=None, line=p.lineno(1))


def p_window_switch(p):
    """window_stmt : SWITCH TO WINDOW STRING"""
    p[0] = SwitchWindow(name=p[4], line=p.lineno(1))


def p_window_open(p):
    """window_stmt : OPEN NEW WINDOW"""
    p[0] = OpenWindow(line=p.lineno(1))


def p_window_close(p):
    """window_stmt : CLOSE WINDOW"""
    p[0] = CloseWindow(line=p.lineno(1))


def p_extract_save_source(p):
    """extract_stmt : SAVE SOURCE AS STRING"""
    p[0] = SaveSource(filename=p[4], line=p.lineno(1))


def p_extract_save_cookies(p):
    """extract_stmt : SAVE COOKIES AS STRING"""
    p[0] = SaveCookies(filename=p[4], line=p.lineno(1))


def p_error(p):
    if p:
        raise SyntaxError(f"Unexpected '{p.value}' ({p.type}) at line {p.lineno}")
    raise SyntaxError("Unexpected end of input")


parser = yacc.yacc()