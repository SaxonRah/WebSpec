"""
WebSpec DSL - Runtime Engine
Walks the AST and executes each node against a live Selenium session.
"""

import re
import time
import json
import os
import logging
from pathlib import Path
from typing import Any

from selenium import webdriver
# from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select as SeleniumSelect
from selenium.webdriver.support import expected_conditions as EC

from webspec_ast import *
from webspec_resolver import SmartResolver

logger = logging.getLogger('webspec')

# ── Key name mapping ─────────────────────────────────────
KEY_MAP = {
    'enter': Keys.ENTER, 'return': Keys.RETURN,
    'tab': Keys.TAB, 'escape': Keys.ESCAPE, 'esc': Keys.ESCAPE,
    'backspace': Keys.BACKSPACE, 'delete': Keys.DELETE,
    'space': Keys.SPACE, 'up': Keys.UP, 'down': Keys.DOWN,
    'left': Keys.LEFT, 'right': Keys.RIGHT,
    'home': Keys.HOME, 'end': Keys.END,
    'page_up': Keys.PAGE_UP, 'page_down': Keys.PAGE_DOWN,
    'f1': Keys.F1, 'f2': Keys.F2, 'f3': Keys.F3, 'f4': Keys.F4,
    'f5': Keys.F5, 'f12': Keys.F12,
}

MODIFIER_MAP = {
    'ctrl': Keys.CONTROL, 'control': Keys.CONTROL,
    'shift': Keys.SHIFT, 'alt': Keys.ALT, 'meta': Keys.META,
    'command': Keys.COMMAND,
}


class WebSpecRuntime:
    """Execute a parsed WebSpec AST against a browser."""

    def __init__(self, driver=None, timeout=10, screenshot_dir='screenshots',
                 retry_timeout=5, retry_interval=0.3, row_failure_mode="collect"):
        self.driver = driver or webdriver.Chrome()
        self.timeout = timeout
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True)

        self.resolver = SmartResolver(
            self.driver,
            retry_timeout=retry_timeout,
            retry_interval=retry_interval
        )
        self.variables: dict[str, Any] = {}
        self.subroutines: dict[str, list] = {}
        self.step_count = 0
        self.errors: list[str] = []
        self.step_timings: list[dict] = []  # for reporting
        self.imports_loaded: set[str] = set()  # for import system

        self.script_stack: list[Path] = []
        self.row_failure_mode = row_failure_mode  # "fail_fast" or "collect"


    # ══════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════

    def run(self, program: Program):
        """Execute an entire program."""
        logger.info("WebSpec run started")
        try:
            self.exec_block(program.statements)
        except AssertionError:
            # Already recorded by _assert - just re-raise, don't double-log
            raise
        except Exception as e:
            self.errors.append(f"FATAL: {e}")
            logger.error(f"Run failed: {e}")
            raise
        finally:
            logger.info(
                f"Run complete: {self.step_count} steps, "
                f"{len(self.errors)} errors"
            )

    def run_script(self, script_text: str, source_path: str | None = None):
        """Parse and run a WebSpec script string."""
        from webspec_parser import parser as ply_parser
        from webspec_lexer import lexer
        lexer.lineno = 1
        if source_path is not None:
            self.script_stack.append(Path(source_path).resolve().parent)
        try:
            ast = ply_parser.parse(script_text, lexer=lexer)
            self.run(ast)
        finally:
            if source_path is not None:
                self.script_stack.pop()

    def _interpolate(self, value):
        """Replace ${varname} in assertion expected values."""
        import re
        if '${' not in value:
            return value

        def _replace(match):
            name = match.group(1)
            resolved = self.variables.get(name)
            if resolved is None:
                raise RuntimeError(f"Variable ${name} not set")
            if hasattr(resolved, 'text'):
                return resolved.text
            return str(resolved)

        return re.sub(r'\$\{(\w+)}', _replace, value)

    @staticmethod
    def _coerce_to_string(value):
        if value is None:
            return ""
        return str(value)

    # ══════════════════════════════════════════════════════
    #  Statement dispatch
    # ══════════════════════════════════════════════════════

    def exec_block(self, statements):
        for stmt in statements:
            if stmt is None:
                continue
            self.step_count += 1
            self._exec(stmt)

    def _exec(self, node):
        import time as _time
        method_name = f'_exec_{type(node).__name__}'
        method = getattr(self, method_name, None)
        if method is None:
            raise RuntimeError(f"No handler for {type(node).__name__}")

        step_info = {
            'step': self.step_count,
            'type': type(node).__name__,
            'line': getattr(node, 'line', 0),
            'status': 'pass',
            'duration': 0,
            'error': None,
        }

        start = _time.time()
        try:
            logger.debug(
                f"[step {self.step_count}] {type(node).__name__}")
            method(node)
        except Exception as e:
            step_info['status'] = 'fail'
            step_info['error'] = str(e)
            raise
        finally:
            step_info['duration'] = round(_time.time() - start, 3)
            self.step_timings.append(step_info)

    # ── Resolve helpers ──────────────────────────────────
    def _resolve(self, ref):
        return self.resolver.resolve(ref, self.variables)

    def _resolve_all(self, ref):
        return self.resolver.resolve_all(ref, self.variables)

    def _eval_expr(self, expr):
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, NumberLiteral):
        # This stores raw numbers in variables
            return expr.value
        # This stores numbers as strings in variables
        #     return str(expr.value)
        if isinstance(expr, VarRef):
            v = self.variables.get(expr.name)
            if v is None:
                raise RuntimeError(f"Variable ${expr.name} not set")
            return v
        if isinstance(expr, Concat):
        # This stores raw numbers in variables
        #     return self._eval_expr(expr.left) + self._eval_expr(expr.right)
            left = self._eval_expr(expr.left)
            right = self._eval_expr(expr.right)
            return self._coerce_to_string(left) + self._coerce_to_string(right)
        # This stores numbers as strings in variables
        #     return str(self._eval_expr(expr.left)) + str(self._eval_expr(expr.right))
        raise RuntimeError(f"Cannot evaluate expression: {expr}")

    def _current_script_dir(self) -> Path:
        if self.script_stack:
            return self.script_stack[-1]
        return Path.cwd()

    def _resolve_runtime_path(self, raw_path: str, *, allow_test_fallbacks: bool = True) -> Path:
        path = Path(raw_path)

        if path.is_absolute():
            return path

        candidates = [
            self._current_script_dir() / path,
            Path.cwd() / path,
        ]

        if allow_test_fallbacks:
            candidates.extend([
                Path('tests/fixtures') / path,
                Path('tests') / path,
            ])

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        # Return the most natural failure path for error messages
        return (self._current_script_dir() / path).resolve()

    # ══════════════════════════════════════════════════════
    #  Navigation
    # ══════════════════════════════════════════════════════

    def _exec_Navigate(self, n: Navigate):
        if isinstance(n.url, str):
            url = n.url
            for var, val in self.variables.items():
                url = url.replace(f'${{{var}}}', str(val))
                url = url.replace(f'${var}', str(val))
        else:
            # url is an Expr node from the parser
            url = self._eval_expr(n.url)
        self.driver.get(url)

    def _exec_GoBack(self, _):
        self.driver.back()

    def _exec_GoForward(self, _):
        self.driver.forward()

    def _exec_Refresh(self, _):
        self.driver.refresh()

    def _exec_SwitchTab(self, n: SwitchTab):
        handles = self.driver.window_handles
        if n.index < len(handles):
            self.driver.switch_to.window(handles[n.index])

    # ══════════════════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════════════════

    def _exec_Click(self, n: Click):
        el = self._resolve(n.target)
        actions = ActionChains(self.driver)
        if n.click_type == 'double':
            actions.double_click(el).perform()
        elif n.click_type == 'right':
            actions.context_click(el).perform()
        else:
            el.click()

    def _exec_TypeText(self, n: TypeText):
        el = self._resolve(n.target)
        text = self._eval_text_value(n.text)
        el.clear()
        el.send_keys(text)

    def _exec_AppendText(self, n: AppendText):
        el = self._resolve(n.target)
        el.send_keys(self._eval_text_value(n.text))

    def _exec_Clear(self, n: Clear):
        self._resolve(n.target).clear()

    # def _exec_Select(self, n: Select):
    #     el = self._resolve(n.target)
    #     sel = SeleniumSelect(el)
    #
    #     # Try 1: exact visible text
    #     try:
    #         sel.select_by_visible_text(n.option)
    #         return
    #     except Exception:
    #         pass
    #
    #     # Try 2: exact value attribute
    #     try:
    #         sel.select_by_value(n.option)
    #         return
    #     except Exception:
    #         pass
    #
    #     # Try 3: case-insensitive partial match on option text
    #     target = n.option.lower().strip()
    #     for opt in sel.options:
    #         if opt.text.lower().strip() == target:
    #             sel.select_by_visible_text(opt.text)
    #             return
    #
    #     # Try 4: substring match
    #     for opt in sel.options:
    #         if target in opt.text.lower().strip():
    #             sel.select_by_visible_text(opt.text)
    #             return
    #
    #     raise RuntimeError(
    #         f"Could not select '{n.option}' - available options: "
    #         f"{[o.text for o in sel.options]}"
    #     )

    def _exec_Select(self, n: Select):
        el = self._resolve(n.target)
        sel = SeleniumSelect(el)

        option = self._eval_runtime_value(n.option)
        if option is None:
            option = ""
        option = str(option)

        # Try 1: exact visible text
        try:
            sel.select_by_visible_text(option)
            return
        except Exception:
            pass

        # Try 2: exact value attribute
        try:
            sel.select_by_value(option)
            return
        except Exception:
            pass

        # Try 3: case-insensitive partial match on option text
        target = option.lower().strip()
        for opt in sel.options:
            if target in opt.text.lower().strip():
                opt.click()
                return

        raise RuntimeError(
            f"Could not select '{n.option}' - available options: "
            f"{[o.text for o in sel.options]}"
        )


    def _exec_Check(self, n: Check):
        el = self._resolve(n.target)
        is_checked = el.is_selected()
        if n.state and not is_checked:
            el.click()
        elif not n.state and is_checked:
            el.click()

    def _exec_Toggle(self, n: Toggle):
        self._resolve(n.target).click()

    def _exec_Hover(self, n: Hover):
        el = self._resolve(n.target)
        ActionChains(self.driver).move_to_element(el).perform()

    def _exec_Focus(self, n: Focus):
        el = self._resolve(n.target)
        self.driver.execute_script("arguments[0].focus()", el)

    def _exec_ScrollTo(self, n: ScrollTo):
        el = self._resolve(n.target)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'smooth',block:'center'})",
            el
        )

    def _exec_ScrollBy(self, n: ScrollBy):
        dy = n.pixels if n.direction == 'down' else -n.pixels
        self.driver.execute_script(f"window.scrollBy(0, {dy})")

    def _exec_DragTo(self, n: DragTo):
        src = self._resolve(n.source)
        dst = self._resolve(n.target)
        ActionChains(self.driver).drag_and_drop(src, dst).perform()

    def _exec_PressKey(self, n: PressKey):
        # This commit makes the AST stable for v1
        # also fixes the runtime/transpiler mismatch without widening the parser yet.
        key = KEY_MAP.get(n.key.lower(), n.key)

        if n.modifier:
            mods = [m.strip().lower() for m in n.modifier.split('+') if m.strip()]
            chain = ActionChains(self.driver)
            resolved_mods = [MODIFIER_MAP.get(m, m) for m in mods]

            for mod in resolved_mods:
                chain.key_down(mod)

            chain.send_keys(key)

            for mod in reversed(resolved_mods):
                chain.key_up(mod)

            chain.perform()
        else:
            ActionChains(self.driver).send_keys(key).perform()

    def _exec_Upload(self, n: Upload):
        el = self._resolve(n.target)
        el.send_keys(os.path.abspath(n.filepath))

    def _exec_Submit(self, n: Submit):
        self._resolve(n.target).submit()

    def _exec_ExecuteJS(self, n: ExecuteJS):
        self.driver.execute_script(n.script)

    # ══════════════════════════════════════════════════════
    #  Assertions
    # ══════════════════════════════════════════════════════

    def _assert(self, condition: bool, message: str):
        if not condition:
            self.errors.append(message)
            raise AssertionError(message)

    def _exec_VerifyState(self, n: VerifyState):
        el = self._resolve(n.target)
        checks = {
            'visible':  el.is_displayed,
            'hidden':   lambda: not el.is_displayed(),
            'enabled':  el.is_enabled,
            'disabled': lambda: not el.is_enabled(),
            'selected': el.is_selected,
            'checked':  el.is_selected,
            'focused':  lambda: el == self.driver.switch_to.active_element,
            'empty':    lambda: el.get_attribute('value') == '',
        }
        check = checks.get(n.state)
        if check is None:
            raise RuntimeError(f"Unsupported verify state: {n.state}")
        self._assert(check(),
                     f"Element is not {n.state} (line {n.line})")

    def _exec_VerifyText(self, n: VerifyText):
        el = self._resolve(n.target)
        actual = el.text or el.get_attribute('value') or ''
        expected = self._interpolate(n.expected)
        if n.mode == 'has':
            self._assert(actual.strip() == expected,
                         f"Expected text '{expected}', got '{actual}' (line {n.line})")
        elif n.mode == 'contains':
            self._assert(expected in actual,
                         f"Text doesn't contain '{expected}', got '{actual}' (line {n.line})")
        elif n.mode == 'matches':
            self._assert(bool(re.search(expected, actual)),
                         f"Text '{actual}' doesn't match /{expected}/ (line {n.line})")

    def _exec_VerifyAttr(self, n: VerifyAttr):
        el = self._resolve(n.target)
        actual = el.get_attribute(n.attr_name) or ""
        expected = self._eval_text_value(n.expected)
        self._check_string_op(actual, expected, n.op,
                              f"Attribute '{n.attr_name}'")

    def _exec_VerifyStyle(self, n: VerifyStyle):
        el = self._resolve(n.target)
        actual = el.value_of_css_property(n.prop) or ''
        expected = self._eval_text_value(n.expected)
        self._check_string_op(actual, expected, n.op, f"Style '{n.prop}'")

    def _exec_VerifyCount(self, n: VerifyCount):
        elements = self._resolve_all(n.target)
        actual = len(elements)
        ops = {
            'is': actual == n.expected,
            'equals': actual == n.expected,
            'greater_than': actual > n.expected,
            'less_than': actual < n.expected,
        }
        self._assert(ops.get(n.op, False),
                     f"Count {actual} is not {n.op} {n.expected}")

    def _exec_VerifyURL(self, n: VerifyURL):
        actual = self.driver.current_url
        expected = self._eval_text_value(n.expected)
        self._check_string_op(actual, expected, n.op, "URL")

    def _exec_VerifyTitle(self, n: VerifyTitle):
        actual = self.driver.title
        expected = self._eval_text_value(n.expected)
        self._check_string_op(actual, expected, n.op, "Title")

    def _exec_VerifyCookie(self, n: VerifyCookie):
        cookie = self.driver.get_cookie(n.name)
        actual = cookie['value'] if cookie else ''
        expected = self._eval_text_value(n.expected)
        self._check_string_op(actual, expected, n.op, f"Cookie '{n.name}'")

    def _exec_VerifyDownloaded(self, n: VerifyDownloaded):
        download_dir = self.variables.get('_download_dir', '/tmp/downloads')
        filepath = Path(download_dir) / n.filename
        self._assert(filepath.exists(),
                     f"File '{n.filename}' not downloaded")

    def _exec_VerifyAlert(self, n: VerifyAlert):
        alert = self.driver.switch_to.alert
        expected = self._eval_text_value(n.expected)
        self._assert(expected in alert.text,
                     f"Alert text '{alert.text}' does not contain '{expected}'")

    def _check_string_op(self, actual, expected, op, label):
        ops = {
            'is': actual == expected,
            'equals': actual == expected,
            'contains': expected in actual,
            'containing': expected in actual,
            'matches': bool(re.search(expected, actual)),
            'matching': bool(re.search(expected, actual)),
            'starts_with': actual.startswith(expected),
            'ends_with': actual.endswith(expected),
        }
        self._assert(ops.get(op, False),
                     f"{label}: '{actual}' does not {op} '{expected}'")

    # ══════════════════════════════════════════════════════
    #  Waits
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _exec_WaitSeconds(n: WaitSeconds):
        time.sleep(n.duration)

    def _exec_WaitForElement(self, n: WaitForElement):
        timeout = n.timeout or self.timeout
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                el = self._resolve(n.target)
                if not n.state:
                    return

                checks = {
                    'visible': el.is_displayed,
                    'hidden': lambda: not el.is_displayed(),
                    'enabled': el.is_enabled,
                    'disabled': lambda: not el.is_enabled(),
                    'selected': el.is_selected,
                    'checked': el.is_selected,
                    'focused': lambda: el == self.driver.switch_to.active_element,
                    'empty': lambda: (el.get_attribute('value') or '') == '',
                }

                check = checks.get(n.state)
                if check is None:
                    raise RuntimeError(f"Unsupported wait state: {n.state}")

                if check():
                    return
            except Exception:
                pass

            time.sleep(0.25)

        raise TimeoutError(f"Timed out waiting for element after {timeout}s")

    def _exec_WaitUntilURL(self, n: WaitUntilURL):
        expected = self._eval_text_value(n.expected)
        WebDriverWait(self.driver, self.timeout).until(
            lambda d: expected in d.current_url
        )

    def _exec_WaitUntilTitle(self, n: WaitUntilTitle):
        expected = self._eval_text_value(n.expected)
        WebDriverWait(self.driver, self.timeout).until(
            lambda d: expected in d.title
        )

    # ══════════════════════════════════════════════════════
    #  Variables
    # ══════════════════════════════════════════════════════

    def _exec_SetVar(self, n: SetVar):
        if n.extract == 'text':
            el = self._resolve(n.target)
            self.variables[n.name] = el.text
        elif n.extract == 'attr':
            el = self._resolve(n.target)
            self.variables[n.name] = el.get_attribute(n.attr_name)
        elif n.extract == 'value':
            el = self._resolve(n.target)
            self.variables[n.name] = el.get_attribute('value')
        elif n.extract == 'count':
            elements = self._resolve_all(n.target)
            self.variables[n.name] = len(elements)
        elif n.extract == 'url':
            self.variables[n.name] = self.driver.current_url
        elif n.extract == 'title':
            self.variables[n.name] = self.driver.title
        else:
            self.variables[n.name] = self._eval_expr(n.value)

    # ══════════════════════════════════════════════════════
    #  Control flow
    # ══════════════════════════════════════════════════════

    def _exec_IfStmt(self, n: IfStmt):
        if self._eval_condition(n.condition):
            self.exec_block(n.then_body)
        elif n.else_body:
            self.exec_block(n.else_body)

    def _exec_RepeatTimes(self, n: RepeatTimes):
        for _ in range(n.count):
            self.exec_block(n.body)

    def _exec_RepeatWhile(self, n: RepeatWhile):
        max_iter = 1000  # safety
        i = 0
        while self._eval_condition(n.condition) and i < max_iter:
            self.exec_block(n.body)
            i += 1

    def _exec_ForEach(self, n: ForEach):
        elements = self._resolve_all(n.target)
        for el in elements:
            self.variables[n.var_name] = el
            self.exec_block(n.body)

    def _exec_TryCatch(self, n: TryCatch):
        try:
            self.exec_block(n.try_body)
        except Exception as e:
            self.variables['_error'] = str(e)
            self.exec_block(n.catch_body)

    def _exec_DefineSub(self, n: DefineSub):
        self.subroutines[n.name] = n.body

    def _exec_CallSub(self, n: CallSub):
        body = self.subroutines.get(n.name)
        if body is None:
            raise RuntimeError(f"Subroutine '{n.name}' not defined")
        self.exec_block(body)

    def _eval_condition(self, cond) -> bool:
        if isinstance(cond, StateCondition):
            try:
                el = self._resolve(cond.target)
                checks = {
                    'visible': el.is_displayed,
                    'hidden': lambda: not el.is_displayed(),
                    'enabled': el.is_enabled,
                    'disabled': lambda: not el.is_enabled(),
                    'selected': el.is_selected,
                    'checked': el.is_selected,
                }
                return checks.get(cond.state, lambda: False)()
            except Exception:
                return cond.state == 'hidden'

        # elif isinstance(cond, CompareCondition):
        #     l = self._eval_expr(cond.left)
        #     r = self._eval_expr(cond.right)
        #     op = cond.op
        #
        #     if op in ("is", "equals"):
        #         return str(l) == str(r)
        #     elif op == "greater_than":
        #         try:
        #             return float(l) > float(r)
        #         except (ValueError, TypeError):
        #             return str(l) > str(r)
        #     elif op == "less_than":
        #         try:
        #             return float(l) < float(r)
        #         except (ValueError, TypeError):
        #             return str(l) < str(r)
        #     return False
        # This stores raw numbers in variables

        elif isinstance(cond, CompareCondition):
            left = self._eval_expr(cond.left)
            right = self._eval_expr(cond.right)

            # if cond.op == "is":
            if cond.op in ["is", "equals"]:
                try:
                    return float(left) == float(right)
                except (TypeError, ValueError):
                    return str(left) == str(right)

            elif cond.op == 'greater_than':
                try:
                    return float(left) > float(right)
                except (TypeError, ValueError):
                    return str(left) > str(right)

            elif cond.op == 'less_than':
                try:
                    return float(left) < float(right)
                except (TypeError, ValueError):
                    return str(left) < str(right)

        elif isinstance(cond, URLCondition):
            expected = self._eval_text_value(cond.expected)
            return expected in self.driver.current_url

        elif isinstance(cond, NotCondition):
            return not self._eval_condition(cond.child)

        elif isinstance(cond, BoolCondition):
            l = self._eval_condition(cond.left)
            if cond.op == 'and':
                return l and self._eval_condition(cond.right)
            return l or self._eval_condition(cond.right)

        return False

    def _eval_text_value(self, value):
        resolved = self._eval_runtime_value(value)

        if resolved is None:
            return ""

        if isinstance(resolved, str):
            import re

            def replace_braced(match):
                name = match.group(1)
                if name not in self.variables:
                    raise RuntimeError(f"Variable ${name} is not set")
                v = self.variables[name]
                return "" if v is None else str(v)

            def replace_unbraced(match):
                name = match.group(1)
                if name not in self.variables:
                    raise RuntimeError(f"Variable ${name} is not set")
                v = self.variables[name]
                return "" if v is None else str(v)

            resolved = re.sub(r'\$\{(\w+)\}', replace_braced, resolved)
            resolved = re.sub(r'(?<!\$)\$(\w+)', replace_unbraced, resolved)

        return str(resolved)

    def _eval_runtime_value(self, value):
        # Backward compatible:
        # - if parser already gave us a plain Python value, keep it
        # - if parser gave us an Expr node, evaluate it
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        # New parser path: expression AST node
        return self._eval_expr(value)

    # ══════════════════════════════════════════════════════
    #  Misc
    # ══════════════════════════════════════════════════════

    def _exec_Import__old(self, n: Import):
        filepath = Path(n.filepath)

        # Resolve relative to the current script's directory
        if not filepath.is_absolute():
            # Check relative to CWD and common locations
            candidates = [
                filepath,
                Path('tests/fixtures') / filepath,
                Path('tests') / filepath,
            ]
            for candidate in candidates:
                if candidate.exists():
                    filepath = candidate
                    break

        abs_path = str(filepath.resolve())
        if abs_path in self.imports_loaded:
            return  # already imported, skip
        self.imports_loaded.add(abs_path)

        if not filepath.exists():
            raise RuntimeError(f"Import file not found: {n.filepath}")

        from webspec_lexer import lexer as import_lexer
        from webspec_parser import parser as import_parser

        script_text = filepath.read_text(encoding='utf-8')
        import_lexer.lineno = 1
        ast = import_parser.parse(script_text, lexer=import_lexer)

        if ast and ast.statements:
            self.exec_block(ast.statements)

    def _exec_Import(self, n: Import):
        filepath = self._resolve_runtime_path(n.filepath, allow_test_fallbacks=True)

        abs_path = str(filepath.resolve())
        if abs_path in self.imports_loaded:
            return

        if not filepath.exists():
            raise RuntimeError(f"Import file not found: {n.filepath}")

        self.imports_loaded.add(abs_path)

        from webspec_lexer import lexer as import_lexer
        from webspec_parser import parser as import_parser

        script_text = filepath.read_text(encoding='utf-8')
        import_lexer.lineno = 1
        ast = import_parser.parse(script_text, lexer=import_lexer)

        self.script_stack.append(filepath.parent)
        try:
            if ast and ast.statements:
                self.exec_block(ast.statements)
        finally:
            self.script_stack.pop()

    def _exec_WithData(self, n: WithData):
        import csv

        filepath = self._resolve_runtime_path(n.filepath, allow_test_fallbacks=True)
        if not filepath.exists():
            raise RuntimeError(f"Data file not found: {n.filepath}")

        ext = filepath.suffix.lower()

        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = [data]
            else:
                raise RuntimeError(f"JSON must be array or object, got {type(data)}")
        else:
            raise RuntimeError(f"Unsupported data format: {ext} (use .csv or .json)")

        logger.info(f"Data-driven: {len(rows)} iterations from {filepath}")

        base_vars = dict(self.variables)
        row_count = len(rows)
        row_failures = []

        try:
            for i, row in enumerate(rows):
                logger.info(f"Data iteration {i + 1}/{row_count}: {row}")

                self.variables = dict(base_vars)
                for key, value in row.items():
                    self.variables[key] = value

                self.variables["_row_index"] = str(i)
                self.variables["_row_count"] = str(row_count)

                try:
                    self.exec_block(n.body)
                except Exception as e:
                    msg = f"Data row {i + 1} failed: {e}"
                    self.errors.append(msg)
                    logger.error(msg)

                    if self.row_failure_mode == "fail_fast":
                        raise RuntimeError(msg) from e

                    row_failures.append(msg)

            if row_failures:
                raise RuntimeError(
                    "One or more data rows failed:\n" + "\n".join(row_failures)
                )
        finally:
            self.variables = base_vars

    def _exec_Log(self, n: Log):
        # msg = self._eval_expr(n.message)
        msg = self._coerce_to_string(self._eval_expr(n.message))
        logger.info(f"[LOG] {msg}")

    def _exec_TakeScreenshot(self, n: TakeScreenshot):
        name = n.filename or f"screenshot_{self.step_count}.png"
        path = self.screenshot_dir / name
        self.driver.save_screenshot(str(path))
        logger.info(f"Screenshot saved: {path}")

    def _exec_AcceptAlert(self, _):
        self.driver.switch_to.alert.accept()

    def _exec_DismissAlert(self, _):
        self.driver.switch_to.alert.dismiss()

    def _exec_SwitchFrame(self, n: SwitchFrame):
        if n.target is None:
            self.driver.switch_to.default_content()
        elif isinstance(n.target, str):
            self.driver.switch_to.frame(n.target)
        else:
            el = self._resolve(n.target)
            self.driver.switch_to.frame(el)

    # def _exec_SwitchWindow(self, n: SwitchWindow):
    #     for handle in self.driver.window_handles:
    #         self.driver.switch_to.window(handle)
    #         if n.name in self.driver.title:
    #             return
    def _exec_SwitchWindow(self, n: SwitchWindow):
        original_handle = self.driver.current_window_handle

        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if n.name in self.driver.title:
                return

        # Restore original focus before failing
        self.driver.switch_to.window(original_handle)
        raise RuntimeError(f'No window found with title containing "{n.name}"')

    def _exec_OpenWindow(self, _):
        self.driver.execute_script("window.open('')")
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def _exec_CloseWindow(self, _):
        self.driver.close()
        if self.driver.window_handles:
            self.driver.switch_to.window(self.driver.window_handles[-1])

    def _exec_SaveSource(self, n: SaveSource):
        Path(n.filename).write_text(self.driver.page_source, encoding='utf-8')

    def _exec_SaveCookies(self, n: SaveCookies):
        cookies = self.driver.get_cookies()
        Path(n.filename).write_text(json.dumps(cookies, indent=2), encoding='utf-8')