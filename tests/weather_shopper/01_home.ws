# ══════════════════════════════════════════════════════════
# 01_home.ws — Home page: navigation, variables, assertions
# Stresses: LEXER (all token types), PARSER (nav + verify
# + set + log), RUNTIME (navigate, assert, extract)
# ══════════════════════════════════════════════════════════

navigate to "https://weathershopper.pythonanywhere.com/"

# ── Title and URL ────────────────────────────────────────
verify title is "Current Temperature"
verify url is "https://weathershopper.pythonanywhere.com/"

# ── Capture the live temperature ─────────────────────────
set $temp_text to text of the element with id "temperature"
log "Current temperature text: " + $temp_text

# ── Headings present ─────────────────────────────────────
verify the heading "Moisturizers" is visible
verify the heading "Sunscreens" is visible

# ── Both buy buttons exist ───────────────────────────────
verify the link "Buy moisturizers" is visible
verify the link "Buy sunscreens" is visible

# ── Footer / about link ─────────────────────────────────
verify the link "About" is visible

# ── Navigate to moisturizers page ────────────────────────
click the link "Buy moisturizers"
wait until url contains "/moisturizer"
verify title contains "Moisturizers"
verify url contains "/moisturizer"

# ── Go back and verify home restored ────────────────────
go back
wait until url contains "pythonanywhere.com/"
verify the heading "Moisturizers" is visible

# ── Navigate to sunscreens page ─────────────────────────
click the link "Buy sunscreens"
wait until url contains "/sunscreen"
verify title contains "Sunscreens"

# ── Go back again ───────────────────────────────────────
go back
wait until url contains "pythonanywhere.com/"

# ── Screenshot the home page ────────────────────────────
take screenshot as "ws_01_home.png"
log "01_home PASSED"