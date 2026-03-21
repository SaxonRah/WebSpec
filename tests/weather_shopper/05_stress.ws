# ══════════════════════════════════════════════════════════
# 05_stress.ws — Edge cases and error handling
# Stresses: PARSER (try/catch, repeat, execute),
# RESOLVER (raw xpath, matching regex, with class),
# RUNTIME (JS execution, scrolling, error recovery)
# ══════════════════════════════════════════════════════════

navigate to "https://weathershopper.pythonanywhere.com/"
wait 2 seconds

# ── Test 1: Raw JavaScript execution ────────────────────
execute "document.title = 'WebSpec Stress Test'"
verify title is "WebSpec Stress Test"
execute "document.title = 'Current temperature'"
log "JS execution: PASS"

# ── Test 2: Scroll operations ───────────────────────────
scroll down 300 pixels
wait 1 seconds
scroll up 300 pixels
wait 1 seconds
log "Scroll operations: PASS"

# ── Test 3: Element with regex matching ─────────────────
# Temperature text should match a number pattern
verify the element with id "temperature" matches "\\d+"
log "Regex matching: PASS"

# ── Test 4: Try/catch with intentional failure ──────────
try
    click the button "This Button Does Not Exist"
on error
    log "Expected error caught: " + $_error
end
log "Try/catch: PASS"

# ── Test 5: Repeat with navigation ──────────────────────
repeat 2 times
    navigate to "https://weathershopper.pythonanywhere.com/moisturizer"
    wait 1 seconds
    verify the heading "Moisturizers" is visible
    go back
    wait 1 seconds
end
log "Repeat navigation: PASS"

# ── Test 6: Multiple pages in sequence ──────────────────
navigate to "https://weathershopper.pythonanywhere.com/moisturizer"
wait 2 seconds

# Use raw CSS selector via element keyword
click element "button.btn.btn-primary"
wait 1 seconds
log "Raw CSS selector click: PASS"

# ── Test 7: Screenshot every page ───────────────────────
navigate to "https://weathershopper.pythonanywhere.com/"
wait 1 seconds
take screenshot as "ws_05_stress_home.png"

navigate to "https://weathershopper.pythonanywhere.com/moisturizer"
wait 1 seconds
take screenshot as "ws_05_stress_moisturizers.png"

navigate to "https://weathershopper.pythonanywhere.com/sunscreen"
wait 1 seconds
take screenshot as "ws_05_stress_sunscreens.png"

# ── Test 8: About page ──────────────────────────────────
navigate to "https://weathershopper.pythonanywhere.com/"
wait 1 seconds
click the link "About"
wait 2 seconds
verify url contains "/about"
take screenshot as "ws_05_stress_about.png"

log "05_stress ALL PASSED"