from webspec_transpiler import WebSpecTranspiler


def test_captured_keypress_with_ctrl_shift_transpiles_correctly():
    events = [
        {
            "eventType": "keypress",
            "key": "X",
            "ctrl": True,
            "shift": True,
            "alt": False,
            "url": "https://example.com/app",
        }
    ]

    out = WebSpecTranspiler().transpile(events)

    assert 'press key "x" with "ctrl+shift"' in out