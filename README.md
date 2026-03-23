# WebSpec DSL

An English-based domain-specific language for browser testing, built with
PLY (Python Lex-Yacc), BeautifulSoup, and Selenium.

Write tests that read like instructions:
```
navigate to "https://myapp.com/login"
type "admin@test.com" into the input near "Email"
type "secret123" into the input near "Password"
click the button "Sign In"
verify the heading "Dashboard" is visible
```

WebSpec figures out the CSS selectors, XPath, and element resolution
automatically using a smart resolver powered by BeautifulSoup.

See [`OperatorsManual.md`] for a full guide on WebSpec.
---

## Quick Start
```bash
# Install dependencies
pip install ply beautifulsoup4 selenium

# Run a script
python webspec_cli.py my_test.ws --browser chrome

# Run headless
python webspec_cli.py my_test.ws --browser chrome --headless

# Run with HTML report
python webspec_cli.py my_test.ws --browser chrome --report

# Run all tests (unit + integration + .ws scripts)
pytest tests/ -v
```

You need Chrome (or Firefox/Edge) and the matching WebDriver installed
and available on your PATH.

---

## Project Map
```
WebSpec/
│
├── Core Engine
│   ├── webspec_lexer.py          PLY tokenizer - 80+ reserved words
│   ├── webspec_parser.py         PLY LALR(1) parser - 182 grammar rules
│   ├── webspec_ast.py            50+ AST node dataclasses
│   ├── webspec_resolver.py       Smart element finder (BS4 + heuristics)
│   └── webspec_runtime.py        Selenium execution engine
│
├── Tools
│   ├── webspec_cli.py            Command-line test runner
│   ├── webspec_repl.py           Interactive REPL
│   ├── webspec_recorder.py       Browser interaction recorder
│   ├── webspec_transpiler.py     Recorded events → WebSpec script
│   ├── webspec_capture.js        JS event capture (injected into browser)
│   └── webspec_report.py         HTML test report generator
│
├── Documentation
│   └── OPERATORS_MANUAL.md       Full language reference & tutorial
│
├── Tests
│   ├── conftest.py               Pytest plugin - auto-discovers .ws files
│   ├── test_lexer.py             Tokenizer unit tests
│   ├── test_parser.py            Grammar/AST unit tests
│   ├── test_resolver.py          Element resolution unit tests
│   ├── test_runtime.py           Execution engine unit tests
│   ├── test_transpiler.py        Recorder transpiler unit tests
│   ├── test_new_features.py      Import, data-driven, retry, report tests
│   ├── test_integration.py       Full-stack tests against local fixture
│   ├── test_mega.py              Monolithic stress test runner
│   │
│   ├── fixtures/                 Local HTML test fixtures
│   │   ├── test_site.html        Multi-section interactive page
│   │   ├── mega_test.html        Comprehensive feature coverage page
│   │   ├── test_login.ws         Login flow script
│   │   ├── test_search.ws        Search & filter script
│   │   ├── test_table.ws         Table operations script
│   │   ├── test_counter.ws       Counter & loops script
│   │   ├── test_data_table.ws    For-each iteration script
│   │   ├── test_full_flow.ws     Multi-section end-to-end
│   │   └── mega_test.ws          The monolithic 15-phase stress test
│   │
│   └── weather_shopper/          Live site tests (weathershopper.pythonanywhere.com)
│       ├── 01_home.ws            Navigation, title, variables
│       ├── 02_products.ws        Fuzzy matching, ordinals, counting
│       ├── 03_cart_flow.ws       Subroutines, multi-page cart
│       ├── 04_smart_buy.ws       Conditionals, both product paths
│       ├── 05_stress.ws          JS exec, regex, try/catch, raw CSS
│       ├── 06_data_driven.ws     CSV-driven multi-page iteration
│       └── products.csv          Data file for 06_data_driven.ws
│
├── Generated at runtime
│   ├── parser.out                PLY parser debug output (383 states)
│   ├── screenshots/              Captured screenshots
│   └── reports/                  HTML test reports
│
└── pytest.ini                    Test configuration
```

---

## Architecture

The pipeline has four stages. Every WebSpec script flows through
all four in sequence:
```
  .ws script
      │
      ▼
  ┌──────────┐     Tokens      ┌──────────┐     AST       ┌──────────┐
  │  Lexer   │ ──────────────> │  Parser  │ ────────────> │ Runtime  │
  │  (PLY)   │                 │  (LALR)  │               │(Selenium)│
  └──────────┘                 └──────────┘               └────┬─────┘
                                                               │
                                                          ┌────▼─────┐
                                                          │ Resolver │
                                                          │  (BS4)   │
                                                          └──────────┘
```

### Lexer (`webspec_lexer.py`)

Tokenizes English keywords into a stream PLY can parse. Key design
decisions:

- **Case-insensitive keywords**
  - `Click`, `CLICK`, and `click` all
    produce the `CLICK` token.
- **Bare words**
  - Any identifier not in the reserved table becomes
    a `STRING` token, so `click the button Submit` works without
    quoting (though quoting is recommended).
- **Ordinals**
  - `1st`, `2nd`, `3rd`, `42nd` are lexed as `ORDINAL`
    tokens with the integer value extracted.
- **Variables**
  - `$name` and `${name}` both produce `VARIABLE` tokens.
- **Escape sequences**
  - String literals process `\\`, `\"`, `\n`,
    `\t`, `\r` so regex patterns like `"\d+"` work correctly.
- **Comments**
  - Lines starting with `#` are stripped by the lexer.
- **Newlines are significant**
  - They serve as statement separators
    (like Python), not whitespace.

### Parser (`webspec_parser.py`)

An LALR(1) grammar built with PLY/Yacc. The grammar compiles to:

- **182 production rules**
- **383 parser states**
- **0 reduce/reduce conflicts**
- **~50 shift/reduce conflicts** (all resolved correctly by PLY's
  default shift preference)

The shift/reduce conflicts fall into three families:

1. **Selector chain greediness**
   - When the parser sees
   `the button "Submit"`, it could reduce `the button` to an
   `element_ref` or shift `"Submit"` into a `selector_chain`. 
   Shift is correct here, selectors should be greedy.

2. **VARIABLE ambiguity in conditions**
   - `$status` could be an
   `element_ref`, an `expr`, or the start of a `VARIABLE IS ...`
   condition. We added explicit `VARIABLE IS STRING`,
   `VARIABLE IS NUMBER`, `VARIABLE IS VARIABLE`, and
   `VARIABLE IS visibility` rules so PLY's shift preference
   picks the right one.

3. **Boolean operator precedence**
   - `AND` binds tighter than `OR`,
     `NOT` binds tightest. Standard boolean semantics via PLY's
     precedence table.

### Resolver (`webspec_resolver.py`)

The smart element finder. Given an English description like
`the input near "Email"`, it:

1. Grabs `driver.page_source` from Selenium
2. Parses it with BeautifulSoup
3. Finds candidate elements by type (e.g., all `<input>` tags)
4. Applies each selector in the chain as a progressive filter
5. Converts the winning BS4 tag to an absolute XPath
6. Returns the Selenium WebElement via `driver.find_element(By.XPATH, ...)`

Key features:

- **Auto-retry**
  - If resolution fails, the resolver re-fetches
    `page_source`, reparses, and retries for up to 5 seconds
    (configurable). This handles asynchronous page loads without
    explicit waits.

- **Label proximity (`near`)**
  - Five-strategy search: `label[for]` →
    exact text on label-like tags → partial text → direct own-text
    on broader tags → `aria-label`. Walks only 1 ancestor level to
    avoid "everything is nearby" false positives.

- **Fuzzy text matching**
  - Exact match → partial match →
    SequenceMatcher (0.6 threshold). Checks text content, aria-label,
    title, placeholder, value, and alt attributes.

- **Variable interpolation**
  - `${varname}` in selector values is
    resolved at runtime from the variables' dict.

### Runtime (`webspec_runtime.py`)

Walks the AST and dispatches each node to a handler method. The
method naming convention is `_exec_{NodeClassName}`, so the
`Click` AST node calls `_exec_Click`.

Key features:

- **Step timing**
  - Every step records its duration for reporting.
- **Failure recording**
  - Assertion failures are recorded for reporting before being raised.
- **Subroutine storage**
  - `define`/`call` store and retrieve named
    statement blocks.
- **Import deduplication**
  - Imported files are tracked by absolute
    path to prevent double-execution.
- **Data-driven iteration**
  - `using` blocks load CSV/JSON and re-run
    the body with different variables per row.

---

## The Recorder

The recorder is a separate tool that watches you use a browser and
generates WebSpec scripts automatically.

### How It Works

1. **`webspec_capture.js`** is injected into every page. It hooks
   `click`, `input`, `change`, `submit`, `keydown`, and `scroll`
   events. For each event, it captures rich context: the element's
   tag, text, label association, attributes, ordinal position among
   siblings, and element type classification.

2. **`webspec_recorder.py`** runs a Python thread that polls the
   browser every 500ms via `execute_script`, draining the JS event
   queue into a Python list. It re-injects the capture script after
   page navigation's.

3. **`webspec_transpiler.py`** converts the raw event list into
   idiomatic WebSpec. The selector strategy prioritizes readability:

   | Priority | Strategy           | Example                                      |
   |----------|--------------------|----------------------------------------------|
   | 1        | `near "Label"`     | `the input near "Email"`                     |
   | 2        | Visible text       | `the button "Submit"`                        |
   | 3        | Placeholder        | `the input with placeholder "Search..."`     |
   | 4        | aria-label         | `the button "Close dialog"`                  |
   | 5        | `containing`       | `the element containing "Welcome"`           |
   | 6        | Readable ID        | `the element with id "login-form"`           |
   | 7        | Semantic class     | `the element with class "product-card"`      |
   | 8        | data-testid / name | `the button with attr "data-testid" is "go"` |
   | 9        | Ordinal            | `the 3rd button`                             |

   Auto-generated IDs (`ember-123`, `:r0:`, pure numbers) and
   utility CSS classes (`col-md-6`, `d-flex`, `p-3`) are
   automatically skipped.

### Typing Debounce

The JS capture layer will debounce typing with a 800ms timer. When
you type into an input, keystrokes accumulate in a buffer. After
800ms of no typing, the buffer flushes as a single `type "value"`
event. This means fast typing produces one clean `type` statement
instead of dozens of individual keypress events.

### Navigation Re-injection

When the browser navigates to a new page, the injected JS is lost.
The recorder's poll loop detects URL changes and re-injects
`webspec_capture.js` automatically. In interactive mode, you can
also use `:inject` manually.

---

## Test Architecture

### Unit Tests

Each subsystem has isolated unit tests with mocked dependencies:

| File                   | What it tests                                     | Mocking                           |
|------------------------|---------------------------------------------------|-----------------------------------|
| `test_lexer.py`        | Token types, strings, numbers, ordinals, comments | None (pure function)              |
| `test_parser.py`       | AST generation for every grammar rule             | None (pure function)              |
| `test_resolver.py`     | BS4 element matching, near, fuzzy, inside         | Mock Selenium driver, canned HTML |
| `test_runtime.py`      | Action dispatch, assertions, control flow         | Mock driver + mock resolver       |
| `test_transpiler.py`   | Event-to-WebSpec conversion, selector strategy    | None (pure function)              |
| `test_new_features.py` | Import, data-driven, auto-retry, reports          | Mock driver, temp files           |

### Integration Tests

`test_integration.py` runs `.ws` scripts against the local
`test_site.html` fixture with a real headless Chrome. Each test
verifies the runtime extracted the correct variables and hit zero
errors.

### .ws File Discovery

`conftest.py` contains a pytest plugin that auto-discovers `.ws`
files and runs them as test items. The discovery logic:

1. Finds all `.ws` files in the test directories
2. For each file, determines which HTML fixture to use:
   - **Same-stem match:** `mega_test.ws` → `mega_test.html`
   - **Directory default:** Falls back to `test_site.html`
   - **No substitution:** Weather shopper scripts have hardcoded URLs
3. Replaces `BASE_URL` and `BASE_URL_SECONDARY` placeholders
4. Launches a fresh headless Chrome per script
5. Reports pass/fail as a standard pytest item

### The Mega Test

`mega_test.ws` is a monolithic 15-phase script that exercises every
feature in a single run. It tests across two HTML pages
(`mega_test.html` and `test_site.html`) with a mid-test URL
transition. Coverage map:

| Phase | Features tested                                                     |
|-------|---------------------------------------------------------------------|
| 0     | Subroutine definition                                               |
| 1     | Navigation, title, URL, variables, logging                          |
| 2     | Type, clear, select, check, uncheck, radio, search, validation      |
| 3     | Table rows, inside selector, attr selector, modal, delete, activate |
| 4     | Product cards, ordinals, counting, cart state                       |
| 5     | Tabs, counter with repeat, accordion, progress, dynamic content     |
| 6     | If/else, variable comparison, boolean ops, not, try/catch, for-each |
| 7     | Regex matching, raw CSS, variable in selector, chained selectors    |
| 8     | Scroll, keyboard, JS execution, hover, focus                        |
| 9     | Iframe switch, interaction inside frame, switch back                |
| 10    | Navigate to secondary page, go back, go forward, refresh            |
| 11    | JS alert accept, confirm dismiss                                    |
| 12    | String concat, number, all extraction types                         |
| 13    | All assertion operators (is, contains, matches, greater than, etc.) |
| 14    | All wait types                                                      |
| 15    | Screenshot, save source, save cookies                               |

---

## How BASE_URL Works

Scripts that target local HTML fixtures use the `BASE_URL` placeholder
instead of hardcoded `file:///` paths. This gets resolved differently
depending on how you run the script:

| Runner                        | How BASE_URL is resolved                                                        |
|-------------------------------|---------------------------------------------------------------------------------|
| `webspec_cli.py`              | `--base-url` flag, or auto-detects `test_site.html` next to the script          |
| `test_integration.py`         | Explicitly set to `test_site.html` fixture path                                 |
| `test_mega.py`                | Explicitly set to `mega_test.html` with `BASE_URL_SECONDARY` → `test_site.html` |
| `conftest.py` (.ws discovery) | Same-stem HTML match, then directory default                                    |

Weather shopper scripts don't use `BASE_URL`, they have real URLs.

---

## Auto-Retry Behavior

The resolver retries element resolution automatically before
throwing an error. This eliminates most `wait` statements in
scripts.
```
       resolve()
           │
           ▼
  ┌──────────────────┐
  │ Parse page HTML  │◄──── force refresh after failure
  │ Find candidates  │
  │ Apply selectors  │
  └────────┬─────────┘
           │
         found?──── [Yes] ──► return WebElement
           │
          [No]
           │
        timeout?─── [Yes] ──► raise RuntimeError
           │
          [No]
           │
      sleep(0.3s)───────────► retry from top
```

Default: 5 second timeout, 0.3 second interval. Configure via CLI:
```bash
python webspec_cli.py test.ws --retry-timeout 10 --retry-interval 0.5
```

---

## HTML Reports

Reports are self-contained HTML files with:

- Pass/fail summary and total duration
- Step-by-step table with timing and error messages
- All captured variables
- Inline base64-encoded screenshots

Generate with `--report`:
```bash
python webspec_cli.py test.ws --browser chrome --report
python webspec_cli.py test.ws --report --report-path results/my_report.html
```

Reports are generated for both passing and failing runs, so you
always get the full picture.

---

## Data-Driven Testing

The `using` keyword runs a block once per row from a CSV or JSON file.
Column headers (CSV) or object keys (JSON) become `$variables`.
```bash
# users.csv
username,password
alice@test.com,pass123
bob@test.com,pass456
```
```
using "users.csv"
    type $username into the input near "Email"
    type $password into the input near "Password"
    click the button "Sign In"
    take screenshot
end
```

If one row fails, the error is logged and execution continues to
the next row. Special variables `$_row_index` (0-based) and
`$_row_count` are available inside the block.

---

## Known Limitations

### Grammar

- **No nested expressions in assertions**
  - `verify count is 5 + 1`
    won't work. Compute the value first with `set $expected to ...`.
- **Type-sensitive comparisons in conditions**
  - conditions attempt numeric comparison when both sides can be interpreted as numbers;
    otherwise they fall back to string comparison.
- **Single-line statements**
  - No semicolons or multi-statement lines.
    Each statement must be on its own line.

### Resolver

- **Shadow DOM**
  - The BS4 resolver parses `page_source`, which
    doesn't include shadow DOM content. Use `execute` with JS for
    shadow DOM interaction.
- **Very dynamic SPAs**
  - Pages that mutate the DOM continuously
    may cause stale element references between BS4 resolution and
    Selenium interaction. The auto-retry mitigates this, but very
    fast mutations can still cause issues.
- **Canvas/WebGL**
  - No element-level interaction with canvas.
    Use `execute` for canvas operations.

### Recorder

- **Iframes**
  - Events inside iframes are not captured automatically.
    Record the main frame, then add `switch to frame` commands
    manually.
- **Shadow DOM**
  - Same limitation as the resolver; shadow DOM
    events are not captured.
- **Drag and drop**
  - Complex drag sequences may not record cleanly.
    Add `drag` commands manually after recording.

### Platform

- **Windows encoding**
  - All file I/O uses UTF-8 explicitly.
    If you see `UnicodeDecodeError`, ensure your script files are
    saved as UTF-8.
- **chromedriver version**
  - Must match your installed Chrome version.
    Use `chromedriver --version` to check.

---

## Exit Codes

| Code | Meaning                       |
|------|-------------------------------|
| 0    | All steps passed              |
| 1    | One or more assertions failed |
| 2    | Script parse error            |

---

## Contributing

### Running the Test Suite
```bash
# Everything (unit tests + .ws scripts against local fixtures + live site)
pytest tests/ -v

# Fast: unit tests only
pytest tests/test_lexer.py tests/test_parser.py tests/test_resolver.py tests/test_runtime.py tests/test_transpiler.py tests/test_new_features.py -v

# Local fixture .ws scripts only
pytest tests/fixtures/ -v

# Live site scripts only (requires internet)
pytest tests/weather_shopper/ -v

# The mega stress test
pytest tests/test_mega.py -v -s
```

### Adding a New Statement Type

1. Add the reserved word(s) to `webspec_lexer.py`'s `reserved` dict
2. Add an AST node dataclass to `webspec_ast.py`
3. Add grammar rule(s) to `webspec_parser.py`
4. Add `_exec_NodeName` handler to `webspec_runtime.py`
5. Add unit tests to the appropriate test file
6. Add a line to a `.ws` fixture script to integration-test it
7. Delete `parser.out` and `parsetab.py` so PLY regenerates

### Adding a New Selector Kind

1. Add the keyword to `reserved` in `webspec_lexer.py`
2. Add a `p_selector_*` rule in `webspec_parser.py`
3. Add handling in `_apply_one` in `webspec_resolver.py`
4. Add tests to `test_resolver.py`

### Debugging Parse Errors

Run with `--verbose` to see the token stream, or inspect
`parser.out` for the full LALR state machine. The most common
issues:

- A reserved word used as a bare string (quote it)
- Missing `end` on a block construct
- `matching` (selector) vs `matches` (assertion verb)
- `containing` (selector) vs `contains` (assertion verb)

---

## License

MIT