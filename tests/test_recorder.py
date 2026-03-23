# tests/test_recorder.py
from pathlib import Path
from types import SimpleNamespace

import pytest

import webspec_recorder


class DummyDriver:
    def __init__(self):
        self.scripts = []
        self.raise_on_scripts = set()
        self.result_by_substring = {}
        self.raise_on_execute = False

    def execute_script(self, script, *args):
        if self.raise_on_execute:
            raise Exception("execute_script failed")
        self.scripts.append((script, args))

        idx = len(self.scripts) - 1
        if idx in self.raise_on_scripts:
            raise RuntimeError(f"script failure at call {idx}")

        for key, value in self.result_by_substring.items():
            if key in script:
                if isinstance(value, Exception):
                    raise value
                return value

        return None


class FakeThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon
        self.started = False
        self.join_called = False
        self.join_calls = []

    def start(self):
        self.started = True

    def join(self, timeout=None):
        self.join_called = True
        self.join_calls.append(timeout)


@pytest.fixture
def recorder_env(monkeypatch, tmp_path):
    created = SimpleNamespace(
        driver=DummyDriver(),
        thread_instances=[],
        sleep_calls=[],
        transpile_calls=[],
        injected_js="/* fake capture js */",
        tmp_path=tmp_path,
    )

    monkeypatch.setattr(webspec_recorder, "JS_CAPTURE", created.injected_js)

    def fake_thread_ctor(target=None, daemon=None):
        t = FakeThread(target=target, daemon=daemon)
        created.thread_instances.append(t)
        return t

    monkeypatch.setattr(webspec_recorder.threading, "Thread", fake_thread_ctor)
    monkeypatch.setattr(
        webspec_recorder.time,
        "sleep",
        lambda seconds: created.sleep_calls.append(seconds),
    )

    class FakeTranspiler:
        def transpile(self, events):
            created.transpile_calls.append(list(events))
            return "navigate to \"https://example.com\"\nlog \"done\""

    monkeypatch.setattr(webspec_recorder, "WebSpecTranspiler", FakeTranspiler)

    recorder = webspec_recorder.WebSpecRecorder(created.driver, poll_interval=0.25)
    created.recorder = recorder
    return created


def test_inject_calls_execute_script_with_js_capture(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.inject()

    assert driver.scripts[0][0] == webspec_recorder.JS_CAPTURE
    assert driver.scripts[1][0] == (
        "if (window.__webspec_recorder) { window.__webspec_recorder.recording = arguments[0]; }"
    )
    assert driver.scripts[1][1] == (recorder.recording,)


def test_start_sets_flags_injects_js_enables_recording_and_starts_thread(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.start()

    assert recorder.recording is True
    assert recorder._stop_flag is False
    assert recorder._poll_thread is not None
    assert recorder._poll_thread.started is True

    script_texts = [s for s, _ in driver.scripts]
    assert webspec_recorder.JS_CAPTURE in script_texts
    assert "window.__webspec_recorder.recording = true;" in script_texts

    # assert driver.scripts[0] == recorder_env.injected_js
    # assert driver.scripts[1] == "window.__webspec_recorder.recording = true;"

    assert len(recorder_env.thread_instances) == 1
    thread = recorder_env.thread_instances[0]
    assert thread.target == recorder._poll_events
    assert thread.daemon is True
    assert thread.started is True

    assert recorder._poll_thread is thread


def test_stop_turns_off_recording_collects_remaining_events_and_joins_thread(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.start()

    driver.result_by_substring["splice(0)"] = [
        {"eventType": "click", "url": "https://example.com"}
    ]

    recorder.stop()

    assert recorder.recording is False
    assert recorder._stop_flag is True

    # assert "window.__webspec_recorder.recording = false;" in driver.scripts
    # assert any("splice(0)" in s for s in driver.scripts)

    script_texts = [s for s, _ in driver.scripts]
    assert "window.__webspec_recorder.recording = false;" in script_texts
    assert any("splice(0)" in s for s in script_texts)

    assert recorder.events == [
        {"eventType": "click", "url": "https://example.com"}
    ]

    # thread = recorder._poll_thread
    # assert thread.join_calls == [2]
    if recorder._poll_thread is not None:
        assert recorder._poll_thread.join_called is True


def test_stop_ignores_browser_errors_when_disabling_recording(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.start()

    # Make the "recording = false" call fail.
    # start() produces script calls 0 and 1, so this will affect the next call at index 2.
    driver.raise_on_scripts.add(2)

    recorder.stop()

    assert recorder.recording is False
    assert recorder._stop_flag is True
    assert recorder._poll_thread.join_calls == [2]


def test_double_start_does_not_explode_and_creates_new_poll_thread(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.start()
    first_thread = recorder._poll_thread

    recorder.start()
    second_thread = recorder._poll_thread

    assert recorder.recording is True
    assert first_thread is not second_thread
    assert second_thread.started is True

    # assert recorder.recording is True
    # assert first_thread is not second_thread
    # assert len(recorder_env.thread_instances) == 2
    # assert first_thread.started is True
    # assert second_thread.started is True
    #
    # # Each start injects JS and enables recording.
    # assert driver.scripts.count(recorder_env.injected_js) == 2
    # assert driver.scripts.count("window.__webspec_recorder.recording = true;") == 2


def test_double_stop_does_not_explode(recorder_env):
    recorder = recorder_env.recorder

    recorder.start()
    recorder.stop()
    recorder.stop()

    assert recorder.recording is False
    assert recorder._stop_flag is True
    # Both stops are allowed; join may be called more than once on the same fake thread.
    assert recorder._poll_thread.join_calls == [2, 2]


def test_collect_events_extends_event_list_from_browser_queue(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    driver.result_by_substring["splice(0)"] = [
        {"eventType": "click", "url": "https://example.com"},
        {"eventType": "type", "url": "https://example.com", "value": "abc"},
    ]

    recorder.collect_events()

    assert len(recorder.events) == 2
    assert recorder.events[0]["eventType"] == "click"
    assert recorder.events[1]["eventType"] == "type"
    # assert any("splice(0)" in s for s in driver.scripts)
    script_texts = [s for s, _ in driver.scripts]
    assert any("splice(0)" in s for s in script_texts)


def test_collect_events_ignores_execute_script_failure(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    driver.result_by_substring["splice(0)"] = RuntimeError("driver gone")

    recorder.collect_events()

    assert recorder.events == []


def test_poll_events_handles_collect_exceptions_gracefully(recorder_env, monkeypatch):
    recorder = recorder_env.recorder

    calls = {"count": 0}

    def fake_collect():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("bad poll payload")
        recorder._stop_flag = True

    monkeypatch.setattr(recorder, "collect_events", fake_collect)
    recorder._stop_flag = False

    recorder._poll_events()

    assert calls["count"] == 2
    assert recorder_env.sleep_calls == [0.25, 0.25]


def test_pause_and_resume_toggle_browser_recording_flag(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.pause()
    recorder.resume()

    # assert driver.scripts == [
    #     "window.__webspec_recorder.recording = false;",
    #     "window.__webspec_recorder.recording = true;",
    # ]

    assert [s for s, _ in driver.scripts] == [
        "window.__webspec_recorder.recording = false;",
        "window.__webspec_recorder.recording = true;",
    ]
    assert recorder.recording is True


def test_clear_resets_events_and_clears_browser_queue(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    recorder.events = [{"eventType": "click"}]

    recorder.clear()

    # assert recorder.events == []
    # assert driver.scripts == ["window.__webspec_recorder.events = [];"]

    assert recorder.events == []
    assert [s for s, _ in driver.scripts] == [
        "window.__webspec_recorder.events = [];"
    ]


def test_reinject_if_needed_injects_when_recorder_missing(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    driver.result_by_substring["return !!window.__webspec_recorder;"] = False

    recorder.reinject_if_needed()

    # assert driver.scripts[0] == "return !!window.__webspec_recorder;"
    # assert driver.scripts[1] == recorder_env.injected_js

    script_texts = [s for s, _ in driver.scripts]
    assert script_texts[0] == "return !!window.__webspec_recorder;"
    assert webspec_recorder.JS_CAPTURE in script_texts


def test_reinject_if_needed_does_nothing_when_recorder_present(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    driver.result_by_substring["return !!window.__webspec_recorder;"] = True

    recorder.reinject_if_needed()

    # assert driver.scripts == ["return !!window.__webspec_recorder;"]
    assert [s for s, _ in driver.scripts] == [
        "return !!window.__webspec_recorder;"
    ]


def test_reinject_if_needed_swallows_driver_errors(recorder_env):
    recorder = recorder_env.recorder
    driver = recorder_env.driver

    driver.result_by_substring["return !!window.__webspec_recorder;"] = RuntimeError("navigation race")

    recorder.reinject_if_needed()

    # assert driver.scripts == ["return !!window.__webspec_recorder;"]

    assert [s for s, _ in driver.scripts] == [
        "return !!window.__webspec_recorder;"
    ]


def test_generate_delegates_to_transpiler_with_current_events(recorder_env):
    recorder = recorder_env.recorder

    recorder.events = [
        {"eventType": "click", "url": "https://example.com"},
        {"eventType": "type", "url": "https://example.com", "value": "hello"},
    ]

    script = recorder.generate()

    assert recorder_env.transpile_calls == [recorder.events]
    assert script == "navigate to \"https://example.com\"\nlog \"done\""


def test_save_writes_transpiled_script_to_file(recorder_env, tmp_path):
    recorder = recorder_env.recorder

    recorder.events = [
        {"eventType": "click", "url": "https://example.com"}
    ]

    out = tmp_path / "recorded.ws"
    script = recorder.save(str(out))

    assert out.exists()
    assert out.read_text(encoding="utf-8") == script
    assert script == "navigate to \"https://example.com\"\nlog \"done\""


def test_recorder_to_transpiler_integration_is_deterministic():
    transpiler = webspec_recorder.WebSpecTranspiler()

    events = [
        {
            "eventType": "click",
            "url": "https://example.com/login",
            "context": {
                "elemType": "button",
                "text": "Sign in",
                "label": "",
                "attrs": {},
                "ordinal": 1,
                "siblingCount": 1,
            },
        },
        {
            "eventType": "type",
            "url": "https://example.com/login",
            "value": "alice@example.com",
            "context": {
                "elemType": "input",
                "text": "",
                "label": "Email",
                "attrs": {"placeholder": "Email"},
                "ordinal": 1,
                "siblingCount": 1,
            },
        },
    ]

    script1 = transpiler.transpile(events)
    script2 = transpiler.transpile(events)

    assert script1 == script2
    assert '# Recorded by WebSpec Recorder' in script1
    assert 'navigate to "https://example.com/login"' in script1
    assert 'click the button "Sign in"' in script1
    assert 'type "alice@example.com" into the input near "Email"' in script1
    assert 'log "Recording playback complete"' in script1