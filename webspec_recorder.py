"""
WebSpec DSL - Browser Recorder
Records user interactions and generates WebSpec scripts.

Usage:
    python webspec_recorder.py --url "https://example.com" --output recorded.ws
    python webspec_recorder.py --url "https://example.com"  (interactive)
"""

import argparse
# import json
import logging
import time
import threading
from pathlib import Path

from selenium import webdriver

from webspec_transpiler import WebSpecTranspiler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('webspec.recorder')

# Load the JS capture script
JS_CAPTURE = (Path(__file__).parent / 'webspec_capture.js').read_text(
    encoding='utf-8')


class WebSpecRecorder:
    """Records browser interactions and transpiles to WebSpec."""

    def __init__(self, driver, poll_interval=0.5):
        self.driver = driver
        self.poll_interval = poll_interval
        self.events: list[dict] = []
        self.recording = False
        self._poll_thread = None
        self._stop_flag = False
        self.transpiler = WebSpecTranspiler()

    def inject(self):
        """Inject the JS event capture layer into the page."""
        self.driver.execute_script(JS_CAPTURE)
        logger.info("Event capture injected")

    def start(self):
        """Start recording events."""
        self.recording = True
        self._stop_flag = False
        self.inject()
        self.driver.execute_script(
            "window.__webspec_recorder.recording = true;")

        # Start polling thread
        self._poll_thread = threading.Thread(
            target=self._poll_events, daemon=True)
        self._poll_thread.start()
        logger.info("Recording started")

    def stop(self):
        """Stop recording and collect remaining events."""
        self.recording = False
        self._stop_flag = True

        try:
            self.driver.execute_script(
                "window.__webspec_recorder.recording = false;")
        except Exception:
            pass  # Browser may already be gone

        try:
            self.collect_events()
        except Exception:
            pass

        if self._poll_thread:
            self._poll_thread.join(timeout=2)

        logger.info(f"Recording stopped: {len(self.events)} events captured")

    def pause(self):
        """Pause recording without losing events."""
        self.driver.execute_script(
            "window.__webspec_recorder.recording = false;")
        logger.info("Recording paused")

    def resume(self):
        """Resume recording."""
        self.driver.execute_script(
            "window.__webspec_recorder.recording = true;")
        logger.info("Recording resumed")

    def clear(self):
        """Clear all captured events."""
        self.events = []
        self.driver.execute_script(
            "window.__webspec_recorder.events = [];")
        logger.info("Events cleared")

    def generate(self) -> str:
        """Generate WebSpec script from captured events."""
        return self.transpiler.transpile(self.events)

    def save(self, filepath: str):
        """Generate and save WebSpec script to file."""
        script = self.generate()
        Path(filepath).write_text(script, encoding='utf-8')
        logger.info(f"Script saved: {filepath} ({len(self.events)} events)")
        return script

    def _poll_events(self):
        """Background thread that polls for new events."""
        while not self._stop_flag:
            try:
                self.collect_events()
            except Exception as e:
                logger.debug(f"Poll error: {e}")
            time.sleep(self.poll_interval)

    def collect_events(self):
        """Pull events from the browser JS queue."""
        try:
            # Atomically drain the JS event queue
            new_events = self.driver.execute_script("""
                var evts = window.__webspec_recorder.events.splice(0);
                return evts;
            """)
            if new_events:
                self.events.extend(new_events)
        except Exception:
            pass

    def reinject_if_needed(self):
        """Re-inject capture script after page navigation."""
        try:
            has_recorder = self.driver.execute_script(
                "return !!window.__webspec_recorder;")
            if not has_recorder:
                self.inject()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(
        description='WebSpec Browser Recorder')
    ap.add_argument('--url', required=True,
                    help='Starting URL to record')
    ap.add_argument('--output', '-o', default=None,
                    help='Output .ws file (default: interactive mode)')
    ap.add_argument('--browser', default='chrome',
                    choices=['chrome', 'firefox', 'edge'])
    ap.add_argument('--poll-interval', type=float, default=0.5,
                    help='Event poll interval in seconds')
    args = ap.parse_args()

    # Set up browser
    driver = None
    if args.browser == 'chrome':
        opts = webdriver.ChromeOptions()
        driver = webdriver.Chrome(options=opts)
    elif args.browser == 'firefox':
        opts = webdriver.FirefoxOptions()
        driver = webdriver.Firefox(options=opts)
    elif args.browser == 'edge':
        opts = webdriver.EdgeOptions()
        driver = webdriver.Edge(options=opts)

    driver.implicitly_wait(2)
    driver.get(args.url)

    recorder = WebSpecRecorder(driver, poll_interval=args.poll_interval)

    # Non-interactive: just record until Ctrl+C
    if args.output:
        print(f"\n  Recording: {args.url}")
        print(f"  Output:    {args.output}")
        print(f"  Press Ctrl+C to stop and save.\n")

        recorder.start()
        try:
            last_url = args.url
            while True:
                time.sleep(1)
                try:
                    current = driver.current_url
                    if current != last_url:
                        recorder.reinject_if_needed()
                        last_url = current
                except Exception:
                    pass
        except KeyboardInterrupt:
            pass

        recorder.stop()

        if recorder.events:
            script = recorder.save(args.output)
            print(f"\n  Saved {len(recorder.events)} events to {args.output}")
            print(f"  Preview:\n")
            for line in script.split('\n')[:20]:
                print(f"    {line}")
            if script.count('\n') > 20:
                print(f"    ... ({script.count(chr(10)) - 20} more lines)")
        else:
            print("\n  No events captured.")

        try:
            driver.quit()
        except Exception:
            pass
        return

    # ── Interactive mode ─────────────────────────────────
    BANNER = """
  ╔═══════════════════════════════════════════╗
  ║        WebSpec Recorder (interactive)      ║
  ║                                           ║
  ║  :start    Begin recording                ║
  ║  :stop     Stop recording                 ║
  ║  :pause    Pause recording                ║
  ║  :resume   Resume recording               ║
  ║  :preview  Show generated script so far   ║
  ║  :save <f> Save script to file            ║
  ║  :events   Show raw event count           ║
  ║  :clear    Clear recorded events          ║
  ║  :inject   Re-inject capture (after nav)  ║
  ║  :quit     Exit                           ║
  ╚═══════════════════════════════════════════╝
"""
    print(BANNER)
    print(f"  Browser opened: {args.url}\n")
    cmd = None
    while True:
        try:
            cmd = input('recorder> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye!')
            break

        if not cmd:
            continue

        if cmd == ':start':
            recorder.start()
            print('  Recording started. Interact with the browser.')

        elif cmd == ':stop':
            recorder.stop()
            print(f'  Stopped. {len(recorder.events)} events captured.')

        elif cmd == ':pause':
            recorder.pause()
            print('  Paused.')

        elif cmd == ':resume':
            recorder.resume()
            print('  Resumed.')

        elif cmd == ':preview':
            if not recorder.events:
                # Collect any pending
                recorder.collect_events()
            script = recorder.generate()
            print('\n  --- Generated WebSpec ---')
            for line in script.split('\n'):
                print(f'  {line}')
            print('  --- End ---\n')

        elif cmd.startswith(':save'):
            parts = cmd.split(maxsplit=1)
            filepath = parts[1] if len(parts) > 1 else 'recorded.ws'
            recorder.collect_events()
            recorder.save(filepath)
            print(f'  Saved to {filepath}')

        elif cmd == ':events':
            recorder.collect_events()
            print(f'  {len(recorder.events)} events captured')
            if recorder.events:
                types = {}
                for e in recorder.events:
                    t = e.get('eventType', '?')
                    types[t] = types.get(t, 0) + 1
                for t, c in sorted(types.items()):
                    print(f'    {t}: {c}')

        elif cmd == ':clear':
            recorder.clear()
            print('  Events cleared.')

        elif cmd == ':inject':
            recorder.inject()
            print('  Capture re-injected.')

        elif cmd in (':quit', ':exit', ':q'):
            print('Bye!')
            break

        else:
            print(f'  Unknown command: {cmd}')
            print('  Type :start to begin recording')

    if recorder.recording:
        recorder.stop()
    try:
        driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()