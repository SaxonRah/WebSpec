from types import SimpleNamespace

import pytest

import webspec_runtime as runtime_mod


class FakeElement:
    def __init__(self):
        self.attrs = {"href": "https://example.com/dashboard"}
        self.styles = {"display": "none"}
        self.visible = True
        self.enabled = True
        self.selected = False

    def get_attribute(self, name):
        return self.attrs.get(name)

    def value_of_css_property(self, prop):
        return self.styles.get(prop)

    def is_displayed(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def is_selected(self):
        return self.selected


class FakeAlert:
    def __init__(self, text):
        self.text = text


class FakeSwitchTo:
    def __init__(self, alert):
        self.alert = alert


class FakeDriver:
    def __init__(self):
        self.title = "Dashboard"
        self._cookie_value = "abc123"
        self.switch_to = FakeSwitchTo(FakeAlert("Warning: session expiring soon"))

    def get_cookie(self, name):
        if name == "session":
            return {"name": "session", "value": self._cookie_value}
        return None


@pytest.fixture
def runtime(monkeypatch):
    driver = FakeDriver()
    rt = runtime_mod.WebSpecRuntime(
        driver=driver,
        timeout=1,
        retry_timeout=0.01,
        retry_interval=0.0,
    )
    fake_el = FakeElement()
    monkeypatch.setattr(rt, "_resolve", lambda target: fake_el)
    return rt


def test_verify_title_is_var(runtime):
    runtime.variables["page_title"] = "Dashboard"
    node = SimpleNamespace(expected="$page_title", op="is")

    runtime._exec_VerifyTitle(node)


def test_verify_attr_contains_var(runtime):
    runtime.variables["path"] = "/dashboard"
    node = SimpleNamespace(
        target=object(),
        attr_name="href",
        expected="$path",
        op="contains",
    )

    runtime._exec_VerifyAttr(node)


def test_verify_style_is_var(runtime):
    runtime.variables["display_value"] = "none"
    node = SimpleNamespace(
        target=object(),
        prop="display",
        expected="$display_value",
        op="is",
    )

    runtime._exec_VerifyStyle(node)


def test_verify_cookie_is_var(runtime):
    runtime.variables["session_value"] = "abc123"
    node = SimpleNamespace(
        name="session",
        expected="$session_value",
        op="is",
    )

    runtime._exec_VerifyCookie(node)


def test_verify_alert_contains_var(runtime):
    runtime.variables["alert_text"] = "session expiring"
    node = SimpleNamespace(expected="$alert_text")

    runtime._exec_VerifyAlert(node)


def test_press_key_with_ctrl_shift_drives_both_modifiers(runtime, monkeypatch):
    calls = []

    class FakeActionChains:
        def __init__(self, driver):
            self.driver = driver

        def key_down(self, key):
            calls.append(("down", key))
            return self

        def send_keys(self, key):
            calls.append(("send", key))
            return self

        def key_up(self, key):
            calls.append(("up", key))
            return self

        def perform(self):
            calls.append(("perform",))
            return self

    monkeypatch.setattr(runtime_mod, "ActionChains", FakeActionChains)

    node = SimpleNamespace(key="a", modifier="ctrl+shift")
    runtime._exec_PressKey(node)

    assert calls == [
        ("down", runtime_mod.MODIFIER_MAP["ctrl"]),
        ("down", runtime_mod.MODIFIER_MAP["shift"]),
        ("send", "a"),
        ("up", runtime_mod.MODIFIER_MAP["shift"]),
        ("up", runtime_mod.MODIFIER_MAP["ctrl"]),
        ("perform",),
    ]


def test_unsupported_verify_state_raises_runtime_error(runtime):
    node = SimpleNamespace(target=object(), state="weird_state")

    with pytest.raises(RuntimeError, match="Unsupported verify state: weird_state"):
        runtime._exec_VerifyState(node)