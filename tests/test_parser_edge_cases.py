import pytest

from webspec_lexer import lexer
from webspec_parser import parser
from webspec_ast import (
    Program,
    IfStmt,
    RepeatTimes,
    ForEach,
    TryCatch,
    WithData,
    DefineSub,
    StateCondition,
    CompareCondition,
    VarElementRef,
    VarRef,
    WaitUntilURL,
    WaitUntilTitle,
    Select,
    Concat,
)


def parse_script(text: str):
    lexer.lineno = 1
    return parser.parse(text, lexer=lexer)


class TestBlankLinesInBlocks:
    def test_if_allows_blank_line_after_then(self):
        ast = parse_script(
            """
if url contains "example" then

log "ok"
end
"""
        )
        assert isinstance(ast, Program)
        stmt = ast.statements[0]
        assert isinstance(stmt, IfStmt)
        assert len(stmt.then_body) == 1

    def test_if_else_allows_blank_lines(self):
        ast = parse_script(
            """
if url contains "example" then

log "then"

else

log "else"

end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, IfStmt)
        assert len(stmt.then_body) == 1
        assert len(stmt.else_body) == 1

    def test_repeat_allows_blank_line(self):
        ast = parse_script(
            """
repeat 2 times

log "x"
end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, RepeatTimes)
        assert len(stmt.body) == 1

    def test_for_each_allows_blank_line_after_do(self):
        ast = parse_script(
            """
for each the row as $row do

log $row
end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, ForEach)
        assert len(stmt.body) == 1

    def test_try_catch_allows_blank_lines(self):
        ast = parse_script(
            """
try

log "a"

on error

log "b"

end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, TryCatch)
        assert len(stmt.try_body) == 1
        assert len(stmt.catch_body) == 1

    def test_using_allows_blank_line(self):
        ast = parse_script(
            """
using "data.csv"

log $name
end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, WithData)
        assert len(stmt.body) == 1

    def test_define_allows_blank_line(self):
        ast = parse_script(
            """
define "helper" as

log "inside"
end
"""
        )
        stmt = ast.statements[0]
        assert isinstance(stmt, DefineSub)
        assert len(stmt.body) == 1


class TestReservedWordTextSelectors:
    def test_quoted_reserved_word_text_selector_parses(self):
        ast = parse_script('click the button "end"')
        stmt = ast.statements[0]
        assert stmt.target.elem_type == "button"
        assert stmt.target.selectors[0].kind == "text"
        assert stmt.target.selectors[0].value == "end"

    def test_with_text_reserved_word_quoted_parses(self):
        ast = parse_script('click the button with text "title"')
        stmt = ast.statements[0]
        assert stmt.target.selectors[0].kind == "with_text"
        assert stmt.target.selectors[0].value == "title"

    def test_reserved_word_text_via_variable_parses(self):
        ast = parse_script('click the button with text $label')
        stmt = ast.statements[0]
        assert stmt.target.selectors[0].kind == "with_text"
        assert stmt.target.selectors[0].value == "${label}"

    def test_unquoted_reserved_word_text_selector_rejected(self):
        with pytest.raises(SyntaxError):
            parse_script("click the button end")


class TestVariableVsElementConditionsHybrid:
    def test_bare_variable_state_condition_still_parses(self):
        ast = parse_script('if $dialog is visible then log "x" end')
        cond = ast.statements[0].condition
        assert isinstance(cond, StateCondition)
        assert isinstance(cond.target, VarElementRef)
        assert cond.target.var_name == "dialog"
        assert cond.state == "visible"

    def test_explicit_element_variable_state_condition_parses(self):
        ast = parse_script('if element $dialog is visible then log "x" end')
        cond = ast.statements[0].condition
        assert isinstance(cond, StateCondition)
        assert isinstance(cond.target, VarElementRef)
        assert cond.target.var_name == "dialog"
        assert cond.state == "visible"

    def test_bare_variable_value_comparison_still_parses(self):
        ast = parse_script('if $status is "visible" then log "x" end')
        cond = ast.statements[0].condition
        assert isinstance(cond, CompareCondition)
        assert isinstance(cond.left, VarRef)
        assert cond.left.name == "status"
        assert cond.op == "is"

    def test_bare_variable_numeric_comparison_still_parses(self):
        ast = parse_script('if $count greater than 3 then log "x" end')
        cond = ast.statements[0].condition
        assert isinstance(cond, CompareCondition)
        assert isinstance(cond.left, VarRef)
        assert cond.left.name == "count"
        assert cond.op == "greater_than"


class TestVariableBasedWaitsAndSelects:
    def test_wait_until_url_contains_variable(self):
        ast = parse_script("wait until url contains $expected_url")
        stmt = ast.statements[0]
        assert isinstance(stmt, WaitUntilURL)
        assert isinstance(stmt.expected, VarRef)
        assert stmt.expected.name == "expected_url"

    def test_wait_until_title_contains_variable(self):
        ast = parse_script("wait until title contains $expected_title")
        stmt = ast.statements[0]
        assert isinstance(stmt, WaitUntilTitle)
        assert isinstance(stmt.expected, VarRef)
        assert stmt.expected.name == "expected_title"

    def test_wait_until_url_contains_concat_expr(self):
        ast = parse_script('wait until url contains ("https://x/" + $slug)')
        stmt = ast.statements[0]
        assert isinstance(stmt, WaitUntilURL)
        assert isinstance(stmt.expected, Concat)

    def test_select_variable_from_dropdown(self):
        ast = parse_script("select $choice from the dropdown")
        stmt = ast.statements[0]
        assert isinstance(stmt, Select)
        assert isinstance(stmt.option, VarRef)
        assert stmt.option.name == "choice"

    def test_select_concat_expr_from_dropdown(self):
        ast = parse_script('select ("Plan " + $tier) from the dropdown')
        stmt = ast.statements[0]
        assert isinstance(stmt, Select)
        assert isinstance(stmt.option, Concat)


class TestRegressionSanity:
    def test_plain_text_selector_still_works(self):
        ast = parse_script('click the button "save"')
        stmt = ast.statements[0]
        assert stmt.target.selectors[0].value == "save"

    def test_verify_url_with_variable_text_value_still_works(self):
        ast = parse_script("verify url is $expected")
        stmt = ast.statements[0]
        assert stmt.expected == "${expected}"

    def test_verify_heading_contains_variable_still_works(self):
        ast = parse_script("verify the heading contains $title")
        stmt = ast.statements[0]
        assert stmt.expected == "${title}"
