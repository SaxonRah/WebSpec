"""
WebSpec DSL - Smart Transpiler
Converts captured browser events into idiomatic WebSpec script.

Selector priority (most readable first):
  1. near "Label"        - when a label[for] or nearby label exists
  2. "Visible text"      - button/link with clear text
  3. with placeholder    - input with placeholder text
  4. containing "text"   - partial text match
  5. with id "x"         - when id is readable (not auto-generated)
  6. with class "x"      - when class is semantic
  7. with attr "x" is "y" - data attributes, name, etc.
  8. element "css"       - raw fallback (last resort)
"""

import re
from typing import Optional


# ── Selector quality heuristics ──────────────────────────

def _is_autogen_id(id_str: str) -> bool:
    """IDs like 'ember123', 'react-456', ':r0:' are auto-generated."""
    if not id_str:
        return True
    if re.match(r'^[a-z]+-\d+$', id_str):  # ember-123
        return True
    if re.match(r'^:\w+:$', id_str):  # React :r0:
        return True
    if re.match(r'^\d+$', id_str):  # pure number
        return True
    if len(id_str) > 30:  # absurdly long
        return True
    return False


def _is_semantic_class(class_str: str) -> Optional[str]:
    """Extract a useful semantic class from a class list."""
    if not class_str:
        return None
    classes = class_str.split()
    # Skip utility classes (Bootstrap, Tailwind, etc.)
    skip_patterns = [
        r'^col-', r'^row$', r'^container', r'^d-', r'^p-', r'^m-',
        r'^text-', r'^bg-', r'^btn-?(sm|lg|xs|md)$', r'^float-',
        r'^flex', r'^grid', r'^w-', r'^h-', r'^rounded',
        r'^border', r'^shadow', r'^overflow', r'^position-',
    ]
    for cls in classes:
        is_utility = False
        for pat in skip_patterns:
            if re.match(pat, cls):
                is_utility = True
                break
        if not is_utility and len(cls) > 2 and not cls.startswith('_'):
            return cls
    return None


def _escape(s: str) -> str:
    """Escape a string for WebSpec."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


class WebSpecTranspiler:
    """Convert captured events into WebSpec DSL statements."""

    def __init__(self):
        self.lines: list[str] = []
        self.last_url: Optional[str] = None
        self.indent = ''

    def transpile(self, events: list[dict]) -> str:
        """Convert a list of captured events to a WebSpec script."""
        self.lines = []
        self.last_url = None

        # Add header
        self.lines.append('# Recorded by WebSpec Recorder')
        self.lines.append('')

        for event in events:
            self._handle_event(event)

        self.lines.append('')
        self.lines.append('log "Recording playback complete"')

        return '\n'.join(self.lines)

    def _handle_event(self, event: dict):
        etype = event.get('eventType', '')

        # Check for URL change (implicit navigation)
        url = event.get('url', '')
        if self.last_url is None:
            self._emit(f'navigate to "{_escape(url)}"')
            self._emit('wait 1 seconds')
            self._emit('')
            self.last_url = url
        elif url != self.last_url and etype != 'navigate':
            # URL changed without an explicit navigate event
            self._emit('')
            self._emit(f'# Page changed to: {url}')
            self._emit(f'wait until url contains "{_escape(self._url_path(url))}"')
            self.last_url = url

        handler = getattr(self, f'_handle_{etype}', None)
        if handler:
            handler(event)

    def _handle_click(self, event: dict):
        ctx = event.get('context', {})
        ref = self._build_ref(ctx)
        self._emit(f'click {ref}')

    def _handle_type(self, event: dict):
        ctx = event.get('context', {})
        value = event.get('value', '')
        ref = self._build_ref(ctx)
        self._emit(f'type "{_escape(value)}" into {ref}')

    def _handle_select(self, event: dict):
        ctx = event.get('context', {})
        option = event.get('option', '')
        ref = self._build_ref(ctx)
        self._emit(f'select "{_escape(option)}" from {ref}')

    def _handle_check(self, event: dict):
        ctx = event.get('context', {})
        ref = self._build_ref(ctx)
        self._emit(f'check {ref}')

    def _handle_uncheck(self, event: dict):
        ctx = event.get('context', {})
        ref = self._build_ref(ctx)
        self._emit(f'uncheck {ref}')

    def _handle_submit(self, event: dict):
        ctx = event.get('context', {})
        ref = self._build_ref(ctx)
        self._emit(f'submit {ref}')

    def _handle_navigate(self, event: dict):
        to_url = event.get('to', '')
        if to_url and to_url != self.last_url:
            self._emit('')
            self._emit(f'wait until url contains "{_escape(self._url_path(to_url))}"')
            self.last_url = to_url

    def _handle_keypress(self, event: dict):
        key = event.get('key', '')
        key_map = {
            'Enter': 'enter', 'Tab': 'tab', 'Escape': 'escape',
            'Backspace': 'backspace', 'Delete': 'delete',
            'ArrowUp': 'up', 'ArrowDown': 'down',
            'ArrowLeft': 'left', 'ArrowRight': 'right',
        }
        ws_key = key_map.get(key, key.lower())

        modifiers = []
        if event.get('ctrl'):
            modifiers.append('ctrl')
        if event.get('shift'):
            modifiers.append('shift')
        if event.get('alt'):
            modifiers.append('alt')

        if modifiers:
            mods = "+".join(modifiers)
            self._emit(f'press key "{ws_key}" with "{mods}"')
        else:
            self._emit(f'press key "{ws_key}"')

    def _handle_scroll(self, event: dict):
        direction = event.get('direction', 'down')
        pixels = event.get('pixels', 300)
        self._emit(f'scroll {direction} {pixels} pixels')

    # ── Smart element reference builder ──────────────────
    def _build_ref(self, ctx: dict) -> str:
        """
        Build the most readable WebSpec element reference
        from captured element context.
        """
        elem_type = ctx.get('elemType', 'element')
        text = ctx.get('text', '').strip()
        label = ctx.get('label', '').strip()
        attrs = ctx.get('attrs', {})
        ordinal = ctx.get('ordinal', 1)
        sibling_count = ctx.get('siblingCount', 1)

        # Strategy 1: near "Label" (best for inputs/dropdowns)
        if label and elem_type in ('input', 'dropdown', 'checkbox', 'radio'):
            ref = f'the {elem_type} near "{_escape(label)}"'
            return ref

        # Strategy 2: Visible text (best for buttons/links)
        if text and elem_type in ('button', 'link', 'heading'):
            if len(text) <= 40:
                ref = f'the {elem_type} "{_escape(text)}"'
                if sibling_count > 1 and ordinal > 1:
                    ref = f'the {self._ordinal(ordinal)} {elem_type} "{_escape(text)}"'
                return ref

        # Strategy 3: Placeholder text (for inputs)
        placeholder = attrs.get('placeholder', '')
        if placeholder and elem_type in ('input', 'field'):
            return f'the {elem_type} with placeholder "{_escape(placeholder)}"'

        # Strategy 4: aria-label
        aria = attrs.get('aria-label', '')
        if aria:
            return f'the {elem_type} "{_escape(aria)}"'

        # Strategy 5: Containing partial text
        if text and len(text) > 40:
            short = text[:30].strip()
            return f'the {elem_type} containing "{_escape(short)}"'

        # Strategy 6: Readable ID
        elem_id = attrs.get('id', '')
        if elem_id and not _is_autogen_id(elem_id):
            return f'the {elem_type} with id "{_escape(elem_id)}"'

        # Strategy 7: Semantic class
        cls = _is_semantic_class(attrs.get('class', ''))
        if cls:
            ref = f'the {elem_type} with class "{_escape(cls)}"'
            if sibling_count > 1 and ordinal > 0:
                ref = f'the {self._ordinal(ordinal)} {elem_type} with class "{_escape(cls)}"'
            return ref

        # Strategy 8: data-testid or name attribute
        testid = attrs.get('data-testid', '')
        if testid:
            return f'the {elem_type} with attr "data-testid" is "{_escape(testid)}"'
        name = attrs.get('name', '')
        if name:
            return f'the {elem_type} with attr "name" is "{_escape(name)}"'

        # Strategy 9: Any readable text
        if text:
            return f'the {elem_type} "{_escape(text[:40])}"'

        # Strategy 10: Ordinal fallback
        if sibling_count > 1:
            return f'the {self._ordinal(ordinal)} {elem_type}'

        # Last resort
        return f'the {elem_type}'

    # ── Helpers ──────────────────────────────────────────
    def _emit(self, line: str):
        self.lines.append(self.indent + line)

    @staticmethod
    def _url_path(url: str) -> str:
        """Extract just the path portion for url contains checks."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path
        if path and path != '/':
            return path
        return parsed.netloc

    @staticmethod
    def _ordinal(n: int) -> str:
        if n == 1: return '1st'
        if n == 2: return '2nd'
        if n == 3: return '3rd'
        return f'{n}th'