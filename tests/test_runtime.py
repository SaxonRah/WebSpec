"""
Tests for the WebSpec runtime engine.
Uses a fully mocked Selenium driver to verify action dispatch.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock

from webspec_ast import *
from webspec_runtime import WebSpecRuntime


# ── Fixture: runtime with mocked driver + resolver ───────

MOCK_HTML = """
<html><body>
  <button id="btn1">OK</button>
  <input id="inp1" name="email" placeholder="Email" value="old@test.com"/>
  <h1>Dashboard</h1>
  <div class="item">A</div>
  <div class="item">B</div>
</body></html>
"""


@pytest.fixture
def runtime():
    driver = MagicMock()
    type(driver).page_source = PropertyMock(return_value=MOCK_HTML)
    type(driver).current_url = PropertyMock(
        return_value='https://example.com/dashboard')
    type(driver).title = PropertyMock(return_value='Dashboard')
    driver.window_handles = ['handle1']

    rt = WebSpecRuntime(driver=driver, timeout=2)

    # Patch the resolver so it returns controllable mocks
    mock_element = MagicMock()
    mock_element.text = 'OK'
    mock_element.is_displayed.return_value = True
    mock_element.is_enabled.return_value = True
    mock_element.is_selected.return_value = False
    mock_element.get_attribute.return_value = 'old@test.com'
    mock_element.value_of_css_property.return_value = 'red'

    rt.resolver = MagicMock()
    rt.resolver.resolve.return_value = mock_element
    rt.resolver.resolve_all.return_value = [mock_element, MagicMock()]

    rt._mock_element = mock_element  # expose for assertions
    return rt


# ═══════════════════════════════════════════════════════════
#  Navigation
# ═══════════════════════════════════════════════════════════

class TestRuntimeNavigation:
    def test_navigate(self, runtime):
        runtime._exec(Navigate(url='https://example.com'))
        runtime.driver.get.assert_called_once_with('https://example.com')

    def test_navigate_with_variable(self, runtime):
        runtime.variables['host'] = 'example.com'
        runtime._exec(Navigate(url='https://${host}/login'))
        runtime.driver.get.assert_called_once_with(
            'https://example.com/login')

    def test_go_back(self, runtime):
        runtime._exec(GoBack())
        runtime.driver.back.assert_called_once()

    def test_go_forward(self, runtime):
        runtime._exec(GoForward())
        runtime.driver.forward.assert_called_once()

    def test_refresh(self, runtime):
        runtime._exec(Refresh())
        runtime.driver.refresh.assert_called_once()


# ═══════════════════════════════════════════════════════════
#  Actions
# ═══════════════════════════════════════════════════════════

class TestRuntimeActions:
    def test_click(self, runtime):
        ref = ElementRef(elem_type='button')
        runtime._exec(Click(target=ref, click_type='single'))
        runtime._mock_element.click.assert_called_once()

    def test_type_text(self, runtime):
        ref = ElementRef(elem_type='input')
        runtime._exec(TypeText(
            text=StringLiteral(value='hello@test.com'), target=ref))
        runtime._mock_element.clear.assert_called_once()
        runtime._mock_element.send_keys.assert_called_once_with(
            'hello@test.com')

    def test_append_text(self, runtime):
        ref = ElementRef(elem_type='input')
        runtime._exec(AppendText(
            text=StringLiteral(value=' extra'), target=ref))
        runtime._mock_element.send_keys.assert_called_once_with(' extra')
        runtime._mock_element.clear.assert_not_called()

    def test_clear(self, runtime):
        ref = ElementRef(elem_type='input')
        runtime._exec(Clear(target=ref))
        runtime._mock_element.clear.assert_called_once()

    def test_check_when_unchecked(self, runtime):
        runtime._mock_element.is_selected.return_value = False
        ref = ElementRef(elem_type='checkbox')
        runtime._exec(Check(target=ref, state=True))
        runtime._mock_element.click.assert_called_once()

    def test_check_when_already_checked(self, runtime):
        runtime._mock_element.is_selected.return_value = True
        ref = ElementRef(elem_type='checkbox')
        runtime._exec(Check(target=ref, state=True))
        runtime._mock_element.click.assert_not_called()

    def test_uncheck_when_checked(self, runtime):
        runtime._mock_element.is_selected.return_value = True
        ref = ElementRef(elem_type='checkbox')
        runtime._exec(Check(target=ref, state=False))
        runtime._mock_element.click.assert_called_once()

    def test_toggle(self, runtime):
        ref = ElementRef(elem_type='checkbox')
        runtime._exec(Toggle(target=ref))
        runtime._mock_element.click.assert_called_once()

    def test_submit(self, runtime):
        ref = ElementRef(elem_type='form')
        runtime._exec(Submit(target=ref))
        runtime._mock_element.submit.assert_called_once()

    def test_execute_js(self, runtime):
        runtime._exec(ExecuteJS(script='window.scrollTo(0,0)'))
        runtime.driver.execute_script.assert_called_once_with(
            'window.scrollTo(0,0)')

    def test_scroll_down(self, runtime):
        runtime._exec(ScrollBy(direction='down', pixels=500))
        runtime.driver.execute_script.assert_called_once_with(
            'window.scrollBy(0, 500)')

    def test_scroll_up(self, runtime):
        runtime._exec(ScrollBy(direction='up', pixels=200))
        runtime.driver.execute_script.assert_called_once_with(
            'window.scrollBy(0, -200)')

    def test_upload(self, runtime):
        ref = ElementRef(elem_type='input')
        runtime._exec(Upload(filepath='/tmp/test.pdf', target=ref))
        runtime._mock_element.send_keys.assert_called_once()
        sent_path = runtime._mock_element.send_keys.call_args[0][0]
        assert 'test.pdf' in sent_path


# ═══════════════════════════════════════════════════════════
#  Assertions
# ═══════════════════════════════════════════════════════════

class TestRuntimeAssertions:
    def test_verify_visible_pass(self, runtime):
        ref = ElementRef(elem_type='button')
        runtime._exec(VerifyState(target=ref, state='visible'))
        # No exception = pass

    def test_verify_visible_fail(self, runtime):
        runtime._mock_element.is_displayed.return_value = False
        ref = ElementRef(elem_type='button')
        with pytest.raises(AssertionError, match="not visible"):
            runtime._exec(VerifyState(target=ref, state='visible'))

    def test_verify_enabled_pass(self, runtime):
        ref = ElementRef(elem_type='button')
        runtime._exec(VerifyState(target=ref, state='enabled'))

    def test_verify_disabled(self, runtime):
        runtime._mock_element.is_enabled.return_value = False
        ref = ElementRef(elem_type='button')
        runtime._exec(VerifyState(target=ref, state='disabled'))

    def test_verify_text_exact(self, runtime):
        runtime._mock_element.text = 'OK'
        ref = ElementRef(elem_type='button')
        runtime._exec(VerifyText(
            target=ref, expected='OK', mode='has'))

    def test_verify_text_exact_fail(self, runtime):
        runtime._mock_element.text = 'Cancel'
        ref = ElementRef(elem_type='button')
        with pytest.raises(AssertionError):
            runtime._exec(VerifyText(
                target=ref, expected='OK', mode='has'))

    def test_verify_contains(self, runtime):
        runtime._mock_element.text = 'Hello World'
        ref = ElementRef(elem_type='element')
        runtime._exec(VerifyText(
            target=ref, expected='World', mode='contains'))

    def test_verify_matches_regex(self, runtime):
        runtime._mock_element.text = 'Order #12345'
        ref = ElementRef(elem_type='element')
        runtime._exec(VerifyText(
            target=ref, expected=r'#\d+', mode='matches'))

    def test_verify_attr(self, runtime):
        runtime._mock_element.get_attribute.return_value = 'email'
        ref = ElementRef(elem_type='input')
        runtime._exec(VerifyAttr(
            target=ref, attr_name='type', expected='email', op='is'))

    def test_verify_style(self, runtime):
        ref = ElementRef(elem_type='element')
        runtime._exec(VerifyStyle(
            target=ref, prop='color', expected='red', op='is'))

    def test_verify_count(self, runtime):
        ref = ElementRef(elem_type='element')
        runtime._exec(VerifyCount(target=ref, op='is', expected=2))

    def test_verify_count_gt(self, runtime):
        ref = ElementRef(elem_type='element')
        runtime._exec(VerifyCount(
            target=ref, op='greater_than', expected=0))

    def test_verify_count_fail(self, runtime):
        ref = ElementRef(elem_type='element')
        with pytest.raises(AssertionError):
            runtime._exec(VerifyCount(target=ref, op='is', expected=99))

    def test_verify_url(self, runtime):
        runtime._exec(VerifyURL(
            expected='https://example.com/dashboard', op='is'))

    def test_verify_url_contains(self, runtime):
        runtime._exec(VerifyURL(expected='/dashboard', op='containing'))

    def test_verify_title(self, runtime):
        runtime._exec(VerifyTitle(expected='Dashboard', op='is'))

    def test_verify_cookie(self, runtime):
        runtime.driver.get_cookie.return_value = {'value': 'abc123'}
        runtime._exec(VerifyCookie(
            name='session', expected='abc123', op='is'))


# ═══════════════════════════════════════════════════════════
#  Variables
# ═══════════════════════════════════════════════════════════

class TestRuntimeVariables:
    def test_set_string(self, runtime):
        runtime._exec(SetVar(
            name='greeting', value=StringLiteral(value='hello')))
        assert runtime.variables['greeting'] == 'hello'

    def test_set_number(self, runtime):
        runtime._exec(SetVar(
            name='count', value=NumberLiteral(value=42)))
        assert runtime.variables['count'] == 42

    def test_set_text_of(self, runtime):
        runtime._mock_element.text = 'Dashboard'
        ref = ElementRef(elem_type='heading')
        runtime._exec(SetVar(
            name='title', extract='text', target=ref))
        assert runtime.variables['title'] == 'Dashboard'

    def test_set_attr_of(self, runtime):
        runtime._mock_element.get_attribute.return_value = '/home'
        ref = ElementRef(elem_type='link')
        runtime._exec(SetVar(
            name='href', extract='attr', attr_name='href', target=ref))
        assert runtime.variables['href'] == '/home'

    def test_set_count_of(self, runtime):
        ref = ElementRef(elem_type='element')
        runtime._exec(SetVar(name='n', extract='count', target=ref))
        assert runtime.variables['n'] == 2

    def test_set_url(self, runtime):
        runtime._exec(SetVar(name='page', extract='url'))
        assert runtime.variables['page'] == 'https://example.com/dashboard'

    def test_set_title(self, runtime):
        runtime._exec(SetVar(name='t', extract='title'))
        assert runtime.variables['t'] == 'Dashboard'

    def test_eval_concat(self, runtime):
        runtime.variables['name'] = 'World'
        result = runtime._eval_expr(Concat(
            left=StringLiteral(value='Hello '),
            right=VarRef(name='name'),
        ))
        assert result == 'Hello World'

    def test_eval_undefined_var_raises(self, runtime):
        with pytest.raises(RuntimeError, match="not set"):
            runtime._eval_expr(VarRef(name='undefined_var'))


# ═══════════════════════════════════════════════════════════
#  Control flow
# ═══════════════════════════════════════════════════════════

class TestRuntimeControlFlow:
    def test_if_true(self, runtime):
        cond = StateCondition(
            target=ElementRef(elem_type='button'), state='visible')
        log_node = Log(message=StringLiteral(value='yes'))
        runtime._exec(IfStmt(condition=cond, then_body=[log_node]))
        # If the condition was true, step_count should have increased

    def test_if_false_runs_else(self, runtime):
        runtime._mock_element.is_displayed.return_value = False
        cond = StateCondition(
            target=ElementRef(elem_type='button'), state='visible')
        then_log = Log(message=StringLiteral(value='yes'))
        else_log = Log(message=StringLiteral(value='no'))
        runtime._exec(IfStmt(
            condition=cond, then_body=[then_log],
            else_body=[else_log]))

    def test_repeat_times(self, runtime):
        ref = ElementRef(elem_type='button')
        click_node = Click(target=ref, click_type='single')
        runtime._exec(RepeatTimes(count=3, body=[click_node]))
        assert runtime._mock_element.click.call_count == 3

    def test_repeat_while_terminates(self, runtime):
        call_count = 0

        def is_displayed_side_effect():
            nonlocal call_count
            call_count += 1
            return call_count <= 2

        runtime._mock_element.is_displayed.side_effect = \
            is_displayed_side_effect

        cond = StateCondition(
            target=ElementRef(elem_type='button'), state='visible')
        log_node = Log(message=StringLiteral(value='loop'))
        runtime._exec(RepeatWhile(condition=cond, body=[log_node]))
        # Should loop exactly 2 times
        assert call_count == 3  # 2 true + 1 false to exit

    def test_for_each(self, runtime):
        mock1, mock2 = MagicMock(), MagicMock()
        mock1.text = 'A'
        mock2.text = 'B'
        runtime.resolver.resolve_all.return_value = [mock1, mock2]

        ref = ElementRef(elem_type='element')
        set_node = SetVar(name='txt', extract='text',
                          target=ElementRef(elem_type='element'))
        runtime._exec(ForEach(
            target=ref, var_name='item', body=[set_node]))
        # After loop, $item should be set to last element
        assert runtime.variables['item'] is mock2

    def test_try_catch(self, runtime):
        # Make click raise an error
        runtime._mock_element.click.side_effect = Exception("boom")
        ref = ElementRef(elem_type='button')
        runtime._exec(TryCatch(
            try_body=[Click(target=ref, click_type='single')],
            catch_body=[Log(message=StringLiteral(value='caught'))],
        ))
        assert runtime.variables['_error'] == 'boom'

    def test_define_and_call(self, runtime):
        # Define
        runtime._exec(DefineSub(
            name='greet',
            body=[Log(message=StringLiteral(value='hello'))],
        ))
        assert 'greet' in runtime.subroutines

        # Call
        runtime._exec(CallSub(name='greet'))

    def test_call_undefined_raises(self, runtime):
        with pytest.raises(RuntimeError, match="not defined"):
            runtime._exec(CallSub(name='nonexistent'))

    def test_condition_not(self, runtime):
        cond = NotCondition(child=StateCondition(
            target=ElementRef(elem_type='button'), state='hidden'))
        # Button is visible → not hidden → True
        assert runtime._eval_condition(cond) is True

    def test_condition_and(self, runtime):
        left = StateCondition(
            target=ElementRef(elem_type='button'), state='visible')
        right = StateCondition(
            target=ElementRef(elem_type='button'), state='enabled')
        cond = BoolCondition(left=left, op='and', right=right)
        assert runtime._eval_condition(cond) is True

    def test_condition_or(self, runtime):
        runtime._mock_element.is_displayed.return_value = False
        left = StateCondition(
            target=ElementRef(elem_type='button'), state='visible')
        right = StateCondition(
            target=ElementRef(elem_type='button'), state='enabled')
        cond = BoolCondition(left=left, op='or', right=right)
        assert runtime._eval_condition(cond) is True

    def test_condition_url(self, runtime):
        cond = URLCondition(expected='/dashboard')
        assert runtime._eval_condition(cond) is True

    def test_condition_compare(self, runtime):
        runtime.variables['count'] = '5'
        cond = CompareCondition(
            left=VarRef(name='count'), op='is',
            right=StringLiteral(value='5'))
        assert runtime._eval_condition(cond) is True


# ═══════════════════════════════════════════════════════════
#  Misc
# ═══════════════════════════════════════════════════════════

class TestRuntimeMisc:
    def test_screenshot(self, runtime):
        runtime._exec(TakeScreenshot(filename='test.png'))
        runtime.driver.save_screenshot.assert_called_once()

    def test_accept_alert(self, runtime):
        runtime._exec(AcceptAlert())
        runtime.driver.switch_to.alert.accept.assert_called_once()

    def test_dismiss_alert(self, runtime):
        runtime._exec(DismissAlert())
        runtime.driver.switch_to.alert.dismiss.assert_called_once()

    def test_switch_default_frame(self, runtime):
        runtime._exec(SwitchFrame(target=None))
        runtime.driver.switch_to.default_content.assert_called_once()

    def test_switch_frame_string(self, runtime):
        runtime._exec(SwitchFrame(target='my-frame'))
        runtime.driver.switch_to.frame.assert_called_once_with('my-frame')

    def test_open_window(self, runtime):
        runtime._exec(OpenWindow())
        runtime.driver.execute_script.assert_called_once_with(
            "window.open('')")

    def test_close_window(self, runtime):
        runtime._exec(CloseWindow())
        runtime.driver.close.assert_called_once()

    def test_wait_seconds(self, runtime):
        import time
        start = time.time()
        runtime._exec(WaitSeconds(duration=0.1))
        elapsed = time.time() - start
        assert elapsed >= 0.1


# ═══════════════════════════════════════════════════════════
#  Full program execution
# ═══════════════════════════════════════════════════════════

class TestRuntimeFullProgram:
    def test_run_program(self, runtime):
        prog = Program(statements=[
            Navigate(url='https://example.com'),
            Click(target=ElementRef(elem_type='button'),
                  click_type='single'),
            Log(message=StringLiteral(value='done')),
        ])
        runtime.run(prog)
        assert runtime.step_count == 3
        assert len(runtime.errors) == 0

    def test_run_program_with_error(self, runtime):
        runtime._mock_element.is_displayed.return_value = False
        prog = Program(statements=[
            VerifyState(target=ElementRef(elem_type='button'),
                        state='visible'),
        ])
        with pytest.raises(AssertionError):
            runtime.run(prog)
        assert len(runtime.errors) == 1