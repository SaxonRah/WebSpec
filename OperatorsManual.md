━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
# ╔══════════════════════════════════════════════════════╗
# ║                                                      ║
# ║              W E B S P E C   D S L                   ║
# ║                                                      ║
# ║          Operator's Manual & Reference               ║
# ║                                                      ║
# ║                  Version 1.0                         ║
# ║                                                      ║
# ╚══════════════════════════════════════════════════════╝
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Table of Contents

    Chapter 1 .... Setting Up
    Chapter 2 .... Your First Script
    Chapter 3 .... Finding Elements (The Smart Resolver)
    Chapter 4 .... Actions
    Chapter 5 .... Assertions & Verification
    Chapter 6 .... Waits & Timing
    Chapter 7 .... Variables & Expressions
    Chapter 8 .... Control Flow
    Chapter 9 .... Subroutines & Imports
    Chapter 10 ... Data-Driven Testing
    Chapter 11 ... The Recorder
    Chapter 12 ... The Interactive REPL
    Chapter 13 ... Reports & CI Integration
    Chapter 14 ... CLI Reference
    Chapter 15 ... Grammar Reference
    Appendix A ... Selector Strategy Guide
    Appendix B ... Troubleshooting


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 1: Setting Up

WebSpec is an English-based testing language. You write scripts
that read like instructions a person would follow, and WebSpec
translates them into Selenium browser automation.

### What You Need

    Python 3.9+
    Google Chrome (or Firefox, or Edge)
    The matching WebDriver (chromedriver, geckodriver, etc.)

### Installation

    pip install ply beautifulsoup4 selenium

### Project Structure

    WebSpec/
    ├── webspec_ast.py          Abstract syntax tree nodes
    ├── webspec_capture.js      JS for browser recorder
    ├── webspec_cli.py          Command-line runner
    ├── webspec_lexer.py        The tokenizer
    ├── webspec_parser.py       The grammar (PLY/YACC)
    ├── webspec_recorder.py     Browser recorder
    ├── webspec_repl.py         Interactive mode
    ├── webspec_report.py       HTML report generator
    ├── webspec_resolver.py     Smart element finder
    ├── webspec_runtime.py      Execution engine
    ├── webspec_transpiler.py   Event-to-script converter
    └── tests/
        ├── test_integration.py
        ├── test_lexer.py
        ├── test_new_features.py
        ├── test_parser.py
        ├── test_resolver.py
        ├── test_runtime.py
        └── test_transpiler.py
        

### Quick Verification

To verify everything is working, create a file called `hello.ws`:

    navigate to "https://example.com"
    verify title contains "Example"
    take screenshot as "hello.png"
    log "WebSpec is working!"

Then run it:

    python webspec_cli.py hello.ws --browser chrome

You should see:

    ✓ PASSED - 4 steps, 0 errors


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 2: Your First Script

A WebSpec script is a plain text file (we use the `.ws` extension
by convention) containing one statement per line. Comments start
with `#`. Blank lines are ignored.

    # my_first_test.ws
    # This script tests a login page.

    navigate to "https://myapp.com/login"

    # Fill in the form
    type "admin@test.com" into the input near "Email"
    type "password123" into the input near "Password"

    # Submit
    click the button "Sign In"

    # Verify we landed on the dashboard
    wait until url contains "/dashboard"
    verify the heading "Dashboard" is visible

    take screenshot as "login_done.png"
    log "Login test passed!"

Let's break down what's happening:

  1. `navigate to` opens a URL in the browser.

  2. `type ... into ...` finds an input field and types text.
     The phrase `near "Email"` tells WebSpec to find the input
     that's associated with a label containing "Email".

  3. `click the button "Sign In"` finds a button whose visible
     text is "Sign In" and clicks it.

  4. `wait until url contains` pauses until the browser's
     address bar matches.

  5. `verify ... is visible` asserts that an element exists
     and is displayed on screen.

  6. `take screenshot` captures the current page.

  7. `log` prints a message to the console.

### Running the Script

    python webspec_cli.py my_first_test.ws --browser chrome

### Headless Mode (No Visible Browser)

    python webspec_cli.py my_first_test.ws --browser chrome --headless


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 3: Finding Elements (The Smart Resolver)

This is the heart of WebSpec. Instead of writing CSS selectors
or XPath expressions, you describe elements in English. WebSpec
uses BeautifulSoup to search the live DOM and find matches.

### Element Types

You can refer to these element types:

    button      <button>, <input type="submit">, [role="button"]
    link        <a>
    input       <input>, <textarea>
    dropdown    <select>
    checkbox    <input type="checkbox">
    radio       <input type="radio">
    image       <img>, <svg>, <picture>
    heading     <h1> through <h6>
    table       <table>
    row         <tr>
    cell        <td>, <th>
    field       <input>, <textarea>, <select>
    form        <form>
    section     <section>, <article>, <aside>
    dialog      <dialog>, [role="dialog"]
    menu        <nav>, [role="menu"]
    item        <li>, [role="menuitem"]
    element     anything (wildcard)

### Basic References

The simplest reference is just a type:

    click the button

This clicks the first button on the page. To be more specific,
add a text selector:

    click the button "Submit"

WebSpec will look for a button whose visible text, aria-label,
title, or value matches "Submit".

### Ordinal Selection

When there are multiple matches, use ordinals:

    click the 1st button "Add"
    click the 2nd button "Add"
    click the 3rd button "Add"

### Selector Chaining

Selectors can be chained to narrow results progressively.
Each selector filters the candidates from the previous one:

    click the button "Save" with class "primary" inside the form "settings"

This finds:
  1. All buttons
  2. Whose text matches "Save"
  3. That have the CSS class "primary"
  4. That are inside a form matching "settings"

### Available Selectors
```
  SELECTOR                              WHAT IT DOES
  ─────────────────────────────────────────────────────
  "text"                                Fuzzy text match
  with class "name"                     CSS class match
  with id "name"                        ID match
  with text "exact"                     Exact text match
  with attr "name" is "value"           Attribute match
  with placeholder "text"               Placeholder match
  with value "text"                     Value attribute
  containing "partial"                  Partial text match
  matching "regex"                      Regex match
  near "label"                          Label proximity
  inside <element_ref>                  DOM containment
  above <element_ref>                   Before in document
  below <element_ref>                   After in document
  after <element_ref>                   After in document
  before <element_ref>                  Before in document
```

### The "near" Selector (Label Proximity)

This is the most powerful selector for form fields. When you
write:

    the input near "Email"

WebSpec uses a multi-strategy search:

  1. First, it looks for `<label for="...">` tags whose text
     contains "Email". If found, it uses the `for` attribute
     to find the exact input.

  2. If no `<label for>` exists, it searches label-like elements
     (`<label>`, `<legend>`, `<dt>`, `<th>`) for exact text match,
     then checks DOM siblings and nearby elements.

  3. Falls back to broader elements (`<span>`, `<p>`, `<div>`)
     checking only their own direct text (not deeply nested
     children) to avoid false matches on container divs.

  4. Finally checks `aria-label` attributes.

This means WebSpec handles all common form patterns:

    <!-- Pattern 1: label with for -->
    <label for="email">Email address</label>
    <input id="email" />

    <!-- Pattern 2: wrapping label -->
    <label>Email <input /></label>

    <!-- Pattern 3: sibling label -->
    <div class="form-group">
      <label>Email</label>
      <input />
    </div>

All three work with: `the input near "Email"`

### Raw Selectors (Escape Hatch)

When the English description isn't enough, you can drop down
to raw CSS or XPath:

    click element "div.container > button.submit:nth-child(2)"
    click element "//div[@class='results']/button[last()]"

WebSpec auto-detects CSS vs XPath based on whether the string
starts with `/` or `(`.

### Variables as Selectors

Selectors accept variables anywhere a string can go:

    set $label to "Email"
    type "test@test.com" into the input near $label

    set $cls to "primary"
    click the button with class $cls

### Fuzzy Matching

Text selectors use fuzzy matching. If no exact match is found,
WebSpec falls back to partial matches, then to SequenceMatcher
with a 0.6 similarity threshold. This means:

    click the button "Submitt"

...will still find `<button>Submit</button>`. The matching
checks visible text, aria-label, title, placeholder, value,
and alt attributes in that order.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 4: Actions

Actions make the browser do things. Every action targets an
element reference (see Chapter 3).

### Clicking

    click the button "Submit"
    double click the element "row"
    right click the image "logo"

### Typing

    type "hello@test.com" into the input near "Email"
    type $username into the field "login"
    type "prefix" + $domain into the input "email"

`type` clears the field first, then types. To add text without
clearing:

    append " additional text" to the input "notes"

To clear a field without typing:

    clear the input near "Password"

### Dropdowns

    select "United States" from the dropdown near "Country"

This tries visible text first, then value attribute, then
case-insensitive match, then substring match. So if the HTML is:

    <option value="us">United States of America</option>

Any of these will work:

    select "United States of America" from the dropdown near "Country"
    select "us" from the dropdown near "Country"
    select "United States" from the dropdown near "Country"

### Checkboxes & Radio Buttons

    check the checkbox near "I agree to the terms"
    uncheck the checkbox near "Subscribe"
    toggle the checkbox "notifications"

`check` only clicks if unchecked. `uncheck` only clicks if
checked. `toggle` always clicks.

### Hovering & Focus

    hover the menu "File"
    focus the input "search"

### Scrolling

    scroll to the button "Submit"
    scroll down 500 pixels
    scroll up 200 pixels

`scroll to` smoothly scrolls an element into view. The pixel
variants scroll the entire page.

### Drag and Drop

    drag the element "card" to the element "target-zone"

### Keyboard

    press key "enter"
    press key "tab"
    press key "a" with "ctrl"
    press key "escape"

Available keys: enter, return, tab, escape, backspace, delete,
space, up, down, left, right, home, end, page_up, page_down,
f1 through f12.

Modifiers: ctrl, shift, alt, meta, command.

### File Upload

    upload "/path/to/file.pdf" to the input with attr "type" is "file"

### Form Submission

    submit the form "registration"

### Raw JavaScript

    execute "document.title = 'New Title'"
    execute "window.scrollTo(0, document.body.scrollHeight)"

Use this for anything the DSL doesn't cover natively.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 5: Assertions & Verification

Assertions check that the page is in the expected state.
If an assertion fails, the script stops with an error.

### Visibility State

    verify the button "Submit" is visible
    verify the dialog "modal" is hidden
    verify the input "email" is enabled
    verify the input "code" is disabled
    verify the checkbox "terms" is checked
    verify the option "premium" is selected
    verify the input "name" is empty
    verify the input "search" is focused

### Text Content

    verify the heading "title" has text "Welcome Back"
    verify the element "status" contains "success"
    verify the element "code" matches "\d{3}"

`has text` checks exact match. `contains` checks substring.
`matches` checks against a regular expression.

### Attributes

    verify the input "email" has attr "type" is "email"
    verify the input "email" has attr "type" contains "mail"
    verify the link "home" has attr "href" starts with "/"
    verify the element "logo" has attr "src" ends with ".png"
    verify the button "go" has class "primary"

### CSS Styles

    verify the element "alert" has style "color" is "red"
    verify the element "box" has style "display" is "none"

### Element Counting

    verify the element with class "product-card" count is 6
    verify the row count greater than 0
    verify the element with class "error" count is 0

### Page-Level Checks

    verify url is "https://example.com/dashboard"
    verify url contains "/dashboard"
    verify title is "Dashboard - MyApp"
    verify title contains "Dashboard"

### Cookies

    verify cookie "session" is "abc123"
    verify cookie "theme" contains "dark"

### File Downloads

    verify downloaded "report.pdf"

### Alerts

    verify alert has text "Are you sure?"
    accept alert
    dismiss alert

### Using Variables in Assertions

All assertion values support variable interpolation:

    set $expected to "Welcome"
    verify the heading contains $expected
    verify title contains $expected


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 6: Waits & Timing

Web pages are asynchronous. Elements appear after API calls,
animations complete, and content loads dynamically. WebSpec
provides explicit waits and has built-in auto-retry.

### Auto-Retry (Smart Waits)

Before you add any wait statements, know that WebSpec's element
resolver automatically retries for 5 seconds (configurable)
when it can't find an element. Each retry reparses the live
DOM. This means many scripts need no wait statements at all.

Configure retry behavior from the CLI:

    python webspec_cli.py test.ws --retry-timeout 10 --retry-interval 0.5

### Explicit Waits

When you need precise timing control:

    wait 2 seconds
    wait 0.5 seconds

### Wait for Element

    wait for the button "Submit"
    wait for the dialog "modal" to be visible
    wait for the input "email" to be enabled

### Wait with Timeout

    wait up to 30 seconds for the button "Submit"

### Wait for Page State

    wait until url contains "/dashboard"
    wait until title contains "Results"

### When to Use Explicit Waits

You generally need waits when:

  1. A page navigation is triggered by JavaScript
     (not a link click) - use `wait until url contains`.

  2. Content loads asynchronously after a button click -
     use `wait for the element`.

  3. An animation needs to complete before you can interact -
     use `wait 1 seconds`.

You generally don't need waits when:

  1. Clicking a link that triggers navigation; the resolver's
     auto-retry handles the fresh page.

  2. An element is already on the page but might take a moment
     to become clickable; auto-retry handles this.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 7: Variables & Expressions

Variables let you capture values from the page and use them
later. Variable names start with `$`.

### Setting Variables

From literal values:

    set $name to "Alice"
    set $count to 42

From page content:

    set $title to text of the heading "main"
    set $href to attr "href" of the link "home"
    set $email to value of the input "email"
    set $items to count of the element with class "item"
    set $page to url
    set $page_title to title

### String Concatenation

    set $greeting to "Hello, " + $name + "!"
    log "Found " + $count + " items at " + $page

### Using Variables

Variables work everywhere strings are accepted:

    navigate to $url
    type $password into the input near "Password"
    verify the heading contains $expected_title
    click the button $button_label
    click the element with class $dynamic_class

### Variable Interpolation in Selectors

When you use a variable inside a selector, WebSpec wraps it
as `${name}` internally and resolves it at runtime:

    set $label to "Email"
    type "test@test.com" into the input near $label

### Special Variables

Inside a `using` data block (Chapter 10):

    $_row_index     Current row number (0-based)
    $_row_count     Total number of rows

Inside a `try/catch` block:

    $_error         The error message from the failed block


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 8: Control Flow

### Conditional Execution

    if the button "Submit" is visible then
        click the button "Submit"
    end

    if $status is "inactive" then
        click the button "Activate"
    else
        log "Already active"
    end

### Conditions

Conditions can check element state:

    if the dialog "modal" is visible then ...
    if the input "email" is enabled then ...
    if $element is hidden then ...

Or compare values:

    if $count is "5" then ...
    if $name equals "Alice" then ...
    if $price greater than "100" then ...
    if $stock less than "10" then ...

Or check the URL:

    if url contains "/admin" then ...

### Boolean Operators

    if the button "OK" is visible and the input "name" is enabled then
        click the button "OK"
    end

    if $role is "admin" or $role is "editor" then
        click the link "Settings"
    end

    if not the dialog "error" is visible then
        log "No errors"
    end

Parentheses control grouping:

    if ($role is "admin" or $role is "editor") and url contains "/dashboard" then
        click the link "Admin Panel"
    end

### Loops

Repeat a fixed number of times:

    repeat 5 times
        click the button "Next"
        wait 1 seconds
    end

Repeat while a condition holds:

    repeat while the button "Load More" is visible
        click the button "Load More"
        wait 2 seconds
    end

Iterate over elements:

    for each the row inside the table as $row
        set $name to text of the cell with class "name" inside $row
        log "Processing: " + $name
    end

The `do` keyword is optional:

    for each the item as $item do
        click $item
    end

### Error Handling

    try
        click the button "Delete"
        verify the dialog "confirm" is visible
    on error
        log "Delete button not found: " + $_error
        take screenshot as "error_state.png"
    end

The `$_error` variable contains the error message from whatever
failed in the `try` block.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 9: Subroutines & Imports

### Defining Subroutines

Group reusable sequences with `define`:

    define "login" as
        type "admin@test.com" into the input near "Email"
        type "secret123" into the input near "Password"
        click the button "Sign In"
        wait until url contains "/dashboard"
    end

    define "logout" as
        click the link "Sign Out"
        wait until url contains "/login"
    end

### Calling Subroutines

    call "login"
    verify the heading "Dashboard" is visible
    call "logout"

Subroutines share the same variable scope as the main script,
so variables set inside a subroutine are visible outside:

    define "get_username" as
        set $username to text of the element with class "username"
    end

    call "get_username"
    log "Logged in as: " + $username

### Importing Scripts

Split your tests across files with `import`:

    # common/setup.ws
    define "login" as
        navigate to "https://myapp.com/login"
        type "admin@test.com" into the input near "Email"
        type "secret" into the input near "Password"
        click the button "Sign In"
    end

    # test_dashboard.ws
    import "common/setup.ws"
    call "login"
    verify the heading "Dashboard" is visible

Imports are idempotent. Importing the same file twice has no
effect the second time. The imported script executes immediately,
so any `define` statements register subroutines, and any
bare statements run in sequence.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 10: Data-Driven Testing

Run the same test steps against multiple sets of data using
`using` blocks with CSV or JSON files.

### CSV Data

Create a data file:

    # users.csv
    username,password,expected_name
    alice@test.com,pass123,Alice Johnson
    bob@test.com,pass456,Bob Smith

Reference it in your script:

    using "users.csv"
        navigate to "https://myapp.com/login"
        type $username into the input near "Email"
        type $password into the input near "Password"
        click the button "Sign In"
        verify the element with class "user-name" contains $expected_name
        log "Verified user: " + $username
        take screenshot
        navigate to "https://myapp.com/logout"
    end

Each column header becomes a variable name. The block runs once
per row. In this case, twice.

### JSON Data

    [
        {"url": "https://myapp.com/page1", "title": "Page One"},
        {"url": "https://myapp.com/page2", "title": "Page Two"}
    ]

Used the same way:

    using "pages.json"
        navigate to $url
        verify title contains $title
        take screenshot
    end

### Special Variables

Inside a `using` block:

    $_row_index    The current iteration (0, 1, 2, ...)
    $_row_count    Total number of data rows

    using "data.csv"
        log "Row " + $_row_index + " of " + $_row_count
    end

### Error Handling in Data Loops

If one iteration fails, WebSpec logs the error and continues
to the next row. This means a single bad data row doesn't kill
the entire test run.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 11: The Recorder

The recorder watches you interact with a browser and generates
a WebSpec script automatically. It's the fastest way to create
a new test.

### How It Works

    ┌─────────────┐    JS events    ┌─────────────┐
    │   Browser   │ ──────────────> │  Collector   │
    │  (you click │                 │  (Python     │
    │   and type) │                 │   polls)     │
    └─────────────┘                 └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │ Transpiler   │
                                    │ (events to   │
                                    │  WebSpec)    │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │  output.ws   │
                                    └─────────────┘

A JavaScript capture layer is injected into the page. It records
clicks, typing, dropdown changes, checkbox toggles, scrolls,
keyboard shortcuts, and navigation. A Python thread polls for
events and the transpiler converts them into idiomatic WebSpec.

### Quick Record (Non-Interactive)

    python webspec_recorder.py \
        --url "https://myapp.com" \
        --output my_test.ws

A browser opens. Do your testing flow; click buttons, fill
forms, navigate pages. When you're done, press Ctrl+C. The
script is saved.

### Interactive Record

    python webspec_recorder.py \
        --url "https://myapp.com"

This opens a command prompt alongside the browser:

    recorder> :start
    (interact with the browser...)
    recorder> :preview
    (see the generated script so far)
    recorder> :save my_test.ws
    recorder> :quit

### Recorder Commands

    :start          Begin capturing events
    :stop           Stop capturing
    :pause          Pause without losing events
    :resume         Resume capturing
    :preview        Show the generated WebSpec script
    :save <file>    Save the script to a file
    :events         Show event count and types
    :clear          Discard all captured events
    :inject         Re-inject capture after navigation
    :quit           Exit

### Smart Selector Generation

The transpiler doesn't just dump CSS selectors. It generates
the most human-readable reference possible using this priority:

    PRIORITY   STRATEGY              EXAMPLE OUTPUT
    ────────────────────────────────────────────────────
    1st        near "Label"          the input near "Email"
    2nd        "Visible text"        the button "Submit"
    3rd        with placeholder      the input with placeholder "Search..."
    4th        aria-label            the button "Close dialog"
    5th        containing "text"     the element containing "Welcome"
    6th        with id "readable"    the element with id "login-form"
    7th        with class "semantic" the element with class "product-card"
    8th        with attr             the button with attr "data-testid" is "go"
    9th        ordinal fallback      the 3rd button

Auto-generated IDs (like `ember-123`, `:r0:`) are automatically
skipped. Utility CSS classes (like `col-md-6`, `d-flex`) are
skipped in favor of semantic classes (like `product-card`).

### Replaying a Recording

    python webspec_cli.py my_test.ws --browser chrome

### Tips for Good Recordings

  1. Go slowly. The capture will debounce typing (800ms) so fast
     typing is grouped correctly, but clicking too fast can
     miss events.

  2. Use the interactive mode and `:preview` frequently to
     check what's being captured.

  3. After recording, edit the script to add assertions.
     The recorder captures actions but not verifications;
     those represent your test intent, which only you know.

  4. If you navigate to a new page and the recorder stops
     capturing, use `:inject` to re-inject the capture script.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 12: The Interactive REPL

The REPL lets you type WebSpec commands one at a time against
a live browser. It's invaluable for exploring a page, debugging
selectors, and building scripts incrementally.

### Starting the REPL

    python webspec_repl.py --browser chrome
    python webspec_repl.py --browser chrome --url "https://myapp.com"

### Usage

    webspec> navigate to "https://weathershopper.pythonanywhere.com/"
      ✓ OK (1 total steps)

    webspec> verify title is "Current Temperature"
      ✓ OK (2 total steps)

    webspec> set $temp to text of the element with id "temperature"
      ✓ OK (3 total steps)

    webspec> :vars
      $temp = 23 °C

    webspec> click the link "Buy moisturizers"
      ✓ OK (4 total steps)

    webspec> set $count to count of the button "Add"
      ✓ OK (5 total steps)

    webspec> :vars
      $temp = 23 °C
      $count = 6

    webspec> :screenshot
      Saved: repl_screenshot_5.png

### REPL Commands

    :help          Show help
    :vars          Show all variables and their values
    :url           Show current browser URL
    :title         Show current page title
    :screenshot    Capture the screen
    :source        Save page HTML to repl_source.html
    :clear         Clear all variables
    :run <file>    Run an entire .ws script file
    :history       Show command history
    :quit          Close browser and exit

### Multi-Line Input

Block constructs are auto-detected. Type `if`, `repeat`, `for`,
`try`, or `define` and the REPL prompts for continuation:

    webspec> if the button "OK" is visible then
         ... click the button "OK"
         ... end
      ✓ OK (6 total steps)

You can also use backslash for line continuation:

    webspec> type "a very long string that \
         ... continues here" into the input "name"
      ✓ OK (7 total steps)


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 13: Reports & CI Integration

### HTML Reports

Add `--report` to any CLI run to generate a self-contained
HTML report:

    python webspec_cli.py test.ws --browser chrome --report

The report includes:

    - Pass/fail summary with total duration
    - Step-by-step table with timing per step
    - Error messages for failed steps
    - All captured variables
    - Inline screenshots (base64 encoded)

Specify a custom output path:

    python webspec_cli.py test.ws --report --report-path results/my_report.html

### CI/CD Integration

WebSpec returns standard exit codes:

    0    All steps passed
    1    One or more assertions failed
    2    Script parse error

Example GitHub Actions workflow:

    - name: Run WebSpec tests
      run: |
        python webspec_cli.py tests/login.ws \
          --browser chrome --headless --report
      continue-on-error: true

    - name: Upload report
      uses: actions/upload-artifact@v3
      with:
        name: test-report
        path: reports/

### Running Multiple Scripts

Use a shell loop or a wrapper script:

    for f in tests/weather_shopper/*.ws; do
        python webspec_cli.py "$f" --browser chrome \
            --headless --report || true
    done

### CLI Variables

Inject values at runtime without editing scripts:

    python webspec_cli.py test.ws \
        --var "username=admin@test.com" \
        --var "password=secret123"

Inside the script, these are available as `$username` and
`$password`.


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 14: CLI Reference

### webspec_cli.py

    python webspec_cli.py <script.ws> [options]

    OPTION                  DEFAULT     DESCRIPTION
    ──────────────────────────────────────────────────
    --browser <name>        chrome      chrome, firefox, edge
    --headless                          Run without visible browser
    --timeout <sec>         10          Default wait timeout
    --retry-timeout <sec>   5           Auto-retry duration
    --retry-interval <sec>  0.3         Time between retries
    --base-url <url>                    Replace BASE_URL in script
    --var NAME=VALUE                    Set a variable (repeatable)
    --report                            Generate HTML report
    --report-path <path>                Custom report output path
    -v, --verbose                       Debug-level logging

### webspec_repl.py

    python webspec_repl.py [options]

    --browser <name>        chrome
    --headless
    --url <url>                         Navigate on startup

### webspec_recorder.py

    python webspec_recorder.py [options]

    --url <url>             (required)  Starting URL
    --output, -o <file>                 Output file (non-interactive)
    --browser <name>        chrome
    --poll-interval <sec>   0.5         Event polling frequency


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Chapter 15: Grammar Reference

This is the formal grammar of the WebSpec DSL expressed in BNF.
The grammar compiles to an LALR(1) parser with 182 rules and
383 states, with zero reduce/reduce conflicts.

### Program Structure

    program         → newlines? statement_list newlines?
    statement_list  → statement (NEWLINE statement)*

### Statements

    statement → nav_stmt | action_stmt | assertion_stmt
              | wait_stmt | var_stmt | control_stmt
              | log_stmt | screenshot_stmt | alert_stmt
              | frame_stmt | window_stmt | extract_stmt
              | import_stmt

### Navigation

    nav_stmt → NAVIGATE TO expr
             | GO BACK
             | GO FORWARD
             | REFRESH
             | SWITCH TO TAB NUMBER

### Element References

    element_ref → THE elem_type selector_chain?
                | THE ORDINAL elem_type selector_chain?
                | ELEMENT STRING
                | VARIABLE

    selector_chain → selector+

    selector → text_value
             | WITH CLASS text_value
             | WITH ID text_value
             | WITH TEXT text_value
             | WITH ATTR text_value IS text_value
             | WITH PLACEHOLDER text_value
             | WITH VALUE text_value
             | CONTAINING text_value
             | MATCHING text_value
             | NEAR text_value
             | INSIDE element_ref
             | ABOVE element_ref
             | BELOW element_ref
             | AFTER element_ref
             | BEFORE element_ref

    text_value → STRING | VARIABLE

### Actions

    action_stmt → CLICK element_ref
                | DOUBLE CLICK element_ref
                | RIGHT CLICK element_ref
                | TYPE expr INTO element_ref
                | APPEND expr TO element_ref
                | CLEAR element_ref
                | SELECT STRING FROM element_ref
                | CHECK element_ref
                | UNCHECK element_ref
                | TOGGLE element_ref
                | HOVER element_ref
                | FOCUS element_ref
                | SCROLL TO element_ref
                | SCROLL DOWN NUMBER PIXELS
                | SCROLL UP NUMBER PIXELS
                | DRAG element_ref TO element_ref
                | PRESS KEY STRING (WITH STRING)?
                | UPLOAD STRING TO element_ref
                | SUBMIT element_ref
                | EXECUTE STRING

### Assertions

    assertion_stmt → VERIFY element_ref IS visibility
                   | VERIFY element_ref HAS TEXT (STRING|VARIABLE)
                   | VERIFY element_ref CONTAINS (STRING|VARIABLE)
                   | VERIFY element_ref MATCHES (STRING|VARIABLE)
                   | VERIFY element_ref HAS ATTR STRING eq_op STRING
                   | VERIFY element_ref HAS CLASS STRING
                   | VERIFY element_ref HAS STYLE STRING eq_op STRING
                   | VERIFY element_ref COUNT comparator NUMBER
                   | VERIFY URL eq_op (STRING|VARIABLE)
                   | VERIFY TITLE eq_op (STRING|VARIABLE)
                   | VERIFY COOKIE STRING eq_op STRING
                   | VERIFY DOWNLOADED STRING

    visibility → VISIBLE | HIDDEN | ENABLED | DISABLED
               | SELECTED | CHECKED | EMPTY | FOCUSED

    eq_op → IS | EQUALS | CONTAINS | CONTAINING
          | MATCHES | STARTS WITH | ENDS WITH

    comparator → IS | EQUALS | GREATER THAN | LESS THAN

### Waits

    wait_stmt → WAIT NUMBER SECONDS
              | WAIT FOR element_ref (TO BE visibility)?
              | WAIT UP TO NUMBER SECONDS FOR element_ref
              | WAIT UNTIL URL CONTAINS STRING
              | WAIT UNTIL TITLE CONTAINS STRING

### Variables

    var_stmt → SET VARIABLE TO expr
             | SET VARIABLE TO TEXT OF element_ref
             | SET VARIABLE TO ATTR STRING OF element_ref
             | SET VARIABLE TO VALUE OF element_ref
             | SET VARIABLE TO COUNT OF element_ref
             | SET VARIABLE TO URL
             | SET VARIABLE TO TITLE

    expr → STRING | NUMBER | VARIABLE
         | expr PLUS expr
         | LPAREN expr RPAREN

### Control Flow

    control_stmt → IF condition THEN NL statement_list (ELSE NL statement_list)? END
                 | REPEAT NUMBER TIMES NL statement_list END
                 | REPEAT WHILE condition NL statement_list END
                 | FOR EACH element_ref AS VARIABLE DO? NL statement_list END
                 | TRY NL statement_list ON ERROR NL statement_list END
                 | DEFINE STRING AS NL statement_list END
                 | CALL STRING
                 | USING STRING NL statement_list END

    condition → element_ref IS visibility
              | expr comparator expr
              | VARIABLE IS (visibility|STRING|NUMBER|VARIABLE)
              | VARIABLE EQUALS (STRING|NUMBER|VARIABLE)
              | VARIABLE (GREATER|LESS) THAN (STRING|NUMBER|VARIABLE)
              | URL CONTAINS STRING
              | NOT condition
              | condition AND condition
              | condition OR condition
              | LPAREN condition RPAREN

### Miscellaneous

    log_stmt        → LOG expr
    screenshot_stmt → TAKE SCREENSHOT (AS STRING)?
    alert_stmt      → ACCEPT ALERT | DISMISS ALERT
                    | VERIFY ALERT HAS TEXT STRING
    frame_stmt      → SWITCH TO FRAME (element_ref|STRING)
                    | SWITCH TO DEFAULT FRAME
    window_stmt     → SWITCH TO WINDOW STRING
                    | OPEN NEW WINDOW | CLOSE WINDOW
    extract_stmt    → SAVE SOURCE AS STRING
                    | SAVE COOKIES AS STRING
    import_stmt     → IMPORT STRING


-━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Appendix A: Selector Strategy Guide

When multiple strategies could match an element, which should
you use? Here's the decision tree:

    Is there a <label> with "for" attribute?
    └── YES → use `near "Label Text"`
    └── NO
        Does the element have visible text?
        └── YES, short (< 40 chars) → use `"text"`
        └── YES, long → use `containing "partial"`
        └── NO
            Does it have a placeholder?
            └── YES → use `with placeholder "text"`
            └── NO
                Does it have a readable id?
                └── YES → use `with id "the-id"`
                └── NO
                    Does it have a semantic class?
                    └── YES → use `with class "name"`
                    └── NO
                        Use `with attr "name" is "value"`
                        or `element "raw-css-selector"`

### Examples from Real Sites

    ELEMENT                         BEST SELECTOR
    ──────────────────────────────────────────────────
    <button>Sign In</button>        the button "Sign In"
    <input> next to "Email" label   the input near "Email"
    <input placeholder="Search">    the input with placeholder "Search"
    <select> next to "Country"      the dropdown near "Country"
    <a href="/about">About Us</a>   the link "About Us"
    <div class="product-card">      the element with class "product-card"
    <button data-testid="submit">   the button with attr "data-testid" is "submit"
    3rd "Add" button on page        the 3rd button "Add"
    Button inside a dialog          the button "OK" inside the dialog "Confirm"


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


## Appendix B: Troubleshooting

### "No element found"

The resolver couldn't find a matching element after retrying.

  - Check that the element is actually on the page (use the
    REPL: `:source` to save and inspect the HTML).
  - Try a less specific selector. `the button` finds any
    button; add specificity from there.
  - The page might not have finished loading. Add a
    `wait 2 seconds` before the failing line.
  - Use the `--verbose` flag to see resolver debug output.

### "Unexpected TOKEN at line N"

A parse error. The script has a syntax problem.

  - Check for unmatched `end` keywords.
  - Check for reserved words used as unquoted strings.
    - For example, `type` is a keyword; if your button text
      is "Type", use `the button "Type"` (quoted).
  - Check that strings are properly quoted. 
    - Both single and
      double quotes work: `"hello"` or `'hello'`.

### "Title: 'X' does not is 'Y'"

Title or URL assertions are case-sensitive and exact (when
using `is`). Use `contains` for partial matching:

    # Too strict:
    verify title is "Products"

    # Better:
    verify title contains "Products"

### Recorder Not Capturing Events

  - After navigating to a new page, the JS capture layer
    needs to be re-injected. Use `:inject` in interactive
    mode, or the recorder does this automatically in
    non-interactive mode.
  - Some events on dynamically loaded content (iframes,
    shadow DOM) may not be captured. Use the REPL to
    write those steps manually.

### Element Found But Click Fails

The resolver found the element in the HTML but Selenium
couldn't interact with it.

  - The element might be obscured by another element
    (a modal overlay, a floating header). Try:
    `scroll to the element "target"` first.
  - The element might be outside the viewport. The auto-retry
    will keep trying, but `scroll to` helps.
  - Try `execute "arguments[0].click()"` as a workaround
    for stubborn elements (this bypasses Selenium's
    visibility check).

### Windows: Unicode Encoding Error

If you see `UnicodeDecodeError: 'charmap'`, your script
contains non-ASCII characters and Windows defaulted to
cp1252. The CLI reads files as UTF-8 by default, so ensure
your text editor saves as UTF-8.

### Stale Element Reference

This happens when the page changes between finding and
clicking an element. The auto-retry mechanism handles most
cases by reparsing the DOM on each attempt. If it persists,
add a short wait before the action.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


    WebSpec DSL v1.0
    Built with PLY, BeautifulSoup, and Selenium

    Happy testing!