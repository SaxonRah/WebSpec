"""
WebSpec DSL — HTML Test Report Generator
Produces a self-contained HTML report with pass/fail status,
timing, screenshots, and variable dumps.
"""

# import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from webspec_runtime import WebSpecRuntime


def generate_report(
    runtime: WebSpecRuntime,
    script_name: str = 'unknown',
    output_path: Optional[str] = None,
) -> str:
    """Generate an HTML report and return the file path."""

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'reports/report_{timestamp}.html'

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    total = len(runtime.step_timings)
    passed = sum(1 for s in runtime.step_timings if s['status'] == 'pass')
    failed = total - passed
    total_time = sum(s['duration'] for s in runtime.step_timings)

    # Build step rows
    step_rows = ''
    for s in runtime.step_timings:
        status_class = 'pass' if s['status'] == 'pass' else 'fail'
        status_icon = '&#10004;' if s['status'] == 'pass' else '&#10008;'
        error_html = ''
        if s['error']:
            escaped = s['error'].replace('<', '&lt;').replace('>', '&gt;')
            error_html = f'<div class="error-msg">{escaped}</div>'

        step_rows += f'''
        <tr class="{status_class}">
            <td class="step-num">{s['step']}</td>
            <td><span class="status-badge {status_class}">{status_icon}</span></td>
            <td class="step-type">{s['type']}</td>
            <td class="step-line">L{s['line']}</td>
            <td class="step-time">{s['duration']}s</td>
            <td>{error_html}</td>
        </tr>'''

    # Build variables section
    var_rows = ''
    for k, v in runtime.variables.items():
        val = str(v)[:200].replace('<', '&lt;').replace('>', '&gt;')
        var_rows += f'<tr><td>${k}</td><td>{val}</td></tr>'

    # Find screenshots
    screenshot_html = ''
    if runtime.screenshot_dir.exists():
        screenshots = sorted(runtime.screenshot_dir.glob('*.png'))
        for ss in screenshots:
            import base64
            data = base64.b64encode(ss.read_bytes()).decode()
            screenshot_html += f'''
            <div class="screenshot">
                <div class="screenshot-name">{ss.name}</div>
                <img src="data:image/png;base64,{data}" />
            </div>'''

    result_class = 'pass' if failed == 0 else 'fail'
    result_text = 'PASSED' if failed == 0 else 'FAILED'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WebSpec Report - {script_name}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
        Roboto, sans-serif; background: #f5f5f5; color: #333;
        padding: 24px; line-height: 1.5; }}
.container {{ max-width: 960px; margin: 0 auto; }}
h1 {{ font-size: 22px; font-weight: 500; margin-bottom: 8px; }}
h2 {{ font-size: 17px; font-weight: 500; margin: 24px 0 12px;
      color: #555; }}

.summary {{ display: flex; gap: 16px; margin: 16px 0 24px;
            flex-wrap: wrap; }}
.summary-card {{ background: white; border-radius: 8px; padding: 16px 20px;
                 flex: 1; min-width: 140px;
                 border: 1px solid #e0e0e0; }}
.summary-card .label {{ font-size: 12px; color: #888;
                        text-transform: uppercase; letter-spacing: 0.5px; }}
.summary-card .value {{ font-size: 28px; font-weight: 500;
                        margin-top: 4px; }}
.summary-card .value.pass {{ color: #2a8a2a; }}
.summary-card .value.fail {{ color: #cc3333; }}

.result-banner {{ padding: 12px 20px; border-radius: 8px;
                  font-weight: 500; font-size: 16px; margin-bottom: 24px; }}
.result-banner.pass {{ background: #e6f4e6; color: #2a8a2a;
                       border: 1px solid #b8deb8; }}
.result-banner.fail {{ background: #fce6e6; color: #cc3333;
                       border: 1px solid #f0b8b8; }}

table {{ width: 100%; border-collapse: collapse; background: white;
         border-radius: 8px; overflow: hidden;
         border: 1px solid #e0e0e0; }}
th {{ background: #fafafa; text-align: left; padding: 10px 12px;
      font-size: 12px; font-weight: 500; color: #888;
      text-transform: uppercase; letter-spacing: 0.5px;
      border-bottom: 1px solid #e0e0e0; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0;
      font-size: 14px; }}
tr.fail {{ background: #fff5f5; }}
tr:last-child td {{ border-bottom: none; }}
.step-num {{ color: #999; width: 50px; }}
.step-type {{ font-family: monospace; font-size: 13px; }}
.step-line {{ color: #999; font-size: 12px; }}
.step-time {{ color: #666; font-size: 12px; }}
.status-badge {{ display: inline-block; width: 22px; height: 22px;
                 border-radius: 50%; text-align: center;
                 line-height: 22px; font-size: 12px; }}
.status-badge.pass {{ background: #e6f4e6; color: #2a8a2a; }}
.status-badge.fail {{ background: #fce6e6; color: #cc3333; }}
.error-msg {{ font-size: 12px; color: #cc3333;
              font-family: monospace; max-width: 400px;
              word-break: break-word; }}

.var-table td:first-child {{ font-family: monospace; font-weight: 500;
                             color: #0066cc; white-space: nowrap; }}
.var-table td:last-child {{ font-family: monospace; font-size: 13px;
                            word-break: break-all; }}

.screenshots {{ display: flex; flex-wrap: wrap; gap: 16px;
                margin-top: 12px; }}
.screenshot {{ background: white; border-radius: 8px; overflow: hidden;
               border: 1px solid #e0e0e0; max-width: 460px; }}
.screenshot img {{ width: 100%; display: block; }}
.screenshot-name {{ padding: 8px 12px; font-size: 12px; color: #666;
                    border-bottom: 1px solid #f0f0f0; }}

.meta {{ font-size: 12px; color: #999; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">
    <h1>WebSpec Test Report</h1>
    <div class="meta">Script: {script_name} &middot;
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

    <div class="result-banner {result_class}">
        {result_text} &mdash; {passed}/{total} steps passed
        in {total_time:.2f}s
    </div>

    <div class="summary">
        <div class="summary-card">
            <div class="label">Total Steps</div>
            <div class="value">{total}</div>
        </div>
        <div class="summary-card">
            <div class="label">Passed</div>
            <div class="value pass">{passed}</div>
        </div>
        <div class="summary-card">
            <div class="label">Failed</div>
            <div class="value {"fail" if failed else ""}">{failed}</div>
        </div>
        <div class="summary-card">
            <div class="label">Duration</div>
            <div class="value">{total_time:.2f}s</div>
        </div>
    </div>

    <h2>Step Details</h2>
    <table>
        <thead>
            <tr><th>#</th><th>Status</th><th>Action</th>
                <th>Line</th><th>Time</th><th>Details</th></tr>
        </thead>
        <tbody>{step_rows}</tbody>
    </table>

    {"<h2>Variables</h2><table class='var-table'><thead><tr><th>Name</th><th>Value</th></tr></thead><tbody>" + var_rows + "</tbody></table>" if var_rows else ""}

    {"<h2>Screenshots</h2><div class='screenshots'>" + screenshot_html + "</div>" if screenshot_html else ""}

    <div class="meta" style="margin-top: 32px;">
        Generated by WebSpec DSL</div>
</div>
</body>
</html>'''

    Path(output_path).write_text(html, encoding='utf-8')
    return output_path