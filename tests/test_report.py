from pathlib import Path

from webspec_report import generate_report


class DummyRuntime:
    def __init__(self, step_timings=None, variables=None, screenshot_dir=None):
        self.step_timings = step_timings or []
        self.variables = variables or {}
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir is not None else Path("screenshots")


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def test_generate_report_creates_default_output_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    runtime = DummyRuntime(
        step_timings=[],
        variables={},
        screenshot_dir=tmp_path / "screenshots",
    )
    runtime.screenshot_dir.mkdir()

    output_path = generate_report(runtime, script_name="sample.ws")

    out = Path(output_path)
    assert out.exists()
    assert out.parent.name == "reports"
    assert out.name.startswith("report_")
    assert out.suffix == ".html"

    html = read_text(out)
    assert "WebSpec Report - sample.ws" in html
    assert "PASSED" in html


def test_generate_report_works_with_zero_steps(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[],
        variables={},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="zero_steps.ws",
        output_path=str(tmp_path / "zero_steps_report.html"),
    )

    html = read_text(output_path)
    assert "zero_steps.ws" in html
    assert "PASSED" in html
    assert "0/0 steps passed" in html
    assert "0.00s" in html
    assert "<h2>Step Details</h2>" in html
    assert "<tbody></tbody>" in html


def test_generate_report_works_with_failed_steps(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[
            {
                "step": 1,
                "status": "pass",
                "type": "Open",
                "line": 3,
                "duration": 0.12,
                "error": "",
            },
            {
                "step": 2,
                "status": "fail",
                "type": "Click",
                "line": 4,
                "duration": 0.34,
                "error": "Button not found",
            },
        ],
        variables={"count": 2},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="failed.ws",
        output_path=str(tmp_path / "failed_report.html"),
    )

    html = read_text(output_path)
    assert "FAILED" in html
    assert "1/2 steps passed" in html
    assert "0.46s" in html
    assert "Button not found" in html
    assert "Open" in html
    assert "Click" in html
    assert "<h2>Variables</h2>" in html
    assert "$count" in html
    assert ">2<" in html


def test_generate_report_escapes_special_characters_in_errors_and_variables(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[
            {
                "step": 1,
                "status": "fail",
                "type": "Assert",
                "line": 9,
                "duration": 0.5,
                "error": 'bad & <tag> "quoted" value',
            }
        ],
        variables={
            "danger": 'x & y < z > w "quote" \'single\''
        },
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="escape.ws",
        output_path=str(tmp_path / "escape_report.html"),
    )

    html = read_text(output_path)

    assert 'bad & <tag> "quoted" value' not in html
    assert 'x & y < z > w "quote" \'single\'' not in html

    assert "bad &amp; &lt;tag&gt; &quot;quoted&quot; value" in html
    assert "x &amp; y &lt; z &gt; w &quot;quote&quot; &#x27;single&#x27;" in html


def test_generate_report_embeds_png_screenshots(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    png_path = screenshot_dir / "step_001.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\nfakepngdata")

    runtime = DummyRuntime(
        step_timings=[
            {
                "step": 1,
                "status": "pass",
                "type": "Screenshot",
                "line": 10,
                "duration": 0.2,
                "error": "",
            }
        ],
        variables={},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="screens.ws",
        output_path=str(tmp_path / "screens_report.html"),
    )

    html = read_text(output_path)
    assert "<h2>Screenshots</h2>" in html
    assert "step_001.png" in html
    assert "data:image/png;base64," in html


def test_generate_report_does_not_break_with_empty_screenshot_directory(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[
            {
                "step": 1,
                "status": "pass",
                "type": "Open",
                "line": 1,
                "duration": 0.1,
                "error": "",
            }
        ],
        variables={},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="empty_screens.ws",
        output_path=str(tmp_path / "empty_screens_report.html"),
    )

    html = read_text(output_path)
    assert Path(output_path).exists()
    assert "empty_screens.ws" in html
    assert "<h2>Screenshots</h2>" not in html


def test_generate_report_includes_variables_section_when_present(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[],
        variables={
            "name": "alice",
            "count": 42,
        },
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="vars.ws",
        output_path=str(tmp_path / "vars_report.html"),
    )

    html = read_text(output_path)
    assert "<h2>Variables</h2>" in html
    assert "$name" in html
    assert "alice" in html
    assert "$count" in html
    assert ">42<" in html


def test_generate_report_omits_variables_section_when_empty(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[],
        variables={},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="no_vars.ws",
        output_path=str(tmp_path / "no_vars_report.html"),
    )

    html = read_text(output_path)
    assert "<h2>Variables</h2>" not in html


def test_generate_report_sums_total_duration_correctly(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()

    runtime = DummyRuntime(
        step_timings=[
            {
                "step": 1,
                "status": "pass",
                "type": "Open",
                "line": 1,
                "duration": 1.25,
                "error": "",
            },
            {
                "step": 2,
                "status": "pass",
                "type": "Click",
                "line": 2,
                "duration": 2.75,
                "error": "",
            },
        ],
        variables={},
        screenshot_dir=screenshot_dir,
    )

    output_path = generate_report(
        runtime,
        script_name="timing.ws",
        output_path=str(tmp_path / "timing_report.html"),
    )

    html = read_text(output_path)
    assert "2/2 steps passed" in html
    assert "4.00s" in html
    assert "1.25s" in html
    assert "2.75s" in html