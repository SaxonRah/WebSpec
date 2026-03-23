// webspec_capture.js - Injected into the browser page by the recorder.
// Captures user interactions with full element context for WebSpec transpilation.

(function() {
    if (window.__webspec_recorder) return;
    window.__webspec_recorder = {
        events: [],
        recording: true,
        lastUrl: location.href,
        typingBuffer: {},   // element -> accumulated keystrokes
        typingTimers: {},   // element -> flush timer
    };

    var R = window.__webspec_recorder;

    // ── Element context extraction ──────────────────────
    function getContext(el) {
        if (!el || !el.tagName) return null;

        var tag = el.tagName.toLowerCase();
        var text = '';

        // Get visible text (not deeply nested)
        if (tag === 'select') {
            var opt = el.options[el.selectedIndex];
            text = opt ? opt.text.trim() : '';
        } else if (tag === 'input' || tag === 'textarea') {
            text = '';
        } else {
            // Direct text content only (first 100 chars)
            var childTexts = [];
            for (var i = 0; i < el.childNodes.length; i++) {
                if (el.childNodes[i].nodeType === 3) {
                    var t = el.childNodes[i].textContent.trim();
                    if (t) childTexts.push(t);
                }
            }
            text = childTexts.join(' ').substring(0, 100);
            if (!text) text = (el.textContent || '').trim().substring(0, 100);
        }

        // Find associated label
        var label = '';
        if (el.id) {
            var lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) label = lbl.textContent.trim();
        }
        if (!label) {
            // Walk up to find a sibling/parent label
            var parent = el.parentElement;
            for (var depth = 0; depth < 3 && parent; depth++) {
                var lbl = parent.querySelector('label');
                if (lbl && lbl !== el) {
                    label = lbl.textContent.trim();
                    break;
                }
                // Check preceding sibling text
                var prev = el.previousElementSibling || (parent && parent.previousElementSibling);
                if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'SPAN' || prev.tagName === 'P')) {
                    label = prev.textContent.trim();
                    break;
                }
                parent = parent.parentElement;
            }
        }

        // Get useful attributes
        var attrs = {};
        var attrNames = ['id', 'class', 'name', 'type', 'placeholder', 'value',
                         'href', 'role', 'aria-label', 'title', 'alt',
                         'data-id', 'data-testid', 'data-product-id'];
        for (var i = 0; i < attrNames.length; i++) {
            var v = el.getAttribute(attrNames[i]);
            if (v) attrs[attrNames[i]] = v.substring(0, 200);
        }

        // Element type classification
        var elemType = 'element';
        if (tag === 'button' || (tag === 'input' && (attrs.type === 'submit' || attrs.type === 'button'))) {
          elemType = 'button';
        } else if (tag === 'a') {
          elemType = 'link';
        } else if (tag === 'input' && attrs.type === 'checkbox') {
          elemType = 'checkbox';
        } else if (tag === 'input' && attrs.type === 'radio') {
          elemType = 'radio';
        } else if (tag === 'select') {
          elemType = 'dropdown';
        } else if (tag === 'input' || tag === 'textarea') {
          elemType = 'input';
        }
        else if (tag === 'img') elemType = 'image';
        else if (/^h[1-6]$/.test(tag)) elemType = 'heading';
        else if (tag === 'table') elemType = 'table';
        else if (tag === 'tr') elemType = 'row';
        else if (tag === 'td' || tag === 'th') elemType = 'cell';
        else if (tag === 'form') elemType = 'form';
        else if (attrs.role === 'button') elemType = 'button';
        else if (attrs.role === 'link') elemType = 'link';
        else if (attrs.role === 'checkbox') elemType = 'checkbox';

        // Ordinal: how many siblings of same type precede this element?
        var ordinal = 0;
        var siblings = document.querySelectorAll(tag + (attrs['class'] ? '.' + attrs['class'].split(' ')[0] : ''));
        for (var i = 0; i < siblings.length; i++) {
            if (siblings[i] === el) { ordinal = i + 1; break; }
        }

        return {
            tag: tag,
            elemType: elemType,
            text: text,
            label: label,
            attrs: attrs,
            ordinal: ordinal,
            siblingCount: siblings ? siblings.length : 1,
        };
    }

    R._getContext = getContext;

    function pushEvent(type, data) {
        if (!R.recording) return;
        data.eventType = type;
        data.timestamp = Date.now();
        data.url = location.href;
        R.events.push(data);
    }

    // ── Flush typing buffer ─────────────────────────────
    function flushTyping(key) {
        if (R.typingBuffer[key]) {
            var buf = R.typingBuffer[key];
            pushEvent('type', {
                context: buf.context,
                value: buf.value,
            });
            delete R.typingBuffer[key];
            delete R.typingTimers[key];
        }
    }

    // ── Click ───────────────────────────────────────────
    document.addEventListener('click', function(e) {
        var ctx = getContext(e.target);
        if (!ctx) return;
        // Skip if this is an input field (focus, not click action)
        if (ctx.elemType === 'input' && ctx.tag !== 'button') return;
        pushEvent('click', { context: ctx });
    }, true);

    // ── Input / typing ──────────────────────────────────
    document.addEventListener('input', function(e) {
        var el = e.target;
        var ctx = getContext(el);
        if (!ctx) return;

        var key = ctx.attrs.id || ctx.attrs.name || ctx.label || 'unknown';

        // Accumulate keystrokes
        R.typingBuffer[key] = {
            context: ctx,
            value: el.value,
        };

        // Debounce: flush after 800ms of no typing
        if (R.typingTimers[key]) clearTimeout(R.typingTimers[key]);
        R.typingTimers[key] = setTimeout(function() {
            flushTyping(key);
        }, 800);
    }, true);

    // ── Select / dropdown change ────────────────────────
    document.addEventListener('change', function(e) {
        var el = e.target;
        var ctx = getContext(el);
        if (!ctx) return;

        if (el.tagName.toLowerCase() === 'select') {
            var opt = el.options[el.selectedIndex];
            pushEvent('select', {
                context: ctx,
                option: opt ? opt.text.trim() : el.value,
            });
        } else if (ctx.attrs.type === 'checkbox') {
            pushEvent(el.checked ? 'check' : 'uncheck', {
                context: ctx,
            });
        } else if (ctx.attrs.type === 'radio') {
            pushEvent('check', {
                context: ctx,
            });
        }
    }, true);

    // ── Form submit ─────────────────────────────────────
    document.addEventListener('submit', function(e) {
        var ctx = getContext(e.target);
        if (ctx) pushEvent('submit', { context: ctx });
    }, true);

    // ── Keyboard (special keys only) ────────────────────
    document.addEventListener('keydown', function(e) {
        var special = ['Enter', 'Tab', 'Escape', 'Backspace', 'Delete',
                       'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
        if (special.indexOf(e.key) !== -1) {
            // Flush any pending typing first
            for (var k in R.typingBuffer) flushTyping(k);

            pushEvent('keypress', {
                key: e.key,
                ctrl: e.ctrlKey,
                shift: e.shiftKey,
                alt: e.altKey,
                meta: e.metaKey,
            });
        }
    }, true);

    // ── URL change detection ────────────────────────────
    setInterval(function() {
        if (location.href !== R.lastUrl) {
            pushEvent('navigate', {
                from: R.lastUrl,
                to: location.href,
            });
            R.lastUrl = location.href;
        }
    }, 300);

    // ── Scroll (throttled) ──────────────────────────────
    var scrollTimer = null;
    var scrollStart = 0;
    window.addEventListener('scroll', function() {
        if (!scrollTimer) scrollStart = window.scrollY;
        if (scrollTimer) clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function() {
            var delta = window.scrollY - scrollStart;
            if (Math.abs(delta) > 100) {
                pushEvent('scroll', {
                    direction: delta > 0 ? 'down' : 'up',
                    pixels: Math.abs(Math.round(delta)),
                });
            }
            scrollTimer = null;
        }, 500);
    }, true);
})();
