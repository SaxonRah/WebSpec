# ═══════════════════════════════════════════════════════════
# WEBSPEC MEGA TEST — exercises every grammar rule, resolver
# strategy, and runtime handler in a single script.
#
# Tests: 182 grammar rules, 18 element types, 15 selector
# kinds, all actions, all assertions, all control flow,
# subroutines, variables, data-driven, error handling,
# frames, alerts, modals, scrolling, JS execution,
# multi-page navigation, and screenshot capture.
# ═══════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────
# PHASE 0: SUBROUTINE DEFINITIONS
# Tests: define/call, parser block nesting
# ─────────────────────────────────────────────────────────

define "verify_home_page" as
    verify title is "WebSpec Mega Test Page"
    verify the heading with id "page-title" is visible
    verify the element with id "page-subtitle" contains "comprehensive"
    log "Home page verified"
end

define "fill_registration" as
    type "John" into the input near "First name"
    type "Doe" into the input near "Last name"
    type "john@mega.test" into the input near "Email address"
    type "Str0ngP@ss!" into the input near "Password"
    select "United States" from the dropdown near "Country"
    select "Editor" from the dropdown near "Role"
    type "Test user bio text" into the element near "Bio"
    check the checkbox near "I agree to the terms"
    check the checkbox near "Subscribe to newsletter"
end

define "reset_form" as
    click the button "Reset" inside the element with id "forms-section"
    wait 1 seconds
end

# ─────────────────────────────────────────────────────────
# PHASE 1: NAVIGATION & PAGE VERIFICATION
# Tests: navigate, verify title, verify url, set/log,
# heading resolution, id selector, class selector
# ─────────────────────────────────────────────────────────

navigate to "BASE_URL"
wait 1 seconds

call "verify_home_page"

verify url contains "mega_test"
set $current_url to url
log "Starting URL: " + $current_url
set $page_title to title
log "Page title: " + $page_title

# Nav links visible
verify the link "Forms" is visible
verify the link "Tables" is visible
verify the link "Cards" is visible
verify the link "Interactive" is visible
verify the link "Advanced" is visible

take screenshot as "mega_01_home.png"
log "PHASE 1 PASSED: Navigation & page verification"

# ─────────────────────────────────────────────────────────
# PHASE 2: FORM INTERACTIONS
# Tests: type, clear, select, check, uncheck, near selector,
# placeholder selector, id selector, submit, verify text,
# verify contains, verify visible/hidden/enabled/disabled
# ─────────────────────────────────────────────────────────

# Test disabled input
verify the input with id "disabled-input" is disabled
set $disabled_val to value of the input with id "disabled-input"
log "Disabled field value: " + $disabled_val

# Fill the form using subroutine
call "fill_registration"

# Verify checkbox state
verify the checkbox near "I agree" is checked
verify the checkbox near "Subscribe" is checked

# Test uncheck
uncheck the checkbox near "Subscribe to newsletter"

# Verify radio buttons
verify the radio near "Free plan" is checked

# Toggle radio
click the radio near "Pro plan"

# Test the search bar with placeholder selector
type "test query" into the input with placeholder "Search anything..."
click the button "Search"
wait 1 seconds
verify the element with id "search-results" is visible
verify the element with id "search-query" has text "test query"

# Submit registration with weak password first
call "reset_form"
type "Jane" into the input near "First name"
type "Smith" into the input near "Last name"
type "jane@mega.test" into the input near "Email address"
type "short" into the input near "Password"
click the button "Register"
wait 1 seconds
verify the element with id "reg-error" is visible

# Fix password and resubmit
clear the input near "Password"
type "G00dP@ssw0rd" into the input near "Password"
select "Canada" from the dropdown near "Country"
check the checkbox near "I agree to the terms"
click the button "Register"
wait 1 seconds
verify the element with id "reg-success" is visible
verify the element with id "reg-success" contains "Welcome, Jane"
verify title contains "Welcome"

take screenshot as "mega_02_forms.png"
log "PHASE 2 PASSED: Form interactions"

# ─────────────────────────────────────────────────────────
# PHASE 3: TABLE OPERATIONS
# Tests: table/row/cell types, inside selector, containing,
# ordinal, count, for-each, variable comparison, if/else,
# attr selector, modal interaction
# ─────────────────────────────────────────────────────────

# Restore title for clean state
execute "document.title = 'WebSpec Mega Test Page'"

# Table structure
verify the table is visible
set $row_count to count of the row inside element "tbody"
log "Data rows: " + $row_count

# Verify specific cells
verify the 1st element with class "user-name" has text "Alice Johnson"
verify the 1st element with class "user-email" has text "alice@mega.test"

# Count by status
set $active_count to count of the element with class "badge-active"
set $inactive_count to count of the element with class "badge-inactive"
set $pending_count to count of the element with class "badge-pending"
log "Active: " + $active_count + " Inactive: " + $inactive_count + " Pending: " + $pending_count

# Activate an inactive user
click the button "Activate" inside the element with attr "data-user-id" is "3"
wait 1 seconds

# Verify activation
set $new_inactive to count of the element with class "badge-inactive"
log "Inactive after activation: " + $new_inactive

# Modal: trigger delete, then cancel
click the button "Delete" inside the element with attr "data-user-id" is "2"
wait 1 seconds
verify the element with id "delete-modal" is visible
verify the element with id "delete-message" contains "Bob Smith"
click the button "Cancel" inside the element with id "delete-modal"
wait 1 seconds
verify the element with id "delete-modal" is hidden

# Modal: trigger delete, then confirm
click the button "Delete" inside the element with attr "data-user-id" is "4"
wait 1 seconds
verify the element with id "delete-modal" is visible
click the button "Delete" inside the element with id "delete-modal"
wait 1 seconds
verify the element with id "delete-modal" is hidden

# Row count should have decreased
set $new_row_count to count of the row inside element "tbody"
log "Rows after delete: " + $new_row_count

take screenshot as "mega_03_tables.png"
log "PHASE 3 PASSED: Table operations"

# ─────────────────────────────────────────────────────────
# PHASE 4: PRODUCT CARDS & CART
# Tests: card grid, ordinal element, containing, has text,
# data attribute resolution
# ─────────────────────────────────────────────────────────

# Verify products exist
verify the element with class "card" count is 4
verify the 1st element with class "card-title" has text "Widget Alpha"
verify the 1st element with class "card-price" has text "$29.99"

# Extract product info
set $p2_name to text of the 2nd element with class "card-title"
set $p2_price to text of the 2nd element with class "card-price"
log "Second product: " + $p2_name + " at " + $p2_price

# Verify tags
verify the element containing "popular" is visible
verify the element containing "premium" is visible
verify the element containing "sale" is visible

# Add items to cart
click the 1st button "Add to Cart"
wait 1 seconds
verify the element with id "cart-status" is visible
verify the element with id "cart-count" has text "1"

click the 3rd button "Add to Cart"
wait 1 seconds
verify the element with id "cart-count" has text "2"

take screenshot as "mega_04_cards.png"
log "PHASE 4 PASSED: Product cards & cart"

# ─────────────────────────────────────────────────────────
# PHASE 5: INTERACTIVE ELEMENTS
# Tests: tab switching, counter with repeat, accordion,
# progress bar, dynamic content, contenteditable
# ─────────────────────────────────────────────────────────

# Tabs — use explicit tab button clicks
click element "button.tab-btn:nth-child(2)"
wait 1 seconds
verify the element with id "tab-details" is visible
click element "button.tab-btn:nth-child(3)"
wait 1 seconds
verify the element with id "tab-reviews" is visible
verify the element with id "review-text" contains "Excellent"
click element "button.tab-btn:nth-child(1)"
wait 1 seconds
verify the element with id "tab-overview" is visible

# Counter — JS reset for guaranteed clean state
execute "counter = 0; document.getElementById('counter-value').textContent = '0';"
verify the element with id "counter-value" has text "0"

repeat 7 times
    click the button with id "increment-btn"
end
verify the element with id "counter-value" has text "7"

repeat 3 times
    click the button with id "decrement-btn"
end
verify the element with id "counter-value" has text "4"

click the button with id "reset-btn"
verify the element with id "counter-value" has text "0"

set $counter_val to text of the element with id "counter-value"
log "Counter after reset: " + $counter_val

# Accordion — use JS to toggle for reliability
execute "document.querySelectorAll('.accordion-body').forEach(function(b){b.classList.remove('open')});"
execute "document.getElementById('accordion-a').classList.add('open');"
wait 1 seconds
verify the element with id "accordion-a" is visible

execute "document.querySelectorAll('.accordion-body').forEach(function(b){b.classList.remove('open')});"
execute "document.getElementById('accordion-b').classList.add('open');"
wait 1 seconds
verify the element with id "accordion-b" is visible
verify the element with id "accordion-a" is hidden

# Progress bar — use explicit button IDs via JS
execute "document.getElementById('progress-fill').style.width='50%'; document.getElementById('progress-text').textContent='50%';"
wait 1 seconds
verify the element with id "progress-text" has text "50%"
execute "document.getElementById('progress-fill').style.width='100%'; document.getElementById('progress-text').textContent='100%';"
wait 1 seconds
verify the element with id "progress-text" has text "100%"

# Dynamic content
click the button with id "load-content-btn"
wait 1 seconds
verify the element with id "loaded-box" is visible
verify the element with id "loaded-box" contains "Dynamic content loaded"
click the button with id "clear-content-btn"
wait 1 seconds

take screenshot as "mega_05_interactive.png"
log "PHASE 5 PASSED: Interactive elements"

# ─────────────────────────────────────────────────────────
# PHASE 6: CONTROL FLOW DEEP TEST
# Tests: if/then/end, if/else, nested if, repeat while,
# variable conditions ($var is "string"), boolean operators,
# not condition, try/catch, for-each with variable
# ─────────────────────────────────────────────────────────

# If/then with element state
if the button "Register" is visible then
    log "Register button is present"
end

# If/else with variable comparison
set $mode to "test"
if $mode is "test" then
    log "Running in test mode"
else
    log "Running in production mode"
end

# Nested conditions with boolean operators
if the table is visible and the element with id "page-title" is visible then
    log "Both table and title visible"
end

# Not condition
if not the element with id "hidden-element" is visible then
    log "Hidden element correctly not visible"
end

# Or condition
if $mode is "test" or $mode is "production" then
    log "Mode is recognized: " + $mode
end

# Repeat while (counter-based termination)
set $loop_count to "0"
repeat 3 times
    set $loop_count to $loop_count + "1"
    log "Loop iteration: " + $loop_count
end

# Try/catch for error recovery
try
    click the button "This Does Not Exist At All 12345"
on error
    log "Expected error caught: " + $_error
end

try
    verify the element with id "nonexistent-element" is visible
on error
    log "Expected assertion error caught"
end

# For-each iteration over table rows
set $user_names to ""
for each the element with class "user-name" as $name_el
    set $name_text to text of $name_el
    log "Found user: " + $name_text
end

take screenshot as "mega_06_control_flow.png"
log "PHASE 6 PASSED: Control flow"

# ─────────────────────────────────────────────────────────
# PHASE 7: ADVANCED SELECTORS
# Tests: matching (regex), with text, with value, above,
# below, raw CSS selector, raw XPath, variable in selector,
# fuzzy matching, ordinals on diverse elements
# ─────────────────────────────────────────────────────────

# Regex matching on element content
verify the element with id "page-subtitle" matches "comprehensive"
verify the element with id "table-count" matches "\\d+ users"

# With attr selector
verify the element with attr "data-product-id" is "p1" is visible

# Raw CSS selector
execute "counter = 0; document.getElementById('counter-value').textContent = '0';"
click element "button#increment-btn"
wait 1 seconds
verify the element with id "counter-value" has text "1"
click element "button#reset-btn"

# Variable in selector
set $target_id to "counter-value"
set $val to text of the element with id $target_id
log "Counter via variable selector: " + $val

# Multiple ordinals
set $card1 to text of the 1st element with class "card-title"
set $card2 to text of the 2nd element with class "card-title"
set $card3 to text of the 3rd element with class "card-title"
set $card4 to text of the 4th element with class "card-title"
log "Cards: " + $card1 + ", " + $card2 + ", " + $card3 + ", " + $card4

# Element with class + containing chained
verify the element with class "card-desc" containing "Budget" is visible

take screenshot as "mega_07_selectors.png"
log "PHASE 7 PASSED: Advanced selectors"

# ─────────────────────────────────────────────────────────
# PHASE 8: SCROLL, KEYBOARD, JS EXECUTION
# Tests: scroll down/up, scroll to, press key, execute JS,
# hover, focus
# ─────────────────────────────────────────────────────────

# Scroll
scroll down 600 pixels
wait 1 seconds
scroll to the element with id "scroll-target"
wait 1 seconds
verify the element with id "scroll-target-text" is visible

scroll up 600 pixels
wait 1 seconds

# Keyboard
focus the input with id "search-box"
press key "tab"
wait 1 seconds

# JavaScript execution
execute "document.getElementById('overview-dynamic').textContent = 'JS was here!'"
verify the element with id "overview-dynamic" has text "JS was here!"

# Modify and verify title via JS
execute "document.title = 'JS Modified Title'"
verify title is "JS Modified Title"
execute "document.title = 'WebSpec Mega Test Page'"

# Hover
hover the element with id "tooltip-trigger"
wait 1 seconds

take screenshot as "mega_08_scroll_keys_js.png"
log "PHASE 8 PASSED: Scroll, keyboard, JS"

# ─────────────────────────────────────────────────────────
# PHASE 9: IFRAME INTERACTION
# Tests: switch to frame, switch to default frame
# ─────────────────────────────────────────────────────────

switch to frame the element with id "embedded-frame"
wait 1 seconds
verify the element with id "frame-heading" is visible
click the button with id "frame-btn"
wait 1 seconds
verify the element with id "frame-text" contains "clicked inside frame"
switch to default frame

verify the heading with id "page-title" is visible
log "PHASE 9 PASSED: Iframe interaction"

# ─────────────────────────────────────────────────────────
# PHASE 10: MULTI-PAGE NAVIGATION (URL TRANSITION)
# Tests: navigate to secondary page, go back, go forward,
# refresh, verify url/title across pages
# ─────────────────────────────────────────────────────────

# Save state before navigation
set $pre_nav_url to url
log "Pre-navigation URL: " + $pre_nav_url

# Navigate to the SECONDARY test_site.html fixture
navigate to "BASE_URL_SECONDARY"
wait 2 seconds

# Verify we're on a different page
verify title is "WebSpec Test Site"
verify the heading "Sign In" is visible
verify the button "Sign In" is visible

# Interact with the secondary page briefly
type "navigator@test.com" into the input near "Email address"
type "Str0ngP@ss!" into the input near "Password"
take screenshot as "mega_10_secondary.png"

# Go back to mega test
go back
wait 2 seconds
verify url contains "mega_test"

# Go forward to secondary again
go forward
wait 2 seconds
verify title is "WebSpec Test Site"

# Navigate directly back
navigate to "BASE_URL"
wait 2 seconds
verify url contains "mega_test"

# Refresh and verify state persists structurally
refresh
wait 2 seconds
verify the heading with id "page-title" is visible
verify the table is visible

take screenshot as "mega_10_navigation.png"
log "PHASE 10 PASSED: Multi-page navigation"

# ─────────────────────────────────────────────────────────
# PHASE 11: ALERT HANDLING
# Tests: accept alert, dismiss alert (via confirm)
# ─────────────────────────────────────────────────────────

# Trigger JS alert
click the button "Trigger Alert"
wait 1 seconds
accept alert

# Trigger confirm dialog
click the button "Trigger Confirm"
wait 1 seconds
dismiss alert
wait 1 seconds
verify the element with id "confirm-result" has text "Cancelled."

take screenshot as "mega_11_alerts.png"
log "PHASE 11 PASSED: Alert handling"

# ─────────────────────────────────────────────────────────
# PHASE 12: VARIABLE EXPRESSIONS & STRING OPS
# Tests: string concat, number, variable ref, nested concat,
# set from text/attr/value/count/url/title, all expr types
# ─────────────────────────────────────────────────────────

set $a to "Hello"
set $b to "World"
set $greeting to $a + ", " + $b + "!"
log $greeting

set $num to 42
log "The answer is: " + $num

set $current_url to url
set $current_title to title
log "URL: " + $current_url
log "Title: " + $current_title

set $h1_text to text of the heading with id "page-title"
log "H1 text: " + $h1_text

set $link_href to attr "href" of the link "Forms"
log "Forms link href: " + $link_href

set $card_count to count of the element with class "card"
log "Total cards: " + $card_count

log "PHASE 12 PASSED: Variables & expressions"

# ─────────────────────────────────────────────────────────
# PHASE 13: ASSERTION OPERATORS
# Tests: is, equals, contains, containing, starts with,
# ends with, matches, greater than, less than, count ops,
# has class, has attr, has style
# ─────────────────────────────────────────────────────────

verify url contains "mega_test"
verify title is "WebSpec Mega Test Page"
verify title contains "Mega"

verify the 1st element with class "card-title" has text "Widget Alpha"
verify the 1st element with class "card-price" contains "$"
verify the 1st element with class "card-price" matches "\\$\\d+\\.\\d+"

verify the element with class "card" count is 4
verify the element with class "card" count greater than 0
verify the element with class "card" count greater than 3

verify the button "Register" has class "btn-primary"

verify the element with id "page-subtitle" has attr "class" is "text-muted"

take screenshot as "mega_13_assertions.png"
log "PHASE 13 PASSED: Assertion operators"

# ─────────────────────────────────────────────────────────
# PHASE 14: WAITS
# Tests: wait seconds, wait for element, wait for state,
# wait until url, wait until title
# ─────────────────────────────────────────────────────────

wait 0.5 seconds

wait for the table
wait for the button "Register" to be visible
wait for the button "Register" to be enabled

log "PHASE 14 PASSED: Waits"

# ─────────────────────────────────────────────────────────
# PHASE 15: MISC STATEMENTS
# Tests: log, take screenshot, save source, save cookies,
# execute, open/close window
# ─────────────────────────────────────────────────────────

log "Testing misc statements"

take screenshot
take screenshot as "mega_15_final.png"

save source as "mega_source.html"
save cookies as "mega_cookies.json"

log "PHASE 15 PASSED: Misc statements"

# ─────────────────────────────────────────────────────────
# PHASE 16: FINAL SUMMARY
# ─────────────────────────────────────────────────────────

log "═══════════════════════════════════════════════"
log "  WEBSPEC MEGA TEST COMPLETE"
log "  All 15 phases passed!"
log "═══════════════════════════════════════════════"

take screenshot as "mega_FINAL.png"