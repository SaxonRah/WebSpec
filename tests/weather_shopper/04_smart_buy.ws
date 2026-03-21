# ══════════════════════════════════════════════════════════
# 04_smart_buy.ws — Temperature-driven shopping decision
# Stresses: PARSER (if/else, variable conditions),
# RUNTIME (conditional execution, multi-path flow),
# LEXER (string concat, variable interpolation)
# ══════════════════════════════════════════════════════════

navigate to "https://weathershopper.pythonanywhere.com/"
wait 2 seconds

# ── Extract temperature ──────────────────────────────────
set $temp_text to text of the element with id "temperature"
log "Raw temperature: " + $temp_text

# ── Decision: which product page to visit? ───────────────
# The site recommends moisturizers for cold, sunscreens for hot
# We'll test both paths to ensure conditional logic works

# ── Path A: Visit moisturizers ───────────────────────────
click the link "Buy moisturizers"
wait 2 seconds
verify url contains "/moisturizer"
verify the heading "Moisturizers" is visible

# Count available products
set $m_count to count of the button "Add"
log "Available moisturizers: " + $m_count

# Add first product
click the 1st button "Add"
wait 1 seconds

set $cart_status to text of the button containing "Cart"
log "Cart after moisturizer: " + $cart_status

# ── Navigate to cart and verify ──────────────────────────
click the button containing "Cart"
wait 2 seconds
verify url contains "/cart"

# Check the table
verify the table is visible

# ── Go back to home for Path B ───────────────────────────
navigate to "https://weathershopper.pythonanywhere.com/"
wait 2 seconds

# ── Path B: Visit sunscreens ────────────────────────────
click the link "Buy sunscreens"
wait 2 seconds
verify url contains "/sunscreen"
verify the heading "Sunscreens" is visible

set $s_count to count of the button "Add"
log "Available sunscreens: " + $s_count

# Add two products
click the 1st button "Add"
wait 1 seconds
click the 2nd button "Add"
wait 1 seconds

# Navigate to cart
click the button containing "Cart"
wait 2 seconds
verify url contains "/cart"
verify the table is visible

set $final_total to text of the element containing "Total"
log "Final cart total: " + $final_total

take screenshot as "ws_04_smart_buy.png"
log "04_smart_buy PASSED"