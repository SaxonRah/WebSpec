"""
WebSpec DSL - PLY Parser
LALR(1) grammar rules that build the AST from the token stream.
"""

import ply.yacc as yacc
from webspec_lexer import tokens  # noqa - PLY needs this import
from webspec_ast import *

# ── Precedence (lowest to highest) ───────────────────────
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'PLUS'),
)


# ══════════════════════════════════════════════════════════
#  Program & statement list
# ══════════════════════════════════════════════════════════

def p_program(p):
    '''program : newlines statement_list
               | statement_list'''
    if len(p) == 3:
        p[0] = Program(statements=p[2])
    else:
        p[0] = Program(statements=p[1])

def p_program_empty(p):
    '''program : newlines
               | '''
    p[0] = Program(statements=[])

def p_newlines(p):
    '''newlines : NEWLINE
               | newlines NEWLINE'''
    pass

def p_statement_list(p):
    '''statement_list : statement
                      | statement_list NEWLINE statement
                      | statement_list NEWLINE'''
    if len(p) == 2:
        p[0] = [p[1]] if p[1] else []
    elif len(p) == 3:
        p[0] = p[1]
    else:
        p[0] = p[1] + ([p[3]] if p[3] else [])

def p_statement(p):
    '''statement : nav_stmt
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
                 | import_stmt'''
    p[0] = p[1]

def p_block(p):
    '''block : newlines statement_list
             | statement_list
             | newlines'''
    p[0] = [] if len(p) == 2 and p.slice[1].type == 'newlines' else (p[2] if len(p) == 3 else p[1])

# ══════════════════════════════════════════════════════════
#  Element references (the smart-find core)
# ══════════════════════════════════════════════════════════

def p_element_ref_typed(p):
    '''element_ref : THE elem_type selector_chain'''
    p[0] = ElementRef(elem_type=p[2], selectors=p[3], line=p.lineno(1))

def p_element_ref_ordinal(p):
    '''element_ref : THE ORDINAL elem_type selector_chain'''
    p[0] = ElementRef(elem_type=p[3], ordinal=p[2], selectors=p[4],
                       line=p.lineno(1))

def p_element_ref_ordinal_no_sel(p):
    '''element_ref : THE ORDINAL elem_type'''
    p[0] = ElementRef(elem_type=p[3], ordinal=p[2], line=p.lineno(1))

def p_element_ref_typed_no_sel(p):
    '''element_ref : THE elem_type'''
    p[0] = ElementRef(elem_type=p[2], line=p.lineno(1))

def p_element_ref_raw(p):
    '''element_ref : ELEMENT STRING'''
    p[0] = RawElementRef(locator=p[2], line=p.lineno(1))

def p_element_ref_var(p):
    '''element_ref : VARIABLE'''
    p[0] = VarElementRef(var_name=p[1], line=p.lineno(1))

def p_elem_type(p):
    '''elem_type : BUTTON
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
                 | ITEM'''
    p[0] = p[1].lower()


# ── Selector chains ─────────────────────────────────────

# ── Text value: string literal or variable reference ─────
# Variables are stored as ${name} for runtime interpolation
def p_text_value_string(p):
    '''text_value : STRING'''
    p[0] = p[1]

def p_text_value_variable(p):
    '''text_value : VARIABLE'''
    p[0] = f'${{{p[1]}}}'  # e.g. ${title} - resolved at runtime

def p_selector_chain(p):
    '''selector_chain : selector
                      | selector_chain selector'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_selector_text(p):
    '''selector : text_value'''
    p[0] = Selector(kind='text', value=p[1])

def p_selector_class(p):
    '''selector : WITH CLASS text_value'''
    p[0] = Selector(kind='class', value=p[3])

def p_selector_id(p):
    '''selector : WITH ID text_value'''
    p[0] = Selector(kind='id', value=p[3])

def p_selector_with_text(p):
    '''selector : WITH TEXT text_value'''
    p[0] = Selector(kind='with_text', value=p[3])

def p_selector_attr(p):
    '''selector : WITH ATTR text_value IS text_value'''
    p[0] = Selector(kind='attr', extra=p[3], value=p[5])

def p_selector_placeholder(p):
    '''selector : WITH PLACEHOLDER text_value'''
    p[0] = Selector(kind='placeholder', value=p[3])

def p_selector_with_value(p):
    '''selector : WITH VALUE text_value'''
    p[0] = Selector(kind='value', value=p[3])

def p_selector_containing(p):
    '''selector : CONTAINING text_value'''
    p[0] = Selector(kind='containing', value=p[2])

def p_selector_matching(p):
    '''selector : MATCHING text_value'''
    p[0] = Selector(kind='matching', value=p[2])

def p_selector_near(p):
    '''selector : NEAR text_value'''
    p[0] = Selector(kind='near', value=p[2])

def p_selector_inside(p):
    '''selector : INSIDE element_ref'''
    p[0] = Selector(kind='inside', child=p[2])

def p_selector_above(p):
    '''selector : ABOVE element_ref'''
    p[0] = Selector(kind='above', child=p[2])

def p_selector_below(p):
    '''selector : BELOW element_ref'''
    p[0] = Selector(kind='below', child=p[2])

def p_selector_after(p):
    '''selector : AFTER element_ref'''
    p[0] = Selector(kind='after', child=p[2])

def p_selector_before(p):
    '''selector : BEFORE element_ref'''
    p[0] = Selector(kind='before', child=p[2])


# ══════════════════════════════════════════════════════════
#  Navigation
# ══════════════════════════════════════════════════════════

def p_nav_navigate(p):
    '''nav_stmt : NAVIGATE TO expr'''
    p[0] = Navigate(url=p[3], line=p.lineno(1))

def p_nav_back(p):
    '''nav_stmt : GO BACK'''
    p[0] = GoBack(line=p.lineno(1))

def p_nav_forward(p):
    '''nav_stmt : GO FORWARD'''
    p[0] = GoForward(line=p.lineno(1))

def p_nav_refresh(p):
    '''nav_stmt : REFRESH'''
    p[0] = Refresh(line=p.lineno(1))

def p_nav_switch_tab(p):
    '''nav_stmt : SWITCH TO TAB NUMBER'''
    p[0] = SwitchTab(index=int(p[4]), line=p.lineno(1))


# ══════════════════════════════════════════════════════════
#  Actions
# ══════════════════════════════════════════════════════════

def p_action_click(p):
    '''action_stmt : CLICK element_ref'''
    p[0] = Click(target=p[2], click_type='single', line=p.lineno(1))

def p_action_double_click(p):
    '''action_stmt : DOUBLE CLICK element_ref'''
    p[0] = Click(target=p[3], click_type='double', line=p.lineno(1))

def p_action_right_click(p):
    '''action_stmt : RIGHT CLICK element_ref'''
    p[0] = Click(target=p[3], click_type='right', line=p.lineno(1))

def p_action_type(p):
    '''action_stmt : TYPE expr INTO element_ref'''
    p[0] = TypeText(text=p[2], target=p[4], line=p.lineno(1))

def p_action_append(p):
    '''action_stmt : APPEND expr TO element_ref'''
    p[0] = AppendText(text=p[2], target=p[4], line=p.lineno(1))

def p_action_clear(p):
    '''action_stmt : CLEAR element_ref'''
    p[0] = Clear(target=p[2], line=p.lineno(1))

def p_action_select(p):
    '''action_stmt : SELECT STRING FROM element_ref'''
    p[0] = Select(option=p[2], target=p[4], line=p.lineno(1))

def p_action_check(p):
    '''action_stmt : CHECK element_ref'''
    p[0] = Check(target=p[2], state=True, line=p.lineno(1))

def p_action_uncheck(p):
    '''action_stmt : UNCHECK element_ref'''
    p[0] = Check(target=p[2], state=False, line=p.lineno(1))

def p_action_toggle(p):
    '''action_stmt : TOGGLE element_ref'''
    p[0] = Toggle(target=p[2], line=p.lineno(1))

def p_action_hover(p):
    '''action_stmt : HOVER element_ref'''
    p[0] = Hover(target=p[2], line=p.lineno(1))

def p_action_focus(p):
    '''action_stmt : FOCUS element_ref'''
    p[0] = Focus(target=p[2], line=p.lineno(1))

def p_action_scroll_to(p):
    '''action_stmt : SCROLL TO element_ref'''
    p[0] = ScrollTo(target=p[3], line=p.lineno(1))

def p_action_scroll_by(p):
    '''action_stmt : SCROLL DOWN NUMBER PIXELS
                   | SCROLL UP NUMBER PIXELS'''
    p[0] = ScrollBy(direction=p[2].lower(), pixels=int(p[3]),
                     line=p.lineno(1))

def p_action_drag(p):
    '''action_stmt : DRAG element_ref TO element_ref'''
    p[0] = DragTo(source=p[2], target=p[4], line=p.lineno(1))

def p_action_press_key(p):
    '''action_stmt : PRESS KEY STRING'''
    p[0] = PressKey(key=p[3], line=p.lineno(1))

def p_action_press_key_mod(p):
    '''action_stmt : PRESS KEY STRING WITH STRING'''
    p[0] = PressKey(key=p[3], modifier=p[5], line=p.lineno(1))

def p_action_upload(p):
    '''action_stmt : UPLOAD STRING TO element_ref'''
    p[0] = Upload(filepath=p[2], target=p[4], line=p.lineno(1))

def p_action_submit(p):
    '''action_stmt : SUBMIT element_ref'''
    p[0] = Submit(target=p[2], line=p.lineno(1))

def p_action_execute(p):
    '''action_stmt : EXECUTE STRING'''
    p[0] = ExecuteJS(script=p[2], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
#  Assertions
# ══════════════════════════════════════════════════════════

def p_assert_state(p):
    '''assertion_stmt : VERIFY element_ref IS visibility'''
    p[0] = VerifyState(target=p[2], state=p[4], line=p.lineno(1))

def p_visibility(p):
    '''visibility : VISIBLE
                  | HIDDEN
                  | ENABLED
                  | DISABLED
                  | SELECTED
                  | CHECKED
                  | EMPTY
                  | FOCUSED'''
    p[0] = p[1].lower()

def p_assert_has_text(p):
    '''assertion_stmt : VERIFY element_ref HAS TEXT STRING'''
    p[0] = VerifyText(target=p[2], expected=p[5], mode='has',
                       line=p.lineno(1))

def p_assert_contains(p):
    '''assertion_stmt : VERIFY element_ref CONTAINS STRING'''
    p[0] = VerifyText(target=p[2], expected=p[4], mode='contains',
                       line=p.lineno(1))

def p_assert_matches(p):
    '''assertion_stmt : VERIFY element_ref MATCHES STRING'''
    p[0] = VerifyText(target=p[2], expected=p[4], mode='matches',
                       line=p.lineno(1))

def p_assert_attr(p):
    '''assertion_stmt : VERIFY element_ref HAS ATTR STRING eq_op STRING'''
    p[0] = VerifyAttr(target=p[2], attr_name=p[5], expected=p[7],
                       op=p[6], line=p.lineno(1))

def p_assert_has_class(p):
    '''assertion_stmt : VERIFY element_ref HAS CLASS STRING'''
    p[0] = VerifyAttr(target=p[2], attr_name='class', expected=p[5],
                       op='contains', line=p.lineno(1))

def p_assert_style(p):
    '''assertion_stmt : VERIFY element_ref HAS STYLE STRING eq_op STRING'''
    p[0] = VerifyStyle(target=p[2], prop=p[5], expected=p[7],
                        op=p[6], line=p.lineno(1))

def p_assert_count(p):
    '''assertion_stmt : VERIFY element_ref COUNT comparator NUMBER'''
    p[0] = VerifyCount(target=p[2], op=p[4], expected=int(p[5]),
                        line=p.lineno(1))

# ── Assertion rules with VARIABLE support ────────────────

def p_assert_url_var(p):
    '''assertion_stmt : VERIFY URL eq_op VARIABLE'''
    p[0] = VerifyURL(expected=f'${{{p[4]}}}', op=p[3], line=p.lineno(1))

def p_assert_title_var(p):
    '''assertion_stmt : VERIFY TITLE eq_op VARIABLE'''
    p[0] = VerifyTitle(expected=f'${{{p[4]}}}', op=p[3], line=p.lineno(1))

def p_assert_has_text_var(p):
    '''assertion_stmt : VERIFY element_ref HAS TEXT VARIABLE'''
    p[0] = VerifyText(target=p[2], expected=f'${{{p[5]}}}', mode='has',
                       line=p.lineno(1))

def p_assert_contains_var(p):
    '''assertion_stmt : VERIFY element_ref CONTAINS VARIABLE'''
    p[0] = VerifyText(target=p[2], expected=f'${{{p[4]}}}', mode='contains',
                       line=p.lineno(1))

def p_assert_matches_var(p):
    '''assertion_stmt : VERIFY element_ref MATCHES VARIABLE'''
    p[0] = VerifyText(target=p[2], expected=f'${{{p[4]}}}', mode='matches',
                       line=p.lineno(1))

def p_comparator(p):
    '''comparator : IS
                  | EQUALS
                  | GREATER THAN
                  | LESS THAN'''
    if len(p) == 2:
        p[0] = p[1].lower()
    else:
        p[0] = f'{p[1].lower()}_{p[2].lower()}'

def p_eq_op(p):
    '''eq_op : IS
             | EQUALS
             | CONTAINS
             | CONTAINING
             | MATCHES
             | STARTS WITH
             | ENDS WITH'''
    if len(p) == 2:
        val = p[1].lower()
        # Normalize synonyms so the runtime sees one consistent value
        if val == 'contains':
            val = 'containing'
        if val == 'matches':
            val = 'matching'
        p[0] = val
    else:
        p[0] = f'{p[1].lower()}_{p[2].lower()}'

def p_assert_url(p):
    '''assertion_stmt : VERIFY URL eq_op STRING'''
    p[0] = VerifyURL(expected=p[4], op=p[3], line=p.lineno(1))

def p_assert_title(p):
    '''assertion_stmt : VERIFY TITLE eq_op STRING'''
    p[0] = VerifyTitle(expected=p[4], op=p[3], line=p.lineno(1))

def p_assert_cookie(p):
    '''assertion_stmt : VERIFY COOKIE STRING eq_op STRING'''
    p[0] = VerifyCookie(name=p[3], expected=p[5], op=p[4],
                         line=p.lineno(1))

def p_assert_downloaded(p):
    '''assertion_stmt : VERIFY DOWNLOADED STRING'''
    p[0] = VerifyDownloaded(filename=p[3], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
#  Waits
# ══════════════════════════════════════════════════════════

def p_wait_seconds(p):
    '''wait_stmt : WAIT NUMBER SECONDS'''
    p[0] = WaitSeconds(duration=p[2], line=p.lineno(1))

def p_wait_for_element(p):
    '''wait_stmt : WAIT FOR element_ref'''
    p[0] = WaitForElement(target=p[3], line=p.lineno(1))

def p_wait_for_state(p):
    '''wait_stmt : WAIT FOR element_ref TO BE visibility'''
    p[0] = WaitForElement(target=p[3], state=p[6], line=p.lineno(1))

def p_wait_timeout(p):
    '''wait_stmt : WAIT UP TO NUMBER SECONDS FOR element_ref'''
    p[0] = WaitForElement(target=p[7], timeout=p[4], line=p.lineno(1))

def p_wait_url(p):
    '''wait_stmt : WAIT UNTIL URL CONTAINS STRING'''
    p[0] = WaitUntilURL(expected=p[5], line=p.lineno(1))

def p_wait_title(p):
    '''wait_stmt : WAIT UNTIL TITLE CONTAINS STRING'''
    p[0] = WaitUntilTitle(expected=p[5], line=p.lineno(1))


# ══════════════════════════════════════════════════════════
#  Variables & expressions
# ══════════════════════════════════════════════════════════

def p_expr_string(p):
    '''expr : STRING'''
    p[0] = StringLiteral(value=p[1])

def p_expr_number(p):
    '''expr : NUMBER'''
    p[0] = NumberLiteral(value=p[1])

def p_expr_var(p):
    '''expr : VARIABLE'''
    p[0] = VarRef(name=p[1])

def p_expr_concat(p):
    '''expr : expr PLUS expr'''
    p[0] = Concat(left=p[1], right=p[3])

def p_expr_paren(p):
    '''expr : LPAREN expr RPAREN'''
    p[0] = p[2]

def p_var_set_expr(p):
    '''var_stmt : SET VARIABLE TO expr'''
    p[0] = SetVar(name=p[2], value=p[4], line=p.lineno(1))

def p_var_set_text(p):
    '''var_stmt : SET VARIABLE TO TEXT OF element_ref'''
    p[0] = SetVar(name=p[2], extract='text', target=p[6],
                   line=p.lineno(1))

def p_var_set_attr(p):
    '''var_stmt : SET VARIABLE TO ATTR STRING OF element_ref'''
    p[0] = SetVar(name=p[2], extract='attr', attr_name=p[5],
                   target=p[7], line=p.lineno(1))

def p_var_set_value(p):
    '''var_stmt : SET VARIABLE TO VALUE OF element_ref'''
    p[0] = SetVar(name=p[2], extract='value', target=p[6],
                   line=p.lineno(1))

def p_var_set_count(p):
    '''var_stmt : SET VARIABLE TO COUNT OF element_ref'''
    p[0] = SetVar(name=p[2], extract='count', target=p[6],
                   line=p.lineno(1))

def p_var_set_url(p):
    '''var_stmt : SET VARIABLE TO URL'''
    p[0] = SetVar(name=p[2], extract='url', line=p.lineno(1))

def p_var_set_title(p):
    '''var_stmt : SET VARIABLE TO TITLE'''
    p[0] = SetVar(name=p[2], extract='title', line=p.lineno(1))


# ══════════════════════════════════════════════════════════
#  Control flow
# ══════════════════════════════════════════════════════════

def p_if(p):
    '''control_stmt : IF condition THEN NEWLINE statement_list END'''
    p[0] = IfStmt(condition=p[2], then_body=p[5], line=p.lineno(1))

def p_if_else(p):
    '''control_stmt : IF condition THEN NEWLINE statement_list ELSE NEWLINE statement_list END'''
    p[0] = IfStmt(condition=p[2], then_body=p[5], else_body=p[8],
                   line=p.lineno(1))

def p_repeat_times(p):
    '''control_stmt : REPEAT NUMBER TIMES NEWLINE statement_list END'''
    p[0] = RepeatTimes(count=int(p[2]), body=p[5], line=p.lineno(1))

def p_repeat_while(p):
    '''control_stmt : REPEAT WHILE condition NEWLINE statement_list END'''
    p[0] = RepeatWhile(condition=p[3], body=p[5], line=p.lineno(1))

def p_for_each(p):
    '''control_stmt : FOR EACH element_ref AS VARIABLE DO NEWLINE statement_list END'''
    p[0] = ForEach(target=p[3], var_name=p[5], body=p[8],
                    line=p.lineno(1))
def p_for_each_no_do(p):
    '''control_stmt : FOR EACH element_ref AS VARIABLE NEWLINE statement_list END'''
    p[0] = ForEach(target=p[3], var_name=p[5], body=p[7],
                    line=p.lineno(1))

def p_try_catch(p):
    '''control_stmt : TRY NEWLINE statement_list ON ERROR NEWLINE statement_list END'''
    p[0] = TryCatch(try_body=p[3], catch_body=p[7], line=p.lineno(1))

def p_call_sub(p):
    '''control_stmt : CALL STRING'''
    p[0] = CallSub(name=p[2], line=p.lineno(1))

def p_define_sub(p):
    '''control_stmt : DEFINE STRING AS NEWLINE statement_list END'''
    p[0] = DefineSub(name=p[2], body=p[5], line=p.lineno(1))


# ── Conditions ───────────────────────────────────────────

def p_cond_state(p):
    '''condition : element_ref IS visibility'''
    p[0] = StateCondition(target=p[1], state=p[3])

def p_cond_compare(p):
    '''condition : expr comparator expr'''
    p[0] = CompareCondition(left=p[1], op=p[2], right=p[3])

# ── Variable-starting conditions (resolve VARIABLE ambiguity) ──
# These use VARIABLE as a raw terminal, avoiding the
# element_ref vs expr reduce/reduce conflict.

def p_cond_var_state(p):
    '''condition : VARIABLE IS visibility'''
    # $element is visible / hidden / enabled ...
    p[0] = StateCondition(
        target=VarElementRef(var_name=p[1]), state=p[3])

def p_cond_var_is_string(p):
    '''condition : VARIABLE IS STRING'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='is',
        right=StringLiteral(value=p[3]))

def p_cond_var_is_number(p):
    '''condition : VARIABLE IS NUMBER'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='is',
        right=NumberLiteral(value=p[3]))

def p_cond_var_is_var(p):
    '''condition : VARIABLE IS VARIABLE'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='is',
        right=VarRef(name=p[3]))

def p_cond_var_equals_string(p):
    '''condition : VARIABLE EQUALS STRING'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='equals',
        right=StringLiteral(value=p[3]))

def p_cond_var_equals_number(p):
    '''condition : VARIABLE EQUALS NUMBER'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='equals',
        right=NumberLiteral(value=p[3]))

def p_cond_var_equals_var(p):
    '''condition : VARIABLE EQUALS VARIABLE'''
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='equals',
        right=VarRef(name=p[3]))

def p_cond_var_gt(p):
    '''condition : VARIABLE GREATER THAN STRING
                 | VARIABLE GREATER THAN NUMBER
                 | VARIABLE GREATER THAN VARIABLE'''
    right = p[4]
    if isinstance(right, str):
        right = StringLiteral(value=right)
    elif isinstance(right, (int, float)):
        right = NumberLiteral(value=right)
    else:
        right = VarRef(name=right)
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='greater_than', right=right)

def p_cond_var_lt(p):
    '''condition : VARIABLE LESS THAN STRING
                 | VARIABLE LESS THAN NUMBER
                 | VARIABLE LESS THAN VARIABLE'''
    right = p[4]
    if isinstance(right, str):
        right = StringLiteral(value=right)
    elif isinstance(right, (int, float)):
        right = NumberLiteral(value=right)
    else:
        right = VarRef(name=right)
    p[0] = CompareCondition(
        left=VarRef(name=p[1]), op='less_than', right=right)

def p_cond_url(p):
    '''condition : URL CONTAINS STRING'''
    p[0] = URLCondition(expected=p[3])

def p_cond_not(p):
    '''condition : NOT condition'''
    p[0] = NotCondition(child=p[2])

def p_cond_and(p):
    '''condition : condition AND condition'''
    p[0] = BoolCondition(left=p[1], op='and', right=p[3])

def p_cond_or(p):
    '''condition : condition OR condition'''
    p[0] = BoolCondition(left=p[1], op='or', right=p[3])

def p_cond_paren(p):
    '''condition : LPAREN condition RPAREN'''
    p[0] = p[2]


# ══════════════════════════════════════════════════════════
#  Misc statements
# ══════════════════════════════════════════════════════════

def p_import(p):
    '''import_stmt : IMPORT STRING'''
    p[0] = Import(filepath=p[2], line=p.lineno(1))

def p_with_data(p):
    '''control_stmt : USING STRING NEWLINE statement_list END'''
    p[0] = WithData(filepath=p[2], body=p[4], line=p.lineno(1))

def p_log(p):
    '''log_stmt : LOG expr'''
    p[0] = Log(message=p[2], line=p.lineno(1))

def p_screenshot(p):
    '''screenshot_stmt : TAKE SCREENSHOT'''
    p[0] = TakeScreenshot(line=p.lineno(1))

def p_screenshot_named(p):
    '''screenshot_stmt : TAKE SCREENSHOT AS STRING'''
    p[0] = TakeScreenshot(filename=p[4], line=p.lineno(1))

def p_accept_alert(p):
    '''alert_stmt : ACCEPT ALERT'''
    p[0] = AcceptAlert(line=p.lineno(1))

def p_dismiss_alert(p):
    '''alert_stmt : DISMISS ALERT'''
    p[0] = DismissAlert(line=p.lineno(1))

def p_verify_alert(p):
    '''alert_stmt : VERIFY ALERT HAS TEXT STRING'''
    p[0] = VerifyAlert(expected=p[5], line=p.lineno(1))

def p_switch_frame(p):
    '''frame_stmt : SWITCH TO FRAME element_ref'''
    p[0] = SwitchFrame(target=p[4], line=p.lineno(1))

def p_switch_frame_name(p):
    '''frame_stmt : SWITCH TO FRAME STRING'''
    p[0] = SwitchFrame(target=p[4], line=p.lineno(1))

def p_switch_default_frame(p):
    '''frame_stmt : SWITCH TO DEFAULT FRAME'''
    p[0] = SwitchFrame(target=None, line=p.lineno(1))

def p_switch_window(p):
    '''window_stmt : SWITCH TO WINDOW STRING'''
    p[0] = SwitchWindow(name=p[4], line=p.lineno(1))

def p_open_window(p):
    '''window_stmt : OPEN NEW WINDOW'''
    p[0] = OpenWindow(line=p.lineno(1))

def p_close_window(p):
    '''window_stmt : CLOSE WINDOW'''
    p[0] = CloseWindow(line=p.lineno(1))

def p_save_source(p):
    '''extract_stmt : SAVE SOURCE AS STRING'''
    p[0] = SaveSource(filename=p[4], line=p.lineno(1))

def p_save_cookies(p):
    '''extract_stmt : SAVE COOKIES AS STRING'''
    p[0] = SaveCookies(filename=p[4], line=p.lineno(1))


# ── Error handling ───────────────────────────────────────
def p_error(p):
    if p:
        raise SyntaxError(
            f"Unexpected '{p.value}' ({p.type}) at line {p.lineno}"
        )
    raise SyntaxError("Unexpected end of input")


parser = yacc.yacc()